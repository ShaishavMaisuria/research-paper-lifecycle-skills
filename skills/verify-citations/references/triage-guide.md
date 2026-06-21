# Triage guide — what each flag means and how to fix it

Work through ERROR flags first, then WARN. For every fix: pull the canonical
record (see "Fetching canonical BibTeX" in
[verification-sources.md](verification-sources.md)), keep the original
citation key, show the user a before/after diff. Re-check fixed entries with
`--key {key}`, then run one full pass to confirm exit code 0.

## Table of contents

1. [ERROR flags](#error-flags)
   - [UNRESOLVED](#unresolved)
   - [DOI_NOT_FOUND / ARXIV_NOT_FOUND](#doi_not_found--arxiv_not_found)
   - [TITLE_MISMATCH](#title_mismatch)
   - [AUTHOR_MISMATCH](#author_mismatch)
   - [YEAR_MISMATCH](#year_mismatch)
   - [RETRACTED](#retracted)
   - [DUPLICATE_KEY / DUPLICATE_DOI / DUPLICATE_TITLE](#duplicates)
   - [MALFORMED_DOI / MALFORMED_ARXIV_ID](#malformed-identifiers)
2. [WARN flags](#warn-flags)
3. [INFO flags](#info-flags)
4. [Known false positives](#known-false-positives)
5. [The fix workflow, end to end](#the-fix-workflow-end-to-end)

## ERROR flags

### UNRESOLVED

Not found in Crossref, DBLP, Semantic Scholar, or arXiv. For `@article` /
`@inproceedings` / `@book` this is the strongest fabrication signal the
script can produce — indexed venues index their papers.

Triage, in order:
1. Check the title for typos or LaTeX damage (a mangled title can defeat
   search). If plausible, search manually with a corrected title.
2. Search a *distinctive phrase* from the title on DBLP and Crossref by hand.
3. Ask the user where the reference came from. If it arrived via an LLM
   (including this assistant) and cannot be located, treat it as fabricated.
4. Resolution is the user's call: supply the real reference, vouch for an
   unindexed source (then keep with a `note = {...}` pointing at it), or
   remove the entry *and* its `\cite` commands and fix surrounding prose.

Never swap in a different real paper that "sounds right" — that converts a
visible fabrication into an invisible misattribution, which is worse.

### DOI_NOT_FOUND / ARXIV_NOT_FOUND

The identifier resolves nowhere (Crossref + DataCite for DOIs; arXiv for
eprint IDs). Two cases:

- Accompanied by `POSSIBLE_ID_TYPO` — the title exists; the script prints
  the canonical URL/DOI. Replace the bad identifier with the canonical one.
- Alone — both the identifier and the title fail: treat as
  [UNRESOLVED](#unresolved). Fabricated references often pair a real-looking
  title with an invented DOI; the DOI failing is the tell.

### TITLE_MISMATCH

The DOI/ID resolves to a *different paper* (similarity < 0.60). This is
usually a copy-paste error (DOI of the paper above/below in some listing) or
a hallucinated DOI attached to a real title. Decide which side is right:
search the .bib title (is there a paper with this title and a different
DOI?), and resolve the DOI in a browser (what paper is it really?). Fix
whichever side the user actually meant to cite.

### AUTHOR_MISMATCH

First author's family name differs between .bib and the canonical record.
After ruling out the false positives below, this means the entry attributes
the paper to the wrong people — a credibility-killer in front of a reviewer
who knows the area. Replace the author list from the canonical record.

### YEAR_MISMATCH

More than ±1 year apart. Common honest causes: citing the arXiv year for the
published version (or vice versa), or confusing a journal's volume year with
publication year. Set the year to match the version actually cited — if
`booktitle`/`journal` names the venue, use the venue's year.

### RETRACTED

A retraction notice exists (the script prints the notice DOI), or the
publisher renamed the record "RETRACTED ARTICLE: ...". Required handling:

1. Tell the user verbatim, with the notice DOI. Do not soften it.
2. Default action: remove the citation and adjust any claim that leaned on
   it (the claim may now be unsupported — say so).
3. If the user must cite it (history-of-science, studying the retraction
   itself), keep it but mark it: `note = {Retracted; see
   doi:10.xxxx/notice}` and make sure the prose acknowledges the retraction.
4. `EXPRESSION_OF_CONCERN` (WARN) gets the same conversation at lower
   urgency: flag it, let the user decide, suggest a sturdier alternative if
   one exists.

### Duplicates

- **DUPLICATE_KEY** — BibTeX silently drops one definition; which one wins
  depends on the tool. Rename one key and update its `\cite` commands.
- **DUPLICATE_DOI / DUPLICATE_TITLE** — same paper under two keys (classic
  cause: one teammate added the arXiv version, another the published one).
  Keep the published version, delete the other entry, and repoint all
  `\cite` commands to the surviving key (`grep -rn '\\cite[a-z]*{.*oldkey'
  *.tex` to find them).

### Malformed identifiers

- **MALFORMED_DOI** — DOIs match `10.NNNN/suffix`. Strip URL prefixes
  (`https://doi.org/`), `doi:` labels, and trailing punctuation; if what
  remains still is not a DOI, treat as DOI_NOT_FOUND.
- **MALFORMED_ARXIV_ID** — valid shapes are `2104.12345` (optionally `v2`)
  or old-style `cs.DB/0123456`. Fix the `eprint` field; the
  `archivePrefix = {arXiv}` field should accompany it.

## WARN flags

| Flag | Meaning | Action |
|---|---|---|
| POSSIBLE_ID_TYPO | Bad identifier, but the title exists; canonical DOI printed | Replace identifier from canonical record |
| MISSING_DOI | Entry resolved via search; a DOI exists | Add the printed `doi = {...}` — makes future verification unambiguous |
| TITLE_PARTIAL_MATCH | Similarity 0.60–0.85 | Usually subtitle dropped, "RETRACTED" prefix, or LaTeX braces; align with canonical title |
| AUTHOR_LIST_DIFFERS | First author matches; list incomplete or extra names | Complete the list from the canonical record, or end with `and others` deliberately |
| VENUE_MISMATCH | Venue strings disagree | Check the [venue-alias problem](verification-sources.md#the-venue-alias-problem) before changing anything — most hits are aliases |
| NOT_IN_INDEXES | `@techreport`/`@phdthesis` etc. not indexed | Normal for these types; verify by hand against the institution's page, add `url = {...}` |
| MISSING_FIELDS | Required fields for the entry type absent | Fill from canonical record; venues' bib styles error or render badly without them |
| IMPLAUSIBLE_YEAR | Not a 4-digit year in 1900..next year | Fix the typo |
| EXPRESSION_OF_CONCERN | Publisher signaled doubts | See [RETRACTED](#retracted), point 4 |

## INFO flags

- **UNVERIFIABLE_TYPE** — websites/software (`@misc` with only a URL).
  Scholarly indexes cannot confirm these; open the URL, confirm it is live
  and says what the entry claims, prefer adding `urldate = {YYYY-MM-DD}`.
- **RESOLVED_VIA_SEARCH** — no identifier in the entry; matched by title.
  Trust, but add the suggested DOI (see MISSING_DOI).
- **HAS_CORRECTION** — an erratum exists. Usually fine to cite the original;
  mention the erratum to the user if the cited claim might be the corrected
  part.

## Known false positives

- **Online-first vs print year**: Crossref `issued` can be one year earlier
  than the print year a .bib cites. The script tolerates ±1; do not "fix"
  these without checking.
- **arXiv vs published version**: preprint year < venue year. If the entry
  has a real `booktitle`/`journal`, the venue record is authoritative — the
  script already prefers DBLP/Crossref in that case.
- **Venue aliasing**: see
  [verification-sources.md](verification-sources.md#the-venue-alias-problem).
- **Author-list truncation**: `and others` is legitimate BibTeX; the script
  only subset-checks then. `et al.` inside the author field is not — flagged
  under MISSING_FIELDS.
- **Diacritics and LaTeX accents**: `G{\"o}del` vs `Gödel` compare equal
  after normalization; if an AUTHOR flag involves accents, suspect a deeper
  mismatch, not the accent.
- **Mononyms and consortia** ("DeepMind Team", "The HDF Group"): family-name
  heuristics are unreliable — verify by eye before editing.
- **Very short titles** ("Attention", "GPT-4"): fuzzy matching is weak below
  ~15 characters; confirm short-title matches manually.

## The fix workflow, end to end

```bash
# 1. Full check, machine-readable report for the calling skill
python3 scripts/check_bibtex.py refs.bib --json /tmp/citecheck.json

# 2. For each broken entry: fetch the canonical BibTeX
curl -sL -H "Accept: application/x-bibtex" "https://doi.org/10.1145/1327452.1327492"
curl -s "https://dblp.org/rec/journals/cacm/DeanG08.bib"

# 3. Replace the entry body, KEEP the original citation key, show the diff

# 4. Re-verify just the fixed entries
python3 scripts/check_bibtex.py refs.bib --key dean2008mapreduce --refresh

# 5. Final gate: full pass, strict mode for submission-critical runs
python3 scripts/check_bibtex.py refs.bib --strict && echo "GATE PASSED"
```
