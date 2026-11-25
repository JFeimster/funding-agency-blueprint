#!/usr/bin/env python3
"""Public link inventory; no forms, downloads with signed tokens, or external mutations."""
import concurrent.futures, datetime, html, ipaddress, json, re, socket
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin, parse_qsl
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from collections import Counter
root=Path(__file__).resolve().parents[1]
private={'app.notion.com','notion.so','www.notion.so','drive.google.com','docs.google.com'}
sensitive=re.compile(r'(?:token|signature|credential|password|authorization|secret|^x-amz-|api.?key|^key$|^code$|session)',re.I)
action=re.compile(r'/(?:api|unsubscribe|logout|signout|sign-out|checkout|purchase|delete|remove|revoke|confirm|subscribe|newsletter-follow|copy)(?:/|$)',re.I)
media=re.compile(r'\.(?:png|jpe?g|webp|gif|svg|ico|css|js|woff2?|ttf|mp4|wav)$',re.I)
links=set()
skipped=Counter()
def classify(u):
    try: p=urlsplit(u)
    except ValueError:return 'invalid_or_unsafe'
    if p.scheme!='https' or not p.hostname or p.username or p.password:return 'invalid_or_unsafe'
    if p.hostname in private or p.hostname.endswith('.notion.site'):return 'permission_review'
    if any(sensitive.search(k) for k,v in parse_qsl(p.query,keep_blank_values=True)):return 'sensitive_omitted'
    if action.search(p.path):return 'action_not_probed'
    if media.search(p.path):return 'media_not_probed'
    return None
def add(u):
    if not isinstance(u,str) or not u.startswith('https://'):return
    u=html.unescape(u).strip()
    try: p=urlsplit(u)
    except ValueError:return
    if p.hostname=='funding-agency-blueprint.vercel.app':return
    c=classify(u)
    if c in ('permission_review','sensitive_omitted','invalid_or_unsafe'):
        skipped[c]+=1;return
    links.add(u)
class Parser(HTMLParser):
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            for k,v in attrs:
                if k=='href':add(v)
def walk(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in ('url','link','affiliate_url','download_url','website','repository_url'):add(v)
            elif isinstance(v,(list,dict)):walk(v)
    elif isinstance(x,list):
        for v in x:walk(v)
for name in ('data/resource-ecosystem.json','data/editions.json','data/blueprint-public.json','registry/public-release.json'):
    walk(json.loads((root/name).read_text()))
for p in root.rglob('*.html'):
    rel=p.relative_to(root)
    if set(rel.parts)&{'.git','node_modules','.next','dist','build','private','staging'}:continue
    Parser().feed(p.read_text(errors='replace'))
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
opener=build_opener(NoRedirect())
def check(u):
    c=classify(u)
    if c:return c
    current=u
    for _ in range(5):
        try:
            p=urlsplit(current)
            c=classify(current)
            if c:return c
            if p.port not in (None,443):return 'invalid_or_unsafe'
            addr=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
            if not addr or any(not ipaddress.ip_address(a[4][0]).is_global for a in addr):return 'invalid_or_unsafe'
            req=Request(current,headers={'User-Agent':'Mozilla/5.0 (compatible; BlueprintLinkAudit/1.0)','Accept':'text/html,application/pdf,*/*;q=0.5'})
            try:
                with opener.open(req,timeout=8) as res:
                    sample=res.read(16384) if 'html' in res.headers.get('Content-Type','').lower() else b''
                    host=p.hostname or ''
                    if host.endswith(('youtube.com','youtu.be','linkedin.com','chatgpt.com')):return 'platform_access_unconfirmed'
                    if re.search(rb'captcha|verify (?:that )?you are human|just a moment|deployment not found|access denied|sign in to continue',sample,re.I):return 'possible_gate_or_soft_error'
                    return 'redirect_reachable' if current!=u else 'http_reachable'
            except HTTPError as e:
                if e.code in (301,302,303,307,308) and e.headers.get('Location'):
                    current=urljoin(current,e.headers['Location']);continue
                if e.code in (404,410):return 'http_not_found'
                if e.code in (401,403,429):return 'access_or_rate_limit'
                return 'http_error'
        except Exception:return 'unconfirmed'
    return 'redirect_unconfirmed'
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    status=dict(zip(sorted(links),pool.map(check,sorted(links))))
report={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unique_public_urls':len(status),'counts':dict(Counter(status.values())),'excluded_occurrences':dict(skipped),'statuses':status,'limit':'HTTP reachability does not verify functionality, permissions, playback, enrollment, or referral attribution. Not-found links are withheld in generated current resource actions; original article text is retained.'}
(root/'data/public-link-evidence.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='statuses'}))
