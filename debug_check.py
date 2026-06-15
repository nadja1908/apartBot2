from rental_watch import SOURCES, listing_hrefs_for_source, load_last_state, listing_key, _is_blocked_source

last = load_last_state()

for src in SOURCES:
    try:
        blocked = _is_blocked_source(src)
    except Exception:
        blocked = False
    print(f"=== {src.name} === blocked={blocked}")
    try:
        hrefs = listing_hrefs_for_source(src)
    except Exception as e:
        print(" ERROR:", e)
        print()
        continue
    hrefs_sorted = sorted(hrefs)
    keys = [listing_key(h) for h in hrefs_sorted]
    prev = set(last.get(src.name, []))
    new = [h for h,k in zip(hrefs_sorted, keys) if k not in prev]
    print(f" found={len(hrefs_sorted)} prev={len(prev)} new={len(new)}")
    if new:
        for h in new[:50]:
            print("  NEW:", h)
    print()
