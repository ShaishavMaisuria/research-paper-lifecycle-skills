# Copyright & Politeness Rules for Fetching Papers

These rules are load-bearing. A single bundled PDF or a bulk-crawl complaint
can take down the whole repo. When in doubt, fetch less and keep less.

## What is always safe to keep and commit

- **Metadata**: DOIs, titles, author names, venue, year, page ranges, BibTeX
  entries, arXiv IDs, URLs. Facts are not copyrightable.
- **Your own original analysis**: notes about a paper's structure, framing,
  or evaluation patterns, written in your own words.
- **Short quotations** inside analysis (a sentence or two, attributed) —
  standard scholarly fair use.

## What is transient-only (fetch, process, discard)

- **Full text** (PDF or HTML), from explicitly OA locations only:
  Unpaywall `best_oa_location`, arXiv, PMC OA subset, post-2026 ACM DL.
- **Abstracts**: fine to fetch and reason over; do not vendor them into the
  repo. (Semantic Scholar abstracts are ODC-BY with no bulk redistribution;
  publisher abstracts are typically copyrighted.)
- Downloads from `--download` land in a temp directory on purpose. Read,
  extract what the task needs, delete. Never move them into the repository,
  never attach them to commits, never re-host or email them onward.

## What is never acceptable

- Bundling or committing paper text, abstracts, or PDFs into any repo.
- Shadow libraries (Sci-Hub, LibGen, Anna's Archive) or any paywall bypass,
  even if the user asks directly — explain the legal alternatives instead
  (see `oa-sources.md`, "Other legal sources").
- Bulk/robotic downloading. ACM's ToU prohibits it explicitly; arXiv and
  Unpaywall expect single-item politeness. One identifier per invocation.
- Stripping or hiding license/attribution information from an OA copy.

## "Open to read" is not "free to reuse"

The ACM DL being open access (since Jan 1, 2026) means anyone may *read*
any paper there. Individual papers still carry per-paper licenses. Bronze OA
(free on the publisher site, no license) is read-only. Only an explicit
CC-BY-style license permits reuse beyond quotation — and even then, this
repo's policy stays fetch-on-demand, never bundle.

## Politeness contract (encoded in resolve_oa.py — do not weaken)

- ≤ 1 request/second per host; 3 seconds for arxiv.org (their stated policy).
- Identifying User-Agent: `research-paper-skills (mailto:$CONTACT_EMAIL)`
  with a real address, so operators can reach a human instead of blocking.
- Exponential backoff on HTTP 429/503, honoring `Retry-After`.
- API responses cached 24h under `.cache/fetch-paper/` (gitignored) so
  repeated runs cost the services nothing.
- Real email for Unpaywall (`UNPAYWALL_EMAIL`); placeholders are rejected.

## If the user pushes back

Be a copilot, not an accomplice: state plainly that you can only retrieve
legal copies, then immediately offer the highest-yield legal route (author
preprint search, library access, emailing the authors — most researchers
share their accepted manuscript within a day or two).
