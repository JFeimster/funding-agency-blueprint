#!/usr/bin/env python3
"""Recover existing public brand icons, anonymous application screenshots and named GPT avatars.
No login, form submission, private images, invented product artwork or paid generation."""
import asyncio, hashlib, io, json, re
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from PIL import Image
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'assets/images/resources/phase-7a'
DIR.mkdir(parents=True,exist_ok=True)
MAP=ROOT/'data/resource-visuals.json'
visuals=json.loads(MAP.read_text())
candidates=json.loads((ROOT/'data/visual-recovery-candidates.json').read_text())
results={}
gate=re.compile(r'verify (?:that )?you are human|checking your browser|just a moment|deployment not found|application error|access denied|this site can.t be reached|404: not found|sign in to continue|password protected',re.I)
def host(u):
    return (urlsplit(u).hostname or '').lower().removeprefix('www.')
def save(row,raw,role,source):
    if len(raw)>8_000_000:return False
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        if min(im.size)<(32 if role=='brand-icon' else 96):return False
        if role=='avatar' and not .75<im.width/im.height<1.35:return False
        im=im.convert('RGBA' if im.mode=='RGBA' else 'RGB')
        im.thumbnail((960,640) if role=='screenshot' else (384,384))
        f=io.BytesIO();im.save(f,'WEBP',quality=82,method=5);data=f.getvalue()
    digest=hashlib.sha256(data).hexdigest()
    dest=DIR/(row['id']+'.webp')
    for p in sorted(DIR.glob('*.webp')):
        if hashlib.sha256(p.read_bytes()).hexdigest()==digest:dest=p;break
    if role=='avatar' and any(v.get('image_url')=='/'+dest.relative_to(ROOT).as_posix() for v in visuals.values()):return False
    dest.write_bytes(data)
    visuals[row['id']]={'image_url':'/'+dest.relative_to(ROOT).as_posix(),'image_role':role,'provenance':source}
    return True
async def run():
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        sem=asyncio.Semaphore(5)
        async def visit(row,kind):
            async with sem:
                if row['id'] in visuals:return
                ctx=await browser.new_context(viewport={'width':1280,'height':800},device_scale_factor=1,accept_downloads=False)
                page=await ctx.new_page()
                try:
                    # Anonymous top-level public page only; reject cross-site navigation.
                    resp=await page.goto(row['url'],wait_until='domcontentloaded',timeout=18000)
                    if not resp or not resp.ok or host(page.url)!=host(row['url']):raise ValueError('non-matching public destination')
                    await page.wait_for_timeout(900)
                    title=await page.title()
                    body=(await page.locator('body').inner_text(timeout=5000))[:12000]
                    if gate.search(title+' '+body[:1000]) or len(body.strip())<80:raise ValueError('gate, error or empty page')
                    if kind=='applications':
                        if await page.locator('input[type=password]').count():raise ValueError('authentication page')
                        if re.search(r'\b(?:sign in|log in)\b',title,re.I):raise ValueError('authentication page')
                        raw=await page.screenshot(type='png',animations='disabled',full_page=False,timeout=10000)
                        ok=save(row,raw,'screenshot','Anonymous public landing-page screenshot from '+row['url']+'; no functionality claim.')
                    elif kind=='partners':
                        # Favicon from the partner's own page, not a purported official wordmark.
                        urls=await page.locator('link[rel~="icon"],link[rel="apple-touch-icon"]').evaluate_all("(els)=>els.map(e=>e.href)")
                        ok=False
                        for u in urls[:8]+[urljoin(page.url,'/favicon.ico')]:
                            if urlsplit(u).scheme!='https' or host(u)!=host(page.url):continue
                            try:
                                rr=await ctx.request.get(u,timeout=5000,max_redirects=0)
                                if rr.ok and save(row,await rr.body(),'brand-icon','Public site icon supplied by '+host(page.url)+'.'):ok=True;break
                            except Exception:continue
                    else:
                        name=re.sub(r'[^a-z0-9]','',row['title'].lower())
                        if name not in re.sub(r'[^a-z0-9]','',title.lower()):raise ValueError('GPT title mismatch')
                        meta=page.locator('meta[property="og:image"]')
                        if not await meta.count():raise ValueError('no specific avatar')
                        u=await meta.first.get_attribute('content')
                        h=host(u or '')
                        if not (h.endswith('.oaiusercontent.com') or h.endswith('.oaistatic.com') or h.endswith('.openai.com')):raise ValueError('unverified image host')
                        if re.search(r'default|logo|chatgpt-share|share-card|opengraph|og-image',u,re.I):raise ValueError('generic share artwork')
                        rr=await ctx.request.get(u,timeout=8000,max_redirects=0)
                        ok=rr.ok and save(row,await rr.body(),'avatar','Named public GPT page metadata; avatar image only, access not independently confirmed.')
                    results[row['id']]='recovered' if ok else 'no suitable visual'
                except Exception as e:results[row['id']]='withheld: '+str(e).splitlines()[0][:150]
                finally:await ctx.close()
        await asyncio.gather(*(visit(r,k) for k,rows in candidates.items() for r in rows))
        await browser.close()
asyncio.run(run())
MAP.write_text(json.dumps(visuals,indent=2,sort_keys=True)+'\n')
print(json.dumps({'visuals':len(visuals),'roles':{role:sum(v['image_role']==role for v in visuals.values()) for role in sorted({v['image_role'] for v in visuals.values()})},'recovery':results},indent=2))
