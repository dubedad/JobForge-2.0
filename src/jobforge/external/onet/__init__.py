"""O*NET integration package.

Provides NOC-to-SOC crosswalk, O*NET API client, and adapter
for converting O*NET attributes to WiQ schema.
"""

from jobforge.external.onet.adapter import ONetAdapter, get_attributes_for_noc
from jobforge.external.onet.client import ONetClient
from jobforge.external.onet.crosswalk import NOCSOCCrosswalk

__all__ = [
    "NOCSOCCrosswalk",
    "ONetClient",
    "ONetAdapter",
    "get_attributes_for_noc",
]
