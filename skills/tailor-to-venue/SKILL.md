---
name: tailor-to-venue
description: Tailors a paper draft to a target venue and track by diffing it against a machine-readable venue profile. Produces a four-part tailoring plan - contribution reframing for the chosen track (research vs applications/industry vs demo vs short/vision), a page-budget cutting plan, a template/documentclass switch plan (acmart, IEEEtran, NeurIPS-style, llncs), and an anonymization sweep matched to the venue's blind level. Use when the user wants to adapt, retarget, resubmit, or port a paper to a different conference, journal, or track; fit a paper into a page limit ("cut to 10 pages"); switch LaTeX templates ("convert IEEEtran to acmart"); anonymize for double-blind review; or asks "make this fit SIGSPATIAL/NeurIPS/ICDE/KDD", "which track should this go to", or "retarget my rejected paper".
---

# Tailor to Venue

Diff a draft against a target venue's requirements and produce a concrete
**tailoring plan**: what to reposition, what to cut, what to reformat, and
what to anonymize — before any edit is made. This skill plans; the user (or a
follow-up request) executes the edits.

## When to use

- Retargeting a paper (new submission, rejection, or venue switch) to a
  different conference, journal, track, or page limit.
- Converting between template families (acmart / IEEEtran / NeurIPS-style /
  llncs) or between blind levels (single ↔ double ↔ triple).
- Deciding which track at one venue fits the work best.

Related skills: `parse-cfp` (build a missing venue profile), `select-venue`
(choose the venue first), `preflight-check` (final desk-reject lint before
submission), `prepare-camera-ready` (after acceptance).

## Inputs

- The draft: main `.tex` file (the scripts resolve `\input`/`\include`);
  optionally the compiled PDF and `.bib` files.
- Target venue profile: `venues/conferences/<venue-id>.yml` (schema:
  `venues/schema.yml`; family defaults merge automatically from
  `venues/families/`).
- Target track name, if the user has chosen one.

## Process

### 1. Resolve the venue profile

Find the profile in `venues/conferences/`. If none exists, do NOT invent
requirements — run the `parse-cfp` skill against the venue's CFP URL to
create one, or proceed with only facts quoted live from the CFP.

### 2. Re-verify against the live CFP (mandatory)

Profiles go stale and a wrong page limit causes a desk reject. Fetch the
profile's `cfp_url` and re-verify before relying on anything: page limits and
exclusions for the chosen track, deadlines and timezone, blind level,
template/documentclass invocation, and required sections. Note in the plan
what was verified and when; if the live CFP contradicts the profile, the CFP
wins — flag the profile for update. If the CFP cannot be fetched, mark every
profile-derived fact "UNVERIFIED — confirm on CFP" in the plan.

### 3. Pick the track with the user

List the profile's tracks with their page limits (the venue diff report
includes this table). If the user has not chosen, recommend one based on the
work's strongest claim — see
[references/contribution-reframing.md](references/contribution-reframing.md)
for what each track rewards — and confirm before planning.

### 4. Run the deterministic diff

Run from the repo root (or pass absolute paths):

```
python3 skills/tailor-to-venue/scripts/venue_diff.py <main.tex> --venue venues/conferences/<id>.yml --track <Track>
```

This reports template/option gaps, required-section gaps, abstract length,
author-block vs blind level, page-limit context, and the venue facts
(submission system, deadlines, LLM policy) to carry into the plan.

Then size the page budget:

```
python3 skills/tailor-to-venue/scripts/page_budget.py <main.tex> --venue venues/conferences/<id>.yml --track <Track>
```

And scan anonymization at the venue's blind level (add `--pdf <paper.pdf>`
and `--bib <refs.bib>` when available):

```
python3 skills/tailor-to-venue/scripts/anon_sweep.py <main.tex> --venue venues/conferences/<id>.yml
```

All three print Markdown and exit 2 with a clear message on bad input. Treat
script outputs as signals: the compiled PDF and the live CFP are ground truth.

### 5. Build the four-part plan

Turn the script reports into prose plans using the references:

1. **Contribution reframing** — retitle, re-abstract, rewrite contribution
   bullets and evaluation emphasis for the chosen track:
   [references/contribution-reframing.md](references/contribution-reframing.md)
2. **Page-budget cutting plan** — ordered ladder from structural exports to
   line-level compression, with estimated savings per step and the forbidden
   moves listed: [references/page-budget-cutting.md](references/page-budget-cutting.md)
3. **Template switch plan** — only if venue_diff reports a class/option gap;
   per-direction breakage list and bibliography mapping:
   [references/template-switching.md](references/template-switching.md)
4. **Anonymization sweep plan** — fix strategy per leak category, plus the
   beyond-the-PDF checklist and a `camera-ready-restore.md` for removed
   content: [references/anonymization-sweep.md](references/anonymization-sweep.md)

If the draft needs new citations from the target community, route every one
through the `verify-citations` skill — never add an unverified reference.

### 6. Deliver the plan

Write `tailoring-plan-<venue-id>-<track>.md` next to the draft with sections:

1. Verification record — what was checked against the live CFP, when, and
   any profile contradictions found.
2. Track fit and contribution reframing (with rewritten title/abstract/
   contribution-bullet drafts marked as proposals).
3. Page-budget cutting plan (current estimate → target, ordered cuts with
   estimated savings, restore list).
4. Template switch plan (or "no switch needed").
5. Anonymization sweep plan (findings with fixes, beyond-the-PDF checklist).
6. Submission logistics — system, URL, deadlines with timezone, rebuttal
   format, LLM-policy disclosure needs.

Offer to execute the plan step by step; after edits, recommend
`preflight-check` as the final gate.

## Output

A reviewed, verification-stamped `tailoring-plan-<venue-id>-<track>.md`, plus
the three raw script reports on request. No draft files are modified by this
skill unless the user asks for execution of specific plan items.

## Guardrails

- Never submit to any submission system on the user's behalf; stop at the plan.
- Never state venue requirements from memory — profile + live-CFP
  verification only; unverifiable facts are labeled UNVERIFIED.
- Never fabricate or hand-type citations; new references go through
  `verify-citations`.
- Never plan template tampering (negative `\vspace`, margin/font tricks) to
  meet a page limit — these are desk-reject triggers.
- Do not paste text from other authors' papers into the draft; exemplar
  study happens transiently via the `study-exemplars` skill.
