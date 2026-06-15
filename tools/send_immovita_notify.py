import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rental_watch import SOURCES, listing_hrefs_for_source, load_state, listing_key, notify_telegram, notify_console

s = next((x for x in SOURCES if x.name == 'Immovita'), None)
if not s:
    print('Immovita source not configured')
    raise SystemExit(1)

state = load_state()
prev_keys = set(listing_key(k) for k in state.get('Immovita', []))
found = sorted(listing_hrefs_for_source(s))
new = [u for u in found if listing_key(u) not in prev_keys]

if not new:
    msg = 'Immovita — nema novih oglasa.'
    print(msg)
    notify_telegram(msg)
    raise SystemExit(0)

msg_lines = ['Immovita — NOVI OGLASI:']
for u in new:
    msg_lines.append(u)
msg = '\n'.join(msg_lines)
print('Sending Telegram with {} new URLs'.format(len(new)))
ok = notify_telegram(msg)
print('Sent=', ok)
notify_console('Immovita', new)
