# Venue register: family norms, AI-disclosure policy, terminology workflow

How edit pass D (SKILL.md step 8) adapts the prose to where the paper is
going. Family profiles live in `venues/families/`, conference profiles in
`venues/conferences/` (schema: `venues/schema.yml`). Profiles are a
starting point, never ground truth — **re-verify anything decision-grade
against the live `cfp_url`, especially `review.llm_policy`.**

## Contents

- [Reading the profile](#reading-the-profile)
- [Register by venue family](#register-by-venue-family)
- [Person and voice](#person-and-voice)
- [Tense discipline](#tense-discipline)
- [Spelling convention](#spelling-convention)
- [Formality floor](#formality-floor)
- [AI-use disclosure — non-negotiable](#ai-use-disclosure--non-negotiable)
- [Terminology table and glossary workflow](#terminology-table-and-glossary-workflow)

## Reading the profile

From `venues/conferences/<venue>-<year>.yml` take:

- `family` → the register row below.
- `review.llm_policy` → the venue's stated AI-use rules (verbatim summary
  in the profile; the live CFP wins on any conflict).
- `format.required_sections` → some venues require an AI-use
  acknowledgement section; polishing must not delete or contradict it.

No profile? Ask the user for the target venue, or proceed with the
defaults: consistent American spelling, first-person plural, the register
already dominant in the draft.

## Register by venue family

| Family | Register notes |
|---|---|
| `neurips-style` (NeurIPS/ICML/ICLR) | Direct, dense, first-person plural. Contributions as a bullet list in §1 is the norm. Checklist sections have their own factual register — answer plainly, no rhetoric. Limitations honesty is explicitly reviewed. |
| `acm-sigconf` (SIGMOD/KDD/SIGSPATIAL/WWW...) | Systems register: mechanism and measurement up front, present tense for the system. Marketing adjectives ("blazing", "powerful") read especially badly here; numbers are the register. |
| `acm-manuscript-chi` (CHI/CSCW) | More discursive; first person accepted including "I" in single-author and positionality contexts; qualitative claims hedge differently (participant-grounded: "P3 reported...", not "users feel..."). Do not import quantitative claim style into qualitative findings. |
| `ieee-conf` / `ieee-journal` | Conservative formal register; third-person constructions more common historically but "we" is fully accepted; Index Terms vocabulary should match the prose terminology table. |
| `lncs` (Springer conferences) | Compact, formal; European authorship means British spelling appears often — either convention is fine, mixed is not. |
| `acm-journal` (TODS/TKDE-style journals) | Journal register: fuller related-work prose, explicit roadmap paragraphs accepted, less compression pressure than conferences — do not over-tighten into telegraphic style. |

These are conventions, not rules — when the user's community writes
differently, the community wins. Study 2-3 recent accepted papers from the
venue (`study-exemplars` does this legally, fetch-on-demand) when unsure.

## Person and voice

- **"We" is the modern default in CS** for any author count; many venues'
  own templates use it. Single-author papers: "we" is still common and
  safe; "I" is accepted at CHI-family venues; never mix the two.
- Active voice for contributions and decisions ("we chose X because"),
  passive acceptable in methods where the agent is obvious ("packets are
  routed...").
- Anonymized submissions: person conventions interact with blind review
  ("our prior work [3]" is a leak) — that is `anonymize-paper`'s job;
  flag it, do not fix it here.

## Tense discipline

The classic consistent scheme — deviations are fine if uniform:

- **Present** for the paper and the artifact: "Section 5 evaluates...",
  "SkewCache scores tiles by...".
- **Past** for what you did and what happened: "we ran each query ten
  times", "latency dropped".
- **Present** for established facts and prior-work claims that still hold:
  "LSM-trees amortize writes [12]".
- **Past or present perfect** for the history of the field: "early tile
  servers cached uniformly [3, 7]".

The tell to fix: tense drifting within one results paragraph ("the system
reduces... latency dropped... memory will decrease"). Pick the scheme,
sweep the section.

## Spelling convention

- IEEE and ACM production both default to **American** spelling; Springer
  accepts British or American, **consistent within the paper**.
- The linter (`terminology_check.py`) flags -ise/-ize family mixing and
  pair words (behaviour/behavior...). Resolution order: venue family
  default → majority form already in the draft → user preference.
- One exception: direct quotes and proper nouns ("Labour Force Survey")
  keep their original spelling; exclude them from the sweep.

## Formality floor

Regardless of family:

- No contractions ("don't" → "do not") in the paper body; fine in talk
  scripts (`write-talk-script` territory).
- No rhetorical questions as section openers more than once per paper.
- No second person ("you can see that..." → "Figure 3 shows...").
- Latin abbreviations: "e.g.", "i.e." in parentheticals are fine at most
  venues; spell out "et cetera" thoughts instead of trailing "etc." in
  claims.

## AI-use disclosure — non-negotiable

De-AI-ifying the prose changes the register, **not the provenance**. The
workflow:

1. Read `review.llm_policy` from the profile. Example (NeurIPS 2026
   profile): LLM use that is an important/original/non-standard component
   must be described; basic grammar assistance needs no documentation;
   authors remain fully responsible; LLMs may not be authors.
2. **Re-verify against the live `cfp_url`** — AI policies are the
   fastest-churning field in the schema and a stale policy summary is
   dangerous in both directions.
3. Map the user's actual usage to the policy's categories with them
   (drafting assistance vs method component vs grammar polish) and, where
   the venue wants it, draft an honest disclosure statement
   (`format.required_sections` may name a section for it).
4. If the user asks for polish *in order to avoid* a disclosure the venue
   requires: decline that goal explicitly, show the policy text, and offer
   the disclosure draft instead. Polishing for quality then proceeds as
   normal — the two are independent.

Never claim the polished text is "human-written" or "will pass AI
detectors"; both claims are unverifiable and the second is the wrong goal.

## Terminology table and glossary workflow

Edit pass C (SKILL.md step 7) ends in a decision table:

| Concept | Variants found (count) | Canonical | Why |
|---|---|---|---|
| dataset | dataset (14), data set (3), data-set (1) | dataset | majority + ACM norm |
| run time | runtime (6), run time (2), run-time (2) | runtime (n.), run-time (adj.) only if the user wants the grammatical split; else one form | user choice |
| ATC | defined twice, used in abstract before definition | define once at first body use; spell out in abstract | acronym discipline |

Persist it as `glossary.txt` next to the draft so the check is repeatable
across revisions and across co-authors:

```
# canonical = variant | variant
dataset = data set | data-set
runtime = run time | run-time
tile cache = tile-cache
```

Then enforce:

```
python3 scripts/terminology_check.py main.tex --glossary glossary.txt --strict
```

Acronym rules the table should encode: define at first use in the body
(the abstract is self-contained — either spell it out there or define it
there too); one expansion per acronym; drop acronyms used fewer than ~3
times; `--allow` the ones your community never expands (GPS, SQL, GPU
are already whitelisted in the script; extend per field).
