# Venue timing: slot lengths, Q&A norms, and what must be verified

The single most desk-reject-like failure in talk prep is building a
15-minute deck for a 10-minute slot. This file gives the typical shapes
and the verification discipline.

## Contents

- [Ground truth: where slot lengths actually live](#ground-truth-where-slot-lengths-actually-live)
- [Typical slot shapes (conventions, not facts)](#typical-slot-shapes-conventions-not-facts)
- [Q&A arithmetic](#qa-arithmetic)
- [Lightning-talk specifics](#lightning-talk-specifics)
- [Recording and AV requirements](#recording-and-av-requirements)
- [Verification checklist](#verification-checklist)

## Ground truth: where slot lengths actually live

Venue profiles in `venues/` deliberately do NOT encode talk slots: slot
lengths are set per year, per track, and sometimes per session, after
acceptance. The authoritative sources, in order:

1. **The acceptance email / presenter instructions** sent to authors.
2. The venue's "Information for presenters" / program page for THIS year
   (start from `website` / `cfp_url` in the venue profile).
3. The published program: divide session length by talks in the session
   for a sanity estimate — label it an estimate.

If the user cannot produce a number from sources 1-2, ask them to get it,
and meanwhile build to a stated assumption ("assuming 12+3 — re-verify
against your presenter instructions") marked UNVERIFIED. Never present a
remembered slot length as fact: a 2-minute error is 2 slides.

## Typical slot shapes (conventions, not facts)

Use these only to sanity-check what the user reports or to pick a working
assumption — every one varies by year and venue:

| Talk type | Typical slot | Notes |
|---|---|---|
| Full-paper talk (systems/DB/GIS: SIGMOD, VLDB, SIGSPATIAL, KDD…) | 12-20 min **including** Q&A | The dominant shape; mid-size venues often 12-15 min |
| CHI-style talk | historically ~10 min + 5 Q&A | CHI has changed formats across years — verify |
| ML venue oral/spotlight (NeurIPS, ICML, ICLR) | orals often 10-15 min; spotlights ~4-5 min | Most accepted papers get a poster, not a talk; spotlights are often pre-recorded |
| Lightning / teaser session | 3-5 min, often no Q&A | Sometimes auto-advancing slides on a fixed timer |
| Workshop talk | 10-20 min, organizer-set | Ask the organizers; wildly variable |
| Journal-first / extended talk | up to 25-30 min | Treat as a different storyboard, not a stretched full talk |

`slide_budget.py` switches to the lightning shape automatically at
<= 7 minutes; pass `--format` to override.

## Q&A arithmetic

- Always ask whether the stated slot INCLUDES Q&A. "15 minutes" usually
  means ~12 speaking + 3 Q&A; "12+3" is explicit. `slide_budget.py`
  defaults to 3 Q&A minutes for slots over 7 minutes — override with
  `--qa` when the user knows the real split.
- Budget slides against SPEAKING minutes only (`deck_lint.py --minutes`
  takes speaking minutes).
- Session chairs cut speakers off, not questions: running over eats your
  own Q&A and the next speaker's goodwill. Plan to land 30-60 seconds
  early.
- Leave the takeaway slide (with paper/code pointer) on screen during
  Q&A; route anticipated questions to backup slides (`rehearse-qa`).

## Lightning-talk specifics

- One idea, one result, one pointer — the four-beat shape in
  [narrative-storyboard.md](narrative-storyboard.md).
- Check the presenter instructions for: auto-advance timers (fixed
  seconds per slide — then the slide count is dictated, not chosen),
  mandatory slide templates, and PDF-only submission of slides in
  advance with a hard deadline.
- No Q&A in most lightning sessions; the pointer slide does that job
  (poster number, QR code).

## Recording and AV requirements

Presenter instructions frequently add requirements that change the
deliverable — check for each:

- **Pre-recorded video** (common at hybrid venues and for ML spotlights):
  fixed length, format/resolution, upload deadline well before the
  conference.
- **Slide submission in advance** (some venues collect decks PDF-only to
  a shared machine — fonts must embed; test the PDF on another machine).
- **Aspect ratio**: 16:9 is the modern default; a few rooms/venues still
  state 4:3.
- **Templates**: some venues require a title-slide template or a
  disclosure slide (e.g. AI-use or funding acknowledgment).

## Verification checklist

Before handing off the deck, confirm — against presenter instructions or
acceptance email, with the source named:

- [ ] Slot minutes, and whether Q&A is inside the slot
- [ ] Talk type (full / short / spotlight / lightning) for the right shape
- [ ] Auto-advance or fixed-template constraints (lightning)
- [ ] Aspect ratio of the room
- [ ] Pre-recording or advance slide-upload deadlines
- [ ] Anything taken from a `venues/` profile re-checked against the live
      `cfp_url` / venue site (profiles go stale)

Anything unconfirmable gets labeled UNVERIFIED in the handoff, with the
URL the user should check.
