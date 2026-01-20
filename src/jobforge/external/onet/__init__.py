"""O*NET integration package.

Provides NOC-to-SOC crosswalk, O*NET API client, and adapter
for converting O*NET attributes to WiQ schema.
"""

from jobforge.external.onet.crosswalk import NOCSOCCrosswalk

__all__ = [
    "NOCSOCCrosswalk",
]
