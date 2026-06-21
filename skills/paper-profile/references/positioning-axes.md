# Positioning axes — what each option means and how to pick

Use this when interviewing the author. For every axis: offer the options, give
the one-line gloss, suggest a default, and let the author choose. Never infer a
value to avoid asking — the whole point of the profile is that the author
states their intent once. The exact tokens are authoritative in
`scripts/profile_io.py` (run `profile_io.py schema`); this file is the human
explanation behind them.

## Table of contents

- [vertical / emphasis](#vertical--emphasis)
- [contribution_type](#contribution_type)
- [audience](#audience)
- [venue_tier and target_venues](#venue_tier-and-target_venues)
- [risk_appetite](#risk_appetite)
- [writing_preferences](#writing_preferences)
- [context: prior_papers and constraints](#context-prior_papers-and-constraints)
- [How vertical and contribution_type interact](#how-vertical-and-contribution_type-interact)

## vertical / emphasis

Where the *weight* of the paper sits. This is the single most consequential
axis because it changes how `benchmark-paper` scores and how
`simulate-reviewers` reads the paper. Ask: "If a reviewer remembers one thing,
is it the artifact, the proof, the application, the measurement, the synthesis,
or the argument?"

| Value | The heart of the paper is… | Telltale |
|---|---|---|
| `systems` | a built artifact, architecture, engineering at scale | system diagrams, throughput/latency tables, "we implemented" |
| `theory` | a proof, bound, or analysis | theorems/lemmas are the contribution; experiments minor or absent |
| `applied` | a known method applied to a real domain problem | domain framing dominates; novelty is the application, not the method |
| `empirical` | a measurement / empirical study | the study design and findings are the contribution |
| `survey` | a synthesis of existing work | taxonomy, comparison tables, no new method |
| `position` | an argument or research agenda | makes a case; calls for a direction |

If the author can't pick one, ask what the *primary* contribution is — pick the
single dominant emphasis. A systems paper with proofs is still `systems` if the
artifact is the point.

## contribution_type

The *form* of the contribution, finer-grained than vertical. A `systems`
vertical usually pairs with `system`, but not always (a systems-flavored paper
whose contribution is a benchmark is `vertical: systems, contribution_type:
dataset`).

| Value | Meaning |
|---|---|
| `method` | new technique/algorithm/model |
| `system` | system/tool/artifact |
| `theory` | theorem/analysis/lower bound |
| `dataset` | dataset or benchmark IS the contribution |
| `empirical` | measurement / empirical / reproducibility study |
| `application` | application of known methods to a new domain |
| `survey` | survey/review |
| `position` | position/vision |

## audience

Who the paper is written *for*. Drives `write-abstract` (what to lead with) and
`simulate-reviewers` (how much background a reviewer expects).

| Value | Reader |
|---|---|
| `specialists` | sub-field experts who know the area cold |
| `broad-field` | cross-area readers at a flagship venue |
| `practitioners` | industry / applied practitioners |
| `interdisciplinary` | readers from adjacent disciplines |

## venue_tier and target_venues

`venue_tier` is the ambition band; `target_venues` are concrete ids (matching
`venues/conferences/<id>.yml` when known, e.g. `sigspatial-2026`).

| Value | Band |
|---|---|
| `top` | flagship / top-tier main track |
| `specialized` | strong specialized venue or top workshop |
| `regional` | regional / second-tier conference |
| `journal` | journal (no page limit, slow cycle) |
| `workshop` | workshop / short paper |
| `preprint` | arXiv / preprint only for now |
| `undecided` | not chosen — keep options open |

`select-venue` can fill `target_venues` later; it's fine to leave it empty and
set only the tier early on.

## risk_appetite

How much variance the author will accept in reviews. This calibrates
`simulate-reviewers` harshness and how `benchmark-paper` frames gaps.

| Value | Stance |
|---|---|
| `safe` | defend a tight incremental delta; minimize attack surface |
| `balanced` | solid core plus one ambitious claim |
| `ambitious` | stake a big claim; accept polarized reviews |

Be explicit about the trade-off when the author is unsure: `ambitious` raises
the ceiling and the floor of likely reviews; `safe` narrows the distribution.
Do not nudge — record what the author wants.

## writing_preferences

Consumed by `polish-prose` (de-AI-ify / register) and `match-style` (target
voice). All optional; `venue-default` means "defer to the venue's norm."

- `person`: `first-person-we` | `first-person-i` | `impersonal-passive` |
  `venue-default`.
- `tone`: `formal` | `plain` | `assertive` | `hedged` | `venue-default`.
- `notation`: `heavy` | `light` | `venue-default` (how math-dense the prose is).
- `british_spelling`: `true` | `false`.
- `preferred_terms`: terms/acronyms to use consistently (feeds `match-style`).
- `avoid_terms`: words to avoid — banned jargon, AI tells, a co-author's pet
  phrase (feeds `polish-prose`'s removal list).

## context: prior_papers and constraints

- `prior_papers`: paths or ids of the author's earlier papers. `match-style`
  uses these to build the author-voice signature. These must be the author's
  own work.
- `constraints`: hard limits any skill must respect — a fixed deadline, "must
  stay anonymized," "no new experiments possible," a strict page budget. Skills
  read these so they don't suggest something impossible.

## How vertical and contribution_type interact

They are related but separate. Common pairings:

| vertical | usual contribution_type | notable exceptions |
|---|---|---|
| `systems` | `system` | `dataset` (built a benchmark), `method` (new algo in a system) |
| `theory` | `theory` | `method` (algorithm with proofs) |
| `applied` | `application` | `method` (new method for the domain) |
| `empirical` | `empirical` | `dataset` (the data is the artifact) |
| `survey` | `survey` | — |
| `position` | `position` | — |

When they disagree, that's fine and informative — record both. Downstream
skills read both axes, not a single collapsed label.
