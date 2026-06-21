# Open-Access Sources — Field Reference

How `scripts/resolve_oa.py` resolves identifiers, what the output fields mean,
and what to do when something fails.

## Contents

- [Unpaywall (DOI resolver)](#unpaywall-doi-resolver)
- [Interpreting oa_status, version, license](#interpreting-oa_status-version-license)
- [arXiv (preprints)](#arxiv-preprints)
- [ACM Digital Library (open access since 2026)](#acm-digital-library-open-access-since-2026)
- [Other legal sources when all three miss](#other-legal-sources-when-all-three-miss)
- [Troubleshooting](#troubleshooting)

## Unpaywall (DOI resolver)

The standard "DOI → legal OA copy" service (OurResearch, data CC-BY,
~50M Crossref DOIs, 100k calls/day).

- Endpoint: `https://api.unpaywall.org/v2/{DOI}?email={EMAIL}`
- No API key. The `email` param is **mandatory and validated** — placeholder
  addresses (`*@example.com`) are rejected with HTTP 422.
- Key response fields the script surfaces:
  - `is_oa` — any legal OA copy exists anywhere.
  - `oa_status` — gold / hybrid / bronze / green / closed (see below).
  - `best_oa_location.url_for_pdf` — direct PDF when the host exposes one.
  - `best_oa_location.url_for_landing_page` — page hosting the OA copy.
  - `best_oa_location.version` and `.license`.
- `best_oa_location` already encodes Unpaywall's preference order (publisher
  version > accepted manuscript > preprint); trust it rather than scanning
  `oa_locations` yourself. The script only scans `oa_locations` to spot an
  arXiv mirror and derive an HTML link.

## Interpreting oa_status, version, license

| `oa_status` | Meaning | Reading guidance |
|---|---|---|
| gold | OA journal/proceedings, publisher-hosted | Best copy; cite as published |
| hybrid | OA article in a subscription venue, paid APC | Publisher version, safe |
| bronze | Free on publisher site, no open license | Read freely; do not redistribute |
| green | Repository copy (arXiv, institutional) | Often a preprint — check `version` |
| closed | No legal OA copy known | Exit code 3; see fallback list |

| `version` | Meaning |
|---|---|
| publishedVersion | The version of record — quote/cite page numbers safely |
| acceptedVersion | Peer-reviewed text, pre-typesetting — content reliable, pagination not |
| submittedVersion | Preprint — may differ from the reviewed paper; warn the user |

`license` of `cc-by`/`cc-by-*` permits reuse with attribution; `null` (common
for bronze) means *read-only*: process transiently, never republish.

## arXiv (preprints)

- ID forms accepted by the script: `2403.12345`, `2403.12345v2`,
  `arXiv:...`, old-style `cs/0309136`, any `arxiv.org/abs|pdf|html/...` URL,
  and arXiv DOIs `10.48550/arXiv.<id>`.
- URL patterns (everything on arXiv is free to read):
  - PDF: `https://arxiv.org/pdf/{id}` (omit version → latest)
  - HTML: `https://arxiv.org/html/{id}` — native HTML rendering; exists for
    most LaTeX submissions from ~Dec 2023 onward, 404s for older papers. The
    script probes it (skip with `--no-html-check`).
  - Landing/abstract: `https://arxiv.org/abs/{id}`
- Metadata API: `http://export.arxiv.org/api/query?id_list={id}` (Atom XML,
  no key). arXiv asks for **3 seconds between requests**; the script enforces
  this per host.
- arXiv copies are `submittedVersion` green OA. The camera-ready may differ —
  before quoting results or page numbers, check whether a published DOI
  exists (Crossref/`verify-citations`) and prefer it for citations.

## ACM Digital Library (open access since 2026)

- On **January 1, 2026** the entire ACM DL (journals, proceedings, magazines)
  became open access in the free "Basic" edition.
- Consequence: any `10.1145/*` paper is legally readable at
  `https://dl.acm.org/doi/pdf/{doi}` even when Unpaywall hasn't indexed an OA
  location yet. The script uses this as a constructed (unverified) fallback.
- Caveats:
  - dl.acm.org bot protection blocks most scripted fetches — hand the URL to
    the user to open in a browser; don't fight the 403.
  - ACM's terms prohibit "scripts, spiders or other robotic activity" for
    bulk downloading. Single-paper fetches with a real User-Agent are the
    intended use. Text/data-mining requests go to permissions@acm.org.
  - Individual papers still carry per-paper licenses (often CC-BY for recent
    ones, more restrictive for older ones): open to read ≠ free to bundle.

## Other legal sources when all three miss

In order of effort, all legal:

1. **Author preprint** — search author homepages / Google Scholar profile /
   institutional repositories (use `find-papers` with the title).
2. **arXiv by title** — many papers are posted under slightly different titles.
3. **PubMed Central** — biomedical papers; the PMC OA subset is fetchable.
4. **The user's library** — institutional subscription or interlibrary loan.
5. **Email the authors** — nearly all researchers share their accepted
   manuscript on request; offer to draft the email.

Never: Sci-Hub, LibGen, Anna's Archive, or any paywall circumvention.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| exit 2: "real contact email is required" | `UNPAYWALL_EMAIL`/`CONTACT_EMAIL` unset, non-interactive | `export UNPAYWALL_EMAIL=you@uni.edu` |
| HTTP 422 from Unpaywall | placeholder email | use a real address |
| Unpaywall 404 | DOI not in Crossref/Unpaywall (new, or registered with DataCite) | check the DOI for typos; try the doi.org landing page; for `10.1145/*` the script already falls back to dl.acm.org |
| exit 3 (no legal OA copy) | genuinely closed access | walk the fallback list above |
| arXiv HTML probe non-200 | paper predates arXiv HTML or isn't LaTeX | use `pdf_url` |
| 403 downloading from dl.acm.org | bot protection | open the URL in a browser |
| persistent 429s | shared-pool throttling | wait; the script already backs off exponentially — do not lower its rate limits |
| stale answer suspected | 24h response cache | re-run with `--refresh` |
