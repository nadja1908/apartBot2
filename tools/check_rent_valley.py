import sys, os
# Ensure project root is on PYTHONPATH so imports work when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rental_watch import SOURCES, listing_hrefs_for_source, load_state, listing_key
s = next((x for x in SOURCES if x.name=='Rent Valley'), None)
if not s:
    print('Rent Valley source not found')
    raise SystemExit(1)
print('Source URL:', s.url)
cur = sorted(listing_hrefs_for_source(s))
print('\nCurrent found ({}):'.format(len(cur)))
for u in cur:
    print('  ', u)

state = load_state()
prev = state.get('Rent Valley', [])
print('\nState.json entries ({}):'.format(len(prev)))
for p in prev:
    print('  ', p)

# Show normalized keys for current and prev
cur_keys = [listing_key(u) for u in cur]
prev_keys = [listing_key(p) for p in prev]
print('\nNormalized current keys:')
for k in cur_keys:
    print('  ', k)
print('\nNormalized prev keys:')
for k in prev_keys:
    print('  ', k)

# Show any urls present in current but not in prev
missing = [u for u,k in zip(cur,cur_keys) if k not in prev_keys]
print('\nNew (by key) count:', len(missing))
for u in missing:
    print('  NEW:', u)
