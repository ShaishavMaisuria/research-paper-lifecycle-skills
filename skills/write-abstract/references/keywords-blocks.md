# Keywords blocks by venue family

Every family typesets "what is this paper about" differently. The profile
field `format.keywords` (in `venues/`) names the style; this file says how
to produce each one. `scripts/keywords_block.py` emits the skeletons.

## Contents

- [ACM CCS Concepts (`ccs-concepts`)](#acm-ccs-concepts-ccs-concepts)
- [IEEE Index Terms (`ieee-index-terms`)](#ieee-index-terms-ieee-index-terms)
- [LNCS keywords (`lncs-keywords`)](#lncs-keywords-lncs-keywords)
- [No block (`none`, NeurIPS-style)](#no-block-none-neurips-style)
- [Choosing good free-text keywords](#choosing-good-free-text-keywords)

## ACM CCS Concepts (`ccs-concepts`)

ACM venues (acmart: sigconf, manuscript/CHI, ACM journals) require BOTH:

1. **CCS Concepts** — a `\begin{CCSXML}...\end{CCSXML}` block plus
   `\ccsdesc[significance]{...}` lines, placed after the abstract and before
   `\maketitle`/keywords. The XML carries numeric `concept_id`s from the
   2012 ACM Computing Classification System.
2. **Author keywords** — `\keywords{a, b, c}` (free text, comma-separated).

**Never hand-write or guess concept ids.** The only correct source is the
official generator:

1. Open <https://dl.acm.org/ccs>, search, pick 1-4 concepts (most papers: 2-3).
2. Assign significance per concept: `500` primary (exactly one), `300`
   secondary, `100` minor.
3. Click "Generate CCS Codes"; paste the XML and the `\ccsdesc` lines into
   the paper verbatim.

`python3 scripts/keywords_block.py --style ccs --keywords "..."` emits a
skeleton whose placeholders the user fills from the tool; the linter flags
unfilled placeholders as RISK. CCS is mandatory at camera-ready (TAPS
rejects without it) and many ACM venues expect it at submission — check the
venue profile's `format.required_sections`.

## IEEE Index Terms (`ieee-index-terms`)

IEEEtran papers and IEEE journals place Index Terms directly after the
abstract:

```latex
\begin{IEEEkeywords}
caching, query processing, spatial databases
\end{IEEEkeywords}
```

Conventions: alphabetical order; draw terms from the IEEE Thesaurus where a
matching term exists (editors normalize to it); 3-6 terms typical. IEEE
journals additionally make you pick taxonomy keywords inside ScholarOne at
submission — that is a form step, not a LaTeX block (see the
`ieee-journal` family profile). Generate with
`python3 scripts/keywords_block.py --style ieee --keywords "..." --sort`.

## LNCS keywords (`lncs-keywords`)

Springer LNCS (llncs.cls) places keywords immediately after the abstract,
separated by `\and` (rendered as middle dots):

```latex
\keywords{Moving Objects \and Spatial Indexing \and Sketches}
```

Springer guidance and most LNCS CFPs ask for **3-6 keywords**; the abstract
itself is mandated at **150-250 words** (the one family with a hard number —
see the `lncs` family profile). Capitalize each keyword's first word.
Generate with `python3 scripts/keywords_block.py --style lncs --keywords "..."`.

## No block (`none`, NeurIPS-style)

NeurIPS/ICML/ICLR-style templates have **no in-paper keywords or CCS
section**. Topics ("subject areas") are selected in the OpenReview form at
abstract-registration time and double as reviewer-matching signals — choose
the primary area for the reviewer pool you want, not just topical fit.
If a draft ported from an ACM/IEEE template still carries a keywords block,
remove it (the linter reports this as INFO).

## Choosing good free-text keywords

- Mirror the venue's CFP topic list where honest — track chairs and TPC
  matching tools key off them.
- Include: the problem (1-2 terms), the technique (1-2), the domain (1).
- Avoid terms so broad they match everything ("machine learning" at NeurIPS)
  and coined names nobody searches (your system's name is not a keyword).
- Keep keywords consistent with the title and abstract vocabulary — search
  engines and reviewers see all three together.
