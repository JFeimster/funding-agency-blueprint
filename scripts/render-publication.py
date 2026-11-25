"""Incrementally publish confirmed local exports into the static website."""
import argparse
import hashlib
import html
import json
import pathlib
import re
import shutil
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOST = 'https://funding-agency-blueprint.vercel.app'
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
PUBLIC_FIELDS = {'id', 'slug', 'edition_number', 'title', 'status', 'publication_date', 'series', 'topic', 'description', 'seo_title', 'seo_description', 'link', 'reading_minutes', 'source_sha256', 'eyebrow', 'related'}
parser = argparse.ArgumentParser()
parser.add_argument('--export', required=True, type=pathlib.Path)
parser.add_argument('--artwork', action='append', default=[], metavar='SLUG=FILE')
parser.add_argument('--check', action='store_true', help='Validate public export and existing website identities without writing')
args = parser.parse_args()
source = args.export.resolve()
if not (ROOT / 'scripts/generate-public-registry.mjs').is_file():
    raise SystemExit('Not the existing website repository')

def esc(value):
    return html.escape(str(value or ''), quote=True)

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding='utf-8') != value:
        path.write_text(value, encoding='utf-8', newline='\n')

def replace_block(text, key, body):
    pattern = rf'<!-- {key}:begin -->[\s\S]*?<!-- {key}:end -->'
    if not re.search(pattern, text):
        raise ValueError(f'Missing {key} marker')
    return re.sub(pattern, lambda _: f'<!-- {key}:begin -->{body}<!-- {key}:end -->', text, count=1)

def cover(row, prefix):
    if row.get('cover'):
        name = row['cover']
        if not re.fullmatch(r'[a-z0-9][a-z0-9._-]+\.(?:png|jpe?g|webp)', name):
            raise ValueError('Unsafe cover filename')
        if not (ROOT / 'assets/images/editions' / name).is_file():
            raise ValueError('Missing cover ' + name)
        return f'<img class="edition-cover" src="{prefix}assets/images/editions/{esc(name)}" alt="Featured artwork for {esc(row["title"])}" loading="lazy" decoding="async">'
    return f'<div class="edition-cover edition-placeholder" aria-label="Edition {row["edition_number"]} artwork unavailable"><span>FAB.</span><strong>{row["edition_number"]:02d}</strong><span>{esc(row["topic"])}</span></div>'

def card(row, prefix):
    url = f'{prefix}editions/{row["slug"]}/'
    return f'<article class="tile edition-card" data-record data-category="{esc(row["topic"])}"><a href="{url}">{cover(row,prefix)}</a><span class="tile-kicker">{esc(row["eyebrow"])} · {row["reading_minutes"]} MIN</span><h3><a href="{url}">{esc(row["title"])}</a></h3><p>{esc(row["description"])}</p><a href="{url}">READ EDITION ↗</a></article>'

def safe_url(url):
    p = urlparse(url)
    return p.scheme in ('https', 'http') and bool(p.netloc) and not re.search(r'[\x00-\x1f"<>]', url)

def inline(text):
    link = re.compile(r'(!?)\[([^\]]*)\]\(([^)]+)\)')
    def styled(fragment):
        value = esc(fragment)
        value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
        value = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', value)
        value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
        return value
    out, pos = [], 0
    for match in link.finditer(text):
        out.append(styled(text[pos:match.start()]))
        bang, label, url = match.groups()
        if safe_url(url):
            out.append(f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(label) if not bang else "View original article illustration ↗"}</a>')
        else:
            out.append(styled(match.group()))
        pos = match.end()
    out.append(styled(text[pos:]))
    return ''.join(out)

def markdown_body(raw):
    text = raw.decode('utf-8-sig')
    text = re.sub(r'\A# [^\n]+\n\s*Author: [^\n]+\nPublished: [^\n]+\nSource: [^\n]+\nCaptured: [^\n]+\n', '', text)
    text = re.sub(r'<!--[^>]*-->', '', text)
    lines = text.splitlines()
    out, paragraph, items, code = [], [], [], []
    in_code = False
    def flush():
        if paragraph:
            out.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
        if items:
            out.append('<ul>' + ''.join('<li>' + inline(x) + '</li>' for x in items) + '</ul>')
            items.clear()
    for line in lines:
        if line.startswith('```'):
            flush()
            if in_code:
                out.append('<pre><code>' + esc('\n'.join(code)) + '</code></pre>')
                code.clear()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        line = line.strip()
        if not line:
            flush()
        elif re.fullmatch(r'(?:---+|\*\*\*+)', line):
            flush(); out.append('<hr>')
        elif line.startswith(('- ', '* ')):
            if paragraph: flush()
            items.append(line[2:])
        elif re.match(r'^#{1,6} ', line):
            flush(); level = min(len(line) - len(line.lstrip('#')) + 1, 6)
            out.append(f'<h{level}>' + inline(line.lstrip('#').strip()) + f'</h{level}>')
        elif line.startswith('> '):
            flush(); out.append('<blockquote><p>' + inline(line[2:]) + '</p></blockquote>')
        else:
            if items: flush()
            paragraph.append(line)
    flush()
    if in_code:
        out.append('<pre><code>' + esc('\n'.join(code)) + '</code></pre>')
    return '\n'.join(out)

def related_nav(row, published):
    near = [x for x in published if x['slug'] != row['slug'] and ((row.get('series') and x.get('series') == row['series']) or x.get('topic') == row.get('topic'))][:3]
    if not near:
        near = [x for x in published if x['slug'] != row['slug']][:2]
    related = '<section class="content-section"><h2>Related editions.</h2><div class="grid thirds">' + ''.join(card(x, '../../') for x in near) + '</div></section>'
    i = published.index(row)
    nav = ''.join(f'<a href="../{published[j]["slug"]}/">{label}: {esc(published[j]["title"])}</a>' for j, label in ((i + 1, '← Older edition'), (i - 1, 'Newer edition →')) if 0 <= j < len(published))
    return related, '<nav class="edition-nav" aria-label="Edition navigation">' + nav + '</nav>'

def new_page(row, body, published, template):
    related, nav = related_nav(row, published)
    route = f'/editions/{row["slug"]}/'
    visuals = ''.join(f'<a href="../../assets/images/editions/{esc(name)}"><img src="../../assets/images/editions/{esc(name)}" alt="{esc(name)}" loading="lazy"></a>' for name in row.get('supporting_images', []) if (ROOT / 'assets/images/editions' / name).is_file())
    visuals = '<section class="content-section"><h2>Supporting production graphics</h2><div class="supporting-visuals">' + visuals + '</div></section>' if visuals else ''
    main = f'<main id="content"><section class="page-intro"><div class="shell"><div class="page-eyebrow">{esc(row["eyebrow"])} · {row["reading_minutes"]} MIN READ</div><h1>{esc(row["title"])}</h1><p>{esc(row["description"])}</p><p>Jason Feimster · Moonshine Capital</p><a href="{esc(row["link"])}" rel="noopener noreferrer" target="_blank">ORIGINAL LINKEDIN EDITION ↗</a></div></section><div class="shell">{cover(row,"../../")}<article class="article-layout"><aside class="archive-note">Originally published {esc(row["publication_date"])}. Historical offers, program terms, and results reflect the original article and may have changed. Moonshine Capital may receive affiliate compensation; no funding or income outcome is guaranteed.</aside>{body}</article>{visuals}<section class="content-section"><h2>Put the edition to work.</h2><div class="grid thirds">' + ''.join(f'<a class="tile" href="../../{esc(route)}/"><h3>{esc(route.title())}</h3></a>' for route in row.get('related', []) if (ROOT / route / 'index.html').is_file()) + f'</div></section>{related}{nav}<section class="content-section"><h2>BUILD YOUR AGENCY.</h2><a class="button" href="https://tally.so/r/mOe658">EXPLORE BROKER OPPORTUNITIES ↗</a> <a class="button outline" href="https://www.linkedin.com/build-relation/newsletter-follow?entityUrn=7327196925177327617">SUBSCRIBE ↗</a></section><a href="../">← All editions</a></div></main>'
    page = re.sub(r'<!-- ecosystem:begin -->[\s\S]*?<!-- ecosystem:end -->', '', template)
    page = re.sub(r'<main id="content">[\s\S]*?</main>', lambda _: main, page, count=1)
    pairs = [(r'<title>.*?</title>', f'<title>{esc(row["seo_title"])} | Moonshine Capital</title>'), (r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(row["seo_description"])}">'), (r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{HOST}{route}">'), (r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{esc(row["title"])}">'), (r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{esc(row["seo_description"])}">'), (r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{HOST}{route}">'), (r'<meta property="article:published_time" content="[^"]*">', f'<meta property="article:published_time" content="{row["publication_date"]}">')]
    for pattern, value in pairs:
        page = re.sub(pattern, lambda _: value, page, count=1)
    page = re.sub(r'<meta property="og:image" content="[^"]*">', '', page)
    if row.get('cover'):
        page = page.replace('</head>', f'<meta property="og:image" content="{HOST}/assets/images/editions/{esc(row["cover"])}"></head>', 1)
    return page

manifest = load(source / 'editions-source.json')
current = load(ROOT / 'data/editions.json')
old_published = {r['slug']: r for r in current if r.get('status') == 'published'}
old_unpublished = [r for r in current if r.get('status') != 'published']
seen_slugs, seen_numbers, incoming = set(), set(), []
for item in manifest:
    if set(item) - PUBLIC_FIELDS:
        raise ValueError('Private or unsupported publication fields in export')
    slug = item.get('slug')
    number = item.get('edition_number')
    if item.get('status') != 'published' or not isinstance(slug, str) or not SLUG.fullmatch(slug) or not isinstance(number, int) or number < 1 or slug in seen_slugs or number in seen_numbers:
        raise ValueError('Invalid or duplicate confirmed edition')
    raw = (source / 'articles' / f'{slug}.md').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != item.get('source_sha256'):
        raise ValueError('Published Markdown hash mismatch: ' + slug)
    if not safe_url(item.get('link') or ''):
        raise ValueError('Missing published link: ' + slug)
    incoming.append((item, raw))
    seen_slugs.add(slug); seen_numbers.add(number)
if set(old_published) - seen_slugs:
    raise ValueError('Export omits existing published editions')
artwork = {}
for spec in args.artwork:
    slug, sep, filename = spec.partition('=')
    path = pathlib.Path(filename).resolve()
    if not sep or slug not in seen_slugs or not path.is_file() or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise ValueError('Invalid approved artwork mapping: ' + spec)
    head = path.read_bytes()[:12]
    suffix = path.suffix.lower()
    if not ((suffix == '.png' and head.startswith(b'\x89PNG\r\n\x1a\n')) or (suffix in ('.jpg', '.jpeg') and head.startswith(b'\xff\xd8\xff')) or (suffix == '.webp' and head[:4] == b'RIFF' and head[8:12] == b'WEBP')):
        raise ValueError('Approved artwork extension and encoding differ: ' + str(path))
    artwork[slug] = path

published, changed = [], set()
for item, raw in incoming:
    slug = item['slug']
    old = old_published.get(slug)
    if old and old['edition_number'] != item['edition_number']:
        raise ValueError('Existing edition number changed: ' + slug)
    if old and old['source_sha256'] != item['source_sha256']:
        changed.add(slug)
    if not old:
        changed.add(slug)
    row = dict(old or {})
    if not old or slug in changed:
        row.update(item)
    row['id'] = old['id'] if old else next((x['id'] for x in old_unpublished if x.get('slug') == slug or x.get('title') == item['title']), item['id'])
    row['status'] = 'published'
    if slug in artwork:
        dest = ROOT / 'assets/images/editions' / (slug + artwork[slug].suffix.lower())
        if dest.exists() and dest.read_bytes() != artwork[slug].read_bytes():
            raise ValueError('Approved artwork would overwrite existing image: ' + str(dest))
        row['cover'] = dest.name
        changed.add(slug)
        if not args.check and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(artwork[slug], dest)
    published.append(row)
published.sort(key=lambda x: x['edition_number'], reverse=True)
if len({x['id'] for x in published}) != len(published):
    raise ValueError('Duplicate public edition ID')
remaining = [x for x in old_unpublished if x.get('id') not in {r['id'] for r in published} and x.get('title') not in {r['title'] for r in published}]
updated = published + remaining
if args.check:
    print(f'Validated {len(published)} published editions, {len(changed)} changed, {len(remaining)} unpublished records')
    raise SystemExit(0)

for row, raw in incoming:
    target = ROOT / 'content/editions' / (row['slug'] + '.md')
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == row['source_sha256']:
        continue
    if row['slug'] not in changed:
        raise ValueError('Existing website Markdown differs: ' + row['slug'])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

if changed:
    template = (ROOT / 'editions/your-funding-agency-just-got-two-ai-employees/index.html').read_text(encoding='utf-8')
    for row in published:
        page_path = ROOT / 'editions' / row['slug'] / 'index.html'
        if row['slug'] in changed:
            raw = (source / 'articles' / (row['slug'] + '.md')).read_bytes()
            write(page_path, new_page(row, markdown_body(raw), published, template))
        else:
            page = page_path.read_text(encoding='utf-8')
            related, nav = related_nav(row, published)
            page = re.sub(r'<section class="content-section"><h2>Related editions\.</h2>[\s\S]*?</section>', lambda _: related, page, count=1)
            page = re.sub(r'<nav class="edition-nav" aria-label="Edition navigation">[\s\S]*?</nav>', lambda _: nav, page, count=1)
            write(page_path, page)
    archive_path = ROOT / 'editions/index.html'
    archive = archive_path.read_text(encoding='utf-8')
    cats = sorted({r['topic'] for r in published})
    body = f'<section class="content-section" data-catalog><div class="section-cap"><span>THE PUBLISHED ARCHIVE / {len(published)} EDITIONS</span><h2>READ. BUILD. EXECUTE.</h2></div><div class="filter-bar"><input type="search" aria-label="Search editions" placeholder="Search editions…"><select aria-label="Filter category"><option value="all">All categories</option>' + ''.join(f'<option>{esc(c)}</option>' for c in cats) + f'</select></div><p data-count aria-live="polite">{len(published)} records</p><div class="grid thirds">' + ''.join(card(r, '../') for r in published) + '</div></section>'
    write(archive_path, replace_block(archive, 'editorial-archive', body))
    home_path = ROOT / 'index.html'
    home = home_path.read_text(encoding='utf-8')
    feature = ''.join(f'<article class="hp-edition {"hp-feature" if i == 0 else ""}"><a href="./editions/{r["slug"]}/">{cover(r,"./") if i == 0 else ""}</a><div class="hp-edition-copy"><span class="hp-kicker">{"LATEST / " if i == 0 else ""}EDITION {r["edition_number"]}</span><h3><a href="./editions/{r["slug"]}/">{esc(r["title"])}</a></h3><p>{esc(r["description"])}</p><a class="hp-read" href="./editions/{r["slug"]}/">READ EDITION ↗</a></div></article>' for i, r in enumerate(published[:3]))
    write(home_path, replace_block(home, 'latest-editions', '<div class="hp-editions" data-home-editions>' + feature + '</div>'))
    release_path = ROOT / 'registry/public-release.json'
    release = load(release_path)
    latest = published[0]
    candidates = [x for x in release['entries'] if x.get('kind') == 'edition']
    if len(candidates) != 1:
        raise ValueError('Expected one featured edition registry entry')
    candidates[0].update(title=latest['title'], description=latest['description'], label=f'Edition {latest["edition_number"]} · Published {latest["publication_date"]}', local=f'/editions/{latest["slug"]}/')
    write(release_path, json.dumps(release, ensure_ascii=False, indent=2) + '\n')
    sitemap_path = ROOT / 'sitemap.xml'
    sitemap = sitemap_path.read_text(encoding='utf-8')
    sitemap = re.sub(r'<url><loc>[^<]+/editions/[^<]+</loc>(?:<lastmod>[^<]+</lastmod>)?</url>\s*', '', sitemap)
    entries = ''.join(f'<url><loc>{HOST}/editions/{r["slug"]}/</loc><lastmod>{r["publication_date"]}</lastmod></url>\n' for r in published)
    write(sitemap_path, sitemap.replace('</urlset>', entries + '</urlset>'))
write(ROOT / 'data/editions.json', json.dumps(updated, ensure_ascii=False, indent=2) + '\n')
print(f'Publication render: {len(published)} published, {len(changed)} changed, {len(remaining)} unpublished preserved')
