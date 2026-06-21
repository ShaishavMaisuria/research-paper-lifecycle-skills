#!/usr/bin/env python3
"""Print a paper's structural skeleton so its argument architecture is reviewable at a glance.

For the refactor-structure skill. Stdlib only, no network. Reads a LaTeX
main file (following \\input/\\include), strips comments and the preamble,
and emits the sectioning tree (part/chapter/section/subsection/subsubsection/
paragraph) with, for each unit:

  * the heading title (\\section{...}),
  * the FIRST SENTENCE of the prose that opens the unit (the topic sentence —
    where a well-structured section announces its job), and
  * lightweight structural signals: word count, whether it contains floats
    (figure/table), equations, lists, or its own \\cite calls.

The whole point is to make "is the story built in the right order, and does
each section open by doing its job?" answerable from one screenful, WITHOUT
the model re-reading the entire paper (and without quoting large spans of the
author's text — only the one topic sentence per unit is shown).

This script DESCRIBES structure. It does not judge it, rewrite anything, or
emit a plan — that is the human-in-the-loop step the skill drives.

Output: indented text tree (default), Markdown (--md), or JSON (--json).

Exit codes:
  0  outline produced
  2  bad arguments / unreadable main file / empty document
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Sectioning commands, outermost -> innermost. Index = depth.
SECTION_LEVELS = [
    "part",
    "chapter",
    "section",
    "subsection",
    "subsubsection",
    "paragraph",
    "subparagraph",
]
_LEVEL_INDEX = {name: i for i, name in enumerate(SECTION_LEVELS)}

# A sectioning command, optionally starred, with a balanced-brace title.
# We match the command + '*' + '{' here and read the balanced group separately.
_SECTION_CMD_RE = re.compile(
    r"\\(" + "|".join(SECTION_LEVELS) + r")(\*)?\s*(?:\[[^\]]*\])?\s*\{"
)
_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
_BEGIN_DOC_RE = re.compile(r"\\begin\{document\}")
_END_DOC_RE = re.compile(r"\\end\{document\}")
_CITE_RE = re.compile(r"\\(?:cite|citep|citet|citeauthor|citeyear|autocite|parencite|footcite)\b")
_FLOAT_BEGIN_RE = re.compile(r"\\begin\{(figure\*?|table\*?|wrapfigure|algorithm)\}")
_EQ_RE = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray)\}|\\\[")
_LIST_RE = re.compile(r"\\begin\{(itemize|enumerate|description)\}")
_LABEL_RE = re.compile(r"\\label\s*\{([^}]+)\}")


def strip_tex_comment(line: str) -> str:
    """Drop an unescaped % comment; keep \\% literals."""
    out = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            out.append(line[i : i + 2])
            i += 2
            continue
        if c == "%":
            break
        out.append(c)
        i += 1
    return "".join(out)


def read_corpus(main_path, follow_inputs=True, _seen=None, _depth=0, _notes=None):
    """Read a .tex file, inlining \\input/\\include in place.

    Returns (records, notes) where each record is
    {"path", "line", "text"} (comment-stripped). Raises OSError if the MAIN
    file is unreadable; unreadable INCLUDED files are skipped with a note (the
    document would not compile either, so a hard error is not warranted).
    """
    if _seen is None:
        _seen = set()
    if _notes is None:
        _notes = []
    real = os.path.realpath(main_path)
    if real in _seen:
        _notes.append("circular \\input at %s; skipped" % main_path)
        return [], _notes
    if _depth > 8:
        _notes.append("\\input nesting deeper than 8 at %s; stopped" % main_path)
        return [], _notes
    _seen.add(real)
    with open(main_path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    base_dir = os.path.dirname(os.path.abspath(main_path))
    records = []
    for lineno, line in enumerate(raw.splitlines(), 1):
        text = strip_tex_comment(line)
        records.append({"path": main_path, "line": lineno, "text": text})
        if follow_inputs:
            for m in _INPUT_RE.finditer(text):
                target = m.group(1).strip()
                if not os.path.splitext(target)[1]:
                    target += ".tex"
                child = target if os.path.isabs(target) else os.path.join(base_dir, target)
                if os.path.isfile(child):
                    child_recs, _ = read_corpus(
                        child, follow_inputs, _seen, _depth + 1, _notes
                    )
                    records.extend(child_recs)
                else:
                    _notes.append("could not find \\input target: %s" % target)
    return records, _notes


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
                return text[i + 1 : j], j + 1
        j += 1
    return None, i


def flatten(records):
    """Join records into one string plus an offset->record map for line lookup."""
    parts, offsets, pos = [], [], 0
    for rec in records:
        offsets.append((pos, rec))
        parts.append(rec["text"])
        pos += len(rec["text"]) + 1  # +1 for the join newline
    return "\n".join(parts), offsets


def loc_of(offset, offsets):
    """Binary-search the (start, rec) list for the record containing offset."""
    lo, hi, best = 0, len(offsets) - 1, 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if offsets[mid][0] <= offset:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    rec = offsets[best][1]
    return rec["path"], rec["line"]


def body_span(text):
    """Return (start, end) char offsets of the document body.

    Strips the preamble (before \\begin{document}) and anything after
    \\end{document}. If no \\begin{document}, treat the whole thing as body
    (lets the script also run on a single section file given via --no-inputs).
    """
    bm = _BEGIN_DOC_RE.search(text)
    start = bm.end() if bm else 0
    em = _END_DOC_RE.search(text, start)
    end = em.start() if em else len(text)
    return start, end


def title_to_plain(title):
    """Strip common LaTeX markup from a heading for display."""
    t = title
    t = re.sub(r"\\(?:texttt|textbf|textit|emph|textsc|textrm|mbox)\s*\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\(?:label|footnote|thanks)\s*\{[^{}]*\}", "", t)
    t = re.sub(r"[~]", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\s*", "", t)  # drop remaining bare macros
    t = t.replace("{", "").replace("}", "").replace("\\", "")
    return re.sub(r"\s+", " ", t).strip()


# Inline math/cmd scrubbing for the topic-sentence extraction only.
_INLINE_MATH_RE = re.compile(r"\$[^$]*\$")
_CMD_ONE_ARG_RE = re.compile(
    r"\\(?:emph|textbf|textit|texttt|textsc|textrm|mbox)\s*\{([^{}]*)\}"
)
_CMD_DROP_RE = re.compile(r"\\(?:cite|citep|citet|autocite|parencite|footcite|label|ref|cref|Cref|eqref|footnote)\s*\{[^{}]*\}")
_BARE_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?")


def first_sentence(body_text):
    """Extract the first prose sentence opening a unit's body.

    Skips leading environments (floats, equations, lists) and whitespace,
    scrubs inline math/commands/citations, and returns up to the first
    sentence terminator. Returns "" if the unit opens with no prose (e.g.
    a section that jumps straight into a figure or a subsection).
    """
    text = body_text
    # Remove environments at the START of the body so we find the first PROSE.
    # We loop because a section may open with several stacked environments.
    env_open_re = re.compile(r"^\s*\\begin\{([a-zA-Z*]+)\}")
    while True:
        m = env_open_re.match(text)
        if not m:
            break
        env = re.escape(m.group(1))
        end = re.search(r"\\end\{" + env + r"\}", text)
        if not end:
            break
        text = text[end.end() :]
    # Drop a leading \\label / display math that isn't an environment.
    text = re.sub(r"^\s*(?:\\label\s*\{[^{}]*\}|\\\[.*?\\\])", "", text, flags=re.S)
    text = text.lstrip()
    if not text:
        return ""
    # Scrub for readability.
    text = _CMD_DROP_RE.sub("", text)
    text = _INLINE_MATH_RE.sub("<math>", text)
    text = _CMD_ONE_ARG_RE.sub(r"\1", text)
    # De-escape LaTeX specials (\% \& \_ \# \$ \{ \}) BEFORE dropping macros,
    # so "38\%" reads as "38%" rather than losing the "%".
    text = re.sub(r"\\([%&_#${}])", r"\1", text)
    text = _BARE_CMD_RE.sub("", text)
    text = text.replace("{", "").replace("}", "").replace("~", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    # First sentence: up to . ! ? followed by space/end, not a decimal/abbrev.
    m = re.search(r"(.+?[.!?])(?:\s|$)", text)
    sentence = m.group(1) if m else text
    return sentence.strip()


class Unit:
    __slots__ = (
        "level", "depth", "starred", "title", "path", "line",
        "first_sentence", "words", "has_float", "has_eq", "has_list",
        "cites", "labels",
    )

    def __init__(self, level, starred, title, path, line):
        self.level = level
        self.depth = _LEVEL_INDEX[level]
        self.starred = starred
        self.title = title
        self.path = path
        self.line = line
        self.first_sentence = ""
        self.words = 0
        self.has_float = False
        self.has_eq = False
        self.has_list = False
        self.cites = 0
        self.labels = []


def parse_units(text, offsets):
    """Walk the body and build the ordered list of sectioning units."""
    start, end = body_span(text)
    headings = []  # (cmd_match_start, level, starred, title_text, content_start)
    i = start
    while True:
        m = _SECTION_CMD_RE.search(text, i)
        if not m or m.start() >= end:
            break
        title, after = read_group(text, m.end() - 1)  # m.end()-1 is the '{'
        if title is None:
            i = m.end()
            continue
        headings.append((m.start(), m.group(1), bool(m.group(2)), title, after))
        i = after

    units = []
    for idx, (hstart, level, starred, title, content_start) in enumerate(headings):
        content_end = headings[idx + 1][0] if idx + 1 < len(headings) else end
        body = text[content_start:content_end]
        path, line = loc_of(hstart, offsets)
        u = Unit(level, starred, title_to_plain(title), path, line)
        u.first_sentence = first_sentence(body)
        # Count words on the comment-stripped, lightly-scrubbed body.
        scrubbed = _BARE_CMD_RE.sub(" ", _INLINE_MATH_RE.sub(" ", body))
        scrubbed = scrubbed.replace("{", " ").replace("}", " ")
        u.words = len(re.findall(r"[A-Za-z][A-Za-z'-]+", scrubbed))
        u.has_float = _FLOAT_BEGIN_RE.search(body) is not None
        u.has_eq = _EQ_RE.search(body) is not None
        u.has_list = _LIST_RE.search(body) is not None
        u.cites = len(_CITE_RE.findall(body))
        u.labels = _LABEL_RE.findall(body)
        units.append(u)
    return units


def signals_str(u):
    tags = []
    if u.words:
        tags.append("%dw" % u.words)
    if u.cites:
        tags.append("%d cite%s" % (u.cites, "" if u.cites == 1 else "s"))
    if u.has_float:
        tags.append("float")
    if u.has_eq:
        tags.append("eqn")
    if u.has_list:
        tags.append("list")
    if u.starred:
        tags.append("unnumbered")
    if not u.first_sentence:
        tags.append("NO-OPENING-PROSE")
    return ", ".join(tags)


def render_tree(units, notes, show_sentence=True):
    lines = []
    for u in units:
        indent = "  " * u.depth
        bullet = title_to_plain(u.title) or "(untitled)"
        lines.append("%s%s  [%s]  (%s:%s)" % (indent, bullet, signals_str(u), u.path, u.line))
        if show_sentence:
            sent = u.first_sentence or "(opens with a float/subsection, no topic sentence)"
            lines.append("%s    -> %s" % (indent, sent))
    if notes:
        lines.append("")
        lines.append("Notes:")
        for n in notes:
            lines.append("  - " + n)
    return "\n".join(lines)


def render_md(units, notes):
    lines = ["# Structural skeleton", ""]
    for u in units:
        indent = "  " * u.depth
        title = title_to_plain(u.title) or "(untitled)"
        lines.append("%s- **%s** _(%s)_" % (indent, title, signals_str(u)))
        sent = u.first_sentence or "_opens with a float/subsection — no topic sentence_"
        lines.append("%s  - %s" % (indent, sent))
    if notes:
        lines.append("")
        lines.append("## Notes")
        for n in notes:
            lines.append("- " + n)
    return "\n".join(lines)


def render_json(units, notes):
    return json.dumps(
        {
            "units": [
                {
                    "level": u.level,
                    "depth": u.depth,
                    "starred": u.starred,
                    "title": title_to_plain(u.title),
                    "file": u.path,
                    "line": u.line,
                    "first_sentence": u.first_sentence,
                    "words": u.words,
                    "cites": u.cites,
                    "has_float": u.has_float,
                    "has_equation": u.has_eq,
                    "has_list": u.has_list,
                    "labels": u.labels,
                }
                for u in units
            ],
            "notes": notes,
            "count": len(units),
        },
        indent=2,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print a paper's section/subsection tree + the first "
        "sentence of each unit, so its argument architecture is reviewable at "
        "a glance. Describes structure; does not judge or rewrite it. "
        "Stdlib only, no network."
    )
    parser.add_argument("tex", help="main .tex file (the one with \\begin{document})")
    parser.add_argument(
        "--no-inputs", action="store_true",
        help="do not follow \\input/\\include (run on a single file as-is)",
    )
    parser.add_argument("--md", action="store_true", help="Markdown output")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON")
    parser.add_argument(
        "--no-sentence", action="store_true",
        help="tree output without the topic sentences (titles + signals only)",
    )
    args = parser.parse_args(argv)

    if args.md and args.json:
        sys.stderr.write("error: choose at most one of --md / --json\n")
        return 2
    if not os.path.isfile(args.tex):
        sys.stderr.write("error: file not found: %s\n" % args.tex)
        return 2

    try:
        records, notes = read_corpus(args.tex, follow_inputs=not args.no_inputs)
    except OSError as exc:
        sys.stderr.write("error: cannot read %s: %s\n" % (args.tex, exc))
        return 2
    if not records:
        sys.stderr.write("error: %s is empty\n" % args.tex)
        return 2

    text, offsets = flatten(records)
    units = parse_units(text, offsets)
    if not units:
        notes.append(
            "no \\section/\\subsection commands found — is this the MAIN file "
            "(with \\begin{document}), or do sections live in \\input files? "
            "(re-run without --no-inputs)"
        )

    if args.json:
        print(render_json(units, notes))
    elif args.md:
        print(render_md(units, notes))
    else:
        print(render_tree(units, notes, show_sentence=not args.no_sentence))
        print(
            "\n%d sectioning unit(s). This is a STRUCTURE MAP, not a verdict — "
            "read it to check the argument's order and whether each unit opens "
            "by doing its job." % len(units)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
