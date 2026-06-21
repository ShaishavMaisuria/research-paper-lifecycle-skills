# Format (c): revise-and-resubmit package with change-log response document

For venues whose profile says `review.rebuttal_format: revise-and-resubmit`
— CHI's 5-week R&R cycle is the conference archetype; SIGMOD/ICDE-style
revision rounds and journal major/minor revisions (TKDE, TODS via
ScholarOne/Manuscript Central) follow the same package shape. Windows,
highlighting requirements, and length rules vary: re-verify on the live
venue pages via the profile's `cfp_url`, and treat the decision
letter/1AC letter as the binding instruction set.

## Contents

- [How R&R differs from a rebuttal](#how-rr-differs-from-a-rebuttal)
- [The three artifacts](#the-three-artifacts)
- [The change-log response document](#the-change-log-response-document)
- [Highlighting changes in the manuscript](#highlighting-changes-in-the-manuscript)
- [Venue nuances](#venue-nuances)
- [Verification before sending](#verification-before-sending)
- [R&R package checklist](#rr-package-checklist)

## How R&R differs from a rebuttal

- You **revise the paper itself**, not just argue. "We have changed X"
  (done, with location) replaces "we will change X". Past tense, verifiable
  against the revised PDF.
- **New experiments are expected**, not banned — a requested baseline or
  ablation should be run and put in the paper, not promised.
- The audience re-reads selectively: the response document must let each
  reviewer find *their* points and the exact location of each change
  without re-reading the whole paper.
- It is still a gate, not an acceptance: CHI historically rejects up to
  half of R&R papers in round 2; journals can reject after a major
  revision. Address everything; the most common round-2 kill is a point
  the authors silently skipped.

## The three artifacts

1. **The revised manuscript** with changes highlighted per the venue's
   instruction (tracked changes, colored text, or latexdiff PDF — see
   below). CHI expects changes flagged; journals usually want both a
   marked and a clean copy.
2. **The response document** (a.k.a. response letter / summary of
   revisions): point-by-point change log keyed to the triage matrix IDs —
   the core artifact, format below.
3. **A short cover note** (one or two paragraphs, often a form field in
   PCS/ScholarOne): thanks, one-sentence summary of the major changes, and
   any change made beyond the reviews (e.g. "we additionally fixed an
   off-by-one in Table 5; results shift by <0.2% and no conclusion
   changes" — disclose such fixes, never slip them in silently).

## The change-log response document

Lead with a half-page **summary of major changes** (3–6 bullets, each with
revised-paper location), then the per-point table or list. Table form:

| ID | Reviewer comment (abridged) | Response | Change made | Location (revised) |
|---|---|---|---|---|
| R1.1 | "no comparison against B" | Agreed; run on all three datasets | Added baseline B | Table 2; Sec. 6.1, p. 8 |
| R2.3 | "novelty over [17] unclear" | [17] is offline-only; setting differs | New contrast paragraph | Sec. 2, p. 3 |
| R3.1 | "could this extend to Y?" | Believed yes via Appendix D reduction; out of scope to validate here | Future-work note added | Sec. 8 |

Rules:

- **Every point gets a row**, including praise ("Thank you — no change
  needed") and points you decline. Declining is legitimate when justified:
  state the reason and what you did instead; an ignored point is not.
- "Change made" is concrete and **locatable in the revised PDF** (section,
  page, figure/table number of the *revised* numbering). Where the venue
  letter asks for it, also reference the highlight color/marker.
- If a requested change conflicts with another reviewer's request, say so
  in both rows and state the resolution the 1AC/editor guidance supports.
- Long discussions go in prose under the table row, not in the cell.
- The response document usually has **no hard length limit** (CHI 2026
  states none) — but the matrix-keyed table keeps it skimmable; verify
  whether your venue caps it before padding.

`scripts/check_coverage.py points.md response-doc.md` verifies every
matrix ID has a row; `--strict` additionally requires each section to
carry location anchors.

## Highlighting changes in the manuscript

- **latexdiff** (external Perl tool, ships with TeX Live; not bundled
  here): `latexdiff submitted.tex revised.tex > diff.tex`, compile
  `diff.tex` for the marked copy. For multi-file projects use
  `latexdiff --flatten`. Check the diff PDF compiles cleanly — latexdiff
  chokes on heavily edited math/floats; fall back to manual marking for
  those blocks.
- **Manual color marking**: define `\newcommand{\revised}[1]{{\color{blue}#1}}`
  and wrap changed passages; remember to strip for camera-ready (add the
  strip step to the change log's own checklist).
- **Word/tracked changes** venues (some journals): keep tracked changes
  on for the marked copy, accept-all for the clean copy.
- Follow the decision letter's stated mechanism if it names one — it
  overrides all defaults here.

## Venue nuances

**CHI-style (conference R&R).** Reviews arrive with a 1AC meta-review
that often enumerates the changes the committee expects — treat that list
as the priority order; the matrix should mark which reviewer points the
1AC endorsed. ~5-week window (CHI 2026: reviews 2025-11-04, resubmission
2025-12-04), submitted via PCS as revised PDF + response document. Word
limits still apply to the revised paper; anonymization rules persist.

**Journal major/minor revision (TKDE/TODS-style).** Deadlines are months,
set in the decision letter; minor revision usually means the editor
checks the response alone, major revision goes back to the same
reviewers — write the response document for whoever rejected you, not the
editor. Page/length limits still bind (TKDE 14 pages including
references and biographies). Submission via ScholarOne/Manuscript
Central as a new version with response files attached. An expired
revision deadline often converts to "reject + new submission" — calendar
it on receipt.

**SIGMOD/ICDE-style revision rounds.** The decision lists *required* and
*optional* revision items; required items are pass/fail and the response
document should open with a required-items table mapping each to its
change and location. One round only, fixed deadline — there is no second
rebuttal to fix a missed item.

## Verification before sending

```
python3 skills/write-rebuttal/scripts/check_coverage.py points.md response-doc.md --strict
```

Then by hand: open the revised PDF next to the change log and click
through every "Location" entry — stale locations (numbering shifted after
edits) are the most common embarrassment in R&R packages. If the revised
paper gained citations, they must already have passed `verify-citations`.
Re-run the `preflight-check` skill on the revised manuscript: page/word
limits and anonymization rules still apply to revisions.

## R&R package checklist

- [ ] Decision/1AC letter parsed; required-changes list extracted and
      prioritized
- [ ] Every matrix ID has a response row (`check_coverage.py` exit 0);
      declines are justified, never silent
- [ ] All claimed changes actually exist in the revised PDF at the stated
      location (clicked through by hand)
- [ ] Changes highlighted per the venue's mechanism; clean copy prepared
      if required
- [ ] Unrequested changes disclosed in the cover note
- [ ] New experiments actually run; new citations passed `verify-citations`
- [ ] Revised paper re-passed `preflight-check` (limits, anonymization)
- [ ] Resubmission deadline and upload portal confirmed live; the user
      uploads it themselves
