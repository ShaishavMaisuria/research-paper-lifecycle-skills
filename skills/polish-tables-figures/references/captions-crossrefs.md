# Captions and cross-references

## Contents

1. [Caption position and style per venue family](#caption-position-and-style-per-venue-family)
2. [Writing good captions](#writing-good-captions)
3. [cleveref setup](#cleveref-setup)
4. [Usage rules for \cref](#usage-rules-for-cref)
5. [Common cross-reference bugs](#common-cross-reference-bugs)

## Caption position and style per venue family

The near-universal CS convention: **table captions ABOVE the table, figure
captions BELOW the figure**. The families differ in numbering/typesetting
details, all handled by the class — your job is only source order
(`\caption` before `tabular`, after `\includegraphics`) and caption text.

| Family (`venues/families/`) | Table caption | Figure caption | Class handles | Notes |
|---|---|---|---|---|
| `acm-sigconf`, `acm-journal` (acmart) | above | below | "Table 1:"/"Figure 1:" styling | `\Description{}` alt-text expected on figures; sentence-style captions ending with a period |
| `acm-manuscript-chi` (acmart manuscript) | above | below | same as acmart | CHI also reviews figure accessibility |
| `ieee-conf`, `ieee-journal` (IEEEtran) | above | below | "Fig. 1." abbreviation, table titles in small caps with Roman numerals | do not hand-type "Fig." in captions — the class does it |
| `neurips-style` (neurips_*.sty) | above | below | numbering | the style instructions state captions: figures below, tables above |
| `lncs` (llncs) | above | below | "Fig. 1." / "Table 1." | Springer guidelines; keep captions in the class's default font setup |

These are encoded as the linter's `floats/caption-position` check. They are
stable conventions, but for camera-ready always re-verify against the
venue's live author instructions (`cfp_url` in the profile) — a handful of
venues issue extra caption rules (e.g. caption-based subfigure labeling).

## Writing good captions

- **Sentence-style, ending with a period.** "Figure 3: Latency vs. batch
  size." not "latency curve".
- **Self-contained**: a reader skimming only floats should get the
  takeaway. State what is shown AND what to conclude: "Ours (blue) is 3.3×
  faster at equal accuracy." Define every abbreviation, marker, and error
  band used in the float.
- Table captions above may be longer (they serve as the table's title plus
  reading instructions); figure captions carry the interpretation.
- Boldface or color references in the caption must match the float
  ("best results in bold" — and then they actually are).
- Never put citations' claims in captions that the body doesn't make.

## cleveref setup

```latex
% preamble — ORDER MATTERS
\usepackage{hyperref}                    % usually already loaded/by class
\usepackage[capitalise,noabbrev]{cleveref}   % LAST, after hyperref
```

- **cleveref loads after hyperref** (and after amsmath/listings if used);
  loading it earlier breaks links/names. The linter checks this order.
- `capitalise`: "Figure 3" everywhere (matching most venues' house style)
  and makes sentence-start handling automatic. `noabbrev`: "Figure" not
  "Fig." — drop `noabbrev` for IEEE if the user wants "Fig." mid-sentence
  to match IEEEtran captions; consistency within the paper is what matters.
- acmart note: acmart loads hyperref itself — just add cleveref after
  `\documentclass`. Some templates (e.g. some year-specific ML style
  files) already load cleveref; check the `.log` for "Package cleveref
  already loaded" warnings before adding it.

## Usage rules for \cref

- `\cref{fig:arch}` → "Figure 3". **Never write the word yourself**:
  "Figure~\cref{fig:arch}" renders "Figure Figure 3" (linter:
  `crossref/double-prefix`).
- Without `capitalise`: `\cref` mid-sentence, `\Cref` at sentence start.
- Multiple: `\cref{fig:a,fig:b,tab:c}` → "Figures 1 and 2 and Table 3";
  ranges: `\crefrange{fig:a}{fig:d}`.
- Subfigures (subcaption package): `\cref{fig:eval-latency}` → "Figure 3b".
- Equations: `\cref{eq:loss}` → "Equation (4)" (or keep `\eqref` — one
  style per paper).
- Pick ONE style for the whole paper: either cleveref everywhere or manual
  "Figure~\ref{...}" everywhere (with non-breaking `~`). The linter flags
  mixes. When converting an existing paper, converting TO cleveref is
  usually less work and prevents future drift.

## Common cross-reference bugs

| Bug | Effect | Fix |
|---|---|---|
| `\label` before `\caption` in a float | label binds to the section number → "Table 2" cites as "Table 4.1" | move `\label` directly after (or inside) `\caption` |
| label defined, never `\ref`d | unmotivated float; reviewers ask "why is this here?" | reference it in the text or cut the float |
| `\ref` to a deleted label | "??" in the PDF | the linter lists undefined refs; fix or remove |
| `Figure \ref` without `~` | line break between "Figure" and the number | use `~` — or cleveref, which handles spacing |
| mixed "Fig." / "Figure" in text | style inconsistency reviewers notice | cleveref with one option set |
| cleveref before hyperref | broken or misnamed links | reorder preamble |

After any round of caption/label edits, recompile TWICE (references need
two passes) and re-run
`python3 scripts/check_floats.py paper.tex` to confirm the `crossref/*`
findings are gone.
