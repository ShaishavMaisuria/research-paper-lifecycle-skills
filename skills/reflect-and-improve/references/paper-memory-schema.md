# The `.paper-memory/` convention

> This is the implementation-level schema for the files `reflect_log.py`
> reads and writes. The repo-wide human reference for the same convention is
> [`paper-memory-convention.md`](../../paper-profile/references/paper-memory-convention.md); the
> `lessons.md` line format here (`- [date] (skill | scope) issue -> rec`) is the
> canonical one all skills append in.

A per-paper memory directory shared across the research-paper toolkit. It lives
in the **user's paper working directory** — NOT in this skills repo — and is
created at use time. It is local; nothing in it is uploaded.

> **Add `.paper-memory/` to your `.gitignore`** unless you deliberately want
> positioning notes and lessons versioned alongside the paper. Reflection,
> preflight, prose, and review skills all read and write here.

```
your-paper/
  main.tex
  .paper-memory/
    profile.yml      # author/paper positioning (written by paper-profile)
    lessons.md       # accumulated, deduplicated, dated lessons
    decisions.md     # venue/track/positioning decisions + rationale
    scores.ndjson    # before/after measurements (written by reflect_log.py)
```

## profile.yml — positioning

Written by the `paper-profile` skill; read by `reflect-and-improve`,
`polish-prose`, `tailor-to-venue`, and others to personalize. Minimal starter:

```yaml
# .paper-memory/profile.yml
vertical: systems            # systems | theory | applied | empirical | survey | position
contribution_type: artifact  # e.g. new-system, new-algorithm, new-dataset,
                             #      empirical-study, theory, position, survey
audience:
  field: databases           # the subfield reviewers come from
  tier: top                  # top | mid | workshop
  venue: SIGMOD              # current target (see decisions.md for why)
risk_appetite: high          # low | medium | high — how boldly to frame claims
writing:
  voice: direct             # direct | formal | narrative
  style_ref: exemplars/sigmod-2023-x.tex   # link for match-style, optional
  hedging: calibrated       # calibrated | conservative — guards over/under-claiming
constraints:
  page_limit: 12            # excl. references, if known
  blind: double             # double | single | none
notes: >
  One-system paper; novelty is the index, not the workload. Reviewers will
  push on baselines — keep the comparison fair and explicit.
```

Reflection uses these fields to avoid generic advice: a `position` vertical
with `voice: narrative` should not be told to "tighten every sentence"; a
`risk_appetite: high` systems paper should not be told to "add more hedging".

## lessons.md — accumulated lessons

Managed by `scripts/reflect_log.py` (safe to hand-edit). One lesson per line:

```
- [YYYY-MM-DD] (skill | scope) issue -> recommendation
```

- **date** — every lesson is dated so stale advice can be pruned.
- **skill** — which skill surfaced it (`polish-prose`, `preflight-check`,
  `verify-citations`, `simulate-reviewers`, `reflect-and-improve`, ...).
- **scope** — `this-paper` (specific; prunable) or `recurring` (cross-paper
  pattern; surfaced proactively, **never pruned**).
- **issue / recommendation** — the pattern observed and what to do about it.

Example:

```
- [2026-06-20] (polish-prose | recurring) abstract over-hedges the contribution -> state the result as a claim once, then qualify in the body
- [2026-06-20] (verify-citations | this-paper) ref [12] page range wrong -> fix to 114-129 per the DOI
```

### Who writes here

Any skill that catches something worth carrying forward APPENDs; every skill
READs at start to avoid repeating advice and to personalize. The append is
deduplicated on **(skill, normalized issue)** so the same lesson logged twice
just refreshes the date and recommendation — the file does not bloat.

### Hygiene

- **Dedupe on append** — automatic (see above).
- **Cap + staleness** — `reflect_log.py prune --keep N --stale-days D` keeps the
  N most-recent `this-paper` lessons and drops `this-paper` lessons older than D
  days. `recurring` lessons are exempt from both.
- **Surface recurring proactively** — `reflect_log.py recurring` prints
  cross-paper patterns most-frequent-first; run it at the start of a reflection.

## decisions.md — venue/positioning decisions

Free-form Markdown written by `select-venue` / `plan-submission`: the chosen
venue, track, deadline cycle, and the rationale (fit, risk, timing). Reflection
reads it for context (e.g. "we picked a top-tier venue, so frame claims for
that bar") but does not manage it.

## scores.ndjson — measurements

Append-only NDJSON written by `reflect_log.py score`; one JSON object per line:

```json
{"ts": "2026-06-20T11:02:00", "skill": "polish-prose", "metric": "hedge-count", "before": 11.0, "after": 6.0, "direction": "lower-is-better", "delta": -5.0, "verdict": "KEEP", "note": ""}
```

This is what turns "did it get better" into data: each reflection leaves an
auditable before→after trail with its verdict, so regressions are caught
mechanically rather than argued about.
