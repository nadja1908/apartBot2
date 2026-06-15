from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
import rental_watch as rw

names = [
    'Karens Real Estate',
    'WoonCompany',
    'Homey Housing',
    'BW Housing',
]

for s in rw.SOURCES:
    if s.name in names:
        try:
            hrefs = rw.listing_hrefs_for_source(s)
            print(s.name, len(hrefs))
            for h in list(sorted(hrefs))[:20]:
                print('  ', h)
        except Exception as e:
            print(s.name, 'ERROR', e)
