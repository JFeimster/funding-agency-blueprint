<img width="1672" height="941" alt="repo-social-preview" src="https://github.com/user-attachments/assets/be6d7f69-facb-4430-8b11-47687e672d0e" />

# The Funding Agency Blueprint

**The operating manual for modern funding agencies.** Published by Moonshine Capital · Jason Feimster.

[Live publication](https://funding-agency-blueprint.vercel.app/) · [LinkedIn newsletter](https://www.linkedin.com/newsletters/7327196925177327617/) · [Subscribe](https://www.linkedin.com/build-relation/newsletter-follow?entityUrn=7327196925177327617) · [Funding partner directory](https://moonshine-ai-directory.vercel.app/partners)

## Publication

A static editorial and practical resource hub for funding brokers, affiliates and agency operators. Broker’s Manifesto is the primary design at the root; six standalone design studies are retained.

| Route | Purpose |
| --- | --- |
| / | Publication homepage |
| /editions/ | Newsletter editions |
| /blueprint/ | Agency launch roadmap |
| /playbooks/ | Operating guides |
| /ai-lab/ | Agents and prompts |
| /automations/ | Workflows |
| /tools/ | Calculators and development catalog |
| /partners/ | Funding and technology resources |
| /resources/ | Downloads and training |
| /field-notes/ | Build notes |
| /start/ | Agency launch path |
| /about/ | Publisher and author |

## Design studies

- [Broker’s Manifesto](sites/brokers-manifesto/)
- [Blueprint Press](sites/blueprint-press/)
- [Agency Signal](sites/agency-signal/)
- [Independent Magazine Editorial](sites/independent-magazine-editorial/)
- [Nocturnal Editorial Noir](sites/nocturnal-editorial-noir/)
- [Dada Riot](sites/dada-riot/)

## Data and content

The master registry contains 259 records. Phase 4 exports 29 connected resources and 119 development concepts (148 public catalog entries). Concepts can be published without deployment URLs; they are not working applications.

- `registry/blueprint-assets.master.json`: source inventory.
- `registry/public-release.json`: release selection.
- `data/blueprint-public.json`: generated public catalog.
- `data/partners.json`: existing mixed partner seed catalog.
- `scripts/generate-public-registry.mjs`: dependency-free JSON and HTML generator.
- `downloads/`: original downloadable resources.

Run with Node 18+:

```sh
node scripts/generate-public-registry.mjs
node scripts/generate-public-registry.mjs --check
python -m http.server 8000
```

Open http://localhost:8000/. Commit regenerated JSON and HTML together.

## Deployment

Production branch: `main`. Git-triggered automatic deployments are enabled for main and disabled for other branches in `vercel.json`. Manual preview deployments are not prohibited by this setting. The production branch in Vercel must remain main.

Current host: https://funding-agency-blueprint.vercel.app/

Proposed media route: `https://media.distilledfunding.com/the-funding-agency/` (requires media-host routing; not configured here). Preserve relative paths for future prefix mounting.

## Partner directory direction

Separate funding providers, affiliate software, and independently recommended technology. Reuse the existing [Moonshine AI Directory](https://github.com/JFeimster/moonshine-ai-directory) provider registry rather than maintaining another lender source of truth. Distinguish recorded affiliate relationships from editorial recommendations. Link to public destinations, not private partner portals.

## Publication boundaries

Educational examples are not funding offers or income promises. The registry folder is excluded from Vercel deployment by `.vercelignore`, not from GitHub visibility. Keep borrower and recruit CRM records, internal payout arrangements and private source links out of public exports. Repository visibility is managed separately.
