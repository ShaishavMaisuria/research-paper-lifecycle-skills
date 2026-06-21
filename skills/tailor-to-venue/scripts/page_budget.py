#!/usr/bin/env python3
"""Section-by-section page-budget analysis for a LaTeX draft (stdlib only).

Estimates how much page space each \\section consumes (words + floats) for a
given venue format, compares the total to the track's page limit, and ranks
cut candidates against typical section-share norms. Output is Markdown; the
tailor-to-venue skill turns it into a prose cutting plan.

ESTIMATES, NOT TRUTH: word-density and float-size constants are rough
medians for each template family (documented below, accuracy roughly
+/-20%). The compiled PDF is always ground truth — recompile after every
cutting pass.

Usage:
    python3 page_budget.py <main.tex> --venue <profile.yml> --track Research
    python3 page_budget.py <main.tex> --limit 10 --format acmart-sigconf

Exit codes: 0 ok, 2 bad input.
"""

import argparse
import re
import sys

import texscan
import venueyaml

# Words of body text per page, by format. Rough medians for full text pages:
# two-column 9-10pt ACM/IEEE pages hold ~950-1000 words; NeurIPS-style
# single-column 10pt ~620; one-column acmart manuscript (CHI review) ~520;
# LNCS ~460 (small trim size). Floats are budgeted separately.
DENSITY = {
    "acmart-sigconf": 980,
    "acmart-manuscript": 520,
    "acmsmall": 560,
    "ieeetran": 1000,
    "neurips": 620,
    "llncs": 460,
    "generic-2col": 950,
    "generic-1col": 550,
}

# Page fraction per float, by kind (column floats in 2-col formats are
# half-width, hence smaller). Medians across typical papers; +/-50% per item.
FLOAT_COST = {
    "figure": 0.30, "figure*": 0.50,
    "table": 0.25, "table*": 0.45,
    "algorithm": 0.30, "algorithm*": 0.40,
    "lstlisting": 0.25,
}

# References per page by format (used only when the track COUNTS references).
REFS_PER_PAGE = {
    "acmart-sigconf": 34, "ieeetran": 36, "acmart-manuscript": 22,
    "acmsmall": 24, "neurips": 26, "llncs": 30,
    "generic-2col": 34, "generic-1col": 24,
}

# Typical share of the BODY budget per canonical section type. Sections far
# above their norm are the first cut candidates.
NORMS = [
    (re.compile(r"(?i)introduction"), "introduction", 0.12),
    (re.compile(r"(?i)related|prior work|background|preliminar"), "related/background", 0.10),
    (re.compile(r"(?i)method|approach|model|system|design|architecture|framework|solution"), "method/system", 0.32),
    (re.compile(r"(?i)experiment|evaluat|result|study|analysis|benchmark"), "evaluation", 0.30),
    (re.compile(r"(?i)discussion|limitation"), "discussion", 0.08),
    (re.compile(r"(?i)conclusion|future"), "conclusion", 0.04),
]

PROFILE_TEMPLATE_TO_FORMAT = {
    ("acmart", 2): "acmart-sigconf",
    ("acmart", 1): "acmart-manuscript",       # refined to acmsmall via documentclass
    ("chi-manuscript", 1): "acmart-manuscript",
    ("IEEEtran", 2): "ieeetran",
    ("IEEEtran", 1): "generic-1col",
    ("neurips", 1): "neurips",
    ("llncs", 1): "llncs",
}


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    sys.exit(2)


def classify(title):
    for pat, label, share in NORMS:
        if pat.search(title):
            return label, share
    return None, None


def split_sections(text):
    """Return list of (title, body) using \\section boundaries."""
    parts = re.split(r"\\section\*?\s*(?:\[[^\]]*\])?\s*\{((?:[^{}]|\{[^{}]*\})*)\}", text)
    sections = []
    if parts[0].strip():
        sections.append(("(front matter / abstract)", parts[0]))
    for i in range(1, len(parts) - 1, 2):
        sections.append((re.sub(r"\\[A-Za-z]+", "", parts[i]).strip() or "(untitled)",
                         parts[i + 1]))
    return sections


def count_floats(body):
    counts = {}
    for kind in FLOAT_COST:
        env = re.escape(kind)
        n = len(re.findall(r"\\begin\{%s\}" % env, body))
        if n:
            counts[kind] = n
    return counts


def count_display_math(body):
    n = len(re.findall(r"\\begin\{(?:equation|align|gather|eqnarray)\*?\}", body))
    n += len(re.findall(r"\\\[", body))
    return n


def unique_cite_keys(text):
    keys = set()
    for m in re.finditer(r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{([^}]*)\}", text):
        for k in m.group(1).split(","):
            if k.strip():
                keys.add(k.strip())
    return keys


def appendix_split(text):
    m = re.search(r"\\appendix\b|\\begin\{appendices\}", text)
    if m:
        return text[: m.start()], text[m.start():]
    return text, ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Estimate per-section page usage of a LaTeX draft and "
        "produce a cut-candidate table against a page limit.")
    parser.add_argument("main_tex", help="main .tex file")
    parser.add_argument("--venue", help="venues/conferences/<id>.yml (gives limit + format)")
    parser.add_argument("--track", help="track name in the profile")
    parser.add_argument("--limit", type=float, help="page limit override")
    parser.add_argument("--format", dest="fmt", choices=sorted(DENSITY),
                        help="format override (default: derived from profile, "
                        "else generic-2col)")
    args = parser.parse_args(argv)

    profile, track = None, None
    if args.venue:
        try:
            profile = venueyaml.load_with_family(args.venue)
        except venueyaml.VenueYamlError as exc:
            fail(str(exc))
        tracks = profile.get("tracks") or []
        if args.track:
            track = next((t for t in tracks
                          if t.get("name", "").lower() == args.track.lower()), None)
            if track is None:
                fail("track %r not in profile. Available: %s"
                     % (args.track, ", ".join(t.get("name", "?") for t in tracks)))
        elif tracks:
            track = tracks[0]

    limit = args.limit
    excludes = []
    if limit is None and track:
        limit = track.get("page_limit")
        excludes = track.get("page_limit_excludes") or []
    if limit is None and not args.limit:
        fail("no page limit: pass --limit N or --venue/--track with a page_limit")

    fmt = args.fmt
    if fmt is None and profile:
        fmt_block = profile.get("format") or {}
        template = fmt_block.get("template")
        columns = fmt_block.get("columns") or 2
        fmt = PROFILE_TEMPLATE_TO_FORMAT.get((template, columns))
        if fmt == "acmart-manuscript" and "acmsmall" in (fmt_block.get("documentclass") or ""):
            fmt = "acmsmall"  # ACM journal single-column, not the CHI review manuscript
        if fmt is None and template:
            fmt = "generic-%dcol" % (2 if columns == 2 else 1)
    fmt = fmt or "generic-2col"
    density = DENSITY[fmt]

    try:
        text, files, warnings = texscan.read_tex(args.main_tex)
    except texscan.TexScanError as exc:
        fail(str(exc))

    body_text, appendix_text = appendix_split(text)
    sections = split_sections(body_text)
    refs_excluded = "references" in excludes
    appendix_excluded = "appendix" in excludes

    rows, total_pages = [], 0.0
    for title, body in sections:
        words = len(texscan.plain_words(body))
        floats = count_floats(body)
        eqs = count_display_math(body)
        float_pages = sum(FLOAT_COST[k] * n for k, n in floats.items())
        eq_pages = eqs * 0.04  # ~4% of a page per display equation
        pages = words / density + float_pages + eq_pages
        total_pages += pages
        rows.append((title, words, floats, eqs, pages))

    n_refs = len(unique_cite_keys(text))
    ref_pages = n_refs / REFS_PER_PAGE[fmt] if n_refs else 0.0
    appendix_words = len(texscan.plain_words(appendix_text)) if appendix_text else 0
    appendix_pages = appendix_words / density if appendix_words else 0.0

    counted = total_pages
    if not refs_excluded:
        counted += ref_pages
    if appendix_text and not appendix_excluded:
        counted += appendix_pages

    out = []
    add = out.append
    add("# Page budget: %s" % args.main_tex)
    add("")
    if profile:
        add("> Venue: %s%s — limit **%s pages** (excl: %s). VERIFY against the live CFP: %s"
            % (profile.get("id", "?"),
               " [%s]" % track.get("name") if track else "",
               limit, ", ".join(excludes) or "nothing",
               profile.get("cfp_url", "?")))
    else:
        add("> Target limit: **%s pages** (manual override)." % limit)
    add("> Format model: `%s` (~%d words/page). Estimates are +/-20%%; the "
        "compiled PDF is ground truth." % (fmt, density))
    add("")
    for w in warnings:
        add("_warning: %s_" % w)
    if warnings:
        add("")

    add("## Section inventory")
    add("")
    add("| section | words | floats | display eqs | est. pages | share |")
    add("|---|---:|---|---:|---:|---:|")
    for title, words, floats, eqs, pages in rows:
        fl = ", ".join("%dx%s" % (n, k) for k, n in sorted(floats.items())) or "-"
        share = (pages / total_pages * 100) if total_pages else 0
        add("| %s | %d | %s | %d | %.2f | %.0f%% |" % (title, words, fl, eqs, pages, share))
    add("| **body total** | | | | **%.2f** | |" % total_pages)
    add("")
    add("- references: %d unique cite keys ≈ %.2f pages — %s" %
        (n_refs, ref_pages,
         "EXCLUDED from the limit" if refs_excluded else "COUNTED toward the limit"))
    if appendix_text:
        add("- appendix: %d words ≈ %.2f pages — %s" %
            (appendix_words, appendix_pages,
             "EXCLUDED from the limit" if appendix_excluded else "COUNTED toward the limit"))
    add("")

    add("## Verdict")
    add("")
    delta = counted - float(limit)
    add("- estimated counted pages: **%.2f** vs limit **%s** -> %s"
        % (counted, limit,
           ("**over by ~%.1f pages — cutting plan required**" % delta) if delta > 0
           else "fits (margin ~%.1f pages) — still confirm with the compiled PDF" % -delta))
    add("")

    add("## Cut candidates (vs typical section shares)")
    add("")
    candidates = []
    for title, words, floats, eqs, pages in rows:
        label, norm_share = classify(title)
        if norm_share is None:
            continue
        norm_pages = norm_share * float(limit)
        if pages > norm_pages + 0.2:
            candidates.append((pages - norm_pages, title, label, pages, norm_pages))
    if not candidates:
        add("- no section is far above its typical share; if over budget, cut "
            "evenly via the compression ladder in references/page-budget-cutting.md.")
    else:
        candidates.sort(reverse=True)
        for over, title, label, pages, norm_pages in candidates:
            add("- **%s** (~%.1f pp; typical %s share ~%.1f pp): over by ~%.1f pp."
                % (title, pages, label, norm_pages, over))
    if appendix_excluded and delta > 0:
        add("- this track EXCLUDES appendix pages — moving proofs/extra tables "
            "to the appendix is the cheapest cut (check the venue's appendix page cap).")
    if refs_excluded:
        add("- references do not count here — do NOT trim the bibliography to save space.")
    add("")
    add("_NEVER recover space via \\vspace hacks, margin/font changes, or "
        "\\baselineskip tweaks: template tampering is an explicit desk-reject "
        "trigger at ACM/Springer venues._")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
