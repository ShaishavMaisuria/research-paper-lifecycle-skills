# Tables: booktabs conversion and column sizing

## Contents

1. [The booktabs rules](#the-booktabs-rules)
2. [Mechanical conversion recipe](#mechanical-conversion-recipe)
3. [Before/after example](#beforeafter-example)
4. [Column sizing within the page budget](#column-sizing-within-the-page-budget)
5. [Number columns](#number-columns)
6. [Headers, footnotes, and highlighting](#headers-footnotes-and-highlighting)
7. [Packages and venue notes](#packages-and-venue-notes)

## The booktabs rules

Professional tables (the style in essentially every ACM/IEEE/NeurIPS
best-paper) follow three rules from the booktabs documentation:

1. **Never use vertical rules.** Columns are separated by whitespace.
2. **Never use double rules.** `\hline\hline` is a typewriter-era artifact.
3. **Use exactly three rule weights**: `\toprule` (above header),
   `\midrule` (below header), `\bottomrule` (after last row). Partial-width
   group separators use `\cmidrule(lr){i-j}`; extra visual breathing room
   between row groups uses `\addlinespace`, not more rules.

Horizontal rules between every body row are also out — if rows are hard to
track, the table is too wide or too dense, not under-ruled.

## Mechanical conversion recipe

This conversion is presentation-only. Cell content must survive
byte-for-byte — diff the table body afterwards to prove it.

1. Ensure `\usepackage{booktabs}` is in the preamble (acmart loads it
   already; IEEEtran, llncs, neurips, article do not).
2. In the column spec, delete every `|` (and `||`): `{|l|c|r|}` → `{lcr}`.
3. First `\hline` (or `\hline\hline`) → `\toprule`.
4. The `\hline` separating header row(s) from the body → `\midrule`.
5. Last `\hline` (or `\hline\hline`) → `\bottomrule`.
6. Interior `\hline`s between body rows → delete; if a group boundary truly
   needs marking, use `\addlinespace` or, for header-group underlines,
   `\cmidrule(lr){i-j}` (the `(lr)` trims the rule ends so adjacent
   cmidrules do not touch).
7. `\cline{i-j}` → `\cmidrule(lr){i-j}`.
8. Remove `\arrayrulewidth` / `\doublerulesep` tweaks — booktabs handles
   weights.
9. Recompile; run `python3 scripts/check_floats.py` again — the
   `tables/*` findings for that table must be gone.

## Before/after example

Before:

```latex
\begin{tabular}{|l|c|c|}
\hline\hline
Method & Accuracy & Time (s) \\
\hline
Baseline & 0.85 & 40.2 \\
\hline
Ours & \textbf{0.91} & 12.0 \\
\hline\hline
\end{tabular}
```

After:

```latex
\begin{tabular}{lcc}
\toprule
Method & Accuracy & Time (s) \\
\midrule
Baseline & 0.85 & 40.2 \\
Ours & \textbf{0.91} & 12.0 \\
\bottomrule
\end{tabular}
```

## Column sizing within the page budget

A table must fit `\columnwidth` (one column) or `\textwidth` (`table*`,
two-column span). Diagnose with a compile: the linter parses
`Overfull \hbox (...pt too wide)` from the `.log` and reports the worst
offenders. Apply these in order — each step is less invasive than the next:

1. **Cut content.** Drop columns derivable from others, merge "Yes/No"
   columns into symbols (`\checkmark` from amssymb / `--`), move
   rarely-compared columns to an appendix table.
2. **Abbreviate headers** and put units in the header once (`Time (s)`),
   never in every cell. Two-line headers: `\begin{tabular}{@{}l...` with
   manual line break in the header cell via `\shortstack` or a `p{}`
   column only for that header.
3. **Trim repeated text in cells**: dataset/method names shortened with a
   legend in the caption ("B = baseline, +A = with attention").
4. **Reduce padding**: `\setlength{\tabcolsep}{4pt}` (default 6pt; do not
   go below ~3pt). Kill outer padding with `@{}` at the spec edges:
   `{@{}lcc@{}}`.
5. **`tabularx`** to absorb slack in one text column:
   `\begin{tabularx}{\columnwidth}{@{}Xrr@{}}` — `X` wraps; never make
   number columns `X`.
6. **Numbers**: fewer significant digits (consistently!), scientific
   notation factored into the header (`Time ($\times 10^3$ s)`).
   Digit changes are a USER decision — propose, never silently round.
7. **Promote to `table*`** to span both columns at two-column venues.
8. **Last resorts** (ask the user, check the venue): `\small` for the whole
   table (many venues set tables in `\small` anyway; `\scriptsize`/`\tiny`
   are below print-readable), or a rotated `sidewaystable` (rotating
   package; journals more than conferences).

**Never `\resizebox{\columnwidth}{!}{...}`.** It scales fonts to arbitrary
sizes (often unreadably small), which reviewers flag and some venues treat
as format tampering. If a table only fits via resizebox, it has too many
columns — restructure (transpose, split, or move to appendix).

## Number columns

- Right-align integer and decimal columns (`r`), or use siunitx `S` columns
  (`S[table-format=2.1]`) for decimal-point alignment when decimals vary.
  Check the venue's accepted-package list before adding siunitx for
  camera-ready (ACM TAPS publishes one; siunitx is commonly on it — verify).
- Same number of decimals down a column. Percent signs in the header, not
  the cells.
- Use `--` (en-dash) for "not applicable", never empty cells or 0.

## Headers, footnotes, and highlighting

- Table notes: `threeparttable` + `tablenotes` keeps notes at table width;
  do not use `\footnote` inside tables (it silently vanishes in floats).
- Highlight the best result with `\textbf{}` — ask the user for the
  criterion (best per column? per dataset? statistically tied bolded too?).
  Do not rely on color alone (grayscale print, colorblind readers).
- Multi-level headers: `\multicolumn{n}{c}{...}` over `\cmidrule(lr)`
  underlines; `\multirow` (multirow package) sparingly for row labels.

## Packages and venue notes

| Construct | Needs package | Notes |
|---|---|---|
| `\toprule` etc. | booktabs | loaded by acmart automatically |
| `tabularx` env | tabularx | `X` columns |
| `\multirow` | multirow | |
| `S` columns | siunitx | verify against venue accepted-package list |
| table notes | threeparttable | |
| `sidewaystable` | rotating | check venue tolerance first |

Venue specifics live in `venues/` profiles — and a stale profile is worse
than none: re-verify any table-relevant rule (font-size floor, package
allowlist, color requirements) against the live `cfp_url` before applying it.
