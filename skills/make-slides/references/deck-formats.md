# Deck formats: Beamer and Marp recipes, figure reuse mechanics

Skeletons and mechanics for the two supported output formats. Storyboard
methodology lives in [narrative-storyboard.md](narrative-storyboard.md);
slot-length facts in [venue-timing.md](venue-timing.md).

## Contents

- [Choosing Beamer vs Marp](#choosing-beamer-vs-marp)
- [Marp skeleton](#marp-skeleton)
- [Beamer skeleton](#beamer-skeleton)
- [Figure reuse mechanics](#figure-reuse-mechanics)
- [Converting PDFs for Marp](#converting-pdfs-for-marp)
- [Speaker notes and handouts](#speaker-notes-and-handouts)
- [Building and verifying](#building-and-verifying)

## Choosing Beamer vs Marp

| Pick | When |
|---|---|
| **Beamer** | The paper is LaTeX (it is), figures are vector PDFs reused as-is, math-heavy slides, the user already lives in a LaTeX toolchain, venue/advisor expects PDF decks |
| **Marp** | Fast iteration with the user, plain-markdown editing, HTML or PPTX export wanted, minimal LaTeX on slides |

Default to Beamer when the paper source is available and math appears on
slides; default to Marp when the user wants quick drafts they can edit by
hand. Ask if unclear — converting between them later is manual work.

## Marp skeleton

```markdown
---
marp: true
theme: default
paginate: true
---

<!-- _class: lead -->
# Paper Title, Shortened for a Slide
## One-line subtitle (the takeaway, softly)

Author — Affiliation · VENUE 2026

---

## LRU evicts the tiles a burst is about to revisit   <!-- claim title -->

![w:900](assets/architecture.png)

<!-- NOTE: ~40s — point at the eviction layer; "the burst comes back
for exactly what we just threw away." -->

---

## Backup: alpha ablation

![w:700](assets/alpha-sweep.png)
```

Rules the linter enforces or assumes:

- `marp: true` front matter is mandatory (`no-marp-header` otherwise).
- Slides split on `---` lines; first `#`/`##`/`###` heading is the title.
- **Images must be PNG or SVG** — Marp cannot render `.pdf` images
  (`marp-pdf-image` RISK). Convert first (below).
- Size images with Marp directives: `![w:900](...)`, `![bg right:40%](...)`.
- Speaker notes are HTML comments `<!-- ... -->` (excluded from word
  counts).
- Backup slides: title starts with `Backup` — everything from the first
  such slide is excluded from pacing.
- Default theme is 16:9; don't override `size:` unless the venue's room
  is known to be 4:3.

## Beamer skeleton

```latex
\documentclass[aspectratio=169]{beamer}
\usetheme{metropolis}   % or default; avoid heavy nav-bar themes
\title{Paper Title, Shortened for a Slide}
\subtitle{The takeaway, softly}
\author{Author \and Coauthor}
\institute{Affiliation}
\date{VENUE 2026}

\begin{document}
\begin{frame}\titlepage\end{frame}

\begin{frame}{LRU evicts the tiles a burst is about to revisit} % claim title
  \centering
  \includegraphics[width=0.9\linewidth]{assets/architecture}
  \note{~40s — point at the eviction layer.}
\end{frame}

\appendix   % everything after this is backup (excluded from pacing)
\begin{frame}{Backup: alpha ablation}
  \includegraphics[width=0.7\linewidth]{assets/alpha-sweep}
\end{frame}
\end{document}
```

Rules:

- `aspectratio=169` — most conference rooms are 16:9; the linter emits
  `aspect-ratio` INFO when missing. Confirm against presenter
  instructions before fighting the default.
- Frame title = the claim (`\begin{frame}{Claim sentence}`).
- No `\tiny`/`\scriptsize` body text (`tiny-font` WARN) — if it only fits
  tiny, it doesn't fit.
- `\note{...}` for speaker notes (excluded from word counts).
- `\appendix` before backup frames; add
  `\usepackage{appendixnumberbeamer}` so the page counter stops at the
  takeaway slide.
- Skip `\tableofcontents` and section nav widgets for <=20-minute talks.

## Figure reuse mechanics

1. Harvest with the bundled script (from the repo root):
   `python3 skills/make-slides/scripts/extract_figures.py paper/main.tex --copy-to talk/assets`
   It resolves `\graphicspath` and extension-less names, copies the
   files, and ranks figures by in-text reference count.
2. Beamer consumes the copied PDFs/PNGs directly:
   `\includegraphics{assets/architecture}`.
3. Crop whitespace from paper figures sized for column widths:
   `pdfcrop assets/architecture.pdf` (TeX Live).
4. Multi-panel figures: show one panel per slide. Crop panels with
   `pdfcrop --bbox "<x1 y1 x2 y2>"` or convert and crop the PNG.
5. TikZ-only figures (the inventory marks them `n/a`): recompile
   standalone (`\documentclass{standalone}` + the tikzpicture) or
   screenshot the paper PDF page at high zoom as a stopgap.
6. Projector check: axis labels and legends must be readable at the back
   of a room — if a figure was sized for a 2-column paper, prefer
   regenerating it with larger fonts over scaling it up blurry.

## Converting PDFs for Marp

Marp renders PNG/SVG, never PDF. Convert each harvested PDF:

```bash
# Poppler (Linux/macOS, if installed):
pdftocairo -png -r 200 -singlefile assets/architecture.pdf assets/architecture

# macOS fallback (no installs):
sips -s format png --resampleWidth 1600 assets/architecture.pdf \
     --out assets/architecture.png

# Vector-preserving alternative (if poppler present):
pdftocairo -svg assets/architecture.pdf assets/architecture.svg
```

Use 200 dpi or higher for raster; prefer SVG when the figure is line art.
Re-run `deck_lint.py` after converting — it flags any `.pdf` image left
in a Marp deck and any image path that doesn't exist.

## Speaker notes and handouts

- Put a 1-2 sentence note stub on every content slide while drafting —
  `write-talk-script` expands these into the timed script; don't
  duplicate that work here.
- Beamer handout for sharing: `\documentclass[aspectratio=169,handout]{beamer}`
  collapses overlays.
- Marp exports: HTML (presenter view with notes), PDF, or PPTX (below).

## Building and verifying

```bash
# Beamer
latexmk -pdf talk/slides.tex          # or pdflatex twice

# Marp (Node tooling; ask before assuming it's installed)
npx @marp-team/marp-cli talk/slides.md --pdf      # PDF
npx @marp-team/marp-cli talk/slides.md --pptx     # PowerPoint
npx @marp-team/marp-cli talk/slides.md -p -w      # live preview
```

If neither toolchain is available, deliver the source and state clearly
that it was not compiled. Always finish with:
`python3 skills/make-slides/scripts/deck_lint.py talk/slides.<md|tex> --minutes <speaking-minutes>`
and fix every RISK before handing off.
