#!/usr/bin/env python3
"""Lint a LaTeX poster (beamerposter or tikzposter) for print-day problems.

Deterministic checks:
  RISK  size-mismatch        declared paper size differs from --expect-size
  RISK  orientation-mismatch declared orientation differs from --expect-orientation
  RISK  wall-of-text         > 800 words of body text (a poster, not a paper)
  RISK  figure-missing       referenced image file does not exist on disk
  WARN  wordy                > 450 words of body text (aim lower)
  WARN  tiny-font            \\footnotesize/\\scriptsize/\\tiny in the body —
                             unreadable at poster viewing distance
  WARN  generic-title        block header is a section noun ("Results", ...) —
                             headers should carry the claim
  WARN  long-title           poster title > 15 words — unreadable from 3 m
  WARN  reference-overload   > 5 \\bibitem entries (posters cite 3-5 key works)
  WARN  no-figures           no \\includegraphics and no tikzpicture — a poster
                             is a visual medium
  WARN  no-takeaway          no QR code, URL, or contact email — visitors have
                             no way to take the work home

If --expect-size / --expect-orientation are omitted, the geometry checks
are skipped (the declared geometry is still reported). Expected values
come from the venue's presenter instructions — never from memory.

Stdlib only. No network.

Usage:
    python3 poster_lint.py poster/poster.tex --expect-size a0 --expect-orientation portrait
    python3 poster_lint.py poster/poster.tex --expect-size 36x48in --strict
    python3 poster_lint.py poster/poster.tex --json

Exit codes: 0 clean (or warnings only); 1 any RISK (with --strict: any
finding); 2 bad arguments or unreadable/unrecognized poster.
"""

import argparse
import json
import os
import re
import sys

CM_PER_IN = 2.54
ISO_SIZES_CM = {"a0": (84.1, 118.9), "a1": (59.4, 84.1), "a2": (42.0, 59.4)}
CUSTOM_RE = re.compile(r"^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)(in|cm)$")
WORDS_WARN, WORDS_RISK = 450, 800
TITLE_WORDS_WARN = 15
BIBITEMS_WARN = 5
SIZE_TOL_CM = 1.0

GENERIC_TITLES = {
    "introduction", "background", "motivation", "overview", "method",
    "methods", "methodology", "approach", "our approach", "system",
    "architecture", "results", "evaluation", "experiments",
    "experimental results", "discussion", "related work", "conclusion",
    "conclusions", "future work", "summary", "abstract",
}

BEAMERPOSTER_RE = re.compile(r"\\usepackage\s*\[([^\]]*)\]\s*\{beamerposter\}")
TIKZPOSTER_RE = re.compile(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{tikzposter\}")
TEX_IMG_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\{((?:\s*\{[^}]*\}\s*)+)\}")
TIKZPIC_RE = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.S)
BLOCK_TITLE_RES = [
    re.compile(r"\\block\s*\{([^}]*)\}"),               # tikzposter
    re.compile(r"\\begin\{block\}\s*\{([^}]*)\}"),      # beamer
]
TINY_RE = re.compile(r"\\(tiny|scriptsize|footnotesize)\b")
TAKEAWAY_RE = re.compile(r"\\qrcode\b|\{qrcode\}|\\url\b|\\href\b|@[A-Za-z]")
EXTS = ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps")


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def parse_size_token(token):
    token = token.strip().lower()
    if token in ISO_SIZES_CM:
        return ISO_SIZES_CM[token] + (token,)
    m = CUSTOM_RE.match(token)
    if not m:
        raise ValueError(
            "unrecognized size %r — use a0/a1/a2 or <W>x<H>in / <W>x<H>cm" % token)
    w, h, unit = float(m.group(1)), float(m.group(2)), m.group(3)
    if unit == "in":
        w, h = w * CM_PER_IN, h * CM_PER_IN
    return w, h, None


def strip_comments(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def declared_geometry(text):
    """Return (template, size_name, w_cm, h_cm, orientation) or None."""
    m = BEAMERPOSTER_RE.search(text)
    if m:
        opts = {}
        for part in m.group(1).split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                opts[k.strip()] = v.strip()
        orientation = opts.get("orientation", "portrait")
        size = opts.get("size", "a0").lower()
        if size == "custom":
            try:
                w = float(opts.get("width", "0"))
                h = float(opts.get("height", "0"))
            except ValueError:
                w = h = 0.0
            return ("beamerposter", "custom", w, h, orientation)
        w, h = ISO_SIZES_CM.get(size, (0.0, 0.0))
        if orientation == "landscape":
            w, h = h, w
        return ("beamerposter", size, w, h, orientation)
    m = TIKZPOSTER_RE.search(text)
    if m:
        opts = [o.strip().lower() for o in (m.group(1) or "").split(",")]
        size = next((o[:-5] for o in opts
                     if o.endswith("paper") and o[:-5] in ISO_SIZES_CM), "a0")
        orientation = "landscape" if "landscape" in opts else "portrait"
        w, h = ISO_SIZES_CM[size]
        if orientation == "landscape":
            w, h = h, w
        return ("tikzposter", size, w, h, orientation)
    return None


def body_text(text):
    """Visible prose after \\begin{document}, commands and graphics stripped."""
    i = text.find("\\begin{document}")
    body = text[i + len("\\begin{document}"):] if i >= 0 else text
    body = TIKZPIC_RE.sub(" ", body)
    body = TEX_IMG_RE.sub(" ", body)
    body = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
                  " ", body, flags=re.S)
    prose = re.sub(r"\\[a-zA-Z]+\*?", " ", body)
    prose = re.sub(r"[{}\[\]&$_^~]", " ", prose)
    return body, prose


def count_words(text):
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", text))


def balanced_arg(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i]
    return text[open_idx + 1:]


def poster_title(text):
    m = re.search(r"\\title\s*(?:\[[^\]]*\])?\s*\{", text)
    if not m:
        return ""
    raw = balanced_arg(text, m.end() - 1)
    raw = re.sub(r"\\[a-zA-Z]+\*?", " ", raw)
    return re.sub(r"[{}~\\]", " ", raw).strip()


def graphics_dirs(text, texdir):
    dirs = [texdir]
    for grp in GRAPHICSPATH_RE.findall(text):
        for d in re.findall(r"\{([^}]*)\}", grp):
            dirs.append(os.path.join(texdir, d))
    return dirs


def resolve_image(name, dirs):
    name = name.strip()
    if re.match(r"https?://", name):
        return True
    for d in dirs:
        for ext in EXTS:
            if os.path.isfile(os.path.join(d, name + ext)):
                return True
    return False


def run_checks(text, poster_dir, expect_size, expect_orientation):
    findings = []

    def add(level, code, msg):
        findings.append({"level": level, "code": code, "message": msg})

    geom = declared_geometry(text)
    if geom is None:
        return None, findings
    template, size_name, w_cm, h_cm, orientation = geom

    if expect_orientation and orientation != expect_orientation:
        add("RISK", "orientation-mismatch",
            "poster declares %s but the venue expects %s — a rotated poster "
            "does not fit the board" % (orientation, expect_orientation))
    if expect_size:
        ew, eh, eiso = parse_size_token(expect_size)
        if expect_orientation == "landscape" or (
                expect_orientation is None and orientation == "landscape" and eiso):
            ew, eh = eh, ew
        if eiso and size_name not in ("custom",):
            if size_name != eiso:
                add("RISK", "size-mismatch",
                    "poster declares %s but the venue expects %s"
                    % (size_name, eiso))
        elif w_cm and h_cm and (abs(w_cm - ew) > SIZE_TOL_CM
                                or abs(h_cm - eh) > SIZE_TOL_CM):
            add("RISK", "size-mismatch",
                "poster declares %.1fx%.1f cm but the venue expects %.1fx%.1f cm"
                % (w_cm, h_cm, ew, eh))

    body, prose = body_text(text)
    words = count_words(prose)
    if words > WORDS_RISK:
        add("RISK", "wall-of-text",
            "%d words of body text — that's a paper pinned to a board "
            "(hard max %d; aim <= %d)" % (words, WORDS_RISK, WORDS_WARN))
    elif words > WORDS_WARN:
        add("WARN", "wordy",
            "%d words of body text (aim <= %d)" % (words, WORDS_WARN))

    if TINY_RE.search(body):
        add("WARN", "tiny-font",
            "\\footnotesize/\\scriptsize/\\tiny in the body — text below "
            "~24pt print size is unreadable from 1.5 m")

    title = poster_title(text)
    title_words = count_words(title)
    if title_words > TITLE_WORDS_WARN:
        add("WARN", "long-title",
            "title is %d words (aim <= %d) — shorten to a claim readable "
            "from 3 m" % (title_words, TITLE_WORDS_WARN))

    for rx in BLOCK_TITLE_RES:
        for t in rx.findall(body):
            clean = re.sub(r"\\[a-zA-Z]+\*?|[{}~]", " ", t).strip()
            if clean.lower().strip(" .:!?") in GENERIC_TITLES:
                add("WARN", "generic-title",
                    "block header %r is a section noun — make it the claim "
                    "(e.g. 'Recency-weighted eviction halves p99')" % clean)

    n_bibitems = len(re.findall(r"\\bibitem\b", body))
    if n_bibitems > BIBITEMS_WARN:
        add("WARN", "reference-overload",
            "%d \\bibitem entries — posters cite the 3-5 works the "
            "conversation needs, not the paper's bibliography" % n_bibitems)

    dirs = graphics_dirs(text, poster_dir)
    images = TEX_IMG_RE.findall(text[text.find("\\begin{document}"):]
                                if "\\begin{document}" in text else text)
    for img in images:
        if not resolve_image(img, dirs):
            add("RISK", "figure-missing",
                "image %s not found relative to the poster" % img.strip())
    n_tikz = len(TIKZPIC_RE.findall(text))
    if not images and not n_tikz:
        add("WARN", "no-figures",
            "no \\includegraphics or tikzpicture found — a poster is a "
            "visual medium; lead with the hero figure")

    if not TAKEAWAY_RE.search(body):
        add("WARN", "no-takeaway",
            "no QR code, URL, or contact email found — give visitors a way "
            "to take the work home (paper QR + email at minimum)")

    geometry = {"template": template, "size": size_name,
                "w_cm": round(w_cm, 2), "h_cm": round(h_cm, 2),
                "orientation": orientation, "body_words": words,
                "bibitems": n_bibitems, "images": len(images),
                "tikzpictures": n_tikz}
    return geometry, findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint a beamerposter/tikzposter .tex file: declared size "
        "and orientation vs the venue's, word count, tiny fonts, generic "
        "block titles, missing images, reference overload, missing "
        "QR/contact takeaway.")
    parser.add_argument("poster", help="path to the poster .tex file")
    parser.add_argument("--expect-size", default=None,
                        help="size the venue published (a0|a1|a2 or "
                        "<W>x<H>in|cm) — from presenter instructions")
    parser.add_argument("--expect-orientation",
                        choices=["portrait", "landscape"], default=None,
                        help="orientation the venue published")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on WARN findings too, not just RISK")
    parser.add_argument("--json", action="store_true",
                        help="emit findings as JSON instead of a report")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.poster):
        return fail("cannot read %s" % args.poster)
    try:
        with open(args.poster, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        return fail("cannot read %s: %s" % (args.poster, exc))
    if args.expect_size:
        try:
            parse_size_token(args.expect_size)
        except ValueError as exc:
            return fail(str(exc))

    text = strip_comments(raw)
    geometry, findings = run_checks(
        text, os.path.dirname(os.path.abspath(args.poster)),
        args.expect_size, args.expect_orientation)
    if geometry is None:
        return fail("%s is neither a beamerposter nor a tikzposter file "
                    "(no \\usepackage[...]{beamerposter} or "
                    "\\documentclass[...]{tikzposter})" % args.poster)

    risks = [f for f in findings if f["level"] == "RISK"]
    if args.json:
        json.dump({"poster": args.poster, "geometry": geometry,
                   "findings": findings}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print("# Poster lint — %s (%s, %s %s, %.1fx%.1f cm, %d body words)"
              % (args.poster, geometry["template"], geometry["size"],
                 geometry["orientation"], geometry["w_cm"], geometry["h_cm"],
                 geometry["body_words"]))
        print()
        if not findings:
            print("No findings. Test-print at 25% scale before sending to the printer.")
        for f in sorted(findings,
                        key=lambda f: {"RISK": 0, "WARN": 1, "INFO": 2}[f["level"]]):
            print("%-4s [%s] %s" % (f["level"], f["code"], f["message"]))
        print()
        print("Summary: %d RISK, %d WARN"
              % (len(risks), sum(1 for f in findings if f["level"] == "WARN")))
        if not args.expect_size and not args.expect_orientation:
            print("(geometry checks skipped — pass --expect-size/--expect-orientation")
            print(" with the values from the venue's presenter instructions)")

    if risks or (args.strict and findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
