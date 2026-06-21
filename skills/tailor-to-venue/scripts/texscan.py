#!/usr/bin/env python3
"""Shared LaTeX-source helpers for the tailor-to-venue scripts (stdlib only).

Provides \\input/\\include resolution, comment stripping, and a rough
plain-word counter. Used by venue_diff.py, page_budget.py and anon_sweep.py.

CLI usage (sanity check of what the other scripts will see):
    python3 texscan.py <main.tex>

Exit codes: 0 ok, 2 unreadable main file.
"""

import argparse
import os
import re
import sys

__all__ = ["read_tex", "strip_comments", "plain_words", "TexScanError"]

_MAX_DEPTH = 6


class TexScanError(Exception):
    pass


def strip_comments(text):
    """Remove % comments (but not \\%) to end of line."""
    out_lines = []
    for line in text.splitlines():
        buf = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "\\" and i + 1 < len(line):
                buf.append(line[i:i + 2])
                i += 2
                continue
            if ch == "%":
                break
            buf.append(ch)
            i += 1
        out_lines.append("".join(buf))
    return "\n".join(out_lines)


_INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")


def read_tex(main_path, _depth=0, _seen=None, warnings=None):
    """Read a .tex file, recursively inlining \\input/\\include/\\subfile.

    Returns (text, files, warnings). Missing includes produce a warning,
    never a crash — drafts often have commented-out or generated inputs.
    """
    if warnings is None:
        warnings = []
    if _seen is None:
        _seen = set()
    main_path = os.path.abspath(main_path)
    if main_path in _seen:
        warnings.append("circular \\input detected at %s; skipping" % main_path)
        return "", [], warnings
    _seen.add(main_path)
    try:
        with open(main_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        raise TexScanError("cannot read %s: %s" % (main_path, exc))
    text = strip_comments(text)
    files = [main_path]
    if _depth >= _MAX_DEPTH:
        warnings.append("max include depth reached at %s" % main_path)
        return text, files, warnings

    base = os.path.dirname(main_path)

    def _inline(match):
        target = match.group(1).strip()
        if not os.path.splitext(target)[1]:
            target += ".tex"
        candidate = target if os.path.isabs(target) else os.path.join(base, target)
        if not os.path.isfile(candidate):
            warnings.append("missing include: %s (referenced from %s)"
                            % (target, os.path.basename(main_path)))
            return ""
        sub_text, sub_files, _ = read_tex(candidate, _depth + 1, _seen, warnings)
        files.extend(sub_files)
        return "\n" + sub_text + "\n"

    text = _INPUT_RE.sub(_inline, text)
    return text, files, warnings


_ENV_DROP_RE = re.compile(
    r"\\begin\{(figure\*?|table\*?|algorithm\*?|algorithmic|tikzpicture|"
    r"equation\*?|align\*?|gather\*?|eqnarray\*?|lstlisting|verbatim|"
    r"tabular\*?|CCSXML)\}.*?\\end\{\1\}",
    re.DOTALL,
)
_MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)", re.DOTALL)
_CMD_ARG_RE = re.compile(
    r"\\(?:cite[tp]?\*?|ref|eqref|autoref|cref|Cref|label|url|href|"
    r"includegraphics|bibliography|bibliographystyle|usepackage|"
    r"documentclass|input|include|vspace|hspace|footnotemark)"
    r"(?:\[[^\]]*\])?\{[^}]*\}"
)
_CMD_RE = re.compile(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?")


def plain_words(text):
    """Strip floats, math, and commands; return the remaining word list."""
    text = _ENV_DROP_RE.sub(" ", text)
    text = _MATH_RE.sub(" MATH ", text)
    text = _CMD_ARG_RE.sub(" ", text)
    text = _CMD_RE.sub(" ", text)
    text = re.sub(r"[{}~]", " ", text)
    return [w for w in text.split() if any(c.isalnum() for c in w)]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Resolve \\input/\\include of a LaTeX main file and print "
        "what the tailor-to-venue scripts will analyze (files, lines, words)."
    )
    parser.add_argument("main_tex", help="path to the main .tex file")
    args = parser.parse_args(argv)
    try:
        text, files, warnings = read_tex(args.main_tex)
    except TexScanError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2
    print("files resolved (%d):" % len(files))
    for f in files:
        print("  " + f)
    for w in warnings:
        print("warning: " + w)
    print("lines: %d" % len(text.splitlines()))
    print("plain words (text only, floats/math/commands stripped): %d"
          % len(plain_words(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
