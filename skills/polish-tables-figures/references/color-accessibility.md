# Color and accessibility for paper figures

## Contents

1. [Principles](#principles)
2. [Bundled palettes](#bundled-palettes)
3. [Using the palette script](#using-the-palette-script)
4. [Redundant encoding](#redundant-encoding)
5. [Sequential and diverging data](#sequential-and-diverging-data)
6. [Auditing an existing figure](#auditing-an-existing-figure)

## Principles

- ~4% of readers (8% of men) have some color-vision deficiency (CVD),
  mostly red-green. Reviewers print in grayscale more often than authors
  expect. Design for both.
- **Never encode information in hue alone.** Pair color with marker shape,
  line style, hatching, or direct labels.
- **Avoid red-green pairs** for contrasting series — the classic
  matplotlib red `#D62728` vs green `#2CA02C` collapses to near-identical
  brown under deuteranopia (the bundled checker measures deltaE ≈ 7 —
  far below the ~12 distinguishability floor).
- Avoid rainbow/jet colormaps for ordered data: they are not perceptually
  uniform and fail in grayscale. Use viridis-family colormaps.
- Fewer series beats cleverer colors: above ~6 lines, split the plot.

## Bundled palettes

Qualitative (categorical series), in order of preference:

| Palette | Colors | Best for |
|---|---|---|
| `okabe-ito` | 8 | the de-facto scientific standard (Okabe & Ito, Color Universal Design) |
| `tol-bright` | 7 | slides + paper, white background (Paul Tol, SRON notes) |
| `tol-muted` | 9 | many-series plots |
| `tol-light` | 9 | filled areas / bar charts behind text |
| `tol-high-contrast` | 3 | 2–3 series, also fully grayscale-safe |

Hex values: `python3 scripts/palettes.py list`. Take the FIRST k colors of
a palette for k series (they are ordered for mutual distinguishability);
for >5 series run `check` on your chosen subset — even within good
palettes some pairs are borderline under one deficiency type, which is
exactly when redundant encoding becomes mandatory.

## Using the palette script

```bash
# emit ready-to-paste definitions
python3 scripts/palettes.py show okabe-ito --format latex       # xcolor \definecolor
python3 scripts/palettes.py show okabe-ito --format pgfplots    # cycle list w/ marks+dashes
python3 scripts/palettes.py show tol-bright --format matplotlib # rcParams cycler
python3 scripts/palettes.py show tol-muted --format hex

# audit the colors a paper actually uses
python3 scripts/palettes.py check 4477AA EE6677 228833
python3 scripts/palettes.py check --palette okabe-ito
python3 scripts/palettes.py check --json D62728 2CA02C          # machine-readable
```

`check` simulates protanopia, deuteranopia, and tritanopia (Machado et al.
2009 matrices) plus grayscale print, computes pairwise deltaE (CIE76), and:

- **CONFUSABLE** (deltaE < 12 under any condition) → exit 1; replace one
  color of the pair.
- **borderline** (deltaE 12–20, or grayscale L* gap < 10) → exit 0 with
  warnings; keep the colors but add redundant encoding (below).
- `--require-grayscale` promotes grayscale collisions to failures (use for
  venues/users that require print-safe figures).

## Redundant encoding

Color + a second channel, so the figure works in grayscale and for all CVD
types:

- **Line plots**: distinct marker per series (`o`, `s`, `^`, `D`) AND
  distinct line style (solid/dashed/dotted/dash-dot). The
  `--format pgfplots` output bakes this into the cycle list; for
  matplotlib, cycle `linestyle` and `marker` alongside `color`.
- **Bar charts**: hatching (`//`, `\\`, `xx`, `..`) per category, thin
  black bar edges.
- **Heatmaps**: viridis/cividis + contour lines or value annotations.
- **Scatter**: marker shape per class; if classes overlap heavily, also
  facet.
- **Direct labeling** beats legends when there is room: label the line at
  its end. Always still readable: legend order = visual order of lines at
  the right edge.

## Sequential and diverging data

The bundled palettes are qualitative. For ordered values use perceptually
uniform colormaps: viridis, cividis (CVD-optimized), magma — available in
matplotlib by name and in pgfplots via `colormap name=viridis`. For
diverging data (negative/zero/positive) use a colormap with a neutral
midpoint (e.g. matplotlib `RdBu_r` is common but red-blue is CVD-safer
than red-green; verify the extremes with `palettes.py check`).

## Auditing an existing figure

1. Collect the figure's colors: `\definecolor`/`xcolor` values in the TeX
   source, color literals in the user's plotting scripts, or ask the user
   for the values if only a flattened PDF/PNG exists.
2. Run `palettes.py check` on them; report CONFUSABLE pairs with their
   deltaE and condition.
3. Propose replacements from `okabe-ito`/`tol-*` that keep the figure's
   feel (swap the minimal number of colors), plus the redundant-encoding
   change for borderline pairs.
4. Edit the user's plotting source and ask them to regenerate — never
   claim a recolored result you did not produce, and never alter data
   while in the plotting code.
5. Re-run `check` on the final set; quote the verdict in the change log.
