#!/usr/bin/env python3
"""Extract candidate CLAIM sentences from a LaTeX paper for evidence mapping.

This is the deterministic front-end for the verify-claims skill. It does NOT
judge whether a claim is true — it has no oracle for "is this the first paper
to do X" or "is this really state-of-the-art". It finds the sentences a
reviewer will attack (novelty / superiority / result-magnitude / generalization
markers) with their file:line, and it lists the numbers in the prose against
the numbers in the tables so the author can reconcile mismatches. The author
then maps each candidate to evidence and sets its status (the claims matrix).

Stdlib only. No network. Reads but never writes the paper.

Usage:
    python3 claim_audit.py main.tex
    python3 claim_audit.py main.tex --json out.json
    python3 claim_audit.py main.tex --type novelty
    python3 claim_audit.py main.tex --numbers
    python3 claim_audit.py main.tex --context 1 --min-confidence high

Exit codes:
    0  no candidate claims found (rare; usually a near-empty/parse-failed input
       worth checking) and no numeric mismatch
    2  candidate claims were found (THE NORMAL, HEALTHY case) — they need author
       triage, not a fix. Also returned when prose/table numbers disagree.
    1  operational failure (unreadable file, bad arguments)

Adapt to your discipline: the marker lexicons below are CS/ML defaults. Edit
NOVELTY/SUPERIORITY/RESULT/GENERALIZATION for your field's claim vocabulary
(a theory paper leans on "we prove"/"theorem"; a survey on "comprehensive").
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# --------------------------------------------------------------------------- #
# Claim marker lexicons (CS/ML defaults — documented for editing per field).
# Each entry: a regex matched case-insensitively against a sentence's words.
# Keep word boundaries so "novelty" does not match inside another word and a
# bare "first" sentence ("In the first stage we ...") is caught for review even
# if it turns out benign — false positives here are cheap, misses are not.
# --------------------------------------------------------------------------- #
NOVELTY = [
    r"\bfirst\b", r"\bnovel(?:ty|ly)?\b", r"\bunlike\s+(?:prior|previous|existing)\b",
    r"\bfor\s+the\s+first\s+time\b", r"\bthe\s+only\b", r"\bwe\s+are\s+the\s+(?:first|only)\b",
    r"\bnew(?:ly)?\b", r"\bunprecedented\b", r"\bto\s+our\s+knowledge\b",
    r"\bhas\s+not\s+been\b", r"\bnever\s+been\b",
]
SUPERIORITY = [
    r"\bstate[\s-]of[\s-]the[\s-]art\b", r"\bsota\b", r"\boutperform(?:s|ed|ing)?\b",
    r"\bbest\b", r"\bsuperior\b", r"\bbetter\s+than\b", r"\bsurpass(?:es|ed|ing)?\b",
    r"\bexceed(?:s|ed|ing)?\b", r"\bbeats?\b", r"\bleading\b", r"\btop[\s-]performing\b",
]
RESULT = [
    r"\bsignificant(?:ly)?\b", r"\bsubstantial(?:ly)?\b", r"\bdramatic(?:ally)?\b",
    r"\bremarkabl[ey]\b", r"\bconsiderabl[ey]\b", r"\bmarked(?:ly)?\b",
    r"\d+(?:\.\d+)?\s*%", r"\b\d+(?:\.\d+)?\s*[x×]\b", r"\border(?:s)?\s+of\s+magnitude\b",
    r"\bspeedup\b", r"\bimprove(?:s|d|ment)?\b",
]
GENERALIZATION = [
    r"\balways\b", r"\bin\s+all\s+cases\b", r"\bevery\s+case\b", r"\bguarantee(?:s|d)?\b",
    r"\brobust(?:ness)?\b", r"\bgeneral(?:ize|izes|ization|ly)?\b", r"\buniversal(?:ly)?\b",
    r"\bany\s+(?:input|dataset|setting|case)\b", r"\bproven\b", r"\bensures?\b",
]
TYPES = {
    "novelty": NOVELTY,
    "superiority": SUPERIORITY,
    "result": RESULT,
    "generalization": GENERALIZATION,
}
# Compile once: type -> list[compiled]
_COMPILED = {t: [re.compile(p, re.I) for p in pats] for t, pats in TYPES.items()}

# A "high confidence" candidate carries one of these strong markers (the ones
# that almost always demand explicit evidence). Used by --min-confidence high.
HIGH_CONF = re.compile(
    r"\bfirst\b|\bnovel|\bstate[\s-]of[\s-]the[\s-]art\b|\bsota\b|\boutperform"
    r"|\bsignificant|\bguarantee|\balways\b|\bonly\b|\bbest\b",
    re.I,
)

# Sentence-splitter that does not break on common abbreviations / decimals.
_ABBREV = r"(?<!\be\.g)(?<!\bi\.e)(?<!\bet\sal)(?<!\bvs)(?<!\bFig)(?<!\bcf)(?<!\bEq)"
_SENT_SPLIT = re.compile(_ABBREV + r"(?<=[.!?])\s+(?=[A-Z\\])")


class TexFile:
    """A loaded .tex file plus the line index for file:line reporting.

    `segments` carries source provenance for \\input/\\include inlining: a sorted
    list of (resolved_line, source_path, source_line) boundaries so a claim in
    an included file is reported at its REAL file and line, not the top-level
    file. When nothing is inlined it is a single identity segment.
    """

    def __init__(self, path: str, text: str, segments=None):
        self.path = path
        self.text = text
        # offset -> resolved-line number lookup
        self._line_starts = [0]
        for m in re.finditer(r"\n", text):
            self._line_starts.append(m.end())
        # provenance: (resolved_line, source_path, source_line), sorted by
        # resolved_line. Default identity if the resolver gave us none.
        self.segments = segments or [(1, path, 1)]

    def line_of(self, offset: int) -> int:
        """Resolved-text line number for an offset (1-based)."""
        import bisect
        return bisect.bisect_right(self._line_starts, offset)

    def locate(self, offset: int) -> tuple[str, int]:
        """Map an offset to its (source_file, source_line) via the provenance
        segments — the real origin even across \\input/\\include."""
        import bisect
        rline = self.line_of(offset)
        starts = [s[0] for s in self.segments]
        i = bisect.bisect_right(starts, rline) - 1
        if i < 0:
            return self.path, rline
        rl0, src_path, src_l0 = self.segments[i]
        return src_path, src_l0 + (rline - rl0)


def _strip_comments(text: str) -> str:
    """Remove % comments (respecting \\%), keep newlines for line counting."""
    out = []
    for line in text.split("\n"):
        i, n, esc = 0, len(line), False
        cut = n
        while i < n:
            c = line[i]
            if c == "\\":
                esc = not esc
            elif c == "%" and not esc:
                cut = i
                break
            else:
                esc = False
            i += 1
        out.append(line[:cut])
    return "\n".join(out)


_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]*)\}")


def _resolve_inputs(path: str, text: str, seen: set, depth: int = 0):
    """Inline \\input{f} / \\include{f} (one body of prose), depth-limited.

    Returns (resolved_text, segments) where segments is a list of
    (resolved_line, source_path, source_line) provenance boundaries so a claim
    in an included file is later reported at its real file:line. Resolution is
    line-aware: when an \\input is the only meaningful content on a line, the
    included file is spliced in with correct provenance; an \\input embedded
    mid-line is inlined inline (provenance stays on the parent line).
    """
    out_lines: list[str] = []
    segments: list[tuple[int, str, int]] = []

    def emit_segment(src_path: str, src_line: int):
        cur_resolved = len(out_lines) + 1
        if segments:
            rl0, sp0, sl0 = segments[-1]
            # contiguous continuation of the same source file needs no boundary:
            # the previous segment already predicts this (path, line) pair.
            if sp0 == src_path and sl0 + (cur_resolved - rl0) == src_line:
                return
        segments.append((cur_resolved, src_path, src_line))

    base = os.path.dirname(os.path.abspath(path))

    def resolve_name(name: str):
        name = name.strip()
        if not name:
            return None
        cand = name if name.endswith(".tex") else name + ".tex"
        for p in (os.path.join(base, cand), os.path.join(base, name)):
            ap = os.path.abspath(p)
            if os.path.isfile(ap):
                return ap
        return None

    lines = text.split("\n")
    for li, line in enumerate(lines, start=1):
        # A line that is ONLY an \input/\include (optionally with whitespace):
        # splice the included file as its own provenance segment.
        stripped = line.strip()
        m_solo = _INPUT_RE.fullmatch(stripped) if stripped else None
        if m_solo and depth <= 8:
            ap = resolve_name(m_solo.group(1))
            if ap and ap not in seen:
                seen.add(ap)
                try:
                    with open(ap, encoding="utf-8", errors="replace") as fh:
                        sub = _strip_comments(fh.read())
                    sub_text, sub_segs = _resolve_inputs(ap, sub, seen, depth + 1)
                    # splice: record where the child's lines start in the parent
                    child_start = len(out_lines) + 1
                    for cl in sub_text.split("\n"):
                        out_lines.append(cl)
                    for (rl, sp, sl) in sub_segs:
                        segments.append((child_start + (rl - 1), sp, sl))
                    # after the child, resume the parent file on the NEXT line
                    emit_segment(path, li + 1)
                    continue
                except OSError:
                    pass
            # unresolved / cyclic / too deep: drop the line (not prose), but
            # keep a blank so following lines keep their relative spacing
            emit_segment(path, li)
            out_lines.append("")
            continue
        # Ordinary line (may contain a mid-line \input we inline w/o provenance
        # splitting — rare; the parent line is the reported origin).
        if depth <= 8 and _INPUT_RE.search(line):
            def repl(m: re.Match) -> str:
                ap2 = resolve_name(m.group(1))
                if ap2 and ap2 not in seen:
                    seen.add(ap2)
                    try:
                        with open(ap2, encoding="utf-8", errors="replace") as fh:
                            sub = _strip_comments(fh.read())
                        sub_text, _ = _resolve_inputs(ap2, sub, seen, depth + 1)
                        return " " + sub_text.replace("\n", " ") + " "
                    except OSError:
                        return ""
                return ""
            line = _INPUT_RE.sub(repl, line)
        emit_segment(path, li)
        out_lines.append(line)

    return "\n".join(out_lines), segments


# Environments whose body is NOT prose to scan for claim sentences.
_NONPROSE_ENVS = (
    "equation", "align", "gather", "multline", "eqnarray", "math", "displaymath",
    "tabular", "tabularx", "tabular*", "array", "table", "table*", "figure",
    "figure*", "verbatim", "lstlisting", "minted", "algorithm", "algorithmic",
    "tikzpicture", "CCSXML",
)


def _mask_nonprose(text: str) -> str:
    """Replace math and non-prose environment bodies with blank space of equal
    length (so offsets/line numbers stay valid) before sentence scanning."""
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    # display + inline math
    text = re.sub(r"\$\$.*?\$\$", blank, text, flags=re.S)
    text = re.sub(r"(?<!\\)\$.*?(?<!\\)\$", blank, text, flags=re.S)
    text = re.sub(r"\\\[.*?\\\]", blank, text, flags=re.S)
    text = re.sub(r"\\\(.*?\\\)", blank, text, flags=re.S)
    # named non-prose environments
    for env in _NONPROSE_ENVS:
        pat = re.compile(r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{"
                         + re.escape(env) + r"\}", re.S)
        text = pat.sub(blank, text)
    return text


def _prose_window(text: str) -> tuple[int, int]:
    """Offsets of the document body (after \\begin{document}, before \\end)."""
    start = 0
    m = re.search(r"\\begin\{document\}", text)
    if m:
        start = m.end()
    end = len(text)
    m = re.search(r"\\end\{document\}", text)
    if m:
        end = m.start()
    return start, end


def _clean_sentence(s: str) -> str:
    """Light de-LaTeX for display: drop a few commands, collapse whitespace."""
    # Drop sectioning/caption commands WITH their brace argument so a heading
    # title ("Introduction") does not bleed into the following claim sentence.
    s = re.sub(r"\\(?:sub){0,2}section\*?\s*\{[^}]*\}", " ", s)
    s = re.sub(r"\\(?:chapter|paragraph|subparagraph|caption|title)\*?\s*\{[^}]*\}",
               " ", s)
    s = re.sub(r"\\(?:label|ref|eqref|cref|Cref|cite[a-z]*)\s*\{[^}]*\}", "", s)
    s = re.sub(r"\\[a-zA-Z@]+\s*\*?", " ", s)
    s = re.sub(r"[{}~]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_claims(tf: TexFile, want_type: str | None, min_conf: str,
                   context: int) -> list[dict]:
    """Return candidate claim records: type(s), sentence, file, line."""
    raw = tf.text
    pstart, pend = _prose_window(raw)
    masked = _mask_nonprose(raw)

    # Split into sentences while keeping ABSOLUTE offsets into `masked`. Masking
    # preserves length and newlines (math/non-prose bodies become equal-length
    # blanks), so an offset into `masked` is the SAME offset into `raw` — we read
    # offsets directly, rather than the fragile raw.find() relocate (which broke
    # when a sentence's masked text did not appear verbatim in raw, e.g. after a
    # \section title). Offsets are bounds into the full `masked`, [pstart, pend).
    claims: list[dict] = []
    sentences: list[tuple[int, str]] = []
    last = pstart
    for m in _SENT_SPLIT.finditer(masked, pstart, pend):
        sentences.append((last, masked[last:m.start() + 1]))
        last = m.end()
    sentences.append((last, masked[last:pend]))

    for i, (off, sent) in enumerate(sentences):
        words = sent.strip()
        if len(words) < 8:
            continue
        matched_types = []
        hits = []
        # Track the offset of the FIRST marker within the sentence so the
        # reported file:line points at the claim itself, not the sentence start
        # (which can be a preceding \section line that merged in for lack of
        # terminal punctuation). Default to the sentence start if none found.
        marker_off = off + (len(sent) - len(sent.lstrip()))
        first_hit_pos = None
        for t, comps in _COMPILED.items():
            if want_type and t != want_type:
                continue
            for c in comps:
                m = c.search(words)
                if m:
                    matched_types.append(t)
                    hits.append(m.group(0).strip())
                    # position of this marker within the original (unstripped)
                    # sentence text, mapped back to an absolute offset
                    lead = len(sent) - len(sent.lstrip())
                    abs_pos = off + lead + m.start()
                    if first_hit_pos is None or abs_pos < first_hit_pos:
                        first_hit_pos = abs_pos
                    break
        if not matched_types:
            continue
        if first_hit_pos is not None:
            marker_off = first_hit_pos
        conf = "high" if HIGH_CONF.search(words) else "medium"
        if min_conf == "high" and conf != "high":
            continue
        clean = _clean_sentence(words)
        if not clean:
            continue
        ctx = ""
        if context:
            lo = max(0, i - context)
            hi = min(len(sentences), i + context + 1)
            ctx = _clean_sentence(" ".join(s for _, s in sentences[lo:hi]))
        src_file, src_line = tf.locate(marker_off)
        claims.append({
            "types": sorted(set(matched_types)),
            "markers": sorted(set(hits)),
            "confidence": conf,
            "sentence": clean,
            "context": ctx,
            "file": src_file,
            "line": src_line,
        })
    return claims


# --------------------------------------------------------------------------- #
# Prose-number vs table-number cross-check
# --------------------------------------------------------------------------- #
# suffix allows LaTeX-escaped percent (\%), a plain %, or a multiplier x/×.
_NUM = re.compile(r"(?<![\w.])(\d{1,4}(?:[.,]\d+)?)(\s*\\?%|\s*[x×])?")


def _numbers(text: str) -> set[str]:
    """Normalized numeric tokens (strip thousands commas; keep %/x suffix)."""
    out = set()
    for m in _NUM.finditer(text):
        val = m.group(1).replace(",", "")
        suf = (m.group(2) or "").strip().lstrip("\\")
        # ignore years and tiny ordinals that are rarely "results"
        try:
            f = float(val)
        except ValueError:
            continue
        if not suf and (1900 <= f <= 2099 or f == int(f) and f < 4):
            continue
        out.add(val + ("%" if suf == "%" else ("x" if suf in ("x", "×") else "")))
    return out


def _table_bodies(raw: str) -> str:
    """Concatenated text of every tabular environment (the table numbers)."""
    bodies = []
    for env in ("tabular", "tabularx", "tabular*", "array"):
        for m in re.finditer(r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{"
                             + re.escape(env) + r"\}", raw, re.S):
            bodies.append(m.group(0))
    return "\n".join(bodies)


def number_crosscheck(tf: TexFile) -> dict:
    """Numbers that appear in prose but NOT in any table (candidate mismatches),
    and a summary. A prose result number with no table match is the classic
    'stale sentence after a table revision' smell — the author reconciles it."""
    raw = tf.text
    masked = _mask_nonprose(raw)
    pstart, pend = _prose_window(masked)
    prose_nums = _numbers(masked[pstart:pend])
    table_nums = _numbers(_table_bodies(raw))
    # only flag prose numbers that look like results: carry % or x, or are
    # non-integer (pure integers in prose are too noisy to cross-check)
    result_like = {n for n in prose_nums
                   if n.endswith("%") or n.endswith("x") or "." in n}
    unmatched = sorted(result_like - {n for n in table_nums} - _suffix_variants(table_nums))
    return {
        "prose_result_numbers": sorted(result_like),
        "table_numbers": sorted(table_nums),
        "prose_numbers_absent_from_tables": unmatched,
    }


def _suffix_variants(nums: set[str]) -> set[str]:
    """Allow a prose '12.0%' to match a table '12' etc. (loose numeric match)."""
    out = set()
    for n in nums:
        core = n.rstrip("%x")
        out.add(core)
        if "." in core:
            out.add(core.rstrip("0").rstrip("."))
    return out


# --------------------------------------------------------------------------- #
def _load(path: str) -> TexFile:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"no such file: {path}")
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = _strip_comments(fh.read())
    text, segments = _resolve_inputs(path, text, seen={os.path.abspath(path)})
    return TexFile(path, text, segments)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Extract candidate claim sentences (novelty / superiority / "
                    "result / generalization) and cross-check prose numbers "
                    "against table numbers, for the verify-claims skill. Finds "
                    "claims; does NOT judge them — the author maps each to "
                    "evidence.",
        epilog="Exit: 0 = nothing flagged; 2 = candidates found (normal/healthy, "
               "needs author triage); 1 = operational failure.",
    )
    ap.add_argument("tex", help="main .tex file (\\input/\\include are followed)")
    ap.add_argument("--type", choices=sorted(TYPES),
                    help="restrict to one claim type")
    ap.add_argument("--numbers", action="store_true",
                    help="only the prose-number vs table-number cross-check")
    ap.add_argument("--context", type=int, default=0, metavar="N",
                    help="include N sentences of surrounding context per claim")
    ap.add_argument("--min-confidence", choices=("medium", "high"),
                    default="medium",
                    help="'high' keeps only strong-signal candidates")
    ap.add_argument("--json", metavar="PATH", nargs="?", const="-",
                    help="write JSON report to PATH (or stdout if no PATH)")
    args = ap.parse_args(argv)

    try:
        tf = _load(args.tex)
    except (FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    cross = number_crosscheck(tf)
    claims = [] if args.numbers else extract_claims(
        tf, args.type, args.min_confidence, args.context)

    report = {
        "tex": args.tex,
        "claims": claims,
        "number_crosscheck": cross,
        "summary": {
            "candidate_claims": len(claims),
            "by_type": {t: sum(1 for c in claims if t in c["types"]) for t in TYPES},
            "prose_numbers_absent_from_tables": len(
                cross["prose_numbers_absent_from_tables"]),
        },
    }

    if args.json is not None:
        out = json.dumps(report, indent=2)
        if args.json == "-":
            print(out)
        else:
            try:
                with open(args.json, "w", encoding="utf-8") as fh:
                    fh.write(out + "\n")
                print(f"wrote {args.json}")
            except OSError as exc:
                print(f"error: cannot write {args.json}: {exc}", file=sys.stderr)
                return 1
    else:
        _print_human(report, args)

    flagged = bool(claims) or bool(cross["prose_numbers_absent_from_tables"])
    return 2 if flagged else 0


def _print_human(report: dict, args) -> None:
    print(f"== verify-claims: candidate-claim audit of {report['tex']} ==")
    print("  (these are candidates a reviewer may attack — map each to evidence;")
    print("   the script does NOT judge whether any claim is true.)")
    s = report["summary"]
    if not args.numbers:
        print(f"\n  {s['candidate_claims']} candidate claim(s) "
              f"[{', '.join(f'{t}:{n}' for t, n in s['by_type'].items() if n)}"
              f"{'none' if not any(s['by_type'].values()) else ''}]:")
        for c in report["claims"]:
            loc = f"{os.path.basename(c['file'])}:{c['line']}"
            tags = "/".join(c["types"]) + f",{c['confidence']}"
            print(f"\n  - [{tags}] {loc}  (markers: {', '.join(c['markers'])})")
            print(f"      {_truncate(c['sentence'], 240)}")
            if c["context"]:
                print(f"      context: {_truncate(c['context'], 280)}")
    cc = report["number_crosscheck"]
    miss = cc["prose_numbers_absent_from_tables"]
    print(f"\n  number cross-check: {len(miss)} prose result-number(s) not found "
          f"in any table")
    if miss:
        print(f"      prose-only numbers (reconcile against tables): "
              f"{', '.join(miss)}")
        print("      a result number in the prose with no matching table cell is "
              "often a")
        print("      stale sentence left behind by a revised table — verify each.")
    print("\n  next: open paper-workspace/review/claims-matrix.md and record, per "
          "claim,")
    print("        its evidence (table/figure/theorem/citation) and status "
          "(SUPPORTED/")
    print("        WEAK/UNSUPPORTED/MISMATCH/SCOPED). The script found them; you "
          "judge them.")


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


if __name__ == "__main__":
    sys.exit(main())
