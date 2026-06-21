#!/usr/bin/env python3
"""Detect text overlap for an originality / plagiarism / self-plagiarism check.

Deterministic, stdlib only. This is NOT iThenticate/Turnitin: it has no access
to any private publisher corpus. It catches three things honestly:

  1. --against  : verbatim / near-verbatim overlap between a draft and sources
                  YOU provide (your own prior papers, a co-author's draft, a
                  specific suspected source, or papers fetched via fetch-paper).
  2. --self     : internal text recycling — near-duplicate paragraphs within
                  one document (boilerplate copied across sections).
  3. --distinctive : emit the draft's most distinctive long phrases so the
                  model can search them on the web / Semantic Scholar to find
                  matches this script can't see locally.

Method: text is normalized (lowercase, punctuation stripped, whitespace
collapsed) and tokenized to words; overlap is measured with word k-grams
("shingles", default k=8). Matching shingles are merged into contiguous
passages and reported with the matched text and an overlap percentage. k=8
keeps common phrases ("in this paper we present") from being flagged while
catching copied sentences.
"""
import argparse
import re
import sys
from difflib import SequenceMatcher

WORD_RE = re.compile(r"[A-Za-z0-9]+")


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        print(f"ERROR cannot read {path}: {exc}", file=sys.stderr)
        sys.exit(1)
    if path.endswith(".tex"):
        raw = re.sub(r"(?<!\\)%.*", "", raw)
        raw = re.sub(r"\\(cite|ref|label|citep|citet)\{[^}]*\}", " ", raw)
        raw = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", raw)
        raw = raw.replace("{", " ").replace("}", " ")
    return raw


def tokens(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text)]


def shingles(toks: list[str], k: int) -> dict[tuple, int]:
    """Map each k-gram -> first start index in toks."""
    out: dict[tuple, int] = {}
    for i in range(len(toks) - k + 1):
        sh = tuple(toks[i:i + k])
        out.setdefault(sh, i)
    return out


def find_overlaps(draft_toks, source_toks, k):
    """Return (overlap_fraction, list of merged matched passages as strings)."""
    src = set(shingles(source_toks, k))
    if not draft_toks or len(draft_toks) < k:
        return 0.0, []
    matched = [False] * len(draft_toks)
    for i in range(len(draft_toks) - k + 1):
        if tuple(draft_toks[i:i + k]) in src:
            for j in range(i, i + k):
                matched[j] = True
    # merge contiguous matched runs into passages
    passages, run = [], []
    for idx, m in enumerate(matched):
        if m:
            run.append(draft_toks[idx])
        elif run:
            if len(run) >= k:
                passages.append(" ".join(run))
            run = []
    if len(run) >= k:
        passages.append(" ".join(run))
    frac = sum(matched) / len(matched)
    return round(frac, 4), passages


def self_overlap(text: str, min_words: int):
    """Near-duplicate paragraph detection within one document."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(WORD_RE.findall(p)) >= min_words]
    dups = []
    for a in range(len(paras)):
        for b in range(a + 1, len(paras)):
            ratio = SequenceMatcher(None, paras[a].lower(), paras[b].lower()).ratio()
            if ratio >= 0.80:
                dups.append((round(ratio, 2), paras[a][:120], paras[b][:120]))
    return dups


def distinctive_phrases(toks: list[str], n: int, span: int = 10):
    """Pick spread-out long phrases likely to be unique enough to web-search."""
    if len(toks) < span:
        return []
    step = max(1, (len(toks) - span) // max(1, n))
    out = []
    for i in range(0, len(toks) - span + 1, step):
        out.append(" ".join(toks[i:i + span]))
        if len(out) >= n:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Originality / overlap checker (not a publisher-corpus service).")
    ap.add_argument("--draft", required=True, help="the draft to check")
    ap.add_argument("--against", nargs="*", default=[], help="source files to compare against")
    ap.add_argument("--self", action="store_true", help="also check internal text recycling")
    ap.add_argument("--distinctive", type=int, metavar="N", default=0,
                    help="emit N distinctive phrases to search externally")
    ap.add_argument("-k", "--shingle", type=int, default=8, help="k-gram size (default 8)")
    ap.add_argument("--flag-threshold", type=float, default=0.15,
                    help="overlap fraction above which a source is flagged (default 0.15)")
    args = ap.parse_args()

    draft_text = read(args.draft)
    dtoks = tokens(draft_text)
    print(f"originality check — {args.draft} ({len(dtoks)} words, k={args.shingle})\n")

    flagged = 0
    for src in args.against:
        stoks = tokens(read(src))
        frac, passages = find_overlaps(dtoks, stoks, args.shingle)
        status = "FLAG" if frac >= args.flag_threshold else "ok"
        if status == "FLAG":
            flagged += 1
        print(f"[{status}] vs {src}: {frac*100:.1f}% of draft overlaps "
              f"({len(passages)} passage(s) >= {args.shingle} words)")
        for p in passages[:8]:
            snippet = p if len(p) <= 160 else p[:160] + "…"
            print(f"    » {snippet}")
        if len(passages) > 8:
            print(f"    … and {len(passages)-8} more")

    if args.self:
        dups = self_overlap(draft_text, args.shingle)
        print(f"\nself-recycling: {len(dups)} near-duplicate paragraph pair(s) "
              f"(>=80% similar)")
        for ratio, a, b in dups[:6]:
            print(f"    {ratio}: '{a}…' ~ '{b}…'")

    if args.distinctive:
        print(f"\ndistinctive phrases to search externally (web / Semantic Scholar):")
        for p in distinctive_phrases(dtoks, args.distinctive):
            print(f'    "{p}"')

    print(f"\nSummary: {flagged} source(s) flagged at >= {args.flag_threshold*100:.0f}% overlap.")
    print("NOTE: this compares only against the sources you provided and the "
          "phrases it surfaced — it is not a full plagiarism-database scan. "
          "Verify any flag by hand; high overlap with your OWN prior work is "
          "text recycling/self-plagiarism, which many venues still treat as a "
          "violation.")
    return 2 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
