import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rental_watch import fetch_playwright_html
from bs4 import BeautifulSoup

url='https://www.pararius.com/apartments/den-haag'
print('Fetching', url)
html = fetch_playwright_html(url)
soup = BeautifulSoup(html, 'html.parser')
hs = set()
for a in soup.find_all('a', href=True):
    h = a['href']
    if '/apartment' in h or '/apartments' in h or 'listing' in h:
        hs.add(h)

print('Found', len(hs), 'candidates')
for h in sorted(hs):
    print(h)
