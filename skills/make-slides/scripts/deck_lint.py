#!/usr/bin/env python3
"""Lint a talk deck (Marp markdown or Beamer .tex) for slide-craft problems.

Deterministic checks, per slide:
  RISK  figure-missing   referenced image file does not exist on disk
  RISK  marp-pdf-image   Marp cannot render .pdf images — convert to PNG/SVG
  RISK  overfull         > 100 words on one slide (a document, not a slide)
  RISK  pacing           content slides > 1.5x the speaking minutes (--minutes)
  WARN  wordy            > 60 words on one slide
  WARN  bullet-overload  > 6 bullets on one slide
  WARN  generic-title    title is a section noun ("Results", "Method", ...) —
                         one-claim-per-slide wants a takeaway sentence instead
  WARN  pacing           content slides > 1.1x the speaking minutes
  WARN  tiny-font        Beamer \\tiny or \\scriptsize body text
  WARN  no-marp-header   markdown deck without `marp: true` front matter
  INFO  aspect-ratio     Beamer deck without aspectratio=169 (most rooms are 16:9)

Backup slides are excluded from pacing: everything after \\appendix (Beamer)
or after the first slide whose title starts with "Backup" (Marp).
Speaker notes (\\note{...}, <!-- ... -->) are excluded from word counts.

Stdlib only. No network.

Usage:
    python3 deck_lint.py talk/slides.md --minutes 12
    python3 deck_lint.py talk/slides.tex --minutes 12 --strict
    python3 deck_lint.py talk/slides.md --json

Exit codes: 0 clean (or warnings only); 1 any RISK (with --strict: any
finding); 2 bad arguments or unreadable/unrecognized deck.
"""

import argparse
import json
import os
import re
import sys

GENERIC_TITLES = {
    "introduction", "background", "motivation", "outline", "overview",
    "agenda", "method", "methods", "methodology", "approach", "our approach",
    "system", "architecture", "results", "evaluation", "experiments",
    "experimental results", "discussion", "related work", "conclusion",
    "conclusions", "future work", "summary",
}
WORDS_WARN, WORDS_RISK = 60, 100
BULLETS_WARN = 6
PACE_WARN, PACE_RISK = 1.1, 1.5

MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)")
HTML_IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
TEX_IMG_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
TEX_EXTS = ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps")


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def strip_balanced_command(text, command):
    """Remove every \\command{...} group (balanced braces)."""
    out, i, token = [], 0, "\\" + command
    while True:
        j = text.find(token, i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = text.find("{", j)
        if k < 0:
            i = j + len(token)
            continue
        depth = 0
        end = len(text)
        for p in range(k, len(text)):
            if text[p] == "{":
                depth += 1
            elif text[p] == "}":
                depth -= 1
                if depth == 0:
                    end = p + 1
                    break
        i = end
    return "".join(out)


def count_words(text):
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", text)
    return len(tokens)


# ---------------------------------------------------------------------------
# Marp / markdown parsing
# ---------------------------------------------------------------------------

def parse_marp(raw):
    lines = raw.splitlines()
    front, body_start = "", 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                front = "\n".join(lines[1:i])
                body_start = i + 1
                break
    body = "\n".join(lines[body_start:])
    chunks = re.split(r"^\s*---\s*$", body, flags=re.M)
    slides = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        title_m = re.search(r"^#{1,3}\s+(.+?)\s*$", chunk, re.M)
        notes_removed = re.sub(r"<!--.*?-->", " ", chunk, flags=re.S)
        no_code = re.sub(r"```.*?```", " ", notes_removed, flags=re.S)
        images = MD_IMG_RE.findall(no_code) + HTML_IMG_RE.findall(no_code)
        text_only = MD_IMG_RE.sub(" ", no_code)
        text_only = HTML_IMG_RE.sub(" ", text_only)
        bullets = len(re.findall(r"^\s*(?:[-*+]|\d+\.)\s+\S", no_code, re.M))
        slides.append({
            "title": title_m.group(1).strip() if title_m else "",
            "words": count_words(text_only),
            "bullets": bullets,
            "images": images,
        })
    return {"kind": "marp", "frontmatter": front, "slides": slides}


# ---------------------------------------------------------------------------
# Beamer parsing
# ---------------------------------------------------------------------------

def tex_strip_comments(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def beamer_frame_title(body):
    m = re.match(r"\s*(?:\[[^\]]*\]\s*|<[^>]*>\s*)*\{", body)
    if m:
        depth, start = 0, m.end() - 1
        for p in range(start, len(body)):
            if body[p] == "{":
                depth += 1
            elif body[p] == "}":
                depth -= 1
                if depth == 0:
                    return body[start + 1:p].strip()
    m = re.search(r"\\frametitle\s*\{([^}]*)\}", body)
    return m.group(1).strip() if m else ""


def parse_beamer(raw):
    text = tex_strip_comments(raw)
    appendix_pos = text.find("\\appendix")
    slides = []
    for m in re.finditer(r"\\begin\{frame\}(.*?)\\end\{frame\}", text, re.S):
        body = m.group(1)
        title = beamer_frame_title(body)
        clean = strip_balanced_command(body, "note")
        images = TEX_IMG_RE.findall(clean)
        tiny = bool(re.search(r"\\(tiny|scriptsize)\b", clean))
        no_img = TEX_IMG_RE.sub(" ", clean)
        bullets = len(re.findall(r"\\item\b", no_img))
        prose = re.sub(r"\\[a-zA-Z]+\*?", " ", no_img)
        prose = re.sub(r"[{}\[\]&$_^~]", " ", prose)
        slides.append({
            "title": title,
            "words": count_words(prose),
            "bullets": bullets,
            "images": [i.strip() for i in images],
            "tiny_font": tiny,
            "backup": appendix_pos >= 0 and m.start() > appendix_pos,
        })
    aspect_169 = bool(re.search(r"aspectratio\s*=\s*169", text))
    return {"kind": "beamer", "slides": slides, "aspect_169": aspect_169}


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def resolve_image(path, deck_dir, kind):
    if re.match(r"https?://", path):
        return True  # remote: existence not checkable offline
    candidate = os.path.join(deck_dir, path)
    if kind == "beamer":
        return any(os.path.isfile(candidate + ext) for ext in TEX_EXTS)
    return os.path.isfile(candidate)


def run_checks(deck, deck_dir, minutes):
    findings = []

    def add(level, code, slide_no, msg):
        findings.append({"level": level, "code": code,
                         "slide": slide_no, "message": msg})

    if deck["kind"] == "marp" and not re.search(
            r"^\s*marp\s*:\s*true\s*$", deck.get("frontmatter", ""), re.M):
        add("WARN", "no-marp-header", 0,
            "no `marp: true` front matter — Marp tooling will treat this as plain markdown")
    if deck["kind"] == "beamer" and not deck.get("aspect_169"):
        add("INFO", "aspect-ratio", 0,
            "no aspectratio=169 in \\documentclass — most conference rooms are 16:9")

    in_backup = False
    content_slides = 0
    for idx, slide in enumerate(deck["slides"], 1):
        title = slide["title"]
        if deck["kind"] == "marp" and title.lower().startswith("backup"):
            in_backup = True
        backup = in_backup or slide.get("backup", False)
        if not backup:
            content_slides += 1

        if slide["words"] > WORDS_RISK:
            add("RISK", "overfull", idx,
                "%d words — that's a document, not a slide (limit %d)"
                % (slide["words"], WORDS_RISK))
        elif slide["words"] > WORDS_WARN:
            add("WARN", "wordy", idx,
                "%d words (aim under %d)" % (slide["words"], WORDS_WARN))
        if slide["bullets"] > BULLETS_WARN:
            add("WARN", "bullet-overload", idx,
                "%d bullets (aim <= %d, or split the slide)"
                % (slide["bullets"], BULLETS_WARN))
        if title and title.lower().strip(" .:!?") in GENERIC_TITLES and not backup:
            add("WARN", "generic-title", idx,
                "title %r is a section noun — make it the slide's claim "
                "(e.g. 'Eviction by access recency halves tail latency')" % title)
        if slide.get("tiny_font"):
            add("WARN", "tiny-font", idx,
                "\\tiny/\\scriptsize body text — unreadable past row 3")
        for img in slide["images"]:
            if deck["kind"] == "marp" and img.lower().endswith(".pdf"):
                add("RISK", "marp-pdf-image", idx,
                    "%s — Marp cannot render PDF images; convert to PNG/SVG "
                    "(pdftocairo -png -r 200, or `sips -s format png` on macOS)" % img)
            if not resolve_image(img, deck_dir, deck["kind"]):
                add("RISK", "figure-missing", idx,
                    "image %s not found relative to the deck" % img)

    if minutes is not None and content_slides:
        ratio = content_slides / minutes
        if ratio > PACE_RISK:
            add("RISK", "pacing", 0,
                "%d content slides for %g speaking minutes (%.2f/min; >%.1f/min "
                "is a sprint) — cut slides, don't talk faster"
                % (content_slides, minutes, ratio, PACE_RISK))
        elif ratio > PACE_WARN:
            add("WARN", "pacing", 0,
                "%d content slides for %g speaking minutes (%.2f/min; ~1/min "
                "is sustainable)" % (content_slides, minutes, ratio))
    return findings, content_slides


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint a Marp markdown or Beamer .tex talk deck: pacing vs "
        "the slot, overfull slides, bullet overload, generic (non-claim) "
        "titles, missing/unrenderable figures.")
    parser.add_argument("deck", help="path to slides.md (Marp) or slides.tex (Beamer)")
    parser.add_argument("--minutes", type=float, default=None,
                        help="SPEAKING minutes (slot minus Q&A) for the pacing check")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on WARN/INFO findings too, not just RISK")
    parser.add_argument("--json", action="store_true",
                        help="emit findings as JSON instead of a report")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.deck):
        return fail("cannot read %s" % args.deck)
    if args.minutes is not None and args.minutes <= 0:
        return fail("--minutes must be positive")
    try:
        with open(args.deck, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        return fail("cannot read %s: %s" % (args.deck, exc))

    if args.deck.endswith(".tex") or "\\begin{frame}" in raw:
        deck = parse_beamer(raw)
    elif args.deck.endswith((".md", ".markdown")):
        deck = parse_marp(raw)
    else:
        return fail("unrecognized deck format — expected Marp .md or Beamer .tex")
    if not deck["slides"]:
        return fail("no slides found in %s — is this really a deck?" % args.deck)

    findings, content_slides = run_checks(
        deck, os.path.dirname(os.path.abspath(args.deck)), args.minutes)

    risks = [f for f in findings if f["level"] == "RISK"]
    if args.json:
        json.dump({"deck": args.deck, "kind": deck["kind"],
                   "content_slides": content_slides,
                   "total_slides": len(deck["slides"]),
                   "findings": findings}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print("# Deck lint — %s (%s, %d slides, %d content)"
              % (args.deck, deck["kind"], len(deck["slides"]), content_slides))
        print()
        if not findings:
            print("No findings. Now rehearse it out loud with a timer.")
        for f in sorted(findings, key=lambda f: (f["slide"],
                        {"RISK": 0, "WARN": 1, "INFO": 2}[f["level"]])):
            where = "slide %d" % f["slide"] if f["slide"] else "deck"
            print("%-4s [%s] %s: %s" % (f["level"], f["code"], where, f["message"]))
        print()
        print("Summary: %d RISK, %d WARN, %d INFO"
              % (len(risks),
                 sum(1 for f in findings if f["level"] == "WARN"),
                 sum(1 for f in findings if f["level"] == "INFO")))

    if risks or (args.strict and findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
