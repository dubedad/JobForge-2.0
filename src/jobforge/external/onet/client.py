"""O*NET Web Services API client.

This module provides an async HTTP client for the O*NET Web Services API v2,
supporting skills, abilities, and knowledge retrieval for SOC codes.

Authentication uses X-API-Key header (API key from environment or parameter).
Includes retry logic with exponential backoff for rate limit handling.
"""

import os
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# O*NET Web Services API v2 base URL
ONET_BASE_URL = "https://services.onetcenter.org/ws"


class ONetAPIError(Exception):
    """Exception raised for O*NET API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ONetRateLimitError(ONetAPIError):
    """Exception raised when O*NET API rate limit is hit."""

    pass


class ONetClient:
    """O*NET Web Services API v2 client with retry logic.

    Provides async methods for fetching skills, abilities, and knowledge
    for SOC codes. Uses X-API-Key header authentication.

    Args:
        api_key: O*NET API key. If None, reads from ONET_API_KEY env var.
        timeout: HTTP request timeout in seconds.

    Example:
        client = ONetClient()
        if client.is_available():
            skills = await client.get_skills("15-1252.00")
    """

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self._api_key = api_key or os.environ.get("ONET_API_KEY")
        self._timeout = timeout
        self._base_url = ONET_BASE_URL

    def is_available(self) -> bool:
        """Check if API key is configured.

        Returns:
            True if API key is available, False otherwise.
        """
        return bool(self._api_key)

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Basic {self._api_key}"
        return headers

    @retry(
        retry=retry_if_exception_type(ONetRateLimitError),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _request(self, endpoint: str) -> dict[str, Any]:
        """Make authenticated request to O*NET API with retry.

        Args:
            endpoint: API endpoint path (e.g., "/occupations/15-1252.00").

        Returns:
            JSON response as dictionary.

        Raises:
            ONetRateLimitError: If rate limit is hit (triggers retry).
            ONetAPIError: For other API errors.
        """
        url = f"{self._base_url}{endpoint}"
        logger.debug("onet_api_request", url=url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(url, headers=self._get_headers())
            except httpx.TimeoutException as e:
                raise ONetAPIError(f"Request timeout: {e}") from e
            except httpx.RequestError as e:
                raise ONetAPIError(f"Request error: {e}") from e

        if response.status_code == 429:
            logger.warning("onet_rate_limit_hit", endpoint=endpoint)
            raise ONetRateLimitError("O*NET API rate limit exceeded", status_code=429)

        if response.status_code == 401:
            raise ONetAPIError("Invalid or missing API key", status_code=401)

        if response.status_code == 404:
            logger.debug("onet_soc_not_found", endpoint=endpoint)
            return {}

        if response.status_code != 200:
            raise ONetAPIError(
                f"API error: {response.status_code} - {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    async def get_skills(self, soc_code: str) -> list[dict[str, Any]]:
        """Fetch skills for a SOC code.

        Args:
            soc_code: O*NET SOC code (e.g., "15-1252.00").

        Returns:
            List of skill dictionaries from O*NET.
            Empty list if SOC not found or no skills.
        """
        # O*NET API uses occupations/{code}/summary/skills endpoint
        data = await self._request(f"/online/occupations/{soc_code}/summary/skills")
        return data.get("element", []) if data else []

    async def get_abilities(self, soc_code: str) -> list[dict[str, Any]]:
        """Fetch abilities for a SOC code.

        Args:
            soc_code: O*NET SOC code (e.g., "15-1252.00").

        Returns:
            List of ability dictionaries from O*NET.
            Empty list if SOC not found or no abilities.
        """
        data = await self._request(f"/online/occupations/{soc_code}/summary/abilities")
        return data.get("element", []) if data else []

    async def get_knowledge(self, soc_code: str) -> list[dict[str, Any]]:
        """Fetch knowledge areas for a SOC code.

        Args:
            soc_code: O*NET SOC code (e.g., "15-1252.00").

        Returns:
            List of knowledge dictionaries from O*NET.
            Empty list if SOC not found or no knowledge.
        """
        data = await self._request(f"/online/occupations/{soc_code}/summary/knowledge")
        return data.get("element", []) if data else []

    async def get_all_attributes(self, soc_code: str) -> dict[str, list[dict[str, Any]]]:
        """Fetch all attribute types for a SOC code.

        Fetches skills, abilities, and knowledge in parallel.

        Args:
            soc_code: O*NET SOC code (e.g., "15-1252.00").

        Returns:
            Dictionary with 'skills', 'abilities', 'knowledge' keys.
        """
        import asyncio

        skills, abilities, knowledge = await asyncio.gather(
            self.get_skills(soc_code),
            self.get_abilities(soc_code),
            self.get_knowledge(soc_code),
        )

        return {
            "skills": skills,
            "abilities": abilities,
            "knowledge": knowledge,
        }

    async def get_occupation_summary(self, soc_code: str) -> dict[str, Any]:
        """Fetch occupation summary information.

        Args:
            soc_code: O*NET SOC code (e.g., "15-1252.00").

        Returns:
            Occupation summary dictionary from O*NET.
            Empty dict if SOC not found.
        """
        return await self._request(f"/online/occupations/{soc_code}")
