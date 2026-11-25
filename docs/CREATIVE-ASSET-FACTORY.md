# FAB Creative Asset Factory

40 specifications: 18 original AI artworks (IDs 01–17, 19), one deterministic logo (18), one subscription banner (20), and 20 editorial posters (21–40). The existing portrait and landscape from ChatGPT can be imported rather than regenerated. Alternate art directions keep the collection visually varied. All posters use exact code-rendered copy, not AI text.

## Setup (PowerShell, from repo root)

```powershell
python -m pip install -r scripts/creative/requirements.txt
node scripts/generate-images.mjs --pending
```

Node 22+ and Python 3.10+ recommended. No production build dependencies. Configure OPENAI_API_KEY in your local environment before requesting new art; API usage is billed separately from ChatGPT. Model defaults to gpt-image-1.5 (supports reference image edits and transparency); override with --model or OPENAI_IMAGE_MODEL. Optional CREATIVE_PYTHON and CREATIVE_FONT_BOLD / CREATIVE_FONT_REGULAR environment variables.

## Import existing ChatGPT output (no API usage)

```powershell
node scripts/optimize-images.mjs --id 01 --file "C:\path\agency-machine-4x5.png"
node scripts/optimize-images.mjs --id 02 --file "C:\path\agency-machine-16x9.png"
```

The importer converts files to the actual registry format and exact dimensions. Transparent assets must contain real alpha. Opaque files are center-cropped to the target aspect ratio. The original is preserved. Alternatively put same-basename PNGs alongside the requested WebPs and run optimize-images without arguments. Existing final outputs are skipped unless --force is supplied.

## Sequential AI production

```powershell
node scripts/generate-images.mjs --pending --execute --limit 1
node scripts/generate-images.mjs --pending --execute
node scripts/render-branded-assets.mjs
```

Without --execute the AI command only lists pending work. Generation uses the existing social preview or a named prior illustration as reference. --no-reference creates from text only. Raw results are cached outside the deployed output; if processing fails, rerun to resume from cache. API errors stop the queue; no automatic paid retries. --id selects a specific record. --force explicitly allows replacing outputs and, for AI jobs, regeneration. Poster rendering skips missing source artwork and reports the prerequisite. No Git commands or automatic publishing inside the creative scripts.

## Catalog graphics

```powershell
node scripts/render-branded-assets.mjs --catalog --type gpt --limit 5
node scripts/render-branded-assets.mjs --catalog
```

Eight catalog families, including published newsletter editions, map to reusable templates. Existing artwork is reused. No API calls. Static registry outputs are indexed in data/image-assets.generated.json; catalog graphics are written under assets/images/generated/fab/{type}/. These are independent assets, not automatically inserted into website pages or posted to LinkedIn. Use the manifest to wire up the intended route when ready.

## Multi-publication use

Add a publication configuration to data/creative-publications.json and its own image registry. Provide masthead, publisher, palette/theme, output root, manifest path and catalog root. Run each script with --publication ID. Shared renderer and theme/template libraries are publication-agnostic; catalog mappings currently use the FAB data filenames, so adjust those inputs for another publication before catalog rendering.

The factory uses Pillow for precise layout, font sizing, actual file conversion and transparency. Design variants are style directions; not every template requires new AI art. No external posting, repository visibility changes or API billing happens on installation.
