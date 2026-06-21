# Manual Preflight Checks

Source-level linting cannot decide these. Work through them with the user
after the scripts run clean. Each item names the desk-reject risk it covers.

## 1. Compiled-PDF metadata

The linter catches `pdfauthor=` in the source, but the PDF producer can embed
the author or machine username anyway. Have the user inspect the compiled PDF:

```
pdfinfo paper.pdf            # poppler; look at Author / Creator / Producer
exiftool paper.pdf | head    # if installed
strings paper.pdf | grep -i -m5 author   # crude stdlib-ish fallback
```

Fix in LaTeX with `\hypersetup{pdfauthor={}}` (or recompile in a clean CI
container). CHI and NeurIPS treat PDF-metadata identity as an anonymization
violation.

## 2. Where the references actually start

When a limit *excludes* references (NeurIPS 9, SIGSPATIAL 10, ICDE 12), the
only test that matters is: **does content end by page N of the compiled
PDF?** Open the PDF and check the page on which the bibliography begins; the
linter's page-count finding only bounds total pages.

## 3. Supplementary materials

Double-blind rules extend to everything uploaded: appendix PDFs, code ZIPs,
videos, linked repos. Check: author names in code headers and notebook
outputs, `git log` identity in shipped `.git` directories (strip them),
README badges pointing at the real repo, dataset paths containing usernames.
CHI desk-rejects for leaks in supplementary materials and linked repositories.

## 4. Submission-form requirements (not in the PDF)

- **COI declarations** — ICDE collects them in CMT; missing them is a desk
  reject even though the paper itself is fine.
- **Abstract registration** — most ML/data venues require title + abstract +
  authors + conflicts registered 2–7 days before the paper deadline
  (NeurIPS: 2 days; SIGSPATIAL: 1 week). A perfect PDF misses the cycle if
  the abstract was never registered.
- **Topic/subject areas** — chosen in OpenReview/CMT/EasyChair, not the paper.

## 5. Dual and concurrent submission

No linter can see another venue's submission queue. Ask the user directly:
is any overlapping paper under review elsewhere? NeurIPS treats overlapping
in-review work by the same authors as prior work and bans concurrent archival
submission; cross-track double submission inside one venue can desk-reject
both copies.

## 6. File-size and count caps

- NeurIPS 2026: single PDF ≤ 50MB; supplementary ZIP ≤ 100MB.
- ICDE 2026: max 6 papers per author across two rounds; rejected papers carry
  a 1-year resubmission embargo.
- Check `ls -lh paper.pdf` against the venue cap before upload.

## 7. Fonts, figures, and compilation hygiene

- All fonts embedded (`pdffonts paper.pdf` — every row should say "yes" twice);
  IEEE PDF eXpress and ACM TAPS both reject non-embedded fonts at
  camera-ready, and some venues check at submission.
- No Type 3 bitmap fonts (common from old matplotlib configs).
- Figures legible at 100% zoom; colorblind-safe palettes are a review-quality
  issue, not a desk-reject one.

## 8. LLM-policy compliance

Venue policies differ (profile field `review.llm_policy`). Verify the user's
AI-use disclosure matches the venue's wording — ICDE wants the AI system and
affected sections named; ACM wants disclosure "commensurate with the
proportion of content generated"; NeurIPS requires describing LLM use that is
"important, original, or non-standard". Never advise hiding use.

## 9. The deadline itself

Confirm the deadline and its timezone from the live CFP — SIGSPATIAL runs
11:59 PM **Pacific**, not AoE; most others are AoE. Submitting "a day early"
in the wrong timezone has desk-rejected real papers.
