"""NOC to O*NET SOC crosswalk loading and lookup.

This module provides the NOCSOCCrosswalk class for mapping Canadian NOC codes
to US O*NET SOC codes using the Brookfield Institute crosswalk data.

The crosswalk handles 1:N cardinality where one NOC may map to multiple SOC codes.
"""

from pathlib import Path
from typing import Any

import polars as pl


class NOCSOCCrosswalk:
    """NOC 2021 to O*NET 26 crosswalk for mapping Canadian to US occupational codes.

    Loads the Brookfield Institute NOC-O*NET crosswalk CSV and provides
    efficient lookup methods for NOC-to-SOC and SOC-to-NOC mappings.

    The crosswalk handles 1:N cardinality where one NOC code may map to
    multiple SOC codes (and vice versa).

    Example:
        >>> cw = NOCSOCCrosswalk("data/crosswalk/noc2021_onet26.csv")
        >>> cw.noc_to_soc("21211")
        ['15-2051.00']
        >>> cw.has_mapping("21211")
        True
    """

    def __init__(self, crosswalk_path: str | Path):
        """Initialize crosswalk from CSV file.

        Args:
            crosswalk_path: Path to the noc2021_onet26.csv file.

        Raises:
            FileNotFoundError: If crosswalk file doesn't exist.
            ValueError: If CSV structure is invalid.
        """
        self._path = Path(crosswalk_path)
        if not self._path.exists():
            raise FileNotFoundError(f"Crosswalk file not found: {self._path}")

        # Load CSV with Polars - cast noc to string to handle leading zeros
        self._df = pl.read_csv(
            self._path,
            schema_overrides={"noc": pl.Utf8, "onet": pl.Utf8},
        )

        # Validate required columns
        required_cols = {"noc", "onet"}
        actual_cols = set(self._df.columns)
        if not required_cols.issubset(actual_cols):
            missing = required_cols - actual_cols
            raise ValueError(f"Crosswalk CSV missing required columns: {missing}")

        # Build lookup indexes for fast access
        self._noc_to_soc_map: dict[str, list[str]] = {}
        self._soc_to_noc_map: dict[str, list[str]] = {}
        self._noc_titles: dict[str, str] = {}
        self._soc_titles: dict[str, str] = {}

        # Group by NOC to build NOC -> SOC mapping
        noc_groups = self._df.group_by("noc").agg(
            pl.col("onet").alias("soc_codes"),
            pl.col("noc_title").first().alias("noc_title"),
        )
        for row in noc_groups.iter_rows(named=True):
            noc = str(row["noc"])
            self._noc_to_soc_map[noc] = row["soc_codes"]
            if row.get("noc_title"):
                self._noc_titles[noc] = row["noc_title"]

        # Group by SOC to build SOC -> NOC mapping
        soc_groups = self._df.group_by("onet").agg(
            pl.col("noc").alias("noc_codes"),
            pl.col("onet_title").first().alias("onet_title"),
        )
        for row in soc_groups.iter_rows(named=True):
            soc = str(row["onet"])
            self._soc_to_noc_map[soc] = row["noc_codes"]
            if row.get("onet_title"):
                self._soc_titles[soc] = row["onet_title"]

    def noc_to_soc(self, noc_code: str) -> list[str]:
        """Get O*NET SOC codes for a NOC code.

        Handles 1:N cardinality - one NOC may map to multiple SOC codes.

        Args:
            noc_code: Canadian NOC code (e.g., "21211").

        Returns:
            List of O*NET SOC codes (e.g., ["15-2051.00"]).
            Empty list if no mapping exists.
        """
        return self._noc_to_soc_map.get(str(noc_code), [])

    def soc_to_noc(self, soc_code: str) -> list[str]:
        """Get NOC codes for an O*NET SOC code.

        Handles N:1 cardinality - one SOC may map to multiple NOC codes.

        Args:
            soc_code: O*NET SOC code (e.g., "15-2051.00").

        Returns:
            List of Canadian NOC codes.
            Empty list if no mapping exists.
        """
        return self._soc_to_noc_map.get(str(soc_code), [])

    def has_mapping(self, noc_code: str) -> bool:
        """Check if a NOC code has O*NET mapping.

        Args:
            noc_code: Canadian NOC code to check.

        Returns:
            True if NOC has at least one SOC mapping.
        """
        return str(noc_code) in self._noc_to_soc_map

    def get_noc_title(self, noc_code: str) -> str | None:
        """Get the title for a NOC code.

        Args:
            noc_code: Canadian NOC code.

        Returns:
            NOC title or None if not found.
        """
        return self._noc_titles.get(str(noc_code))

    def get_soc_title(self, soc_code: str) -> str | None:
        """Get the title for a SOC code.

        Args:
            soc_code: O*NET SOC code.

        Returns:
            SOC title or None if not found.
        """
        return self._soc_titles.get(str(soc_code))

    def coverage_stats(self) -> dict[str, Any]:
        """Get crosswalk coverage statistics.

        Returns:
            Dict with statistics including:
            - total_mappings: Total number of NOC-SOC pairs
            - unique_noc_codes: Number of unique NOC codes
            - unique_soc_codes: Number of unique SOC codes
            - avg_soc_per_noc: Average SOC codes per NOC
            - max_soc_per_noc: Maximum SOC codes for any NOC
            - avg_noc_per_soc: Average NOC codes per SOC
            - max_noc_per_soc: Maximum NOC codes for any SOC
        """
        soc_counts = [len(socs) for socs in self._noc_to_soc_map.values()]
        noc_counts = [len(nocs) for nocs in self._soc_to_noc_map.values()]

        return {
            "total_mappings": len(self._df),
            "unique_noc_codes": len(self._noc_to_soc_map),
            "unique_soc_codes": len(self._soc_to_noc_map),
            "avg_soc_per_noc": sum(soc_counts) / len(soc_counts) if soc_counts else 0,
            "max_soc_per_noc": max(soc_counts) if soc_counts else 0,
            "avg_noc_per_soc": sum(noc_counts) / len(noc_counts) if noc_counts else 0,
            "max_noc_per_soc": max(noc_counts) if noc_counts else 0,
        }

    @property
    def noc_codes(self) -> list[str]:
        """Get all NOC codes in the crosswalk."""
        return list(self._noc_to_soc_map.keys())

    @property
    def soc_codes(self) -> list[str]:
        """Get all SOC codes in the crosswalk."""
        return list(self._soc_to_noc_map.keys())

    def __len__(self) -> int:
        """Get total number of mappings."""
        return len(self._df)

    def __repr__(self) -> str:
        """String representation."""
        return f"NOCSOCCrosswalk(path={self._path}, mappings={len(self)})"
