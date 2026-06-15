import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rental_watch as rw

for src in rw.SOURCES:
    if src.name.lower().startswith("immovita"):
        print('Checking source:', src.name, src.url)
        try:
            hrefs = rw.listing_hrefs_for_source(src)
        except Exception as e:
            print('Error fetching:', e)
            raise
        print('Found', len(hrefs), 'listings:')
        for h in sorted(hrefs):
            print(h)
        break
else:
    print('Immovita source not configured in SOURCES')
