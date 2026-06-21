# Venue Aliases Across Scholarly APIs

The same conference has a *different identity in every API*, and getting the
string wrong silently returns zero (or wrong) results. Example — SIGSPATIAL:

- DBLP venue key: `conf/gis` (toc pages `db/conf/gis/gis<year>.bht`)
- Semantic Scholar `venue`: `SIGSPATIAL/GIS`
- Crossref `container-title`: `Proceedings of the 31st ACM International
  Conference on Advances in Geographic Information Systems` (varies per year)
- arXiv: no venue concept at all — search by category + keywords

This table maps ~20 top CS venues across the four APIs used by this skill.
Rows for venues that have a profile in `venues/conferences/` mirror that
profile's `aliases:` block — when in doubt, the year-versioned profile wins.

## Table of contents

1. [How to use each column](#how-to-use-each-column)
2. [The alias table](#the-alias-table)
3. [Per-venue gotchas](#per-venue-gotchas)
4. [arXiv hints by venue](#arxiv-hints-by-venue)
5. [Verification provenance](#verification-provenance)
6. [Adding or re-verifying a venue](#adding-or-re-verifying-a-venue)

## How to use each column

| Column | Feeds | Query template |
|---|---|---|
| DBLP key | `dblp_search.py` | `--key <key> --year <YYYY>` (conferences) or `--volume <N>` (journals) |
| S2 venue | `s2_search.py` | `--venue "<exact string>" --year <YYYY>` |
| Crossref container | `crossref_search.py` | `--container "<substring>" --from-date <YYYY>-01-01 --until-date <YYYY>-12-31` |
| arXiv | `arxiv_search.py` | no venue filter exists — see [arXiv hints](#arxiv-hints-by-venue) |

## The alias table

Confidence: ✅ = verified live 2026-06-11 · ◑ = long-established string, not
re-verified live (re-check before relying on it; S2 rate limits blocked some
verifications) · ✗ = provider does not cover this venue.

| Venue | DBLP key | Semantic Scholar `venue` | Crossref `query.container-title` |
|---|---|---|---|
| AAAI | ✅ `conf/aaai` | ✅ `AAAI Conference on Artificial Intelligence` | ✅ `Proceedings of the AAAI Conference on Artificial Intelligence` |
| ACL | ✅ `conf/acl` ⚠️ multi-volume | ◑ `Annual Meeting of the Association for Computational Linguistics` | ◑ `Annual Meeting of the Association for Computational Linguistics` |
| CHI | ✅ `conf/chi` | ✅ `International Conference on Human Factors in Computing Systems` | ✅ `CHI Conference on Human Factors in Computing Systems` |
| CVPR | ✅ `conf/cvpr` | ◑ `Computer Vision and Pattern Recognition` | ✅ `IEEE/CVF Conference on Computer Vision and Pattern Recognition` |
| ECCV | ✅ `conf/eccv` ⚠️ multi-volume | ◑ `European Conference on Computer Vision` | ⚠️ Springer book volumes — see gotchas |
| EDBT | ✅ `conf/edbt` | ◑ `International Conference on Extending Database Technology` | ✗ modern DOIs are DataCite, not Crossref |
| EMNLP | ✅ `conf/emnlp` ⚠️ multi-volume | ◑ `Conference on Empirical Methods in Natural Language Processing` | ◑ `Conference on Empirical Methods in Natural Language Processing` |
| ICCV | ✅ `conf/iccv` | ◑ `IEEE International Conference on Computer Vision` | ◑ `IEEE/CVF International Conference on Computer Vision` |
| ICDE | ✅ `conf/icde` | ✅ `IEEE International Conference on Data Engineering` | ✅ `International Conference on Data Engineering` |
| ICLR | ✅ `conf/iclr` | ◑ `International Conference on Learning Representations` | ✗ verified absent — OpenReview, no Crossref DOIs |
| ICML | ✅ `conf/icml` | ◑ `International Conference on Machine Learning` | ✗ verified absent — PMLR, no Crossref DOIs |
| IJCAI | ✅ `conf/ijcai` | ◑ `International Joint Conference on Artificial Intelligence` | ◑ `International Joint Conference on Artificial Intelligence` |
| KDD | ✅ `conf/kdd` | ✅ `Knowledge Discovery and Data Mining` | ✅ `ACM SIGKDD Conference on Knowledge Discovery and Data Mining` |
| NeurIPS | ✅ `conf/nips` ⚠️ see gotchas | ◑ `Neural Information Processing Systems` | ⚠️ historical volumes only — see gotchas |
| SIGIR | ✅ `conf/sigir` | ◑ `Annual International ACM SIGIR Conference on Research and Development in Information Retrieval` | ◑ `SIGIR Conference on Research and Development in Information Retrieval` |
| SIGMOD | ✅ `conf/sigmod` + `journals/pacmmod` (2023+) | ◑ `Proceedings of the ACM on Management of Data` (2023+) | ✅ `Proceedings of the ACM on Management of Data` |
| SIGSPATIAL | ✅ `conf/gis` | ✅ `SIGSPATIAL/GIS` | ✅ `International Conference on Advances in Geographic Information Systems` |
| TKDE (journal) | ✅ `journals/tkde` | ✅ `IEEE Transactions on Knowledge and Data Engineering` | ✅ `IEEE Transactions on Knowledge and Data Engineering` |
| TODS (journal) | ✅ `journals/tods` | ✅ `ACM Transactions on Database Systems` | ✅ `ACM Transactions on Database Systems` |
| VLDB (PVLDB) | ✅ `journals/pvldb` ⚠️ volume, not year | ✅ `Proceedings of the VLDB Endowment` | ✅ `Proceedings of the VLDB Endowment` |
| WWW (The Web Conf) | ✅ `conf/www` | ✅ `The Web Conference` | ✅ `Proceedings of the ACM Web Conference` |

## Per-venue gotchas

- **SIGSPATIAL**: DBLP indexes it under its historical acronym **GIS** — the
  key is `conf/gis`, never `conf/sigspatial`. Verified counts for 2025:
  DBLP toc 195 papers, S2 `SIGSPATIAL/GIS` 191, Crossref 130 (Crossref count
  includes co-located workshops with their own proceedings — filter by
  container-title substring "Advances in Geographic Information Systems" for
  the main conference only).
- **VLDB**: modern VLDB papers live in the *journal* `journals/pvldb`
  ("Proceedings of the VLDB Endowment"), so use `--volume`, not `--year`.
  Volume = year − 2007 (Vol 17 = 2024, Vol 18 = 2025, Vol 19 = 2026).
  `conf/vldb` exists but only covers pre-2008 proceedings.
- **SIGMOD**: research papers since 2023 are published as the journal
  *Proceedings of the ACM on Management of Data* (PACMMOD) — DBLP
  `journals/pacmmod`, Crossref/S2 use that title. Pre-2023 papers are under
  `conf/sigmod` / "Proceedings of the ... SIGMOD International Conference on
  Management of Data". Query both for full coverage.
- **NeurIPS**: DBLP key is the historical `conf/nips`. Toc basenames switched
  with the rebrand: `nips2017.bht` and earlier, `neurips2018.bht` onward —
  if `--key conf/nips --year Y` returns 0, retry with
  `--toc db/conf/nips/neurips<Y>.bht`. Crossref only has MIT-Press-era
  "Advances in Neural Information Processing Systems <vol>" volumes; modern
  NeurIPS (proceedings.neurips.cc) mints no Crossref DOIs.
- **ICLR / ICML**: not in Crossref at all (verified absent live) — ICLR
  publishes via OpenReview, ICML via PMLR; neither registers Crossref DOIs.
  Enumerate via DBLP, enrich via S2.
- **ACL / EMNLP / ECCV**: DBLP splits each edition into multiple toc volumes
  (`acl2024-1.bht`, `acl2024-2.bht`, ..., `eccv2024-1.bht`...). The plain
  `--key X --year Y` toc returns 0 or partial results — use
  `--toc db/conf/acl/acl2024-1.bht` per volume, or fall back to S2 venue
  search for one-shot enumeration. ACL Anthology DOIs (prefix 10.18653) ARE
  in Crossref; per-edition container titles vary ("Proceedings of the 62nd
  Annual Meeting of the Association for Computational Linguistics (Volume 1:
  Long Papers)"), so query the stable substring shown in the table.
- **ECCV in Crossref**: papers are Springer LNCS *book chapters*; the
  container is the book ("Computer Vision – ECCV 2024" / "Lecture Notes in
  Computer Science"), which collides with other LNCS volumes. Prefer DBLP.
- **CVPR / ICCV / ICDE (IEEE venues)**: Crossref container titles are minted
  per year with prefixes like "2024 IEEE 40th ..." — query the stable
  substring from the table, never the acronym. Expect months of lag before a
  new edition appears in Crossref; OpenAlex fragments these venues into
  per-year sources, another reason this skill leads with DBLP.
- **KDD in Crossref**: 2023+ titles say "ACM SIGKDD Conference on Knowledge
  Discovery and Data Mining" (2025 split into "... V.1"/"... V.2"); pre-2023
  say "...International Conference on Knowledge Discovery & Data Mining".
  Querying "SIGKDD Knowledge Discovery" catches both.
- **CHI**: posters/LBW live in a separate "...Extended Abstracts" Crossref
  container; the table string matches the main proceedings phrasings.
- **EDBT**: modern EDBT DOIs (prefix 10.48786, OpenProceedings) are
  registered with **DataCite**, so Crossref returns only legacy ~2008–2013
  volumes. Use DBLP for enumeration.
- **S2 venue strings are never acronyms**: searching `venue=WWW`, `venue=KDD`
  or `venue=SIGSPATIAL` returns 0 or garbage. Use the exact strings above;
  S2 normalizes "WWW" to `The Web Conference` across all years.

## arXiv hints by venue

arXiv has **no venue field** for conference papers (preprints precede
acceptance). Two strategies:

1. **Category + keywords** — primary categories by area:
   `cs.AI` (AAAI, IJCAI) · `cs.CL` (ACL, EMNLP) · `cs.CV` (CVPR, ICCV, ECCV) ·
   `cs.DB` (SIGMOD, VLDB, ICDE, EDBT, TODS, TKDE, SIGSPATIAL) ·
   `cs.HC` (CHI) · `cs.IR` (SIGIR, WWW, partly KDD) ·
   `cs.LG` (NeurIPS, ICML, ICLR, KDD).
2. **journal-ref** — authors sometimes set it after acceptance:
   `--query 'jr:SIGSPATIAL'` finds some accepted versions, but coverage is
   sparse and author-dependent. Never treat a jr: hit as proof of acceptance —
   confirm via DBLP/Crossref.

## Verification provenance

- 15 rows (AAAI, CHI, CVPR, EDBT, ICDE, ICLR, ICML, KDD, NeurIPS, SIGMOD,
  SIGSPATIAL, TKDE, TODS, VLDB, WWW) mirror the `aliases:` blocks of
  `venues/conferences/*.yml`, each verified live on 2026-06-11 (per-field
  provenance comments live in those files; S2 strings marked ◑ hit HTTP 429
  during that pass).
- ACL, EMNLP, ICCV, ECCV, SIGIR, IJCAI DBLP keys: verified live 2026-06-11
  via `dblp_search.py --find-venue`.
- End-to-end counts re-verified live 2026-06-11 while testing this skill's
  scripts: DBLP toc `conf/gis` 2025 → 195; Crossref SIGSPATIAL 2025
  proceedings-articles → 130; S2 `SIGSPATIAL/GIS` 2025 → 191.
- NeurIPS toc rename confirmed live 2026-06-11: `nips2024.bht` → 0 papers,
  `neurips2024.bht` → 4,495. PVLDB volume arithmetic confirmed live:
  `journals/pvldb` volume 17 → 431 papers, all year 2024.
- ACL multi-volume toc confirmed live 2026-06-11:
  `db/conf/acl/acl2024-1.bht` → 866 long papers with 10.18653 (ACL
  Anthology / Crossref) DOIs.

## Adding or re-verifying a venue

1. DBLP key: `python3 scripts/dblp_search.py --find-venue "<name>"` — the key
   is the `db/...` path segment of the venue URL.
2. S2 string: fetch one known paper from the venue by DOI —
   `python3 scripts/s2_search.py --paper DOI:<doi> --fields title,venue` —
   and copy the exact `venue` value (do NOT guess from the acronym).
3. Crossref container: `python3 scripts/crossref_search.py --query "<a known
   paper title>"` and copy the `container-title`; prefer the year-stable
   substring.
4. Sanity-check the trio returns plausible, mutually consistent counts for
   one recent year, then record the strings (with a verified date) in the
   venue's `venues/conferences/<id>.yml` `aliases:` block and update this
   table. Aliases drift (rebrands like NeurIPS, publisher moves like
   SIGMOD→PACMMOD) — re-verify any row older than a year before betting a
   literature review on it.
