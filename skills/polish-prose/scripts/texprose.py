#!/usr/bin/env python3
"""Shared LaTeX-to-prose helpers for the polish-prose scripts (not a CLI).

Turns a .tex (or plain-text) source into a list of (line_number, prose)
pairs with comments stripped, non-prose environments masked, and
\\cite/\\ref/math/URL tokens replaced by neutral placeholders so that lint
lexicons never fire on BibTeX keys, labels, or math.
"""

import re

# environments whose body is never prose
MASK_ENVS = (
    "verbatim", "verbatim*", "lstlisting", "minted", "alltt",
    "equation", "equation*", "align", "align*", "gather", "gather*",
    "multline", "multline*", "eqnarray", "eqnarray*", "displaymath",
    "tikzpicture", "algorithmic", "algorithm", "algorithm2e",
    "thebibliography", "filecontents", "filecontents*", "CCSXML",
)

_COMMENT_RE = re.compile(r"(?<!\\)%.*")
_CITE_RE = re.compile(
    r"\\(?:cite[a-zA-Z]*|ref|autoref|eqref|cref|Cref|pageref|label|"
    r"bibliography(?:style)?|input|include|includegraphics)\*?"
    r"\s*(?:\[[^\]]*\]){0,2}\s*\{[^{}]*\}")
_URL_RE = re.compile(r"\\(?:url|href)\{[^}]*\}(?:\{[^}]*\})?|https?://\S+")
_INLINE_MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$\n]*\$|\\\(.*?\\\)")
_BEGIN_END_RE = re.compile(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?(?:\{[^}]*\})*")
_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?")


class SourceError(Exception):
    pass


def read_source(path):
    """Read a source file (or '-' for stdin). Returns (raw_text, label)."""
    import os
    import sys
    if path == "-":
        raw = sys.stdin.read()
        label = "<stdin>"
    else:
        if not os.path.isfile(path):
            raise SourceError("file not found: %s" % path)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        label = path
    if not raw.strip():
        raise SourceError("%s is empty" % label)
    return raw, label


def is_tex(path, raw):
    return path.endswith(".tex") or "\\begin{document}" in raw or \
        "\\documentclass" in raw


def prose_lines(raw, tex=True):
    """Return [(lineno, masked_prose_line), ...] — 1-based line numbers.

    Non-prose lines (preamble, masked environments, display math) come back
    as empty strings so line numbering stays aligned with the source file.
    """
    lines = raw.split("\n")
    out = []
    in_doc = ("\\begin{document}" not in raw) or not tex
    env_depth = 0   # depth inside masked environments
    in_dmath = False  # inside \[ ... \]
    begin_re = re.compile(r"\\begin\{(%s)\}" % "|".join(
        re.escape(e) for e in MASK_ENVS))
    end_re = re.compile(r"\\end\{(%s)\}" % "|".join(
        re.escape(e) for e in MASK_ENVS))

    for i, line in enumerate(lines, 1):
        work = _COMMENT_RE.sub("", line) if tex else line
        if tex and not in_doc:
            if "\\begin{document}" in work:
                in_doc = True
            out.append((i, ""))
            continue
        if tex:
            opens = len(begin_re.findall(work))
            closes = len(end_re.findall(work))
            if env_depth > 0 or opens:
                env_depth = max(0, env_depth + opens - closes)
                out.append((i, ""))
                continue
            if in_dmath:
                if "\\]" in work:
                    in_dmath = False
                out.append((i, ""))
                continue
            if "\\[" in work and "\\]" not in work:
                in_dmath = True
                work = work.split("\\[")[0]
            work = _INLINE_MATH_RE.sub(" [math] ", work)
            work = _URL_RE.sub(" [url] ", work)
            work = _CITE_RE.sub(" [ref] ", work)
            work = _BEGIN_END_RE.sub(" ", work)
            for esc, lit in (("\\%", "%"), ("\\&", "&"), ("\\_", "_"),
                             ("\\$", "$"), ("~", " "), ("\\\\", " ")):
                work = work.replace(esc, lit)
            work = _CMD_RE.sub(" ", work)
            work = work.replace("{", " ").replace("}", " ")
        out.append((i, work))
    return out


def joined_prose(plines):
    """Single string of all prose, for sentence-level statistics."""
    return " ".join(t for _, t in plines if t.strip())


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return [p for p in parts if len(p.split()) >= 2]


def word_count(plines):
    return sum(len([w for w in t.split() if any(c.isalnum() for c in w)])
               for _, t in plines)


def paragraphs(plines):
    """Group prose lines into blank-line-separated paragraphs.

    Returns [(first_lineno, text), ...]; only non-empty paragraphs.
    """
    paras, cur, start = [], [], None
    for ln, t in plines:
        if t.strip():
            if start is None:
                start = ln
            cur.append(t)
        else:
            if cur:
                paras.append((start, " ".join(cur)))
            cur, start = [], None
    if cur:
        paras.append((start, " ".join(cur)))
    return paras
