#!/usr/bin/env python3
"""Shared LaTeX-source scanning helpers for the preflight-check scripts.

Stdlib only. Loads a .tex file (following \\input/\\include), strips comments,
and exposes position->file:line mapping plus balanced-brace command parsing.
Also holds the Finding record and the common CLI/report plumbing so all four
checkers behave identically.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys

SEVERITIES = ("ERROR", "WARN", "INFO")


@dataclasses.dataclass
class Finding:
    severity: str  # ERROR | WARN | INFO
    check: str  # e.g. "anonymization/author-block"
    file: str
    line: int | None
    message: str

    def format(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity:5}] {self.check:32} {loc} — {self.message}"


@dataclasses.dataclass
class TexLine:
    file: str
    lineno: int
    code: str  # comment-stripped source


def strip_tex_comment(line: str) -> str:
    """Drop an unescaped % comment; keeps \\% literals."""
    out: list[str] = []
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


_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def _load_lines(
    path: pathlib.Path,
    root_dir: pathlib.Path,
    seen: set,
    notes: list[str],
    depth: int = 0,
) -> list[TexLine]:
    if depth > 8:
        notes.append(f"\\input nesting deeper than 8 at {path}; stopped following")
        return []
    key = str(path.resolve())
    if key in seen:
        notes.append(f"circular \\input detected at {path}; skipped")
        return []
    seen.add(key)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        notes.append(f"could not read {path}: {exc}")
        return []
    out: list[TexLine] = []
    rel = str(path)
    for n, raw in enumerate(text.splitlines(), start=1):
        code = strip_tex_comment(raw)
        out.append(TexLine(rel, n, code))
        for m in _INPUT_RE.finditer(code):
            child = m.group(1).strip()
            cpath = root_dir / child
            if cpath.suffix == "":
                cpath = cpath.with_suffix(".tex")
            if cpath.is_file():
                out.extend(_load_lines(cpath, root_dir, seen, notes, depth + 1))
            else:
                notes.append(f"{rel}:{n}: \\input{{{child}}} not found; skipped")
    return out


class TexDoc:
    """Comment-stripped, \\input-flattened LaTeX source with line mapping."""

    def __init__(self, lines: list[TexLine], notes: list[str]):
        self.lines = lines
        self.notes = notes
        self.text = "\n".join(ln.code for ln in lines)
        self._starts: list[int] = []
        pos = 0
        for ln in lines:
            self._starts.append(pos)
            pos += len(ln.code) + 1

    @classmethod
    def load(cls, path: str | pathlib.Path, follow_inputs: bool = True) -> "TexDoc":
        p = pathlib.Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"tex file not found: {p}")
        notes: list[str] = []
        if follow_inputs:
            lines = _load_lines(p, p.parent, set(), notes)
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = [
                TexLine(str(p), n, strip_tex_comment(raw))
                for n, raw in enumerate(text.splitlines(), start=1)
            ]
        return cls(lines, notes)

    def loc(self, pos: int) -> tuple[str, int]:
        """Map a character offset in self.text to (file, lineno)."""
        lo, hi = 0, len(self._starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        ln = self.lines[lo] if self.lines else None
        return (ln.file, ln.lineno) if ln else ("?", 0)

    # -- command / environment scanning ------------------------------------

    def extract_braced(self, start: int) -> tuple[str | None, int]:
        """Balanced {...} starting at self.text[start]; returns (body, end)."""
        if start >= len(self.text) or self.text[start] != "{":
            return None, start
        depth = 0
        i = start
        while i < len(self.text):
            c = self.text[i]
            if c == "\\":
                i += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return self.text[start + 1 : i], i + 1
            i += 1
        return None, start  # unbalanced

    def find_commands(self, name: str) -> list[tuple[int, str | None, str | None]]:
        """All \\<name>[opt]{arg} occurrences -> (pos, opt, arg)."""
        out = []
        boundary = r"\b" if name[-1].isalnum() else ""
        for m in re.finditer(r"\\" + re.escape(name) + boundary + r"\s*", self.text):
            i = m.end()
            opt = None
            if i < len(self.text) and self.text[i] == "[":
                j = self.text.find("]", i)
                if j != -1:
                    opt = self.text[i + 1 : j]
                    i = j + 1
                    while i < len(self.text) and self.text[i] in " \t\n":
                        i += 1
            arg, _ = self.extract_braced(i)
            out.append((m.start(), opt, arg))
        return out

    def env_spans(self, name: str) -> list[tuple[int, int, str]]:
        """(start, end, inner) for each \\begin{name}...\\end{name}."""
        out = []
        begin = re.compile(r"\\begin\s*\{" + re.escape(name) + r"\}")
        end = re.compile(r"\\end\s*\{" + re.escape(name) + r"\}")
        for m in begin.finditer(self.text):
            e = end.search(self.text, m.end())
            stop = e.start() if e else len(self.text)
            out.append((m.start(), stop, self.text[m.end() : stop]))
        return out


_CITE_RE = re.compile(r"\\(?:cite|citep|citet|citeauthor|citeyear)[a-zA-Z*]*\s*(?:\[[^\]]*\])*\s*\{[^}]*\}")


def de_latex(text: str) -> str:
    """Rough plain-text rendering for word counting (abstracts etc.)."""
    text = _CITE_RE.sub(" [cite] ", text)
    text = re.sub(r"\\(?:label|ref|eqref|url|href)\s*\{[^}]*\}", " ", text)
    text = re.sub(r"\$\$[^$]*\$\$|\$[^$]*\$", " [math] ", text)
    text = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z@]+\s*(?:\[[^\]]*\])?", " ", text)  # drop commands, keep {args}
    text = re.sub(r"[{}~]", " ", text)
    return text


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-\[\]]*", de_latex(text)))


# ---------------------------------------------------------------------------
# Common CLI and reporting
# ---------------------------------------------------------------------------


def base_parser(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("tex", help="main .tex file of the submission")
    ap.add_argument(
        "--venue",
        required=True,
        help="path to the venue profile YAML (venues/conferences/<venue>.yml)",
    )
    ap.add_argument("--venues-dir", help="venues/ root for family lookup (auto by default)")
    ap.add_argument("--track", help="track name substring (default: first track in profile)")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument(
        "--strict", action="store_true", help="exit 1 on WARN findings too, not just ERROR"
    )
    ap.add_argument(
        "--no-inputs", action="store_true", help="do not follow \\input/\\include files"
    )
    return ap


def report(
    tool: str,
    findings: list[Finding],
    doc_notes: list[str],
    profile_notes: list[str],
    args,
    profile: dict,
    track: dict | None,
) -> int:
    """Print findings (text or JSON); return the process exit code."""
    findings = sorted(
        findings, key=lambda f: (SEVERITIES.index(f.severity), f.file, f.line or 0)
    )
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}
    if args.json:
        json.dump(
            {
                "tool": tool,
                "tex": args.tex,
                "venue": profile.get("id"),
                "track": (track or {}).get("name"),
                "findings": [dataclasses.asdict(f) for f in findings],
                "notes": profile_notes + doc_notes,
                "summary": counts,
            },
            sys.stdout,
            indent=2,
            default=str,
        )
        print()
    else:
        print(f"== {tool}: {args.tex} vs {profile.get('id')} "
              f"(track: {(track or {}).get('name', 'n/a')}) ==")
        for note in profile_notes + doc_notes:
            print(f"  note: {note}")
        if not findings:
            print("  no findings — clean.")
        for f in findings:
            print("  " + f.format())
        print(
            f"  summary: {counts['ERROR']} error(s), {counts['WARN']} warning(s), "
            f"{counts['INFO']} info"
        )
        cfp = profile.get("cfp_url")
        if cfp:
            print(f"  reminder: re-verify limits/policies against the live CFP: {cfp}")
    if counts["ERROR"] or (args.strict and counts["WARN"]):
        return 1
    return 0


def run_checker(tool: str, description: str, collect) -> int:
    """Standard main() for a checker: parse args, load, collect, report."""
    # local import to avoid a hard cycle at module import time
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import venue_profile as vp

    args = base_parser(description).parse_args()
    try:
        profile, pnotes = vp.load_profile(args.venue, args.venues_dir)
        track, tnote = vp.pick_track(profile, args.track)
        pnotes.append(tnote)
        doc = TexDoc.load(args.tex, follow_inputs=not args.no_inputs)
    except (vp.ProfileError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = collect(doc, profile, track, args)
    return report(tool, findings, doc.notes, pnotes, args, profile, track)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="texlib.py",
        description=(
            "Shared library for the preflight-check scripts — not a checker "
            "itself. Run one of: run_preflight.py, check_template.py, "
            "check_anonymization.py, check_sections.py, check_abstract.py, "
            "venue_profile.py."
        ),
    )
    parser.parse_args()
    parser.print_help()
    sys.exit(0)
