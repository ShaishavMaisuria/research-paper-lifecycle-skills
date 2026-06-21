#!/usr/bin/env python3
"""Map where a paper's length goes, section by section.

This deterministic stdlib script parses a LaTeX source, counts prose words
under each section/subsection, estimates pages, and compares the total to an
optional target. It produces the map; the skill decides what to cut or grow.

Word counting strips comments, math, citations/refs, and most commands so the
count reflects readable prose, not markup. Page estimates are rough aids, never
a substitute for compiling and checking the real page count.
"""

import argparse
import json
import re
import sys


SECTION_RE = re.compile(r"\\(section|subsection|paragraph)\*?\{([^}]*)\}")


def strip(tex: str) -> str:
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\$\$.*?\$\$", " ", tex, flags=re.S)
    tex = re.sub(r"\$[^$]*\$", " ", tex)
    tex = re.sub(
        r"\\begin\{(equation|align|figure|table|tabular|algorithm)\*?\}.*?"
        r"\\end\{\1\*?\}",
        " ",
        tex,
        flags=re.S,
    )
    tex = re.sub(r"\\(cite|citep|citet|ref|cref|label|eqref)\{[^}]*\}", " ", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", tex)
    tex = tex.replace("{", " ").replace("}", " ")
    return tex


def words(text: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'-]+", text))


def sections(tex: str):
    """Return [(level, title, body_word_count)] in document order."""
    body = tex
    match = re.search(r"\\begin\{document\}(.*?)(\\end\{document\}|$)", tex, flags=re.S)
    if match:
        body = match.group(1)

    marks = list(SECTION_RE.finditer(body))
    out = []

    if marks and marks[0].start() > 0:
        pre = strip(body[: marks[0].start()])
        count = words(pre)
        if count > 20:
            out.append(("frontmatter", "(abstract/intro front matter)", count))

    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        segment = strip(body[mark.end() : end])
        out.append((mark.group(1), mark.group(2).strip(), words(segment)))

    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map per-section length of a LaTeX paper and compare to a target."
    )
    parser.add_argument("texfile")
    parser.add_argument(
        "--target-pages",
        type=float,
        default=None,
        help="venue page limit or target length to compare against",
    )
    parser.add_argument(
        "--words-per-page",
        type=float,
        default=900.0,
        help="estimate basis (two-column about 900, single-column about 550); default 900",
    )
    parser.add_argument(
        "--current-pages",
        type=float,
        default=None,
        help="actual compiled page count, if known; calibrates the estimate",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        tex = open(args.texfile, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(f"ERROR cannot read {args.texfile}: {exc}", file=sys.stderr)
        return 1

    found_sections = sections(tex)
    total = sum(count for _, _, count in found_sections) or 1
    words_per_page = args.words_per_page
    if args.current_pages:
        words_per_page = total / args.current_pages
    estimated_pages = total / words_per_page

    rows = [
        {
            "level": level,
            "title": title,
            "words": count,
            "pct": round(100 * count / total, 1),
            "est_pages": round(count / words_per_page, 2),
        }
        for level, title, count in found_sections
    ]

    if args.json:
        print(
            json.dumps(
                {
                    "total_words": total,
                    "est_pages": round(estimated_pages, 2),
                    "words_per_page": round(words_per_page),
                    "target_pages": args.target_pages,
                    "sections": rows,
                },
                indent=2,
            )
        )
        return 0

    calibrated = " calibrated" if args.current_pages else ""
    print(f"section budget - {args.texfile}")
    print(
        f"  total prose words: {total}   est. pages: {estimated_pages:.1f} "
        f"(@ {words_per_page:.0f} words/page{calibrated})\n"
    )
    print(f"  {'words':>6} {'pages':>6} {'%':>5}  section")
    for row in sorted(rows, key=lambda item: -item["words"]):
        indent = "  " if row["level"] in ("subsection", "paragraph") else ""
        print(
            f"  {row['words']:>6} {row['est_pages']:>6.2f} {row['pct']:>4.0f}%  "
            f"{indent}{row['title'][:60]}"
        )

    if args.target_pages:
        delta = estimated_pages - args.target_pages
        if delta > 0.15:
            needed_words = round(delta * words_per_page)
            print(
                f"\n  OVER by ~{delta:.1f} pages (~{needed_words} words). Compress "
                "from the largest low-value sections first: redundancy, long related "
                "work, verbose method text, or appendix-eligible details. Never "
                "delete results, claims, or citations to fit."
            )
        elif delta < -0.5:
            print(
                f"\n  UNDER by ~{-delta:.1f} pages. Expand with substance: ablations, "
                "analysis, limitations, or clearer motivation. Never add filler."
            )
        else:
            print(
                f"\n  Within ~{abs(delta):.1f} pages of the {args.target_pages:.0f}-page "
                "target; fine-tune with prose tightening."
            )

    print("\n  Estimate only - compile and check the real page count before relying on it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
