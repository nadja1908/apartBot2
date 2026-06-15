import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rental_watch import SOURCES, listing_hrefs_for_source, load_state, listing_key
state = load_state()
for s in SOURCES:
    name = s.name
    try:
        found = sorted(listing_hrefs_for_source(s))
    except Exception as e:
        print(f"=== {name} === ERROR fetching: {e}")
        continue
    prev = state.get(name, [])
    raw_new = [u for u in found if u not in prev]
    found_keys = [listing_key(u) for u in found]
    prev_keys = [listing_key(u) for u in prev]
    norm_new = [u for u,k in zip(found, found_keys) if k not in prev_keys]
    print(f"=== {name} === found={len(found)} prev={len(prev)} raw_new={len(raw_new)} norm_new={len(norm_new)}")
    if raw_new:
        print("  Raw-only (found not in prev):")
        for u in raw_new[:10]:
            print('   ', u)
    if norm_new:
        print("  Norm-only (normalized key not in prev_keys):")
        for u in norm_new[:10]:
            print('   ', u)
    print()
