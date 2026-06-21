#!/usr/bin/env python3
"""Abstract-length and keywords-format checker for LaTeX submissions.

Counts abstract words against the venue profile's format.abstract_words
bounds (or reports against the 150-250 CS norm when the venue mandates no
bound), flags multi-paragraph abstracts at venues that want one paragraph,
citations/URLs inside the abstract, and validates the keywords block format
(ACM \\keywords + CCS, IEEE Index Terms, LNCS 3-6 keywords).

Usage:
    python3 check_abstract.py paper.tex --venue venues/conferences/sigspatial-2026.yml

Exit codes: 0 clean (or warnings without --strict), 1 ERROR findings, 2 failure.
"""
from __future__ import annotations

import re
import sys

import texlib
from texlib import Finding


def _get_abstract(doc: texlib.TexDoc):
    """Returns (pos, text) of the abstract, or (None, None)."""
    spans = doc.env_spans("abstract")
    if spans:
        start, _end, inner = spans[0]
        return start, inner
    cmds = doc.find_commands("abstract")
    for pos, _opt, arg in cmds:
        if arg and arg.strip():
            return pos, arg
    return None, None


def _split_keywords(arg: str) -> list[str]:
    parts = re.split(r"\\and\b|[,;·]", arg)
    return [p.strip() for p in (texlib.de_latex(p).strip() for p in parts) if p.strip()]


def collect(doc: texlib.TexDoc, profile: dict, track: dict | None, args) -> list[Finding]:
    findings: list[Finding] = []
    fmt = profile.get("format") or {}
    bounds = fmt.get("abstract_words")  # [min, max] or None
    kw_style = fmt.get("keywords")  # ccs-concepts | ieee-index-terms | lncs-keywords | none

    def add(sev, check, pos, msg):
        if pos is not None:
            f, ln = doc.loc(pos)
        else:
            f, ln = args.tex, None
        findings.append(Finding(sev, check, f, ln, msg))

    # ---- abstract --------------------------------------------------------
    pos, text = _get_abstract(doc)
    if text is None:
        add("ERROR", "abstract/missing", None,
            "no abstract found (\\begin{abstract} or \\abstract{...})")
    else:
        words = texlib.count_words(text)
        if isinstance(bounds, list) and len(bounds) == 2 and all(
            isinstance(b, int) for b in bounds
        ):
            lo, hi = bounds
            if words < lo:
                add("WARN", "abstract/too-short", pos,
                    f"abstract is {words} words; venue mandates {lo}-{hi}")
            elif words > hi:
                add("WARN", "abstract/too-long", pos,
                    f"abstract is {words} words; venue mandates {lo}-{hi}")
            else:
                add("INFO", "abstract/length-ok", pos,
                    f"abstract is {words} words (venue bound {lo}-{hi})")
        else:
            sev = "WARN" if words > 350 else "INFO"
            add(sev, "abstract/length", pos,
                f"abstract is {words} words; profile mandates no numeric bound "
                "(CS norm is roughly 150-250) — verify the live CFP: "
                f"{profile.get('cfp_url')}")

        if re.search(r"\n\s*\n", text.strip()) and fmt.get("template") == "neurips":
            add("WARN", "abstract/multi-paragraph", pos,
                "abstract has multiple paragraphs; this venue family asks for a "
                "single paragraph")
        n_cites = len(re.findall(r"\\cite[a-zA-Z*]*\s*\{", text))
        if n_cites:
            add("WARN", "abstract/citations", pos,
                f"{n_cites} \\cite command(s) inside the abstract — abstracts are "
                "read standalone (digital libraries, OpenReview); avoid citations")
        if re.search(r"https?://", text):
            add("WARN", "abstract/url", pos,
                "URL inside the abstract — style smell and a possible "
                "anonymization leak")
        if re.search(r"\$\$|\\\[|\\begin\{(?:equation|align)", text):
            add("INFO", "abstract/display-math", pos,
                "display math inside the abstract — most venues advise against it")

    # ---- keywords format ---------------------------------------------------
    kw_cmds = [(p, a) for p, _o, a in doc.find_commands("keywords") if a is not None]
    ieee_kw = doc.env_spans("IEEEkeywords")

    if kw_style in ("ccs-concepts", "lncs-keywords"):
        if not kw_cmds:
            add("ERROR", "keywords/missing", None,
                f"venue keyword style is '{kw_style}' but no \\keywords{{...}} found")
        else:
            kpos, karg = kw_cmds[0]
            terms = _split_keywords(karg)
            if not terms:
                add("ERROR", "keywords/empty", kpos, "\\keywords{} is empty")
            elif kw_style == "lncs-keywords" and not (3 <= len(terms) <= 6):
                add("WARN", "keywords/count", kpos,
                    f"{len(terms)} keyword(s) — LNCS guidelines say 3-6")
            elif len(terms) < 2:
                add("WARN", "keywords/count", kpos,
                    f"only {len(terms)} keyword(s) — most venues expect several")
            else:
                add("INFO", "keywords/ok", kpos,
                    f"{len(terms)} keywords: {', '.join(terms[:6])}")
            if kw_style == "lncs-keywords" and "\\and" not in karg and len(terms) > 1:
                add("INFO", "keywords/lncs-separator", kpos,
                    "LNCS convention separates keywords with \\and")
        if kw_style == "ccs-concepts" and not doc.env_spans("CCSXML"):
            add("INFO", "keywords/ccs-crossref", None,
                "ACM venues also need the CCSXML block + \\ccsdesc — "
                "check_sections.py validates those")
    elif kw_style == "ieee-index-terms":
        if not ieee_kw:
            add("ERROR", "keywords/missing", None,
                "venue keyword style is 'ieee-index-terms' but no "
                "\\begin{IEEEkeywords} environment found")
        else:
            kpos, _e, inner = ieee_kw[0]
            terms = _split_keywords(inner)
            if len(terms) < 2:
                add("WARN", "keywords/count", kpos,
                    f"only {len(terms)} Index Term(s) — IEEE papers normally list several")
            else:
                add("INFO", "keywords/ok", kpos, f"{len(terms)} IEEE Index Terms")
    elif kw_style == "none":
        if kw_cmds or ieee_kw:
            add("INFO", "keywords/not-used", kw_cmds[0][0] if kw_cmds else ieee_kw[0][0],
                "this venue uses no in-paper keywords (topics are selected in the "
                "submission form) — the keywords block is harmless but unused")
    else:
        add("INFO", "keywords/unknown-style", None,
            f"profile keyword style is {kw_style!r} — no automated format check; "
            f"verify against the CFP: {profile.get('cfp_url')}")
    return findings


def main() -> int:
    return texlib.run_checker("check_abstract", __doc__.splitlines()[0], collect)


if __name__ == "__main__":
    sys.exit(main())
