"""Exercise an unpublished-to-published transition in an isolated site copy."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile

SOURCE = pathlib.Path(__file__).resolve().parents[1]
EXPORT = pathlib.Path(__import__('sys').argv[1]).resolve()

def run(site, *args):
    subprocess.run(args, cwd=site, check=True, stdout=subprocess.DEVNULL)

with tempfile.TemporaryDirectory(prefix='fab-publication-fixture-') as temp:
    base = pathlib.Path(temp)
    site = base / 'site'
    shutil.copytree(SOURCE, site, ignore=shutil.ignore_patterns('.git', '.vercel', '.env.local', '__pycache__'))
    staging = base / 'staging'
    shutil.copytree(EXPORT, staging)
    old = json.loads((site / 'data/editions.json').read_text(encoding='utf-8'))
    originals = {r['slug']: hashlib.sha256((site / 'content/editions' / (r['slug'] + '.md')).read_bytes()).hexdigest() for r in old if r.get('status') == 'published'}
    manifest_path = staging / 'editions-source.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    slug = 'how-to-build-an-ai-powered-funding-agency-from-scratch'
    body = b'# Fixture edition\n\n<script>alert(1)</script>\n\n## Safe heading\n\n- First step\n- Second step\n\n[Unsafe](javascript:alert(1))\n'
    (staging / 'articles' / (slug + '.md')).write_bytes(body)
    manifest.insert(0, {
        'id': 'fixture-id', 'slug': slug, 'edition_number': 18, 'title': 'How to Build an AI-Powered Funding Agency From Scratch',
        'status': 'published', 'publication_date': '2026-11-26', 'series': 'The AI-Powered Funding Agency',
        'topic': 'Agency Architecture', 'description': 'Isolated fixture, never published.',
        'seo_title': 'Fixture edition', 'seo_description': 'Fixture description',
        'link': 'https://www.linkedin.com/pulse/fixture-edition/', 'reading_minutes': 1,
        'source_sha256': hashlib.sha256(body).hexdigest(), 'eyebrow': 'Edition 18 · 2026-11-26'
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    first_run_hashes = None
    for _ in range(2):
        run(site, 'python', 'scripts/render-publication.py', '--export', str(staging))
        run(site, 'node', 'scripts/generate-public-registry.mjs')
        run(site, 'node', 'scripts/generate-resource-ecosystem.mjs')
        run(site, 'node', 'scripts/generate-resource-ecosystem.mjs', '--check')
        run(site, 'node', 'scripts/generate-public-registry.mjs', '--check')
        generated_hashes = {p.relative_to(site): hashlib.sha256(p.read_bytes()).hexdigest() for p in site.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        if first_run_hashes is not None:
            assert generated_hashes == first_run_hashes, 'Second publication run changed generated files'
        first_run_hashes = generated_hashes
    records = json.loads((site / 'data/editions.json').read_text(encoding='utf-8'))
    assert len([r for r in records if r.get('status') == 'published']) == 18
    assert len([r for r in records if r.get('status') != 'published']) == 1
    assert len([r for r in records if r.get('title') == manifest[0]['title']]) == 1
    assert next(r for r in records if r['slug'] == slug)['id'] == 'ai-powered-agency-from-scratch'
    assert next(r for r in records if r['slug'] == slug)['related'] == ['blueprint', 'ai-lab', 'automations']
    assert len(json.loads((site / 'data/resource-ecosystem.json').read_text(encoding='utf-8'))['records']) == 443
    for old_slug, digest in originals.items():
        assert hashlib.sha256((site / 'content/editions' / (old_slug + '.md')).read_bytes()).hexdigest() == digest
    page = (site / 'editions' / slug / 'index.html').read_text(encoding='utf-8')
    assert '&lt;script&gt;' in page and '<script>alert(1)</script>' not in page
    assert 'href="javascript:' not in page
    assert 'EDITION 18' in (site / 'index.html').read_text(encoding='utf-8')
    assert f'/editions/{slug}/' in (site / 'sitemap.xml').read_text(encoding='utf-8')
    assert '18 records' in (site / 'editions/index.html').read_text(encoding='utf-8')
    print('Fixture passed: 18 published, 1 planned, 443 resources, original hashes retained, safe Markdown, repeat run stable')
