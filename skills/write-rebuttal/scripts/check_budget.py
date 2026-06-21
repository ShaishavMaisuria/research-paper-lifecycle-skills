#!/usr/bin/env python3
"""Budget checker for rebuttal artifacts. Stdlib only, fully offline.

Two modes:

  text  — per-section character/word counts for threaded responses
          (OpenReview-style limits, e.g. NeurIPS 10,000 chars per review).
          Sections are split on level-2 markdown headings ("## ..."); each
          heading is assumed to be one response box. The heading line itself
          is NOT counted (it usually goes in the comment's title field).
          Everything else — markdown syntax, newlines, spaces — IS counted,
          because submission-system text boxes count pasted characters.

  pdf   — page count for one-page PDF rebuttals (CVPR-style). Parses the
          compiled PDF directly; no LaTeX toolchain needed.

The budget is resolved in priority order:
  --limit / --max-pages  >  --venue profile review.rebuttal_limit  >  default
  (10,000 chars for text, 1 page for pdf — defaults are flagged as ASSUMED).

Exit codes: 0 = within budget, 1 = over budget, 2 = bad input / error.

Examples:
    python3 check_budget.py text responses.md --sections --venue venues/conferences/neurips-2026.yml
    python3 check_budget.py text responses.md --limit 5000
    python3 check_budget.py pdf rebuttal.pdf --max-pages 1
"""

import argparse
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import venueyaml
except ImportError:  # pragma: no cover
    venueyaml = None

DEFAULT_CHAR_LIMIT = 10000
DEFAULT_MAX_PAGES = 1

_CHAR_LIMIT_RE = re.compile(r"([\d][\d,]*)\s*(?:characters|chars?)\b", re.I)
_PAGE_LIMIT_RE = re.compile(r"(\d+)\s*page", re.I)


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


# ---------------------------------------------------------------------------
# venue profile helpers
# ---------------------------------------------------------------------------


def load_venue_limits(venue_path):
    """Return (rebuttal_format, char_limit, page_limit, raw_limit_string)."""
    if venueyaml is None:
        raise RuntimeError("venueyaml.py not found next to this script")
    profile = venueyaml.load_with_family(venue_path)
    review = profile.get("review") or {}
    fmt = review.get("rebuttal_format")
    raw = review.get("rebuttal_limit") or ""
    chars = None
    pages = None
    m = _CHAR_LIMIT_RE.search(raw)
    if m:
        chars = int(m.group(1).replace(",", ""))
    m = _PAGE_LIMIT_RE.search(raw)
    if m:
        pages = int(m.group(1))
    return fmt, chars, pages, raw


# ---------------------------------------------------------------------------
# text mode
# ---------------------------------------------------------------------------


def split_sections(text):
    """Split markdown into [(section_title, body)] on '## ' headings."""
    sections = []
    title = "(preamble)"
    buf = []
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("###"):
            sections.append((title, "\n".join(buf)))
            title = line[3:].strip() or "(untitled section)"
            buf = []
        else:
            buf.append(line)
    sections.append((title, "\n".join(buf)))
    out = []
    for name, body in sections:
        body = body.strip("\n")
        if name == "(preamble)" and not body.strip():
            continue
        out.append((name, body))
    return out


def run_text(args):
    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return fail("cannot read %s: %s" % (args.file, exc))
    if not text.strip():
        return fail("%s is empty" % args.file)

    limit = None
    limit_src = None
    fmt = None
    if args.venue:
        try:
            fmt, chars, _pages, raw = load_venue_limits(args.venue)
        except Exception as exc:
            return fail("cannot load venue profile %s: %s" % (args.venue, exc))
        if chars:
            limit, limit_src = chars, "venue profile (%s)" % raw
    if args.limit is not None:
        limit, limit_src = args.limit, "--limit flag"
    if limit is None:
        limit, limit_src = DEFAULT_CHAR_LIMIT, "ASSUMED default — verify on the live CFP"

    if args.sections:
        sections = split_sections(text)
    else:
        sections = [("(whole file)", text.strip("\n"))]
    if not sections:
        return fail("no content found in %s" % args.file)

    print("# Rebuttal text budget — %s" % args.file)
    if fmt:
        print("- venue rebuttal_format: `%s`" % fmt)
    print("- limit: %d chars per section (source: %s)" % (limit, limit_src))
    print("- counting rule: every character incl. markdown and newlines;"
          " '## ' heading lines excluded")
    print()
    print("| Section | Chars | Words | Margin | Status |")
    print("|---|---:|---:|---:|---|")
    over = []
    for name, body in sections:
        chars = len(body)
        words = len(body.split())
        margin = limit - chars
        status = "OK" if margin >= 0 else "OVER by %d" % -margin
        if margin < 0:
            over.append(name)
        elif margin < int(0.05 * limit):
            status = "OK (tight: %d left)" % margin
        print("| %s | %d | %d | %d | %s |" % (name, chars, words, margin, status))
    print()
    if over:
        print("RESULT: OVER BUDGET — trim these sections: %s" % "; ".join(over))
        return 1
    print("RESULT: all sections within budget.")
    return 0


# ---------------------------------------------------------------------------
# pdf mode
# ---------------------------------------------------------------------------


def count_pdf_pages(data):
    """Best-effort page count from raw PDF bytes (stdlib only).

    Strategy: count uncompressed '/Type /Page' objects; if none are visible
    (object streams), inflate FlateDecode streams and retry; finally fall
    back to the largest '/Count N' in a '/Type /Pages' node.
    Returns (count, method) or raises ValueError.
    """
    page_re = re.compile(rb"/Type\s*/Page(?![s/\w])")
    n = len(page_re.findall(data))
    if n:
        return n, "uncompressed /Type /Page objects"

    inflated = []
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        try:
            inflated.append(zlib.decompress(data[start:end]))
        except zlib.error:
            continue
    blob = b"\n".join(inflated)
    n = len(page_re.findall(blob))
    if n:
        return n, "FlateDecode object streams"

    counts = [int(c) for c in re.findall(
        rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", data + b"\n" + blob, re.S)]
    counts += [int(c) for c in re.findall(
        rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages", data + b"\n" + blob, re.S)]
    counts = [c for c in counts if c > 0]
    if counts:
        return max(counts), "/Count in /Type /Pages node"
    raise ValueError("could not determine a positive page count (unsupported "
                     "or empty PDF) — check the page count manually")


def run_pdf(args):
    try:
        with open(args.file, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        return fail("cannot read %s: %s" % (args.file, exc))
    if not data.startswith(b"%PDF"):
        return fail("%s does not look like a PDF (no %%PDF header)" % args.file)

    max_pages = None
    src = None
    if args.venue:
        try:
            _fmt, _chars, pages, raw = load_venue_limits(args.venue)
        except Exception as exc:
            return fail("cannot load venue profile %s: %s" % (args.venue, exc))
        if pages:
            max_pages, src = pages, "venue profile (%s)" % raw
    if args.max_pages is not None:
        max_pages, src = args.max_pages, "--max-pages flag"
    if max_pages is None:
        max_pages, src = DEFAULT_MAX_PAGES, "ASSUMED default — verify on the live CFP"

    try:
        pages, method = count_pdf_pages(data)
    except ValueError as exc:
        return fail(str(exc))

    print("# Rebuttal PDF budget — %s" % args.file)
    print("- pages: %d (counted via %s)" % (pages, method))
    print("- limit: %d page(s) (source: %s)" % (max_pages, src))
    if pages > max_pages:
        print("RESULT: OVER BUDGET — %d page(s) over. Venues with strict "
              "one-page rebuttals will not review this." % (pages - max_pages))
        return 1
    print("RESULT: within the page budget.")
    return 0


# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check rebuttal artifacts against venue budgets "
        "(character limits for threaded responses, page limits for PDF "
        "rebuttals). Offline; stdlib only.")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_text = sub.add_parser(
        "text", help="check character/word budgets of a markdown response file")
    p_text.add_argument("file", help="response file (markdown/plain text)")
    p_text.add_argument("--sections", action="store_true",
                        help="treat each '## ' heading as a separate response box")
    p_text.add_argument("--limit", type=int, default=None,
                        help="character limit per section (overrides venue profile)")
    p_text.add_argument("--venue", default=None,
                        help="venues/conferences/<id>.yml to read rebuttal_limit from")

    p_pdf = sub.add_parser("pdf", help="check the page count of a compiled rebuttal PDF")
    p_pdf.add_argument("file", help="compiled rebuttal PDF")
    p_pdf.add_argument("--max-pages", type=int, default=None,
                       help="maximum allowed pages (overrides venue profile)")
    p_pdf.add_argument("--venue", default=None,
                       help="venues/conferences/<id>.yml to read rebuttal_limit from")

    args = parser.parse_args(argv)
    if args.mode == "text":
        return run_text(args)
    return run_pdf(args)


if __name__ == "__main__":
    sys.exit(main())
