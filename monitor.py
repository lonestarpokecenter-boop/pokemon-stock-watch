import json, os, re, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
PRODUCTS = json.loads((ROOT/'products.json').read_text())
OUT = ROOT/'docs'/'status.json'
OUT.parent.mkdir(exist_ok=True)
previous = json.loads(OUT.read_text()) if OUT.exists() else {'products': []}
old = {p['url']: p for p in previous.get('products', [])}
now = datetime.now(timezone.utc).isoformat(timespec='seconds')
results=[]

def notify(name, url):
    topic = os.getenv('NTFY_TOPIC', '').strip()
    if not topic: return
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', topic):
        print('Invalid NTFY_TOPIC; skipping notification'); return
    req=urllib.request.Request('https://ntfy.sh/'+topic, data=f'{name} may be in stock: {url}'.encode(), headers={'Title':'Pokemon stock alert','Tags':'tada','Click':url}, method='POST')
    try: urllib.request.urlopen(req,timeout=15).read()
    except Exception as e: print('Notification failed:',e)

for p in PRODUCTS:
    name, url = p['name'], p['url']
    status='unknown'
    if not url.startswith('https://www.pokemoncenter.com/'):
        print('Skipping non-Pokemon Center URL:', url)
    else:
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'PokemonStockWatch/1.0 (personal stock checker)','Accept':'text/html'})
            with urllib.request.urlopen(req,timeout=20) as response:
                html=response.read(500_000).decode('utf-8','replace').lower()
                print(
    name,
    'HTTP:', response.status,
    'Page title:',
    re.search(r'<title[^>]*>(.*?)</title>', html, re.S).group(1).strip()[:120]
    if re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
    else 'No title',
    'HTML bytes:', len(html)
)

            # Conservative: only flag in-stock on explicit machine-readable availability.
            if re.search(r'"availability"\s*:\s*"https?://schema\.org/instock"',html):
                status='in_stock'
            elif re.search(r'"availability"\s*:\s*"https?://schema\.org/outofstock"',html):
                status='out_of_stock'
            else:
                status='unknown'
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as e:
            print(name,'not accessible:',e)
        if status=='in_stock' and old.get(url,{}).get('status') != 'in_stock':
            notify(name,url)
    results.append({'name':name,'url':url,'status':status,'checked_at':now})
    time.sleep(2)
OUT.write_text(json.dumps({'updated_at':now,'products':results},indent=2)+'\n')
print(json.dumps(results,indent=2))
