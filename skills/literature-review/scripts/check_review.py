#!/usr/bin/env python3
"""Gate a literature-review document: every claim must cite a verified
reference. Python 3 stdlib only, no network.

Checks review.md against corpus.json:
  FAIL  unknown key        cited key not present in the corpus
  FAIL  unverified key     cited paper whose status.verified is not true
  FAIL  excluded key       cited paper that was screened out
  FAIL  bib drift          (only with --bib) a cited key with no entry in the
                           given references.bib -- corpus/.bib key divergence
                           that silently breaks the verified-citation chain
  FAIL  placeholder        [CITATION NEEDED], [@TODO], [@?], '??'/'???' markers
  FAIL  long quote         verbatim quoted span > --max-quote-words words,
                           including spans that wrap across lines within a
                           paragraph (copyright guard: paraphrase, do not
                           transcribe). Only quotation-marked spans are
                           detectable -- unmarked transcription is on you.
  WARN  uncited paper      included+extracted paper never cited (use --strict
                           to make this a failure)
  WARN  bare paragraph     body paragraph > --para-chars chars with no citation

Recognized citation syntax: pandoc [@key] and [@a; @b], and LaTeX
\\cite{a,b} / \\citep / \\citet.

Examples:
  python3 check_review.py lit-review/x/review.md
  python3 check_review.py review.md --corpus other/corpus.json --strict

Exit codes: 0 pass | 1 failures (or warnings with --strict) | 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BIB_KEY_RE = re.compile(r"@\s*[A-Za-z]+\s*[{(]\s*([^,\s{}()\"]+)")
PANDOC_GROUP_RE = re.compile(r"\[([^\[\]]*@[^\[\]]+)\]")
PANDOC_KEY_RE = re.compile(r"@([A-Za-z0-9][A-Za-z0-9_:.#$%&+?<>~/-]*)")
LATEX_CITE_RE = re.compile(r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{([^}]*)\}")
PLACEHOLDER_RE = re.compile(
    r"\[CITATION NEEDED\]|\[@TODO\]|\[@\?\]|\[@\]|\?\?+",
    re.IGNORECASE,
)
# Quoted spans may wrap across lines inside one paragraph (single newlines
# allowed, blank lines end the span so stray quotes never pair up across
# paragraphs). Both straight and curly double quotes.
QUOTE_RE = re.compile(
    r'"((?:[^"\n]|\n(?!\s*\n)){20,}?)"|“((?:[^”\n]|\n(?!\s*\n)){20,}?)”'
)
HEADING_RE = re.compile(r"^#{1,6}\s")


def fail(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def find_corpus(review_path: Path, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            fail(f"corpus not found: {explicit}")
        return p
    sibling = review_path.parent / "corpus.json"
    if sibling.exists():
        return sibling
    fail(
        f"no corpus.json next to {review_path} -- pass --corpus PATH "
        "(the corpus created by init_review.py)"
    )
    raise AssertionError("unreachable")


def cited_keys(text: str) -> dict[str, list[int]]:
    """Map cite key -> line numbers where it is cited."""
    keys: dict[str, list[int]] = {}
    for i, line in enumerate(text.splitlines(), 1):
        for group in PANDOC_GROUP_RE.findall(line):
            for key in PANDOC_KEY_RE.findall(group):
                keys.setdefault(key, []).append(i)
        for group in LATEX_CITE_RE.findall(line):
            for key in group.split(","):
                key = key.strip()
                if key:
                    keys.setdefault(key, []).append(i)
    return keys


def bib_keys(path: Path) -> set[str]:
    """Cite keys defined in a .bib file (skips @string/@comment/@preamble)."""
    text = path.read_text(encoding="utf-8")
    keys = set()
    for m in BIB_KEY_RE.finditer(text):
        head = text[m.start():m.start() + 40].lower().lstrip("@ ")
        if head.startswith(("string", "comment", "preamble")):
            continue
        keys.add(m.group(1))
    return keys


def paragraphs(text: str):
    """Yield (first_line_number, paragraph_text) for body paragraphs."""
    lines = text.splitlines()
    buf: list[str] = []
    start = 1
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        skip = (
            not stripped
            or HEADING_RE.match(stripped)
            or stripped.startswith(("|", ">", "<!--", "-->", "```"))
        )
        if skip:
            if buf:
                yield start, " ".join(buf)
                buf = []
            continue
        if not buf:
            start = i
        buf.append(stripped)
    if buf:
        yield start, " ".join(buf)


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("review", help="the review markdown file to gate")
    p.add_argument("--corpus", help="corpus.json (default: next to the review)")
    p.add_argument("--strict", action="store_true",
                   help="treat warnings as failures")
    p.add_argument("--max-quote-words", type=int, default=40, metavar="N",
                   help="max words allowed inside one quoted span (default 40)")
    p.add_argument("--para-chars", type=int, default=300, metavar="N",
                   help="paragraphs longer than this with no citation are "
                        "warned about (default 300)")
    p.add_argument("--bib", metavar="PATH",
                   help="also assert every cited key has an entry in this "
                        ".bib (cross-file key-consistency gate)")
    args = p.parse_args()

    review_path = Path(args.review)
    if not review_path.exists():
        fail(f"review file not found: {args.review}")
    text = review_path.read_text(encoding="utf-8")
    corpus_path = find_corpus(review_path, args.corpus)
    try:
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        papers = corpus["papers"]
        assert isinstance(papers, dict)
    except (ValueError, KeyError, AssertionError):
        fail(f"{corpus_path} is not a valid literature-review corpus")

    failures: list[str] = []
    warnings: list[str] = []

    cites = cited_keys(text)
    for key, lines in sorted(cites.items()):
        where = f"line {lines[0]}" + (f" (+{len(lines) - 1} more)" if len(lines) > 1 else "")
        rec = papers.get(key)
        if rec is None:
            failures.append(
                f"unknown key   [@{key}] cited at {where} but not in {corpus_path.name}"
            )
            continue
        status = rec.get("status", {})
        if status.get("screened") == "excluded":
            failures.append(
                f"excluded key  [@{key}] at {where} was screened out"
                + (f" ({rec.get('reason')})" if rec.get("reason") else "")
            )
        if status.get("verified") is not True:
            failures.append(
                f"unverified    [@{key}] at {where} -- run the verify-citations "
                f"skill, then: corpus.py set {key} --verified yes"
            )

    if args.bib:
        bibpath = Path(args.bib)
        if not bibpath.exists():
            fail(f"bib file not found: {args.bib}")
        bkeys = bib_keys(bibpath)
        for key, lines in sorted(cites.items()):
            if key not in bkeys:
                where = f"line {lines[0]}"
                failures.append(
                    f"bib drift     [@{key}] cited at {where} but missing from "
                    f"{bibpath.name} -- regenerate it: corpus.py bibtex > "
                    f"{bibpath.name}"
                )

    for i, line in enumerate(text.splitlines(), 1):
        if PLACEHOLDER_RE.search(line):
            failures.append(f"placeholder   line {i}: unresolved citation marker")

    for m in QUOTE_RE.finditer(text):
        span = m.group(1) or m.group(2)
        words = len(span.split())
        if words > args.max_quote_words:
            lineno = text.count("\n", 0, m.start()) + 1
            failures.append(
                f"long quote    line {lineno}: {words}-word verbatim quote -- "
                f"paraphrase (limit {args.max_quote_words} words)"
            )

    for key, rec in sorted(papers.items()):
        s = rec.get("status", {})
        if (
            s.get("screened") == "included"
            and s.get("extracted")
            and key not in cites
        ):
            warnings.append(
                f"uncited paper [@{key}] is included+extracted but never cited "
                "-- cite it or record why it dropped out"
            )

    for lineno, para in paragraphs(text):
        if len(para) >= args.para_chars and not cited_keys(para):
            warnings.append(
                f"bare paragraph at line {lineno}: "
                f"{len(para)} chars with no citation -- ground it or move it "
                "to scope/method"
            )

    n_cited = len(cites)
    print(f"check_review: {review_path} against {corpus_path}")
    print(f"  {n_cited} distinct keys cited, {len(papers)} papers in corpus")
    for f_msg in failures:
        print(f"  FAIL  {f_msg}")
    for w_msg in warnings:
        print(f"  WARN  {w_msg}")

    if failures or (args.strict and warnings):
        print(
            f"\nRESULT: FAIL ({len(failures)} failures, {len(warnings)} warnings)"
        )
        sys.exit(1)
    print(f"\nRESULT: PASS ({len(warnings)} warnings)")


if __name__ == "__main__":
    main()
