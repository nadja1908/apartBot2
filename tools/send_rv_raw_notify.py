import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from urllib.parse import urlparse
from rental_watch import SOURCES, listing_hrefs_for_source, load_state, notify_telegram, notify_console

s = next((x for x in SOURCES if x.name == 'Rent Valley'), None)
if not s:
    print('Rent Valley source not configured')
    raise SystemExit(1)

state = load_state()
prev = set(state.get('Rent Valley', []))
found = sorted(listing_hrefs_for_source(s))

# compare raw path forms
found_paths = {urlparse(u).path.rstrip('/') for u in found}
prev_paths = {p.rstrip('/') if p.startswith('/') else urlparse(p).path.rstrip('/') for p in prev}
raw_new = [u for u in found if urlparse(u).path.rstrip('/') not in prev_paths]

if not raw_new:
    msg = 'Rent Valley (RAW) — nema novih sirovih URL-ova.'
    print(msg)
    notify_telegram(msg)
    raise SystemExit(0)

msg_lines = ['Rent Valley (RAW) — SIROVI NOVI URL-ovi:']
for u in raw_new:
    msg_lines.append(u)
msg = '\n'.join(msg_lines)
print('Sending Telegram with {} raw-new URLs'.format(len(raw_new)))
ok = notify_telegram(msg)
print('Sent=', ok)
notify_console('Rent Valley (RAW)', raw_new)
