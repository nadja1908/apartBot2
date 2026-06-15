from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
import rental_watch as rw
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / 'tools_output'
OUT.mkdir(exist_ok=True)

TARGETS = [
    'Homey Housing',
    'WoonCompany',
    'BW Housing',
    'Karens Real Estate',
    'Riemersma Real Estate',
    'Expata',
    'Rental Rotterdam Den Haag (max €1500)'
]

for s in rw.SOURCES:
    if s.name not in TARGETS:
        continue
    print('===', s.name)
    logfile = OUT / (s.name.replace(' ', '_') + '_xhr.log')
    lines = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(user_agent=rw.USER_AGENT, locale='en-US', viewport={'width':1366,'height':768})
        page = ctx.new_page()
        def on_request(req):
            if req.resource_type in ('xhr', 'fetch'):
                lines.append(f'REQ {req.method} {req.url}')
        def on_response(resp):
            try:
                if resp.request.resource_type in ('xhr', 'fetch'):
                    url = resp.url
                    ct = resp.headers.get('content-type','')
                    lines.append(f'RESP {resp.status} {url} content-type:{ct} size:{resp.headers.get("content-length","?")}')
                    if 'application/json' in ct:
                        try:
                            txt = resp.text()
                            # store small snippets only
                            lines.append(txt[:2000])
                        except Exception as e:
                            lines.append(f'ERR reading body: {e}')
            except Exception:
                pass
        page.on('request', on_request)
        page.on('response', on_response)
        try:
            page.goto(s.url, wait_until='networkidle', timeout=120000)
            page.wait_for_timeout(4000)
            # scroll to trigger lazy loads
            page.evaluate("() => {window.scrollTo(0, document.body.scrollHeight);} ")
            page.wait_for_timeout(2000)
        except Exception as e:
            lines.append(f'PAGE ERROR: {e}')
        ctx.close()
        browser.close()
    logfile.write_text('\n'.join(lines), encoding='utf-8')
    print('wrote', logfile)
