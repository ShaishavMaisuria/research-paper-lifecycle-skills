# Format (a): strict one-page PDF rebuttal (CVPR-style)

For venues whose profile says `review.rebuttal_format: one-page-pdf` —
CVPR is the archetype (ICCV/WACV historically similar). Always re-verify
the current cycle's author guidelines via the profile's `cfp_url`: the
exact bans below are the CVPR 2026 wording and DO change year to year.

## Contents

- [The hard rules](#the-hard-rules)
- [Use the official kit when one exists](#use-the-official-kit-when-one-exists)
- [Structure that wins on one page](#structure-that-wins-on-one-page)
- [Space economy — legitimate and banned](#space-economy--legitimate-and-banned)
- [Build and verify](#build-and-verify)
- [One-page rebuttal checklist](#one-page-rebuttal-checklist)

## The hard rules

Per the CVPR 2026 author guidelines (re-verify each cycle):

- **One page, period.** "Responses longer than one page will simply not be
  reviewed." There is no appeal; page 2 does not exist to the reviewers.
- **Official rebuttal template mandatory** where the venue ships one (CVPR
  bundles a rebuttal template in the author kit at
  `github.com/cvpr-org/author-kit` — check the current year's tag).
- **Stay anonymous.** Same double-blind rules as the submission; no author
  names, no identifying links, third-person self-citation.
- **No external links** to code, videos, or project pages.
- **No new contributions or experiments** unless specifically requested by
  reviewers. A reviewer asking "how does this behave under X?" is a
  request; volunteering an entirely new method extension is not. When in
  doubt, frame additions as direct answers to a quoted reviewer question.
- The rebuttal is uploaded in the submission system (OpenReview for recent
  CVPR cycles) as a PDF by the `deadlines.rebuttal_end` date — confirm the
  date on the live Dates page, not the profile.

## Use the official kit when one exists

`assets/rebuttal-template.tex` in this skill is a **generic scaffold**: use
it for venues that mandate a one-page PDF without shipping a kit, or for
drafting. For an actual CVPR submission, fetch the current author kit and
port the body text into its `rebuttal.tex` — the official template carries
the venue's ruler, fonts, and margins, and using the wrong template is a
reject-without-review trigger. Do not copy venue `.sty` files into this
repository.

The scaffold's macros transfer directly:

- `\rpoint{R2.1}{abridged quote}` — reviewer point: bold ID, italic quote.
- `\resp{...}` — one response paragraph per point.
- `\rhead{Reviewer 2 (R2)}` — per-reviewer block heading.
- `\rid{R1.2}` — inline cross-reference ("see [R1.2]") so shared concerns
  are answered once.

## Structure that wins on one page

Order the page for an AC skimming in 90 seconds:

1. **Global summary, 2–4 lines.** What the reviewers liked (one clause),
   the two or three main concerns, and the sentence "we address every
   point below, citing sections/tables/line numbers of the submitted PDF."
2. **Shared concerns first.** If two reviewers raise the same issue,
   answer it once in its own block and cross-reference with `\rid{}` —
   the single biggest space win available.
3. **Per-reviewer blocks** in reviewer order, each point as
   `\rpoint` + `\resp`, highest-severity point first within each block.
4. **Optional one-line closing**: scope of promised changes ("all
   presentation-level, within the camera-ready budget").

Allocate space by score leverage, not by review length: the negative
reviewer with concrete objections gets the most lines; the positive
reviewer's questions get one or two each.

## Space economy — legitimate and banned

Legitimate, in order of yield:

1. Abridge reviewer quotes hard — quote only the load-bearing clause:
   `\rpoint{R2.3}{novelty over [17] unclear}`.
2. Merge shared concerns (above).
3. Group all low-severity points into one line: "Typos/clarity
   (R1.4, R3.2): all fixed as suggested."
4. Replace prose with a 2–3 row compact `booktabs` table when reporting
   requested numbers — tables are denser than sentences.
5. Cite the paper by anchor (`Table 2`, `L412`) instead of re-explaining
   content; the reviewers have the PDF.
6. Cut hedging and gratitude beyond the opening line.

Banned (template tampering — itself a reject trigger and visibly obvious
to anyone who has chaired): negative `\vspace`, font-size or margin
changes, `\baselineskip` tricks, shrinking the title block, removing the
ruler in kits that have one, microscopic tables.

## Build and verify

```
pdflatex rebuttal.tex
python3 skills/write-rebuttal/scripts/check_budget.py pdf rebuttal.pdf --max-pages 1
python3 skills/write-rebuttal/scripts/check_coverage.py points.md rebuttal.tex --strict
```

`check_budget.py pdf` parses the compiled PDF (no LaTeX toolchain needed
for the check itself) and exits 1 if the page count exceeds the limit.
`check_coverage.py` accepts `.tex` input — point IDs and anchors are
matched as plain text.

## One-page rebuttal checklist

- [ ] Official venue rebuttal template used, current year's kit (or this
      scaffold only where no kit exists)
- [ ] Exactly 1 page (`check_budget.py pdf` exit 0)
- [ ] Every triaged point covered (`check_coverage.py` exit 0)
- [ ] Every response anchored to Sec./Table/Fig./line numbers
- [ ] No author-identifying content; self-citations in third person
- [ ] No external links anywhere
- [ ] No unrequested new experiments/contributions; new numbers (if
      requested) labeled as new and actually produced
- [ ] No template tampering
- [ ] Deadline + upload location confirmed on the live venue pages, not
      the profile
