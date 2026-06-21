# Figures: sizing, subfigures, formats, placement

## Contents

1. [Width discipline](#width-discipline)
2. [Fonts inside figures](#fonts-inside-figures)
3. [Vector vs raster](#vector-vs-raster)
4. [Subfigure layout with subcaption](#subfigure-layout-with-subcaption)
5. [Float placement](#float-placement)
6. [ACM accessibility: \Description](#acm-accessibility-description)
7. [Plot-quality checklist](#plot-quality-checklist)

## Width discipline

- One-column float at a two-column venue: size to `\columnwidth`
  (or `\linewidth`, which equals it there) —
  `\includegraphics[width=\columnwidth]{...}` or a fraction
  (`width=0.95\columnwidth`).
- `width=\textwidth` inside `figure` at a two-column venue overflows the
  column. Either switch to `\columnwidth` or promote the float to
  `figure*` (spans both columns; note `figure*` floats to page top and may
  drift a page — that is normal).
- Avoid hard-coded `width=8.5cm`: it silently breaks when the template
  changes. Use fractions of `\columnwidth`/`\textwidth`.
- Never upscale (`width` larger than the graphic's natural size) raster
  images — they blur. Get the exact column width for export with
  `\the\columnwidth` printed in a draft compile (acmart sigconf and
  IEEEtran columns are ≈3.3–3.5 in; print the real value, don't guess).

## Fonts inside figures

The most common reviewer complaint after color: unreadable axis labels.

- Target: text inside figures ends up no smaller than ~80% of caption size
  after scaling — in practice 7–9 pt at final size.
- The reliable method: export the figure at its FINAL physical size
  (e.g. 3.3 in wide) with absolute font sizes, then include with
  `width=\columnwidth` so scale factor is ~1.0.
- matplotlib starting point for a one-column figure:

  ```python
  import matplotlib.pyplot as plt
  plt.rcParams.update({
      "figure.figsize": (3.3, 2.2),   # final column size in inches
      "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
      "xtick.labelsize": 7, "ytick.labelsize": 7,
      "savefig.bbox": "tight", "pdf.fonttype": 42,  # embed TrueType
  })
  ```

- TikZ/pgfplots render at document size automatically — prefer them for
  diagrams when feasible.

## Vector vs raster

- Plots, diagrams, architectures: **vector PDF** (or TikZ source). Never
  JPG (compression artifacts on line art), avoid PNG unless the plot has
  millions of points (then rasterize the data layer only, keep axes/text
  vector — matplotlib `rasterized=True` per-artist).
- Photos and screenshots: PNG (or JPG for photos), ≥300 dpi at final size.
- Fonts must be embedded in figure PDFs (matplotlib `pdf.fonttype: 42`;
  camera-ready validators reject unembedded fonts).

## Subfigure layout with subcaption

Use the **subcaption** package (`\usepackage{subcaption}`). The old
`subfigure` package is deprecated and conflicts with hyperref/modern
classes; `subfig` (`\subfloat`) still works but subcaption is the
maintained, caption-integrated choice.

Two side-by-side subfigures:

```latex
\begin{figure}[t]
  \centering
  \begin{subfigure}{0.48\columnwidth}
    \centering
    \includegraphics[width=\linewidth]{plot-a.pdf}
    \caption{Throughput.}
    \label{fig:eval-throughput}
  \end{subfigure}
  \hfill
  \begin{subfigure}{0.48\columnwidth}
    \centering
    \includegraphics[width=\linewidth]{plot-b.pdf}
    \caption{Latency.}
    \label{fig:eval-latency}
  \end{subfigure}
  \caption{End-to-end evaluation on both clusters.}
  \label{fig:eval}
\end{figure}
```

Rules of thumb:

- Inside a `subfigure`, `\linewidth` = the subfigure's width — always size
  graphics with `width=\linewidth` there.
- `\hfill` between subfigures; widths summing to ≤0.96 of the line leave
  enough gap.
- 2×2 grids: put a blank line (paragraph break) between the rows.
- Caption each subfigure (`(a)`, `(b)` are generated) AND write a main
  caption that reads as a unit. Reference with `\cref{fig:eval-latency}`
  → "Figure 3b" (cleveref + subcaption cooperate).
- Sub-plots that share axes should share scale — if (a) and (b) have
  different y-ranges for the same metric, flag it to the user (reviewers
  read this as misleading; changing it is the user's call).

## Float placement

- Default to `[t]` (top of column/page) — the style of essentially all
  ACM/IEEE/ML papers. `[htbp]` is an acceptable permissive fallback.
- Avoid bare `[h]` ("here") — LaTeX usually can't honor it and strands the
  float at the document end; `[H]` (float pkg) forces placement, breaks
  float order, and creates large white gaps.
- Place the float's source code right after the paragraph that first
  references it; LaTeX floats it forward, never backward.
- Every float must be referenced in the text (the linter flags
  unreferenced labels) and should appear on/after the page of first
  reference.

## ACM accessibility: \Description

acmart documents require alt-text for figures:

```latex
\includegraphics[width=\columnwidth]{arch.pdf}
\Description{Three-stage pipeline: ingestion feeds the index builder,
which feeds the query processor.}
\caption{System architecture.}
```

Write what the figure SHOWS (for a screen-reader user), not a repeat of the
caption. TAPS flags missing `\Description` at camera-ready — fixing it now
is free. (Non-ACM venues: harmless, skip unless asked.)

## Plot-quality checklist

- Axis labels with units on both axes; tick labels not overlapping.
- Legend inside dead space of the plot or above it; never covering data.
- Line width ≥0.75 pt at final size; markers distinguishable in grayscale
  (see references/color-accessibility.md for redundant encoding).
- Log scales labeled as such; broken axes marked.
- Error bars/bands defined in the caption (std? CI? over how many runs?) —
  if the source data doesn't say, ask the user; never guess.
- Identical y-ranges across plots that will be compared side by side.
