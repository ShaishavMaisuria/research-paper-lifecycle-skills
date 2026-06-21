#!/usr/bin/env python3
"""Extract and compare writing-style signatures.

Deterministic, stdlib only. Two modes:
  --corpus FILES... --out sig.json     build a style signature from text
  --compare draft.json --against A.json [B.json] --out gap.md
                                       diff a draft signature against targets

A "signature" is a set of measurable, substance-free style metrics:
sentence rhythm, hedging/booster density, connective usage, voice, citation
density, and terminology variant choices. It deliberately captures HOW text is
written, never WHAT it claims — so aligning toward a signature cannot change a
result, number, or citation.

Accepts .tex/.md/.txt. For .tex it strips comments, common math, and the
heaviest markup so prose metrics aren't skewed; PDFs should be converted to
text first (the skill handles that).
"""
import argparse
import json
import re
import sys
from collections import Counter

HEDGES = ["may", "might", "could", "would", "suggests", "suggest", "appears",
          "appear", "seems", "seem", "likely", "possibly", "perhaps",
          "potentially", "arguably", "relatively", "somewhat", "generally"]
BOOSTERS = ["clearly", "obviously", "significantly", "substantially", "novel",
            "first", "best", "superior", "outperforms", "state-of-the-art",
            "remarkable", "dramatically", "drastically", "crucial", "critical"]
CONNECTIVES = ["however", "moreover", "furthermore", "therefore", "thus",
               "hence", "consequently", "nevertheless", "nonetheless",
               "additionally", "specifically", "notably", "importantly"]
# terminology variants we normalize/measure (each tuple = competing forms)
TERM_VARIANTS = [
    ("dataset", "data set", "data-set"),
    ("baseline", "base-line", "base line"),
    ("hyperparameter", "hyper-parameter", "hyper parameter"),
    ("state-of-the-art", "state of the art"),
    ("method", "approach", "technique"),
]
LLM_TELLS = ["delve", "leverage", "intricate", "realm", "tapestry",
             "underscore", "pivotal", "showcase", "seamless", "robustly"]


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        print(f"WARN cannot read {path}: {exc}", file=sys.stderr)
        return ""
    if path.endswith(".tex"):
        raw = re.sub(r"(?<!\\)%.*", "", raw)            # strip comments
        raw = re.sub(r"\$[^$]*\$", " MATH ", raw)        # inline math
        raw = re.sub(r"\\begin\{equation\}.*?\\end\{equation\}", " MATH ",
                     raw, flags=re.S)
        raw = re.sub(r"\\(cite|ref|label|citep|citet)\{[^}]*\}", " CITE ", raw)
        raw = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", raw)
        raw = raw.replace("{", " ").replace("}", " ")
    return raw


def sentences(text: str) -> list[str]:
    # naive but stable: split on .!? followed by space+capital/newline
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in parts if len(s.strip()) > 1]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]+", text)


def density(toks_lower: list[str], vocab: list[str], per: int = 1000) -> float:
    if not toks_lower:
        return 0.0
    c = sum(toks_lower.count(v) for v in vocab if " " not in v)
    return round(per * c / len(toks_lower), 2)


def phrase_count(text_lower: str, phrases: list[str]) -> int:
    return sum(text_lower.count(p) for p in phrases if " " in p or "-" in p)


def signature(paths: list[str]) -> dict:
    text = "\n".join(read_text(p) for p in paths)
    low = text.lower()
    sents = sentences(text)
    toks = words(text)
    low_toks = [t.lower() for t in toks]
    n_words = len(toks) or 1
    lens = [len(words(s)) for s in sents] or [0]
    mean_len = sum(lens) / len(lens)
    var_len = sum((x - mean_len) ** 2 for x in lens) / len(lens)

    passive = len(re.findall(
        r"\b(is|are|was|were|been|being|be)\s+\w+(ed|en)\b", low))
    first_person = low.count(" we ") + low.count("we ") * 0  # count token 'we'
    we = low_toks.count("we")
    cites = low.count(" cite ") + len(re.findall(r"\bet al\b", low))

    term_choice = {}
    for variants in TERM_VARIANTS:
        counts = {v: low.count(v) for v in variants}
        if any(counts.values()):
            term_choice[variants[0]] = max(counts, key=counts.get)

    return {
        "files": paths,
        "n_words": n_words,
        "n_sentences": len(sents),
        "sentence_len_mean": round(mean_len, 1),
        "sentence_len_var": round(var_len, 1),
        "hedging_per_1k": density(low_toks, HEDGES),
        "booster_per_1k": density(low_toks, BOOSTERS),
        "connective_per_1k": density(low_toks, CONNECTIVES),
        "connective_top": dict(Counter(
            {c: low_toks.count(c) for c in CONNECTIVES if low_toks.count(c)}
        ).most_common(5)),
        "passive_per_1k": round(1000 * passive / n_words, 2),
        "we_per_1k": round(1000 * we / n_words, 2),
        "citation_per_1k": round(1000 * cites / n_words, 2),
        "llm_tells_per_1k": density(low_toks, LLM_TELLS),
        "terminology_choice": term_choice,
    }


NUMERIC = [
    ("sentence_len_mean", "mean sentence length (words)", 3.0),
    ("sentence_len_var", "sentence-length variance", 30.0),
    ("hedging_per_1k", "hedging per 1k words", 2.0),
    ("booster_per_1k", "boosters per 1k words", 2.0),
    ("connective_per_1k", "connectives per 1k words", 3.0),
    ("passive_per_1k", "passive voice per 1k words", 5.0),
    ("we_per_1k", "first-person 'we' per 1k words", 3.0),
    ("citation_per_1k", "citation density per 1k words", 4.0),
    ("llm_tells_per_1k", "LLM-tell words per 1k words", 0.5),
]


def compare(draft: dict, targets: list[tuple[str, dict]]) -> str:
    L = ["# Style gap\n",
         f"Draft: {', '.join(draft.get('files', []))} "
         f"({draft.get('n_words','?')} words)\n"]
    for name, tgt in targets:
        L.append(f"\n## vs {name}\n")
        L.append("| Metric | Draft | Target | Gap | Note |")
        L.append("|---|---|---|---|---|")
        for key, label, tol in NUMERIC:
            d = draft.get(key, 0)
            t = tgt.get(key, 0)
            gap = round(d - t, 2)
            flag = "" if abs(gap) <= tol else ("↑ higher" if gap > 0 else "↓ lower")
            note = f"within tolerance (±{tol})" if not flag \
                else f"draft is {flag.split()[1]} than target"
            L.append(f"| {label} | {d} | {t} | {gap:+} | {note} |")
        # terminology divergence
        dt, tt = draft.get("terminology_choice", {}), tgt.get("terminology_choice", {})
        diffs = [f"{k}: draft '{dt[k]}' vs target '{tt[k]}'"
                 for k in tt if k in dt and dt[k] != tt[k]]
        if diffs:
            L.append("\n**Terminology to reconcile:** " + "; ".join(diffs))
        # connective habits
        if tgt.get("connective_top"):
            L.append(f"\n**Target's favored connectives:** "
                     f"{', '.join(tgt['connective_top'])}")
    L.append("\n\n> Gaps are suggestions, not mandates. Align wording only — "
             "never change a number, result, claim, or citation. Author-vs-"
             "venue conflicts must be surfaced, not silently resolved.")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract/compare writing-style signatures.")
    ap.add_argument("--corpus", nargs="+", help="text files to profile")
    ap.add_argument("--out", help="output path (.json for --corpus, .md for --compare)")
    ap.add_argument("--compare", metavar="DRAFT_JSON", help="draft signature to compare")
    ap.add_argument("--against", nargs="+", metavar="SIG_JSON",
                    help="one or two target signature JSONs (author.json venue.json)")
    args = ap.parse_args()

    if args.compare:
        if not args.against:
            ap.error("--compare requires --against")
        try:
            draft = json.load(open(args.compare, encoding="utf-8"))
            targets = []
            for p in args.against:
                name = "author voice" if "author" in p.lower() \
                    else "venue register" if "venue" in p.lower() else p
                targets.append((name, json.load(open(p, encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        md = compare(draft, targets)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(md)
            print(f"wrote {args.out}")
        else:
            print(md)
        return 0

    if args.corpus:
        sig = signature(args.corpus)
        out = json.dumps(sig, indent=2)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(out)
            print(f"wrote signature for {sig['n_words']} words -> {args.out}")
        else:
            print(out)
        return 0

    ap.error("provide --corpus FILES (to profile) or --compare/--against (to diff)")


if __name__ == "__main__":
    sys.exit(main())
