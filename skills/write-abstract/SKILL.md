---
name: write-abstract
description: Writes, rewrites, and lints venue-aware paper abstracts and prepares abstract-registration packages. Enforces venue length norms (e.g. LNCS 150-250 words), generates the correct keywords block (ACM CCS Concepts, IEEE Index Terms, LNCS \keywords, or none for NeurIPS-style), structures the abstract as motivation-gap-approach-results-impact, and builds the abstract-registration card (title, abstract, authors, topics, conflicts/COI, deadline countdown) for venues with a separate abstract deadline. Use when the user asks to write, revise, shorten, lengthen, or polish an abstract; asks about abstract word limits, CCS concepts, index terms, or keywords; or needs to register an abstract / meet an abstract-registration deadline (NeurIPS, ICML, KDD, CVPR, CHI, SIGSPATIAL) before the full-paper deadline.
---

# Write Abstract

Produce a venue-compliant abstract — right length, right keywords block,
five-move structure, verified numbers only — and, when the venue has a
separate abstract-registration deadline, the complete registration card
(title, abstract, authors, topics, COI list) ready to paste into the
submission form.

## When to use

- Drafting or rewriting an abstract for a specific venue or template family
  (acmart / IEEEtran / llncs / NeurIPS-style).
- Fitting an abstract to a word limit, or adding the missing CCS Concepts /
  Index Terms / keywords block.
- An abstract-registration deadline is approaching and the user must
  register title + abstract + topics + conflicts before the paper PDF.

Related skills: `tailor-to-venue` (whole-paper retargeting), `parse-cfp`
(build a missing venue profile), `preflight-check` (final desk-reject lint),
`verify-citations` (gate for any reference work).

## Inputs

- The draft (main `.tex` preferred — keyword blocks are checked in context)
  or the abstract as plain text; or, for a fresh draft, the paper's
  contributions and verified results from the user.
- Venue profile: `venues/conferences/<id>.yml` or `venues/families/<f>.yml`
  (schema: `venues/schema.yml`). If neither exists, do NOT invent venue
  facts — run `parse-cfp` on the CFP URL or quote the live CFP directly.

## Process

### 1. Resolve venue norms, then re-verify (mandatory)

Load the profile (`format.abstract_words`, `format.keywords`,
`deadlines.abstract/paper` + `timezone`, `review.blind`). Profiles go
stale: before the user relies on a word limit, keyword requirement, or any
deadline, re-verify it against the live `cfp_url` and say what was checked
and when. If the CFP cannot be fetched, label every profile-derived fact
"UNVERIFIED — confirm on CFP". When `abstract_words` is null, present
150-250 words as a convention, never as a venue rule — see
[references/venue-norms.md](references/venue-norms.md).

### 2. Draft (or diagnose) with the five-move structure

Build the abstract as motivation → gap → approach → results → impact, with
family-appropriate tone and word budget per move:
[references/abstract-structure.md](references/abstract-structure.md).

Hard rules while drafting:

- Results numbers come from the draft's evaluation or the user — NEVER
  invent, round up, or extrapolate. The quantified result is the abstract's
  single most-predictive surface; the results→impact arc cannot score in
  the top band without it. If results are pending, leave exactly ONE typed
  quantified-result slot — a structured contract with metric name, units,
  sign/direction, and comparison target, e.g. `[RESULT: +XX% Recall@20 vs
  best hashing baseline under matched budget]` — never a bare `[RESULT: ...]`
  or free-text prose. Any bracketed slot leaves the abstract
  DRAFT-not-submittable; bind every slot with a verified value before
  delivery. Contract details: [references/abstract-structure.md](references/abstract-structure.md).
- No `\cite`, `\ref`, math, or undefined acronyms in the abstract (it ships
  as standalone metadata). Any prior work named in prose that needs a
  citation elsewhere goes through `verify-citations`.
- At double-blind venues, no identity leaks (institution, grant numbers,
  "our previous work", personal repo URLs).

For rewrites, run the linter first and let its findings drive the edit.

### 3. Lint deterministically

Run from the repo root (or pass absolute paths):

```
python3 skills/write-abstract/scripts/abstract_check.py <main.tex|abstract.txt|-> \
    --venue venues/conferences/<id>.yml [--strict]
```

Reports length vs the venue limit, keywords-block presence/shape,
self-containedness (cite/ref/math/URL/placeholders), the typed
quantified-result-slot invariant, the acmart abstract-before-`\maketitle`
gotcha, and lexical move signals. Fix RISK and WARN findings, re-run until
RISK-free. `--venue` also accepts a family profile when no conference
profile exists.

The slot gate is non-overridable: the script prints an open-slot count and
**hard-fails with a non-zero exit whenever any `[LABEL: ...]` slot remains**
(independent of `--strict`), marking the abstract DRAFT-not-submittable. A
results-pending draft passes only once its one typed RESULT slot — and any
`[CONFIRM: ...]` slots — are bound with verified values written into the
prose. Never satisfy the gate by inventing a number.

### 4. Generate the keywords block

Pick keywords with the user (problem + technique + domain; mirror the CFP
topic list where honest — guidance in
[references/keywords-blocks.md](references/keywords-blocks.md)), then emit
the family-correct LaTeX:

```
python3 skills/write-abstract/scripts/keywords_block.py \
    --venue venues/conferences/<id>.yml --keywords "kw1, kw2, kw3"
```

For ACM venues the script emits a CCS skeleton whose concept ids MUST be
filled from the official tool at <https://dl.acm.org/ccs> — never fabricate
CCSXML concept ids. For NeurIPS-style venues it correctly emits no block
(topics live in the submission form).

### 5. Build the registration card (when there is an abstract deadline)

If `deadlines.abstract` is set — NeurIPS, ICML, KDD, CVPR, CHI, SIGSPATIAL
all register abstracts 2-7 days before the paper — assemble everything the
form will ask for:

```
python3 skills/write-abstract/scripts/abstract_registration.py \
    --venue venues/conferences/<id>.yml --title "<title>" \
    --abstract-file <main.tex|abstract.txt> \
    --authors "Name <email> (Affiliation)" --topics "t1; t2" \
    [--coi-file conflicts.txt] [--track <Track>] [--out abstract-registration-<id>.md]
```

The card includes the deadline countdown with the venue's timezone (watch
for non-AoE venues — SIGSPATIAL is Pacific Time), placeholder-policy
warnings (KDD/AAAI penalize dummy abstracts), a COI checklist built from
the user's recent co-authors/advisors/institutions, and the submission
system URL. Help the user fill the COI list from their actual recent
papers; the venue form's window and categories are authoritative. Norms:
[references/venue-norms.md](references/venue-norms.md).

### 6. Deliver

Present the final abstract (LaTeX + a plain-text form version), the
keywords block, the linter's clean report, and — if applicable — write
`abstract-registration-<venue-id>.md` next to the draft. State explicitly
that the user registers/submits themselves.

## Output

- The abstract in LaTeX and plain text, RISK-free and with zero open slots
  under `abstract_check.py` for the target venue (a results-pending draft is
  delivered explicitly labeled DRAFT-not-submittable until its typed RESULT
  slot is bound).
- The venue-correct keywords block (or a note that the family has none).
- When the venue registers abstracts: `abstract-registration-<venue-id>.md`
  with title, abstract, authors, topics, COI checklist, deadline math, and
  a verification record.

## Guardrails

- Never fabricate results, numbers, or claims for the abstract; unverified
  values stay as the one typed quantified-result slot (metric, units,
  sign/direction, comparison target), and the abstract ships labeled
  DRAFT-not-submittable until every slot is bound from real data.
- Never fabricate citations or CCS concept ids; citations go through
  `verify-citations`, CCS ids come from dl.acm.org/ccs only.
- Never state venue limits or deadlines from memory — profile + live-CFP
  verification only; unverifiable facts are labeled UNVERIFIED.
- Never register, submit, or enter anything into any submission system on
  the user's behalf; deliverables stop at the card.
- Never paste another paper's abstract text as a template; exemplar study
  happens transiently via the `study-exemplars` skill.
