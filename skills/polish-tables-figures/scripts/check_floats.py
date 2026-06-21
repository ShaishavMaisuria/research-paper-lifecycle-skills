#!/usr/bin/env python3
"""Lint LaTeX tables, figures, captions, and cross-references.

Deterministic checks for the polish-tables-figures skill. Stdlib only.

Check groups:
  tables/*    booktabs style (vertical rules, \\hline, \\cline, double rules),
              missing booktabs package, \\resizebox/\\scalebox font scaling,
              tiny fonts inside tables
  figures/*   missing \\centering, deprecated subfigure package, subcaption/
              subfig package presence, width=\\textwidth inside a single-column
              float at a two-column venue, hard-coded widths, raster formats,
              missing ACM \\Description
  floats/*    caption position per venue convention (tables above, figures
              below), missing caption/label, [h]/[H] placement
  captions/*  trailing period
  crossref/*  label-before-caption, undefined refs, unreferenced floats,
              mixed "Figure~\\ref" vs \\cref styles, "Figure \\cref" double
              prefix, cleveref load order, lowercase \\cref at sentence start
  layout/*    Overfull \\hbox entries parsed from the .log

Exit codes: 0 = no errors, 1 = errors found (or warnings with --strict),
2 = bad arguments / unreadable files.
"""

import argparse
import bisect
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import venueyaml
except ImportError:  # pragma: no cover
    venueyaml = None

SEV_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}

# ---------------------------------------------------------------------------
# tex reading
# ---------------------------------------------------------------------------

COMMENT_RE = re.compile(r"(?<!\\)%.*$")
INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def _strip_comment(line):
    return COMMENT_RE.sub("", line)


def read_corpus(main_path, follow_inputs=True, _seen=None, _depth=0):
    """Read a .tex file (recursively inlining \\input/\\include in place).

    Returns a list of records: {"path", "line", "text"} where text has
    comments stripped. Raises OSError if the MAIN file is unreadable;
    silently skips unreadable included files (a finding is not needed —
    the document would not compile either).
    """
    if _seen is None:
        _seen = set()
    real = os.path.realpath(main_path)
    if real in _seen or _depth > 8:
        return []
    _seen.add(real)
    with open(main_path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    base_dir = os.path.dirname(os.path.abspath(main_path))
    records = []
    for lineno, line in enumerate(raw.splitlines(), 1):
        text = _strip_comment(line)
        records.append({"path": main_path, "line": lineno, "text": text})
        if follow_inputs:
            for m in INPUT_RE.finditer(text):
                target = m.group(1).strip()
                if not os.path.splitext(target)[1]:
                    target += ".tex"
                child = target if os.path.isabs(target) else os.path.join(base_dir, target)
                if os.path.isfile(child):
                    records.extend(
                        read_corpus(child, follow_inputs, _seen, _depth + 1))
    return records


# ---------------------------------------------------------------------------
# brace / colspec helpers
# ---------------------------------------------------------------------------

def read_group(text, i):
    """text[i] must be '{'. Return (content, index_after_close) or (None, i)."""
    if i >= len(text) or text[i] != "{":
        return None, i
    depth, j = 0, i
    while j < len(text):
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    return None, i


def _skip_ws(text, i):
    while i < len(text) and text[i] in " \t\n":
        i += 1
    return i


def tabular_colspec(text, env, i):
    """Extract the column spec of a tabular-like env starting after \\begin{env}."""
    need = 2 if env in ("tabularx", "tabular*", "tabulary") else 1
    groups = []
    while len(groups) < need:
        i = _skip_ws(text, i)
        if i < len(text) and text[i] == "[":
            close = text.find("]", i)
            if close == -1:
                break
            i = close + 1
            continue
        if i < len(text) and text[i] == "{":
            g, i = read_group(text, i)
            if g is None:
                break
            groups.append(g)
            continue
        break
    return groups[-1] if len(groups) == need else None


# ---------------------------------------------------------------------------
# findings
# ---------------------------------------------------------------------------

class Findings:
    def __init__(self):
        self.items = []

    def add(self, severity, check, path, line, message):
        self.items.append({
            "severity": severity, "check": check,
            "file": path, "line": line, "message": message,
        })

    def counts(self):
        out = {"ERROR": 0, "WARN": 0, "INFO": 0}
        for it in self.items:
            out[it["severity"]] += 1
        return out

    def sorted(self):
        return sorted(
            self.items,
            key=lambda it: (SEV_ORDER[it["severity"]], it["file"], it["line"] or 0))


# ---------------------------------------------------------------------------
# preamble: documentclass + packages
# ---------------------------------------------------------------------------

PKG_RE = re.compile(r"\\(?:usepackage|RequirePackage)\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}")
CLASS_RE = re.compile(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}")


def scan_preamble(corpus):
    """Return (docclass, class_opts, packages) — packages maps name -> dict."""
    docclass, class_opts = None, []
    packages = {}
    for seq, rec in enumerate(corpus):
        m = CLASS_RE.search(rec["text"])
        if m and docclass is None:
            docclass = m.group(2).strip()
            class_opts = [o.strip() for o in (m.group(1) or "").split(",") if o.strip()]
        for pm in PKG_RE.finditer(rec["text"]):
            opts = [o.strip() for o in (pm.group(1) or "").split(",") if o.strip()]
            for name in pm.group(2).split(","):
                name = name.strip()
                if name and name not in packages:
                    packages[name] = {"seq": seq, "opts": opts,
                                      "path": rec["path"], "line": rec["line"]}
    return docclass, class_opts, packages


def detect_columns(docclass, class_opts):
    if docclass == "acmart":
        return 2 if any(o.startswith("sigconf") for o in class_opts) else 1
    if docclass == "IEEEtran":
        return 1 if "onecolumn" in class_opts else 2
    if "twocolumn" in class_opts:
        return 2
    return 1


# ---------------------------------------------------------------------------
# float blocks
# ---------------------------------------------------------------------------

BEGIN_FLOAT_RE = re.compile(r"\\begin\{(figure\*?|table\*?)\}\s*(?:\[([^\]]*)\])?")
TABULAR_RE = re.compile(r"\\begin\{(tabularx|tabulary|tabular\*?|array|longtable)\}")
GRAPHIC_RE = re.compile(r"\\includegraphics|\\begin\{tikzpicture\}|\\pgfimage|\\epsfig")
CAPTION_RE = re.compile(r"\\caption\s*(?:\[[^\]]*\])?\s*\{")
LABEL_RE = re.compile(r"\\label\s*\{([^}]+)\}")
SUBFIG_ENV_RE = re.compile(r"\\begin\{subfigure\}")
BOOKTABS_RE = re.compile(r"\\(?:toprule|midrule|bottomrule|cmidrule)")
WIDTH_TEXTWIDTH_RE = re.compile(r"width\s*=\s*[\d.]*\s*\\textwidth")
WIDTH_ABS_RE = re.compile(r"width\s*=\s*\d+(?:\.\d+)?\s*(cm|mm|in|pt)\b")
RASTER_RE = re.compile(r"\\includegraphics[^{]*\{([^}]+\.(?:png|jpe?g|bmp|gif))\}",
                       re.IGNORECASE)


class FloatBlock:
    def __init__(self, env, placement, records):
        self.env = env                      # figure | figure* | table | table*
        self.placement = placement          # raw placement string or None
        self.records = records              # records INSIDE the env (incl. begin line)
        self.offsets = []
        parts, pos = [], 0
        for rec in records:
            self.offsets.append(pos)
            parts.append(rec["text"])
            pos += len(rec["text"]) + 1
        self.text = "\n".join(parts)

    def loc(self, char_pos):
        idx = bisect.bisect_right(self.offsets, char_pos) - 1
        rec = self.records[max(idx, 0)]
        return rec["path"], rec["line"]

    @property
    def kind(self):
        return "table" if self.env.startswith("table") else "figure"

    @property
    def starred(self):
        return self.env.endswith("*")


def extract_floats(corpus):
    floats, i, n = [], 0, len(corpus)
    while i < n:
        m = BEGIN_FLOAT_RE.search(corpus[i]["text"])
        if not m:
            i += 1
            continue
        env = m.group(1)
        end_re = re.compile(r"\\end\{" + re.escape(env) + r"\}")
        block = [corpus[i]]
        j = i + 1
        closed = end_re.search(corpus[i]["text"], m.end()) is not None
        while not closed and j < n:
            block.append(corpus[j])
            if end_re.search(corpus[j]["text"]):
                closed = True
            j += 1
        floats.append(FloatBlock(env, m.group(2), block))
        i = j if j > i + 1 else i + 1
    return floats


def _subfigure_spans(text):
    spans, start = [], 0
    while True:
        b = text.find(r"\begin{subfigure}", start)
        if b == -1:
            return spans
        e = text.find(r"\end{subfigure}", b)
        if e == -1:
            spans.append((b, len(text)))
            return spans
        spans.append((b, e))
        start = e + 1


def _outside(pos, spans):
    return all(not (a <= pos < b) for a, b in spans)


# ---------------------------------------------------------------------------
# per-float checks
# ---------------------------------------------------------------------------

def check_float(fb, F, ctx):
    """Run all checks for one float block. ctx: dict with docclass, columns,
    packages, convention_label."""
    text = fb.text
    head_path, head_line = fb.records[0]["path"], fb.records[0]["line"]
    spans = _subfigure_spans(text)

    # ---- placement ----
    if fb.placement is not None:
        pl = fb.placement.strip()
        if pl and set(pl) <= {"h", "!"}:
            F.add("WARN", "floats/placement", head_path, head_line,
                  "[%s] placement fights the float algorithm and strands floats; "
                  "use [t] or [htbp]" % pl)
        elif "H" in pl:
            F.add("WARN", "floats/placement", head_path, head_line,
                  "[H] (float package) forces in-place placement and breaks float "
                  "ordering; most venue templates expect [t]/[htbp]")

    # ---- caption / label / content positions (outside subfigures) ----
    cap_m = None
    for m in CAPTION_RE.finditer(text):
        if _outside(m.start(), spans):
            cap_m = m
            break
    if fb.kind == "table":
        cm = TABULAR_RE.search(text)
        content_pos = cm.start() if cm else None
    else:
        gm = GRAPHIC_RE.search(text)
        content_pos = gm.start() if gm else None

    if cap_m is None:
        F.add("WARN", "floats/missing-caption", head_path, head_line,
              "%s has no \\caption" % fb.env)
    elif content_pos is not None:
        if fb.kind == "table" and cap_m.start() > content_pos:
            F.add("WARN", "floats/caption-position", *fb.loc(cap_m.start()),
                  "table caption is BELOW the tabular body; %s convention puts "
                  "table captions ABOVE the table" % ctx["convention_label"])
        if fb.kind == "figure" and cap_m.start() < content_pos:
            F.add("WARN", "floats/caption-position", *fb.loc(cap_m.start()),
                  "figure caption is ABOVE the graphic; %s convention puts "
                  "figure captions BELOW the figure" % ctx["convention_label"])

    labels = [(m, m.group(1)) for m in LABEL_RE.finditer(text)]
    outer_labels = [(m, name) for m, name in labels if _outside(m.start(), spans)]
    if not labels:
        F.add("WARN", "floats/missing-label", head_path, head_line,
              "%s has no \\label — it cannot be referenced from the text" % fb.env)
    elif cap_m is not None and outer_labels:
        first = outer_labels[0][0]
        if first.start() < cap_m.start():
            F.add("ERROR", "crossref/label-before-caption", *fb.loc(first.start()),
                  "\\label{%s} appears BEFORE \\caption; it will pick up the "
                  "surrounding section number — move it after (or inside) the "
                  "caption" % outer_labels[0][1])

    # ---- caption text: trailing period ----
    if cap_m is not None:
        content, _end = read_group(text, cap_m.end() - 1)
        if content is not None:
            cleaned = LABEL_RE.sub("", content).strip()
            if cleaned and cleaned[-1] not in ".!?":
                F.add("INFO", "captions/no-period", *fb.loc(cap_m.start()),
                      "caption does not end with a period; ACM/IEEE/LNCS captions "
                      "are sentence-style and end with one")

    # ---- centering ----
    if content_pos is not None and "\\centering" not in text \
            and "\\begin{center}" not in text:
        F.add("WARN", "floats/missing-centering", head_path, head_line,
              "%s body is not centered — add \\centering after \\begin{%s}"
              % (fb.env, fb.env))

    # ---- two-column width ----
    if ctx["columns"] == 2 and not fb.starred:
        m = WIDTH_TEXTWIDTH_RE.search(text)
        if m:
            F.add("WARN", "floats/textwidth-in-column", *fb.loc(m.start()),
                  "width=\\textwidth inside single-column %s at a two-column venue "
                  "overflows the column; use \\columnwidth (or \\linewidth), or span "
                  "both columns with %s*" % (fb.env, fb.kind))

    # ---- table-specific ----
    if fb.kind == "table":
        has_booktabs_rules = BOOKTABS_RE.search(text) is not None
        hlines = len(re.findall(r"\\hline", text))
        if has_booktabs_rules and ctx["docclass"] != "acmart" \
                and "booktabs" not in ctx["packages"]:
            F.add("ERROR", "tables/booktabs-missing", head_path, head_line,
                  "table uses \\toprule/\\midrule/\\bottomrule but booktabs is not "
                  "loaded — add \\usepackage{booktabs} (acmart loads it itself; "
                  "%s does not)" % (ctx["docclass"] or "this class"))
        if hlines:
            if has_booktabs_rules:
                F.add("WARN", "tables/mixed-rules", head_path, head_line,
                      "table mixes \\hline with booktabs rules (%d \\hline); use "
                      "\\toprule/\\midrule/\\bottomrule/\\cmidrule only" % hlines)
            else:
                extra = " (\\hline\\hline found — booktabs never doubles rules)" \
                    if "\\hline\\hline" in text.replace(" ", "") else ""
                F.add("WARN", "tables/hline", head_path, head_line,
                      "table uses %d \\hline; convert to booktabs (\\toprule/"
                      "\\midrule/\\bottomrule)%s" % (hlines, extra))
        if re.search(r"\\cline", text):
            F.add("WARN", "tables/cline", head_path, head_line,
                  "\\cline found; use \\cmidrule(lr){i-j} from booktabs")
        for tm in TABULAR_RE.finditer(text):
            spec = tabular_colspec(text, tm.group(1), tm.end())
            if spec and "|" in spec:
                F.add("WARN", "tables/vertical-rules", *fb.loc(tm.start()),
                      "column spec {%s} uses vertical rules; booktabs style (and "
                      "ACM/IEEE/NeurIPS exemplar tables) drops them — separate "
                      "columns with whitespace" % spec.strip())
            env_pkg = {"tabularx": "tabularx", "tabulary": "tabulary",
                       "longtable": "longtable"}.get(tm.group(1))
            if env_pkg and env_pkg not in ctx["packages"]:
                F.add("ERROR", "tables/missing-package", *fb.loc(tm.start()),
                      "%s environment used but \\usepackage{%s} not found"
                      % (tm.group(1), env_pkg))
        if re.search(r"\\(resizebox|scalebox|adjustbox)", text):
            F.add("WARN", "tables/resizebox", head_path, head_line,
                  "table is scaled with \\resizebox/\\scalebox/adjustbox — this "
                  "shrinks fonts below the venue's readable minimum; restructure "
                  "the table instead (see references/tables.md)")
        fm = re.search(r"\\(tiny|scriptsize)\b", text)
        if fm:
            F.add("WARN", "tables/font-too-small", *fb.loc(fm.start()),
                  "\\%s inside a table is below readable size for print "
                  "proceedings; \\small is the usual floor" % fm.group(1))
        if re.search(r"\\multirow", text) and "multirow" not in ctx["packages"]:
            F.add("ERROR", "tables/missing-package", head_path, head_line,
                  "\\multirow used but \\usepackage{multirow} not found")

    # ---- figure-specific ----
    if fb.kind == "figure":
        if SUBFIG_ENV_RE.search(text) and "subcaption" not in ctx["packages"]:
            F.add("ERROR", "figures/missing-package", head_path, head_line,
                  "subfigure environment used but \\usepackage{subcaption} "
                  "not found")
        if re.search(r"\\subfloat", text) and "subfig" not in ctx["packages"]:
            F.add("ERROR", "figures/missing-package", head_path, head_line,
                  "\\subfloat used but \\usepackage{subfig} not found")
        m = WIDTH_ABS_RE.search(text)
        if m:
            F.add("INFO", "figures/hardcoded-width", *fb.loc(m.start()),
                  "hard-coded width (%s) — prefer fractions of \\columnwidth/"
                  "\\linewidth so the figure tracks the template" % m.group(0))
        rm = RASTER_RE.search(text)
        if rm:
            F.add("INFO", "figures/raster-image", *fb.loc(rm.start()),
                  "raster graphic %s — plots and diagrams should be vector "
                  "(PDF); raster is fine only for photos/screenshots at "
                  ">=300 dpi" % os.path.basename(rm.group(1)))
        if ctx["docclass"] == "acmart" and "\\Description" not in text:
            F.add("WARN", "figures/missing-description", head_path, head_line,
                  "acmart figure without \\Description{...}; ACM requires alt-text "
                  "descriptions for accessibility and TAPS flags missing ones")


# ---------------------------------------------------------------------------
# document-wide cross-reference checks
# ---------------------------------------------------------------------------

REF_RE = re.compile(r"\\(ref|eqref|pageref|autoref|vref|cref|Cref|crefrange|Crefrange)\*?\s*\{([^}]+)\}")
MANUAL_PREFIX_REF_RE = re.compile(r"\b(Figure|Figures|Fig\.|Figs\.|Table|Tables|Tab\.)\s*~?\s*\\ref\b")
MANUAL_PREFIX_CREF_RE = re.compile(r"\b(Figure|Figures|Fig\.|Figs\.|Table|Tables|Tab\.)\s*~?\s*\\[cC]ref\b")
SENTENCE_START_CREF_RE = re.compile(r"[.!?]\s+\\cref\b")


def check_crossrefs(corpus, floats, F, ctx, no_inputs):
    labels = {}
    for rec in corpus:
        for m in LABEL_RE.finditer(rec["text"]):
            labels.setdefault(m.group(1), (rec["path"], rec["line"]))
    float_labels = set()
    for fb in floats:
        for m in LABEL_RE.finditer(fb.text):
            float_labels.add(m.group(1))

    refs, cref_count, manual_count = [], 0, 0
    for rec in corpus:
        for m in REF_RE.finditer(rec["text"]):
            cmd = m.group(1)
            for name in m.group(2).split(","):
                refs.append((cmd, name.strip(), rec["path"], rec["line"]))
            if cmd in ("cref", "Cref", "crefrange", "Crefrange"):
                cref_count += 1
        manual_count += len(MANUAL_PREFIX_REF_RE.findall(rec["text"]))
        for m in MANUAL_PREFIX_CREF_RE.finditer(rec["text"]):
            F.add("ERROR", "crossref/double-prefix", rec["path"], rec["line"],
                  '"%s \\cref" produces "Figure Figure 1" — \\cref adds the '
                  "name itself; drop the manual word" % m.group(1))

    # undefined refs
    sev = "INFO" if no_inputs else "ERROR"
    for cmd, name, path, line in refs:
        if name and name not in labels:
            F.add(sev, "crossref/undefined-reference", path, line,
                  "\\%s{%s} has no matching \\label%s"
                  % (cmd, name,
                     " (some files were not followed; re-run without --no-inputs)"
                     if no_inputs else ""))

    # unreferenced floats
    referenced = {name for _cmd, name, _p, _l in refs}
    for fb in floats:
        for m in LABEL_RE.finditer(fb.text):
            if m.group(1) not in referenced:
                F.add("WARN", "crossref/unreferenced-float", *fb.loc(m.start()),
                      "%s labeled %s is never referenced in the text — venues "
                      "expect every float cited (or cut it)"
                      % (fb.env, m.group(1)))

    # style consistency
    packages = ctx["packages"]
    if cref_count and "cleveref" not in packages:
        first = next(rec for rec in corpus if re.search(r"\\[cC]ref\b", rec["text"]))
        F.add("ERROR", "crossref/cref-without-package", first["path"], first["line"],
              "\\cref used but \\usepackage{cleveref} not found")
    if manual_count and cref_count:
        F.add("WARN", "crossref/mixed-ref-styles", corpus[0]["path"], None,
              'document mixes %d manual "Figure~\\ref" style references with %d '
              "\\cref calls — pick one (recommended: cleveref everywhere)"
              % (manual_count, cref_count))
    if "cleveref" in packages and "hyperref" in packages:
        if packages["cleveref"]["seq"] < packages["hyperref"]["seq"]:
            F.add("ERROR", "crossref/cleveref-load-order",
                  packages["cleveref"]["path"], packages["cleveref"]["line"],
                  "cleveref must be loaded AFTER hyperref (it is loaded before); "
                  "move \\usepackage{cleveref} to the end of the preamble")
    capitalise = "cleveref" in packages and any(
        o in ("capitalise", "capitalize") for o in packages["cleveref"]["opts"])
    if cref_count and not capitalise:
        for rec in corpus:
            m = SENTENCE_START_CREF_RE.search(rec["text"])
            if m:
                F.add("WARN", "crossref/sentence-start-cref", rec["path"], rec["line"],
                      "lowercase \\cref at sentence start — use \\Cref here, or load "
                      "cleveref with the capitalise option")


# ---------------------------------------------------------------------------
# log parsing (column sizing within the page budget)
# ---------------------------------------------------------------------------

OVERFULL_RE = re.compile(
    r"Overfull \\hbox \(([\d.]+)pt too wide\) "
    r"(?:in paragraph at lines (\d+)--(\d+)|detected at line (\d+)|in alignment at lines (\d+)--(\d+))")


def check_log(log_path, main_tex, F, threshold):
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            log = fh.read()
    except OSError as exc:
        F.add("INFO", "layout/no-log", log_path, None,
              "could not read log (%s); compile and re-run for the overfull-box "
              "check" % exc)
        return
    hits = OVERFULL_RE.findall(log)
    if not hits:
        F.add("INFO", "layout/overfull-hbox", log_path, None,
              "no Overfull \\hbox entries in the log — nothing sticks out of "
              "the page budget")
        return
    flagged = 0
    for pts, a, b, c, d, e in hits:
        if float(pts) < threshold:
            continue
        flagged += 1
        if flagged > 10:
            continue
        where = a or c or d
        line = int(where) if where else None
        F.add("WARN", "layout/overfull-hbox", main_tex, line,
              "Overfull \\hbox: %spt too wide (log: lines %s) — a table or "
              "figure is wider than its column; see references/tables.md "
              "'Column sizing'" % (pts, a + "--" + b if a else (e and d + "--" + e or where)))
    if flagged > 10:
        F.add("WARN", "layout/overfull-hbox", main_tex, None,
              "...and %d more overfull boxes over %.1fpt (showing first 10)"
              % (flagged - 10, threshold))
    if flagged == 0:
        F.add("INFO", "layout/overfull-hbox", log_path, None,
              "%d Overfull \\hbox entr%s in the log, all under %.1fpt — "
              "cosmetic only" % (len(hits), "y" if len(hits) == 1 else "ies",
                                 threshold))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def load_venue(path):
    if venueyaml is None:
        raise RuntimeError("venueyaml.py not found next to this script")
    return venueyaml.load_with_family(path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint LaTeX tables/figures/captions/cross-references "
                    "(booktabs style, caption position, cleveref consistency, "
                    "overfull boxes). Stdlib only; advisory output.")
    parser.add_argument("tex", help="main .tex file (the one with \\documentclass)")
    parser.add_argument("--venue", help="venue profile YAML (venues/conferences/"
                        "<venue>-<year>.yml); sets columns + template conventions")
    parser.add_argument("--log", help=".log file from a compile (default: "
                        "<tex basename>.log if present) for overfull-box checks")
    parser.add_argument("--overfull-threshold", type=float, default=2.0,
                        help="flag overfull boxes wider than this many pt "
                             "(default: 2.0)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on warnings too")
    parser.add_argument("--no-inputs", action="store_true",
                        help="do not follow \\input/\\include")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.tex):
        sys.stderr.write("error: tex file not found: %s\n" % args.tex)
        return 2

    profile = None
    if args.venue:
        if not os.path.isfile(args.venue):
            sys.stderr.write("error: venue profile not found: %s\n" % args.venue)
            return 2
        try:
            profile = load_venue(args.venue)
        except Exception as exc:
            sys.stderr.write("error: cannot parse venue profile: %s\n" % exc)
            return 2

    try:
        corpus = read_corpus(args.tex, follow_inputs=not args.no_inputs)
    except OSError as exc:
        sys.stderr.write("error: cannot read %s: %s\n" % (args.tex, exc))
        return 2
    if not corpus:
        sys.stderr.write("error: %s is empty\n" % args.tex)
        return 2

    docclass, class_opts, packages = scan_preamble(corpus)
    columns = None
    template = None
    if profile:
        fmt = profile.get("format") or {}
        columns = fmt.get("columns")
        template = fmt.get("template")
    if columns is None:
        columns = detect_columns(docclass, class_opts)
    convention_label = {
        "acmart": "ACM", "IEEEtran": "IEEE", "neurips": "NeurIPS",
        "llncs": "LNCS (Springer)", "chi-manuscript": "ACM (CHI)",
    }.get(template or docclass, (template or docclass or "the standard"))

    ctx = {"docclass": docclass, "class_opts": class_opts, "packages": packages,
           "columns": columns, "convention_label": convention_label}

    F = Findings()
    if re.search(r"\\usepackage(?:\[[^\]]*\])?\s*\{[^}]*\bsubfigure\b", "\n".join(
            r["text"] for r in corpus)):
        p = packages.get("subfigure", {})
        F.add("WARN", "figures/deprecated-package",
              p.get("path", args.tex), p.get("line"),
              "package 'subfigure' is deprecated and clashes with hyperref; "
              "use subcaption (\\begin{subfigure}) instead")

    floats = extract_floats(corpus)
    for fb in floats:
        check_float(fb, F, ctx)
    check_crossrefs(corpus, floats, F, ctx, args.no_inputs)

    log_path = args.log or os.path.splitext(args.tex)[0] + ".log"
    if os.path.isfile(log_path):
        check_log(log_path, args.tex, F, args.overfull_threshold)
    else:
        F.add("INFO", "layout/no-log", args.tex, None,
              "no .log found (%s); compile and re-run (or pass --log) to check "
              "overfull boxes / column sizing" % os.path.basename(log_path))

    counts = F.counts()
    verdict = ("FAIL" if counts["ERROR"] else
               "PASS-WITH-WARNINGS" if counts["WARN"] else "PASS")
    if args.json:
        json.dump({"findings": F.sorted(), "summary": counts,
                   "floats": len(floats), "verdict": verdict},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for it in F.sorted():
            loc = "%s:%s" % (it["file"], it["line"] if it["line"] else "-")
            print("%-5s %-32s %s  %s" % (it["severity"], it["check"], loc,
                                         it["message"]))
        print("\n%d float(s) checked. %d error(s), %d warning(s), %d info. "
              "Verdict: %s" % (len(floats), counts["ERROR"], counts["WARN"],
                               counts["INFO"], verdict))

    if counts["ERROR"] or (args.strict and counts["WARN"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
