# Pipeline map — stage → skill → exit criterion → checkpoint question

The reviewable roadmap `orchestrate-paper` plans against. Each row is one stage:
which sub-skill(s) run, the **measurable exit criterion** that must pass before
advancing (an external signal, not the model's self-judgment — see
[`verification-signals.md`](verification-signals.md)), and the **checkpoint
question** the author answers before the next stage starts.

Stages mirror the lifecycle partition used in `paper-workspace/`:
`research → writing → review → submission → presenting`. Not every paper runs
every stage; the orchestrator picks the subset that fits the draft's current
state (use `pipeline_state.py next` to see the next applicable stage). Skill
names below are exactly the directories under `skills/` — link in to read each.

## 0. Goal + positioning (always first)

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`paper-profile`](../../paper-profile/SKILL.md) | `.paper-memory/profile.yml` exists with `vertical`, `contribution_type`, `audience`, `constraints` filled | "Is this how you want the paper positioned (vertical, contribution type, audience tier, risk appetite)?" |
| [`select-venue`](../../select-venue/SKILL.md) *(only if target is "help me pick")* | A ranked venue+track recommendation written to `.paper-memory/decisions.md` with rationale + fallback | "Target VENUE/track over the alternatives — agree, or weigh a different one?" |

## 0b. Lock the live requirements (gate — re-verify every cycle)

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`parse-cfp`](../../parse-cfp/SKILL.md) | A year-versioned `venues/conferences/<venue>-<year>.yml` written from the **live** CFP, with the `verified:` provenance block (URL + date) populated | "These are the deadline, page limit, blinding level, template, checklist, and any artifact track I read live from the CFP — confirm before we build on them?" |

This is a **hard stop**. The whole plan keys off these facts; an unverified one
is how a paper gets desk-rejected (principle #1, #5). Re-fetch even if a cached
profile exists. Note any artifact-evaluation / camera-ready deadlines as a
*separate* post-acceptance track.

## 1. Research

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`find-papers`](../../find-papers/SKILL.md) | A deduplicated candidate set written to `paper-workspace/research/`; counts logged in `INDEX.md` | "Does this candidate set cover the right subfields, or is a line of work missing?" |
| [`fetch-paper`](../../fetch-paper/SKILL.md) | Summaries of the key works fetched from legal OA sources, transient (never bundled) | "Are these the works the paper must engage with?" |
| [`literature-review`](../../literature-review/SKILL.md) | A review note passing `check_review.py` (coverage/claim-extraction checks) | "Does the synthesis frame our contribution correctly against prior work?" |
| [`study-exemplars`](../../study-exemplars/SKILL.md) | A style-and-structure brief from venue best/top-cited papers (metadata + original analysis only) | "Should the draft follow this venue's structural pattern, or deviate deliberately?" |

## 2. Writing

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`write-abstract`](../../write-abstract/SKILL.md) | Abstract draft within the venue's word/char bound (checked against the live profile) | "Does the abstract state the contribution as a claim, accurately, without over-reach?" |
| [`refactor-structure`](../../refactor-structure/SKILL.md) *(if the argument arc is off)* | An outline/flow report from `outline_extract.py`; required sections present in a defensible order (distinct from prose-level `polish-prose` and template-level `tailor-to-venue`) | "Is the story built in the right order — does each section do its job before the next?" |
| [`draft-related-work`](../../draft-related-work/SKILL.md) | A related-work draft; every citation it adds resolves via `verify-citations` | "Is each cited work characterized fairly, and is our delta clear?" |
| [`match-style`](../../match-style/SKILL.md) | A style signature recorded in `profile.yml` (`author`/`venue`/`merged`) | "Match your own voice, the venue register, or a merge?" |
| [`polish-prose`](../../polish-prose/SKILL.md) | `texprose.py` lint counts (hedges/passive/readability) improve vs the prior pass; stop on diminishing returns | "Polished within your voice — accept these edits, or did any drift your meaning?" |
| [`polish-tables-figures`](../../polish-tables-figures/SKILL.md) | `check_floats.py` clean (no undefined refs, captions present, floats placed) | "Do the figures/tables read clearly and carry the result?" |

## 3. Review (pre-submission self-review)

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`verify-citations`](../../verify-citations/SKILL.md) | `check_bibtex.py` finds no fabricated/unresolvable/retracted entries; DOIs resolve | "Citations all resolve to real records — any you want to swap (e.g. arXiv → published)?" |
| [`verify-claims`](../../verify-claims/SKILL.md) | `claim_audit.py`: every novelty/superiority/empirical claim traces to a real result, table/figure, or citation — none unsupported (distinct from `verify-citations`, which checks the references, not the claims) | "Does every claim of novelty or improvement trace to evidence we actually have?" |
| [`check-originality`](../../check-originality/SKILL.md) | Overlap / self-recycling report below the integrity threshold | "Any flagged overlap to rephrase or cite before review?" |
| [`preflight-check`](../../preflight-check/SKILL.md) | `check_sections.py` + page/anonymization checks pass against the **live** profile (no desk-reject triggers) | "No desk-reject blockers remain — agree we're compliant with the live CFP?" |
| [`simulate-reviewers`](../../simulate-reviewers/SKILL.md) | Mock reviews + rubric scores written to `review/`; weakest dimensions named | "Which reviewer concern do we address before submitting?" |
| [`benchmark-paper`](../../benchmark-paper/SKILL.md) | Venue-fit scorecard; weakest dimensions ranked | "Is the venue fit strong enough, or should we revisit the target?" |
| [`assess-paper`](../../assess-paper/SKILL.md) | A single `paper-health-report.md` consolidating the above (strengths first, gates, do-next) | "Given the health report, are we go for submission, or is there a must-fix first?" |

## 4. Submission

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`tailor-to-venue`](../../tailor-to-venue/SKILL.md) | A tailored draft conforming to the live template + required sections/checklist | "Tailored to VENUE's template and required sections — review the changes?" |
| [`anonymize-paper`](../../anonymize-paper/SKILL.md) *(if double/triple-blind)* | Anonymization linter clean (PDF metadata, acks, self-citation phrasing, repo links) | "Anonymization is clean per the linter — confirm nothing identifying remains?" |
| [`plan-submission`](../../plan-submission/SKILL.md) | A timeline written to `submission/` covering paper **and** any separate artifact/camera-ready deadlines | "Does this timeline match the real deadlines (AoE vs local), including the artifact track?" |

**Submission itself is the author's action.** The orchestrator hands over a
ready package; it never uploads to OpenReview/CMT/HotCRP/PCS (principle #6).

## 4b. Artifact / reproducibility track (empirical papers; runs in parallel, own deadline)

For papers with code/data, the artifact-evaluation track is a **separate
post-acceptance (or submission-time) deadline** — never folded into the paper
deadline. The orchestrator runs it only when an artifact track applies per the
live CFP (locked in Stage 0b).

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`test-research-code`](../../test-research-code/SKILL.md) | `repro_check.py`: a smoke test runs the real pipeline on a tiny input with pinned seeds; environment captured | "Does the code run deterministically on a tiny input from a clean environment?" |
| [`refactor-research-code`](../../refactor-research-code/SKILL.md) | `release_audit.py` clean: runnable for an evaluator, **no result changed** | "Is the code release-ready without altering any reported result?" |
| [`verify-results`](../../verify-results/SKILL.md) | `compare_metrics.py`: the paper's reported numbers reproduce from the artifact within tolerance (distinct from `verify-claims`, which audits the prose claims) | "Do the numbers in the paper actually reproduce from the code — any mismatch to reconcile?" |
| [`prepare-artifacts`](../../prepare-artifacts/SKILL.md) | `check_artifact.py` + `badge_advisor.py`: artifact appendix + badge requirements (archival DOI, README, env) met against the **live** artifact-track call | "Is the artifact packaged to the badge level you're targeting, per the live call?" |

## 5. Post-decision (only after a real notification)

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`triage-reviews`](../../triage-reviews/SKILL.md) | Reviews bucketed into addressable points with a response plan | "Is this the right reading of what each reviewer is actually asking?" |
| [`write-rebuttal`](../../write-rebuttal/SKILL.md) | A rebuttal within the venue's exact format (e.g. CVPR 1-page) and word/char bound | "Does the rebuttal answer the load-bearing concerns without over-promising? (hard stop before it goes out)" |
| [`prepare-camera-ready`](../../prepare-camera-ready/SKILL.md) | Camera-ready checklist clean against the live author kit; artifact-badge requirements (archival DOI, appendix) met if applicable | "Camera-ready + artifact requirements satisfied per the live author kit?" |

## 6. Presenting

| Sub-skill | Exit criterion (measurable) | Checkpoint question |
|---|---|---|
| [`make-slides`](../../make-slides/SKILL.md) / [`make-poster`](../../make-poster/SKILL.md) | Deck/poster draft in `presenting/` | "Does this carry the story for the talk format and time?" |
| [`write-talk-script`](../../write-talk-script/SKILL.md) | A talk script within the time budget | "Does the script land the contribution in the allotted minutes?" |
| [`rehearse-qa`](../../rehearse-qa/SKILL.md) | Q&A drills graded by `grade_answers.py` | "Are you ready for the likely hard questions?" |

## How the orchestrator uses this table

1. `pipeline_state.py next` reports the next applicable stage given what's
   already in `INDEX.md`.
2. Run that stage's sub-skill(s); each writes its artifact + an `INDEX.md` line.
3. Check the **exit criterion** with the external signal — not by asking the
   model whether it thinks it's done.
4. Run `reflect-and-improve`: confirm the measurable target improved; never
   accept a regression.
5. Ask the **checkpoint question**; record the author's decision (and any
   venue/positioning choice → `decisions.md`); only then `advance`.

The table is a default order, not a straitjacket. Skip inapplicable stages,
loop back when a later check exposes an earlier gap (e.g. `simulate-reviewers`
reveals a missing baseline → return to research), and reorder for a journal
(revise-and-resubmit replaces rebuttal). Every reorder is shown to the author,
not taken silently (principle #2).
