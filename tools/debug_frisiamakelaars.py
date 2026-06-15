import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rental_watch import SOURCES, extract_listing_hrefs, _scan_html_for_urls, listing_key

src = next((s for s in SOURCES if s.name == 'Frisiamakelaars'), None)
if not src:
    print('Frisiamakelaars source not found')
    raise SystemExit(1)

print('URL:', src.url)
try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print('Playwright not installed or failed to import:', e)
    raise SystemExit(1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    ctx = browser.new_context(user_agent='Mozilla/5.0', locale='en-US')
    page = ctx.new_page()
    try:
        print('Navigating with timeout 300s...')
        page.goto(src.url, wait_until='networkidle', timeout=300_000)
        page.wait_for_timeout(3000)
        html = page.content()
        print('Loaded, content length:', len(html))
        hrefs = extract_listing_hrefs(src.url, html, src)
        try:
            hrefs |= _scan_html_for_urls(src.url, html, src)
        except Exception:
            pass
        print('Found links count:', len(hrefs))
        for h in sorted(hrefs):
            print(' ', h)
        print('\nNormalized keys:')
        for h in sorted(hrefs):
            print(' ', listing_key(h))
    except Exception as e:
        print('Error during navigation:', e)
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        browser.close()
