# Narrative and storyboard: problem-first, one claim per slide

How to turn a paper into a talk story. The slide *allocation* (minutes and
counts per section) comes from `scripts/slide_budget.py`; this file is the
*content* methodology for filling that allocation.

## Contents

- [The talk is an ad, not a compression](#the-talk-is-an-ad-not-a-compression)
- [The full-talk shape (12-20 min)](#the-full-talk-shape-12-20-min)
- [The lightning shape (<= 7 min)](#the-lightning-shape--7-min)
- [One claim per slide](#one-claim-per-slide)
- [What to cut from the paper](#what-to-cut-from-the-paper)
- [Figure-led slides](#figure-led-slides)
- [Backup slides](#backup-slides)
- [Storyboard format to confirm with the user](#storyboard-format-to-confirm-with-the-user)
- [Failure modes to refuse](#failure-modes-to-refuse)

## The talk is an ad, not a compression

A conference talk has one job: make the right people read the paper and
remember one idea. It is NOT the paper at 10x speed. Consequences:

- Drop paper order. Papers open with abstract/intro/related-work because
  reviewers demand positioning. Audiences need a reason to care in the
  first 60 seconds.
- Pick ONE headline result and ONE key idea before storyboarding anything.
  If the user can't name them, ask: "If the audience remembers a single
  sentence next week, what should it be?" That sentence becomes the
  takeaway slide and shapes everything before it.
- Completeness is a non-goal. A talk that covers 40% of the paper well
  beats one that covers 100% badly.

## The full-talk shape (12-20 min)

Matches `FULL_PLAN` in `slide_budget.py` (shares of *speaking* time):

| Beat | ~Share | What it must do |
|---|---|---|
| Title & hook | 5% | Who you are + one-line what. No outline slide — at 15 minutes an agenda is wasted breath. |
| The problem & why it matters | 20% | Concrete pain a non-specialist in the room feels. A running example introduced here pays off all talk. |
| Why existing approaches fall short | 10% | One slide. Name the *structural* reason prior work can't fix it — not a related-work tour. |
| The key idea | 15% | The one insight, stripped of machinery. If the audience gets only this far, they got the paper's soul. |
| How it works | 25% | Only the mechanism needed to *believe the results*. Architecture figure from the paper earns its place here. |
| Does it work | 20% | Headline result first, biggest font. One chart per claim. |
| Takeaway + pointer | 5% | The remember-this sentence + where to find paper/code (URL or QR). Leave this slide up during Q&A. |

## The lightning shape (<= 7 min)

Matches `LIGHTNING_PLAN`. Four beats, ~4-6 slides, no detours:

1. **Title + problem merged** — hook in the first sentence.
2. **The one idea** — no architecture, no related work, no notation.
3. **The one result** — a single chart or a single number, huge.
4. **Takeaway + pointer** — "come to the poster / read the paper", QR code.

Lightning talks fail by trying to be small full talks. If a slide needs
the word "additionally", cut it. Some venues auto-advance lightning
slides on a fixed timer — check the presenter instructions (see
[venue-timing.md](venue-timing.md)).

## One claim per slide

Assertion-evidence style: the title is a full-sentence claim; the body is
the evidence for exactly that claim.

- Bad title: "Results". Good title: "Eviction by access recency halves
  tail latency". (`deck_lint.py` flags the bad form as `generic-title`.)
- If a slide supports two claims, split it. If a slide's claim can't be
  stated in one sentence, the slide doesn't know what it's for yet.
- Body: prefer one figure + at most one line of text. Aim under 60 words
  and 6 bullets per slide (linted). 100+ words is a document (`overfull`).
- Math: at most one displayed equation per slide, with every symbol either
  on-screen-labeled or already introduced. Notation is the highest-cost
  item in a talk; minimize ruthlessly.

## What to cut from the paper

| Paper section | In the talk |
|---|---|
| Abstract, outline | Never appears |
| Related work | At most 1 slide ("why existing approaches fall short"); names only if you'll be asked otherwise |
| Formal definitions, proofs | Key idea as a picture/example; proof sketch to backup |
| Full system details | Only the path needed to trust the headline result |
| Evaluation tables | Redesign as a chart or a single highlighted number — `extract_figures.py` counts tables to remind you |
| Secondary experiments, ablations | Backup slides |
| Future work | One spoken line on the takeaway slide, if at all |
| Acknowledgments | Spoken thanks; no slide |

## Figure-led slides

- Build around the paper's most-referenced figures —
  `extract_figures.py` ranks them by in-text reference count, a strong
  signal of which figures carry the argument.
- Reuse beats redraw for architecture/results figures, but: enlarge axis
  labels mentally for a projector (caption-sized fonts vanish at row 10);
  if a figure has 4+ panels, show one panel per slide or crop
  (`pdfcrop`).
- Tables → charts. Paper tables exist for completeness; slides need
  comparison, and bars/lines do comparison.
- Every figure on a slide needs a spoken sentence saying what to look at
  ("the gap between these two lines is the contribution").

## Backup slides

- Go AFTER the takeaway slide (`\appendix` in Beamer; titles starting
  `Backup:` in Marp — both excluded from the pacing lint).
- Stock them with: proof sketches, ablations, dataset details, the
  related-work table, anything a likely Q&A question needs. `rehearse-qa`
  generates the questions; give each anticipated question a backup slide.
- They are free: no pacing cost, high payoff when a question lands.

## Storyboard format to confirm with the user

Before drafting the deck, present one line per slide and get sign-off:

```
 3. [How it works, ~80s] "The scorer reads only metadata LRU already tracks"
    — visual: fig:arch (architecture.pdf), crop right panel
```

Title-claim, beat + rough seconds, supporting visual (with source figure
label). Cheap to reorder now, expensive after slides exist.

## Failure modes to refuse

- **Outline slide** in a <=20-minute talk.
- **Paper-order narration** ("First I'll cover related work…").
- **Talking faster** as the fix for too many slides — cut slides instead
  (the pacing lint exists for this).
- **Wall-of-text slides** read aloud verbatim.
- **New results invented for the talk** — every number traces to the
  paper or the user; pending numbers get `[RESULT]` placeholders.
