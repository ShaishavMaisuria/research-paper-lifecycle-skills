#!/usr/bin/env python3
"""Template, documentclass, and page-limit-risk checker for LaTeX submissions.

Compares \\documentclass (and, for NeurIPS-style venues, the year-versioned
\\usepackage style file) against the venue profile, hunts for margin/spacing
tampering that venues explicitly desk-reject (geometry, savetrees, \\setlength
on layout dimensions, \\linespread < 1, negative \\vspace patterns), and
estimates page-limit risk from an adjacent .log or .pdf if one exists.

Usage:
    python3 check_template.py paper.tex --venue venues/conferences/sigspatial-2026.yml --track Research

Exit codes: 0 clean (or warnings without --strict), 1 ERROR findings, 2 failure.
"""
from __future__ import annotations

import pathlib
import re
import sys

import texlib
from texlib import Finding

# layout lengths whose modification = template tampering (desk-reject grounds)
_HARD_LENGTHS = (
    "textwidth", "textheight", "topmargin", "oddsidemargin", "evensidemargin",
    "columnsep", "headheight", "headsep", "footskip", "marginparwidth",
    "voffset", "hoffset",
)
# spacing lengths whose modification = space-compression (suspicious)
_SOFT_LENGTHS = (
    "parskip", "parindent", "itemsep", "parsep", "topsep", "partopsep",
    "floatsep", "textfloatsep", "intextsep", "dbltextfloatsep", "dblfloatsep",
    "abovecaptionskip", "belowcaptionskip", "abovedisplayskip",
    "belowdisplayskip", "baselineskip",
)
_BANNED_PACKAGES = {
    "geometry": "redefines page geometry",
    "savetrees": "compresses the whole layout",
    "fullpage": "overrides the template margins",
}
_SUSPECT_PACKAGES = {
    "setspace": "line-spacing changes — verify nothing shrinks below single spacing",
    "titlesec": "section-spacing changes — venues treat compressed headings as tampering",
}

_STY_RE = re.compile(
    r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{\s*((?:neurips_\d{4})|(?:icml\d{4})|(?:iclr\d{4}_conference))\s*\}"
)


def _opts(s: str | None) -> list[str]:
    return [o.strip() for o in (s or "").split(",") if o.strip()]


def _count_pdf_pages(pdf: pathlib.Path) -> int | None:
    try:
        data = pdf.read_bytes()
    except OSError:
        return None
    n = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return n or None


def _page_count(tex_path: pathlib.Path) -> tuple[int | None, str]:
    """Best-effort page count from <stem>.log, else <stem>.pdf."""
    log = tex_path.with_suffix(".log")
    if log.is_file():
        try:
            m = re.search(
                r"Output written on .*?\((\d+)\s+pages?",
                log.read_text(encoding="utf-8", errors="replace"),
            )
            if m:
                return int(m.group(1)), f"from {log.name}"
        except OSError:
            pass
    pdf = tex_path.with_suffix(".pdf")
    if pdf.is_file():
        n = _count_pdf_pages(pdf)
        if n:
            return n, f"approximate, from {pdf.name}"
    return None, ""


def collect(doc: texlib.TexDoc, profile: dict, track: dict | None, args) -> list[Finding]:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import venue_profile as vp

    findings: list[Finding] = []
    fmt = profile.get("format") or {}
    review = profile.get("review") or {}
    blind = review.get("blind")

    def add(sev, check, pos, msg):
        f, ln = doc.loc(pos)
        findings.append(Finding(sev, check, f, ln, msg))

    # ---- documentclass --------------------------------------------------
    exp_class, exp_opts = vp.expected_documentclass(profile)
    m = vp._DOCCLASS_RE.search(doc.text)
    if not m:
        findings.append(
            Finding("ERROR", "template/no-documentclass", args.tex, None,
                    "no \\documentclass found in the source")
        )
        found_class, found_opts = None, []
    else:
        found_opts = _opts(m.group(1))
        found_class = m.group(2).strip()
        if exp_class and found_class != exp_class:
            add(
                "ERROR",
                "template/class-mismatch",
                m.start(),
                f"\\documentclass{{{found_class}}} but {profile.get('id')} expects "
                f"{{{exp_class}}} — profile invocation: "
                f"{fmt.get('documentclass', '')!s}".strip(),
            )
        for opt in exp_opts:
            if opt not in found_opts:
                sev = "WARN" if opt == "review" else "ERROR"
                why = {
                    "review": "adds reviewer line numbers",
                    "anonymous": "hides author names (double-blind requirement)",
                }.get(opt, "required by the venue template invocation")
                add(sev, "template/missing-option", m.start(),
                    f"documentclass option [{opt}] missing — {why}")
        if blind == "single" and "anonymous" in found_opts:
            add(
                "ERROR",
                "template/unexpected-option",
                m.start(),
                f"[anonymous] set but {profile.get('id')} is SINGLE-blind: author "
                "names must be listed on the submission",
            )
        cols = fmt.get("columns")
        if cols == 2 and ("onecolumn" in found_opts or doc.find_commands("onecolumn")):
            add("ERROR", "template/columns", m.start(),
                "one-column layout but the venue requires two columns")
        if cols == 1 and "twocolumn" in found_opts:
            add("ERROR", "template/columns", m.start(),
                "twocolumn option set but the venue template is one-column")

    # ---- NeurIPS-style year-versioned style file -------------------------
    exp_sty = vp.expected_style_package(profile)
    if exp_sty:
        hits = list(_STY_RE.finditer(doc.text))
        if not hits:
            findings.append(
                Finding(
                    "ERROR", "template/style-file-missing", args.tex, None,
                    f"no \\usepackage{{{exp_sty}}} found — this venue only accepts "
                    "its current-year style file",
                )
            )
        for h in hits:
            opts, pkg = _opts(h.group(1)), h.group(2)
            if pkg != exp_sty:
                add(
                    "ERROR", "template/style-file-year", h.start(),
                    f"\\usepackage{{{pkg}}} but {profile.get('id')} requires "
                    f"{exp_sty} — submitting on a prior year's style file is a "
                    "desk-reject risk",
                )
            if "final" in opts:
                add("WARN", "template/style-final-option", h.start(),
                    "[final] is the camera-ready mode: it prints author names — "
                    "remove it for the anonymous submission")
            if "preprint" in opts:
                add("ERROR", "template/style-preprint-option", h.start(),
                    "[preprint] is for arXiv versions, not venue submission")

    # ---- margin / template tampering -------------------------------------
    for m2 in re.finditer(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", doc.text):
        for pkg in (p.strip() for p in m2.group(1).split(",")):
            if pkg in _BANNED_PACKAGES:
                add("ERROR", "template/banned-package", m2.start(),
                    f"\\usepackage{{{pkg}}} — {_BANNED_PACKAGES[pkg]}; margin/"
                    "template tampering is explicit desk-reject grounds")
            elif pkg in _SUSPECT_PACKAGES:
                add("WARN", "template/suspect-package", m2.start(),
                    f"\\usepackage{{{pkg}}} — {_SUSPECT_PACKAGES[pkg]}")
    for m2 in re.finditer(r"\\(?:geometry|newgeometry)\s*\{", doc.text):
        add("ERROR", "template/geometry-call", m2.start(),
            "\\geometry{...} call redefines the page layout")

    for m2 in re.finditer(
        r"\\(?:setlength|addtolength)\s*\{?\s*\\([a-zA-Z]+)\s*\}?", doc.text
    ):
        name = m2.group(1)
        if name in _HARD_LENGTHS:
            add("ERROR", "template/layout-length", m2.start(),
                f"\\setlength on \\{name} — layout dimension changes are "
                "template tampering")
        elif name in _SOFT_LENGTHS:
            add("WARN", "template/spacing-length", m2.start(),
                f"\\setlength on \\{name} — spacing compression; reviewers and "
                "chairs check for this")

    for m2 in re.finditer(
        r"\\(?:linespread\s*\{\s*([0-9.]+)|renewcommand\s*\{?\\baselinestretch\}?\s*\{\s*([0-9.]+)|setstretch\s*\{\s*([0-9.]+))",
        doc.text,
    ):
        val = next(g for g in m2.groups() if g)
        try:
            x = float(val)
        except ValueError:
            continue
        if x < 1.0:
            add("ERROR", "template/line-spacing", m2.start(),
                f"line spacing compressed to {val} (<1.0) — desk-reject grounds")
        else:
            add("INFO", "template/line-spacing", m2.start(),
                f"line spacing changed to {val} — confirm the template allows it")

    if re.search(r"\\renewcommand\s*\{?\\normalsize\}?", doc.text):
        m2 = re.search(r"\\renewcommand\s*\{?\\normalsize\}?", doc.text)
        add("ERROR", "template/font-redefinition", m2.start(),
            "\\renewcommand of \\normalsize — body font tampering")

    neg = list(re.finditer(r"\\(?:vspace\*?\s*\{\s*-|vskip\s*-)", doc.text))
    for m2 in neg[:10]:
        add("WARN", "template/negative-vspace", m2.start(),
            "negative \\vspace/\\vskip — occasional use is common but a pattern "
            "of them reads as space compression")
    if len(neg) >= 5:
        findings.append(
            Finding("WARN", "template/negative-vspace-pattern", args.tex, None,
                    f"{len(neg)} negative vertical-space commands found — "
                    "systematic space compression risks a desk reject")
        )
    for m2 in re.finditer(r"\\enlargethispage\b", doc.text):
        add("WARN", "template/enlargethispage", m2.start(),
            "\\enlargethispage extends the text block on a page")

    # ---- page-limit risk --------------------------------------------------
    limit = (track or {}).get("page_limit")
    excludes = (track or {}).get("page_limit_excludes") or []
    pages, src = _page_count(pathlib.Path(args.tex))
    if limit is None:
        findings.append(
            Finding("INFO", "template/page-limit", args.tex, None,
                    "no hard page limit in the profile for this track — verify "
                    f"against the live CFP: {profile.get('cfp_url')}")
        )
    elif pages is None:
        findings.append(
            Finding("INFO", "template/page-count-unknown", args.tex, None,
                    f"limit is {limit} pages (excludes: {', '.join(excludes) or 'nothing'}) "
                    "but no compiled .log/.pdf found next to the .tex — compile "
                    "and re-run, or check the page count manually")
        )
    else:
        desc = f"compiled document is {pages} pages ({src}); limit {limit}"
        if excludes:
            if pages > limit:
                findings.append(
                    Finding("WARN", "template/page-limit-risk", args.tex, None,
                            f"{desc} EXCLUDING {', '.join(excludes)} — confirm that "
                            f"content before the excluded matter ends by page {limit}")
                )
            else:
                findings.append(
                    Finding("INFO", "template/page-limit-ok", args.tex, None,
                            f"{desc} excluding {', '.join(excludes)} — within limit")
                )
        elif pages > limit:
            findings.append(
                Finding("ERROR", "template/page-limit-exceeded", args.tex, None,
                        f"{desc} pages INCLUDING everything — over the limit; "
                        "venues desk-reject for this without review")
            )
        else:
            findings.append(
                Finding("INFO", "template/page-limit-ok", args.tex, None, desc)
            )

    return findings


def main() -> int:
    return texlib.run_checker(
        "check_template",
        __doc__.splitlines()[0],
        collect,
    )


if __name__ == "__main__":
    sys.exit(main())
