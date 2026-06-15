from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
import rental_watch as rw

name = 'Karens Real Estate'
src = next(s for s in rw.SOURCES if s.name==name)
html = None
try:
    html = rw.fetch_playwright_html(src.url)
    print('fetched playwright')
except Exception as e:
    print('playwright failed', e)
    try:
        html = rw.fetch_html(src.url)
        print('fetched http')
    except Exception as e2:
        print('http failed', e2)

if html:
    print('has rts/collections?', 'rts/collections' in html)
    rel = rw._find_rts_query_url(html)
    print('rel=', rel)
    urls = rw.fetch_rts_collection_urls(src)
    print('urls count=', len(urls))
    for u in list(sorted(urls))[:20]:
        print(' ', u)
