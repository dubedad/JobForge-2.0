"""O*NET to WiQ schema adapter.

This module provides the ONetAdapter class for converting O*NET API responses
to WiQ schema with provenance tracking, and handles NOC-to-SOC crosswalk
lookups for 1:N mapping cardinality.
"""

from datetime import datetime, timezone
from typing import Any

import structlog

from jobforge.external.models import ONetAttribute, ONetAttributeSet
from jobforge.external.onet.client import ONetClient
from jobforge.external.onet.crosswalk import NOCSOCCrosswalk

logger = structlog.get_logger(__name__)

# O*NET confidence score per CONTEXT.md: lower than authoritative
ONET_CONFIDENCE = 0.5


class ONetAdapter:
    """Adapter converting O*NET API responses to WiQ schema.

    Handles NOC-to-SOC crosswalk lookup and converts O*NET attributes
    to ONetAttribute models with full provenance tracking.

    Args:
        client: ONetClient instance for API calls.
        crosswalk: NOCSOCCrosswalk instance for NOC-SOC mapping.

    Example:
        client = ONetClient()
        crosswalk = NOCSOCCrosswalk("data/crosswalk/noc2021_onet26.csv")
        adapter = ONetAdapter(client, crosswalk)

        attributes = await adapter.get_attributes_for_noc("21211")
    """

    def __init__(self, client: ONetClient, crosswalk: NOCSOCCrosswalk):
        self.client = client
        self.crosswalk = crosswalk

    def _convert_element(
        self,
        element: dict[str, Any],
        attribute_type: str,
        soc_code: str,
        noc_code: str,
        fetched_at: datetime,
    ) -> ONetAttribute:
        """Convert a single O*NET element to ONetAttribute.

        Args:
            element: Raw O*NET element dictionary.
            attribute_type: Type of attribute (skill, ability, knowledge).
            soc_code: Source SOC code.
            noc_code: Source NOC code (via crosswalk).
            fetched_at: Timestamp when fetched.

        Returns:
            ONetAttribute with full provenance.
        """
        # O*NET uses 'id' for element identifier
        element_id = element.get("id", "")

        # O*NET uses 'name' for display name
        name = element.get("name", "Unknown")

        # O*NET uses 'description' for detailed description
        description = element.get("description", "")

        # O*NET scores are on a scale object with 'value' key
        # Some endpoints return 'score' directly
        score_obj = element.get("score", {})
        if isinstance(score_obj, dict):
            importance_score = score_obj.get("value", 0.0)
        else:
            importance_score = float(score_obj) if score_obj else 0.0

        # Level score may be in a separate 'level' object
        level_obj = element.get("level", {})
        if isinstance(level_obj, dict):
            level_score = level_obj.get("value")
        else:
            level_score = float(level_obj) if level_obj else None

        return ONetAttribute(
            element_id=element_id,
            name=name,
            description=description,
            importance_score=importance_score,
            level_score=level_score,
            source_soc=soc_code,
            source_noc=noc_code,
            confidence=ONET_CONFIDENCE,
            fetched_at=fetched_at,
        )

    async def get_attributes_for_soc(
        self,
        soc_code: str,
        noc_code: str,
        attribute_types: list[str] | None = None,
    ) -> ONetAttributeSet:
        """Fetch and convert O*NET attributes for a SOC code.

        Args:
            soc_code: O*NET SOC code.
            noc_code: Canadian NOC code (for provenance).
            attribute_types: List of types to fetch: "skills", "abilities", "knowledge".
                            If None, fetches all types.

        Returns:
            ONetAttributeSet with converted attributes.
        """
        types = attribute_types or ["skills", "abilities", "knowledge"]
        fetched_at = datetime.now(timezone.utc)

        skills: list[ONetAttribute] = []
        abilities: list[ONetAttribute] = []
        knowledge: list[ONetAttribute] = []

        # Fetch occupation title
        summary = await self.client.get_occupation_summary(soc_code)
        soc_title = summary.get("title", "") if summary else ""

        if "skills" in types:
            raw_skills = await self.client.get_skills(soc_code)
            skills = [
                self._convert_element(e, "skill", soc_code, noc_code, fetched_at)
                for e in raw_skills
            ]

        if "abilities" in types:
            raw_abilities = await self.client.get_abilities(soc_code)
            abilities = [
                self._convert_element(e, "ability", soc_code, noc_code, fetched_at)
                for e in raw_abilities
            ]

        if "knowledge" in types:
            raw_knowledge = await self.client.get_knowledge(soc_code)
            knowledge = [
                self._convert_element(e, "knowledge", soc_code, noc_code, fetched_at)
                for e in raw_knowledge
            ]

        return ONetAttributeSet(
            soc_code=soc_code,
            soc_title=soc_title,
            skills=skills,
            abilities=abilities,
            knowledge=knowledge,
            fetched_at=fetched_at,
        )

    async def get_attributes_for_noc(
        self,
        noc_code: str,
        attribute_types: list[str] | None = None,
    ) -> list[ONetAttribute]:
        """Fetch O*NET attributes for a NOC code via crosswalk.

        Handles 1:N cardinality where one NOC maps to multiple SOC codes.
        Aggregates attributes from all mapped SOC codes.

        Args:
            noc_code: Canadian NOC code.
            attribute_types: List of types to fetch: "skills", "abilities", "knowledge".
                            If None, fetches all types.

        Returns:
            List of ONetAttribute from all mapped SOC codes.
            Empty list if no mapping exists or API unavailable.
        """
        if not self.client.is_available():
            logger.warning("onet_client_not_available", noc_code=noc_code)
            return []

        soc_codes = self.crosswalk.noc_to_soc(noc_code)
        if not soc_codes:
            logger.debug("no_soc_mapping_for_noc", noc_code=noc_code)
            return []

        logger.info(
            "fetching_onet_attributes",
            noc_code=noc_code,
            soc_codes=soc_codes,
            soc_count=len(soc_codes),
        )

        all_attributes: list[ONetAttribute] = []

        for soc_code in soc_codes:
            try:
                attr_set = await self.get_attributes_for_soc(
                    soc_code, noc_code, attribute_types
                )
                all_attributes.extend(attr_set.all_attributes)
                logger.debug(
                    "fetched_soc_attributes",
                    soc_code=soc_code,
                    count=attr_set.attribute_count,
                )
            except Exception as e:
                logger.error(
                    "onet_fetch_error",
                    soc_code=soc_code,
                    noc_code=noc_code,
                    error=str(e),
                )
                # Continue with other SOC codes

        logger.info(
            "fetched_onet_attributes_complete",
            noc_code=noc_code,
            total_attributes=len(all_attributes),
        )

        return all_attributes


async def get_attributes_for_noc(
    noc_code: str,
    attribute_types: list[str] | None = None,
    crosswalk_path: str = "data/crosswalk/noc2021_onet26.csv",
    api_key: str | None = None,
) -> list[ONetAttribute]:
    """Convenience function to get O*NET attributes for a NOC code.

    Creates client and adapter instances, then fetches attributes.
    For bulk operations, create ONetAdapter directly to reuse instances.

    Args:
        noc_code: Canadian NOC code.
        attribute_types: List of types to fetch: "skills", "abilities", "knowledge".
                        If None, fetches all types.
        crosswalk_path: Path to the NOC-SOC crosswalk CSV.
        api_key: O*NET API key. If None, reads from ONET_API_KEY env var.

    Returns:
        List of ONetAttribute from all mapped SOC codes.
        Empty list if no mapping exists or API unavailable.

    Example:
        attributes = await get_attributes_for_noc("21211")
        for attr in attributes:
            print(f"{attr.name}: {attr.importance_score}")
    """
    client = ONetClient(api_key=api_key)
    crosswalk = NOCSOCCrosswalk(crosswalk_path)
    adapter = ONetAdapter(client, crosswalk)

    return await adapter.get_attributes_for_noc(noc_code, attribute_types)
