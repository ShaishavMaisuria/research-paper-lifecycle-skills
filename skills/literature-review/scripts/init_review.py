#!/usr/bin/env python3
"""Scaffold a literature-review workspace. Python 3 stdlib only, no network.

Creates <dir>/ (default: lit-review/<topic-slug>/) containing:
  corpus.json   the screening/tracking corpus (metadata only -- never paper text)
  themes.yml    theme list, filled in during synthesis
  notes/        one grounded-notes file per included paper (paraphrase only)
  review.md     the review document skeleton with [@citekey] citation syntax

corpus.json is the single source of truth for pipeline state. Update it with
scripts/corpus.py; gate the final review.md with scripts/check_review.py.

Exit codes: 0 created | 1 target exists (use --force) or write failure
            | 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

CORPUS_SCHEMA = 1

REVIEW_SKELETON = """\
# Literature review: {topic}

<!--
Citation syntax: every factual claim about prior work cites a corpus key,
pandoc-style [@key] or [@key1; @key2] (LaTeX \\cite{{key}} also recognized).
Keys must exist in corpus.json and be verified=yes before this document is
final. Gate with: python3 scripts/check_review.py review.md
-->

## 1. Scope and method

State the research question, inclusion/exclusion criteria, sources searched
(queries + dates), and counts: found / screened / included.

## 2. Themes

<!-- One subsection per theme from themes.yml. Every claim cites [@key]. -->

### 2.1 THEME-NAME

## 3. Synthesis matrix

| Paper | Theme | Approach | Evaluation | Key result |
|---|---|---|---|---|

## 4. Gaps and open problems

## 5. References

<!-- Generated from the corpus: python3 scripts/corpus.py bibtex > references.bib
     then verified with the verify-citations skill. -->
"""

THEMES_SKELETON = """\
# Themes for: {topic}
# Filled in during synthesis (see references/claim-extraction.md).
# Each theme: a short slug, one-line definition, and the corpus keys assigned.
themes: []
# - slug: example-theme
#   definition: one line on what unites these papers
#   papers: [key1, key2]
"""


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "review"


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("topic", help="research question / topic of the review")
    p.add_argument(
        "--dir",
        metavar="DIR",
        help="workspace directory (default: lit-review/<topic-slug>)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="scaffold even if the directory already exists (never overwrites "
        "an existing corpus.json)",
    )
    args = p.parse_args()

    topic = args.topic.strip()
    if not topic:
        fail("topic must be a non-empty string", 2)

    root = Path(args.dir) if args.dir else Path("lit-review") / slugify(topic)
    if root.exists() and not args.force:
        fail(
            f"{root} already exists. Re-run with --force to scaffold missing "
            "files in place (existing files are kept)."
        )

    try:
        (root / "notes").mkdir(parents=True, exist_ok=True)
        corpus_path = root / "corpus.json"
        if not corpus_path.exists():
            corpus = {
                "schema": CORPUS_SCHEMA,
                "topic": topic,
                "created": date.today().isoformat(),
                "criteria": {"include": [], "exclude": []},
                "search_log": [],
                "papers": {},
            }
            corpus_path.write_text(
                json.dumps(corpus, indent=2) + "\n", encoding="utf-8"
            )
        for name, content in (
            ("review.md", REVIEW_SKELETON.format(topic=topic)),
            ("themes.yml", THEMES_SKELETON.format(topic=topic)),
        ):
            path = root / name
            if not path.exists():
                path.write_text(content, encoding="utf-8")
    except OSError as e:
        fail(f"could not write workspace under {root}: {e}")

    print(f"Workspace ready: {root}/")
    print("  corpus.json  themes.yml  review.md  notes/")
    print("Next: record inclusion/exclusion criteria in corpus.json, then add")
    print("search hits with: python3 scripts/corpus.py add --corpus "
          f"{root}/corpus.json ...")


if __name__ == "__main__":
    main()
