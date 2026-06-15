import sys
from pathlib import Path

# Ensure repo root is importable
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

import rental_watch as rw

PROBLEMATIC = {
    "Immovita",
    "Homey Housing",
    "Frisiamakelaars",
    "Karens Real Estate",
    "WoonCompany",
    "BW Housing",
    "Riemersma Real Estate",
    "Expata",
}

for s in rw.SOURCES:
    try:
        hrefs = rw.listing_hrefs_for_source(s)
    except Exception as e:
        print(f"{s.name}: ERROR: {e}")
        continue
    if s.name in PROBLEMATIC:
        sample = list(sorted(hrefs))[:10]
        print(f"{s.name}: {len(hrefs)} found. Sample: {sample}")
    else:
        print(f"{s.name}: {len(hrefs)} found")
