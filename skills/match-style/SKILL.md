---
name: match-style
description: Aligns a draft to a target writing voice — the author's own previous papers, a target venue's published style, or both — so it reads as consistent, native to the venue, and unmistakably the author's. Use when a researcher says "make this match my other papers", "use my usual writing style", "make it sound like my group's work", "match the style of this venue", "align terminology with my prior work", or "make my co-authored draft read consistently". Extracts a measurable style signature (terminology, sentence rhythm, hedging, connective habits, structure) from a corpus the author supplies, diffs the draft against it, and drives a section-by-section alignment that never changes a technical claim, number, or citation. Only the author's own papers and open-access venue exemplars are used; nothing copyrighted is bundled. Trigger words - match my style, my writing voice, sound like my papers, venue style, consistent terminology, align voice, my group's style.
---

# Match Style

Aligns a draft to a **target voice** without touching its substance. Three modes, combinable:

- **author voice** — match the researcher's own prior papers (terminology, rhythm, hedging, structure) so a new draft reads as theirs.
- **venue register** — match the published style of the target venue (via [`study-exemplars`](../study-exemplars/SKILL.md)).
- **co-author merge** — make a multi-author draft read in one consistent voice instead of a patchwork.

This is part of the acceptance-maximizing toolkit, alongside [`polish-prose`](../polish-prose/SKILL.md) (de-AI-ify + tighten), [`benchmark-paper`](../benchmark-paper/SKILL.md) (venue-fit score), [`simulate-reviewers`](../simulate-reviewers/SKILL.md) (content critique), and [`preflight-check`](../preflight-check/SKILL.md) (desk-reject defects). **Be honest with the user: no rewrite guarantees acceptance.** What style alignment buys is consistency, venue fit, and readability — real but bounded contributors to how a paper is received.

## When to use vs. polish-prose

- `polish-prose` fixes *objective* problems (AI tells, wordiness, inconsistent terms) against general/venue norms.
- `match-style` aligns to a *specific target voice* you provide (your corpus and/or venue exemplars). Run `polish-prose` first to clean, then `match-style` to align.

## Inputs

- The draft: `.tex` / `.md` / text.
- For **author voice**: paths to the author's own prior papers (`.tex`/`.pdf`/`.txt`). **These must be the author's own work** — see Guardrails.
- For **venue register**: the target venue id → `venues/` profile → `study-exemplars` corpus.
- Optional: a glossary of preferred terms/acronyms.

## Process

1. **Build the style signature of the target.**
   - Author voice: run `python3 scripts/style_signature.py --corpus <files...> --out author.json`. It measures terminology frequency, mean/var sentence length, hedging density, connective usage (however/moreover/thus…), passive-voice rate, citation density, section-heading vocabulary.
   - Venue register: run the same over the `study-exemplars` corpus (open-access only) → `venue.json`.
2. **Profile the draft** the same way: `python3 scripts/style_signature.py --corpus <draft> --out draft.json`.
3. **Diff** draft vs target(s): `python3 scripts/style_signature.py --compare draft.json --against author.json [venue.json] --out style-gap.md`. This reports where the draft deviates (e.g. "you use 'we propose' 0×; your prior papers average 3×", "hedging 2× higher than venue exemplars").
4. **Surface conflicts.** When author voice and venue register disagree (e.g. your habitual first-person vs a venue that prefers passive), present the trade-off — do not silently pick one.
5. **Align the draft section by section**, guided by `style-gap.md` and the rewrite norms in [references/style-dimensions.md](references/style-dimensions.md). Preserve every number, result, claim, and citation verbatim. Keep a change log.
6. **Verify nothing substantive moved**: re-run `verify-citations` if references were near edits; diff claims/numbers before/after.

## Output

- `style-gap.md` — the measured deviations (draft vs author and/or venue), each with the numbers behind it.
- The aligned draft (or a section-by-section diff for the author to accept).
- A short note on any author-vs-venue conflicts and which way each was resolved.

## Guardrails

- **Only the author's own papers** are used for the author-voice corpus. If a user supplies someone else's paper to "write like them", decline the copyright/impersonation request and offer venue-register matching from open-access exemplars instead.
- Venue exemplars are fetched on demand from open-access sources and processed transiently (see `study-exemplars`) — never bundled or stored.
- Style only: never alter a technical claim, number, result, or citation. Flag, don't fix, anything that would.
- No acceptance promises. Frame outcomes as consistency and venue fit, not a guaranteed decision.
- Respect the venue's AI-use disclosure policy (in the venue profile); never use style-matching to evade an AI-detection or disclosure requirement.
