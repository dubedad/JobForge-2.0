"""NOC-OG concordance matching module.

Provides mapping between NOC codes and TBS Occupational Groups.
"""

from jobforge.concordance.noc_og import (
    NOCOGMatch,
    match_noc_to_og,
    build_bridge_noc_og,
)

__all__ = [
    "NOCOGMatch",
    "match_noc_to_og",
    "build_bridge_noc_og",
]
