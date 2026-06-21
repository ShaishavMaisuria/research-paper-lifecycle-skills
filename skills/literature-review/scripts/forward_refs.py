#!/usr/bin/env python3
"""Forward-reference reconciliation gate. Python 3 stdlib only, no network.

A draft (review.md) or a related-work plan often *names* methods, baselines,
and backbones in prose -- "we extend X", "compared against Y and Z", "built on
the W backbone" -- as slots to be filled later. A common failure is that those
named works never make it into the corpus: the prose cites them by name but no
verified reference backs them, silently breaking the citation chain.

This script closes that loop. It:
  1. extracts candidate method/baseline/backbone NAMES from the draft/plan,
  2. diffs them against the corpus (titles + keys of included papers),
  3. emits the unresolved names as a retrieval WORKLIST -- each one a name to
     run back through find-papers (search -> screen -> fetch -> verify) before
     the corpus is declared complete.

It is a COPILOT, not an oracle: name extraction is heuristic, so the output is
a worklist for a human to act on, never an automatic add. It makes NO network
calls and never invents a citation.

Extraction signals (all generic, no hardcoded venue or paper):
  - capitalized short tokens / acronyms that read like system or model names
    (GAT, HGT, BERT-Large, GraphSAGE), especially in baseline/backbone context
  - names introduced by role cues ("we extend", "baseline", "backbone",
    "compared (against|to|with)", "based on", "built on", "fine-tune(d)")
  - explicit unresolved slots: <NAME>, [NAME], {{NAME}}, TODO:cite NAME

A candidate is considered RESOLVED if its normalized form matches (substring,
either direction) a cite key or an included paper's title in the corpus, or if
it is already cited as [@key]/\\cite{key} for a key in the corpus.

Usage:
  python3 forward_refs.py review.md --corpus corpus.json
  python3 forward_refs.py review.md plan.md --corpus corpus.json --json wl.json
  python3 forward_refs.py review.md --corpus corpus.json --strict   # exit 1 if any unresolved

Exit codes: 0 = no unresolved names (or warn-only) | 1 = unresolved names with
--strict, or usage/data error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Role cues that, when near a capitalized token, mark it as a method/baseline/
# backbone the draft leans on. Generic English research-writing vocabulary.
ROLE_CUES = re.compile(
    r"\b("
    r"baselines?|backbones?|backbone of|"
    r"we\s+(?:extend|build\s+on|adopt|reuse|adapt|fine-?tune)|"
    r"built?\s+on(?:\s+top\s+of)?|based\s+on|on\s+top\s+of|"
    r"compared?\s+(?:against|to|with)|comparison\s+with|"
    r"outperforms?|improves?\s+(?:over|upon)|"
    r"variant\s+of|instance\s+of|state[- ]of[- ]the[- ]art"
    r")\b",
    re.IGNORECASE,
)

# Explicit unresolved-slot markers a writer leaves behind.
SLOT_RE = re.compile(
    r"<([A-Za-z][\w .+/-]{1,40})>"
    r"|\bTODO[:\s]+cite\s+([A-Za-z][\w .+/-]{1,40})"
    r"|\{\{\s*([A-Za-z][\w .+/-]{1,40})\s*\}\}",
)

# A "name-shaped" token: an acronym (GAT, HGT, RGCN), CamelCase (GraphSAGE,
# PGExplainer), or Cap-with-digits / hyphenated model name (BERT-Large, GPT-4,
# R-GCN). Deliberately NOT plain Title-Case English words (those are caught
# only when a role cue is adjacent, to keep noise down).
NAME_TOKEN = re.compile(
    r"\b("
    r"[A-Z]{2,}(?:[A-Z0-9]|-[A-Za-z0-9]+)*"          # ACRONYM, R-GCN, GPT-4
    r"|[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+"                # CamelCase: GraphSAGE
    r"|[A-Z][A-Za-z]*\d[\w-]*"                        # Word with a digit
    r")\b"
)

# Pandoc / LaTeX citation forms, so already-cited keys count as resolved.
PANDOC_KEY_RE = re.compile(r"@([A-Za-z0-9][A-Za-z0-9_:.#$%&+?<>~/-]*)")
LATEX_CITE_RE = re.compile(r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{([^}]*)\}")

# Common acronyms that are field jargon, not citable systems -- skip to cut
# noise. Generic across CS/ML writing; extend per-project if needed.
STOPWORDS = {
    "GNN", "GNNS", "CNN", "CNNS", "RNN", "RNNS", "MLP", "MLPS", "GPU", "GPUS",
    "CPU", "API", "APIS", "SOTA", "AI", "ML", "DL", "NLP", "CV", "IID", "OOD",
    "SGD", "ADAM", "RELU", "PCA", "SVD", "KNN", "AUC", "ROC", "PR", "MAE",
    "RMSE", "MSE", "F1", "AP", "MAP", "NDCG", "DOI", "URL", "PDF", "HTML",
    "JSON", "YAML", "CSV", "TODO", "FIXME", "XAI", "FAQ", "RQ", "I", "A",
}


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def load_corpus(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        fail(f"corpus not found: {path}")
    try:
        corpus = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        fail(f"{path} is not valid JSON: {e}")
    if not isinstance(corpus.get("papers"), dict):
        fail(f"{path} has no 'papers' map -- not a literature-review corpus")
    return corpus


def corpus_index(corpus: dict):
    """Build resolution material: normalized keys and included-paper title
    tokens. Returns (norm_keys, title_norms) where title_norms is a list of
    normalized title strings for substring matching."""
    norm_keys = set()
    title_norms = []
    for key, rec in corpus["papers"].items():
        norm_keys.add(normalize(key))
        if rec.get("status", {}).get("screened") == "included":
            t = normalize(rec.get("title", ""))
            if t:
                title_norms.append(t)
    return norm_keys, title_norms


def cited_keys(text: str) -> set[str]:
    keys = set()
    for m in PANDOC_KEY_RE.findall(text):
        keys.add(normalize(m))
    for group in LATEX_CITE_RE.findall(text):
        for k in group.split(","):
            if k.strip():
                keys.add(normalize(k.strip()))
    return keys


def extract_candidates(text: str):
    """Return {name: [line numbers]} for name-shaped tokens that either sit
    near a role cue or appear as an explicit unresolved slot."""
    found: dict[str, list[int]] = {}

    def record(name: str, lineno: int) -> None:
        name = name.strip()
        if not name or name.upper() in STOPWORDS:
            return
        # require at least one letter and a minimum of two chars overall
        if len(name) < 2 or not re.search(r"[A-Za-z]", name):
            return
        found.setdefault(name, [])
        if lineno not in found[name]:
            found[name].append(lineno)

    for i, line in enumerate(text.splitlines(), 1):
        # explicit slots are always candidates
        for groups in SLOT_RE.findall(line):
            for g in groups:
                if g:
                    record(g, i)
        # name-shaped tokens only when a role cue is on the same line
        if ROLE_CUES.search(line):
            for tok in NAME_TOKEN.findall(line):
                record(tok, i)
    return found


def is_resolved(name: str, norm_keys, title_norms, cites) -> bool:
    n = normalize(name)
    if not n:
        return True  # nothing to resolve
    if n in cites or n in norm_keys:
        return True
    for nk in norm_keys:
        if len(n) >= 3 and (n in nk or nk in n):
            return True
    for t in title_norms:
        if len(n) >= 3 and n in t:
            return True
    return False


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("docs", nargs="+",
                   help="draft and/or plan markdown files to scan")
    p.add_argument("--corpus", required=True,
                   help="corpus.json the names must reconcile against")
    p.add_argument("--strict", action="store_true",
                   help="exit 1 when any name is unresolved (default: warn)")
    p.add_argument("--json", metavar="PATH",
                   help="also write the worklist as JSON")
    args = p.parse_args()

    corpus = load_corpus(args.corpus)
    norm_keys, title_norms = corpus_index(corpus)

    all_text = []
    candidates: dict[str, list[int]] = {}
    for doc in args.docs:
        path = Path(doc)
        if not path.exists():
            fail(f"document not found: {doc}")
        t = path.read_text(encoding="utf-8")
        all_text.append(t)
        for name, lines in extract_candidates(t).items():
            tagged = [f"{path.name}:{ln}" for ln in lines]
            candidates.setdefault(name, []).extend(tagged)

    cites = cited_keys("\n".join(all_text))

    unresolved = {
        name: locs for name, locs in sorted(candidates.items())
        if not is_resolved(name, norm_keys, title_norms, cites)
    }

    print(f"forward_refs: scanned {len(args.docs)} document(s) against "
          f"{args.corpus}")
    print(f"  {len(candidates)} candidate method/baseline/backbone names found, "
          f"{len(unresolved)} unresolved")
    if unresolved:
        print("\nRETRIEVAL WORKLIST -- each name should be run back through "
              "find-papers")
        print("(search -> screen -> fetch -> extract -> verify) before the "
              "corpus is final:")
        for name, locs in unresolved.items():
            where = ", ".join(locs[:4]) + (" ..." if len(locs) > 4 else "")
            print(f"  [ ] {name:<24} named at {where}")
        print("\nIf a name is NOT a citable work (your own system, a dataset, "
              "a metric), ignore it -- this list is a prompt, not an order.")
    else:
        print("  all named methods/baselines/backbones reconcile to the "
              "corpus.")

    if args.json:
        try:
            Path(args.json).write_text(
                json.dumps(
                    {"unresolved": unresolved,
                     "all_candidates": {k: v for k, v in sorted(candidates.items())}},
                    indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"\nworklist written to {args.json}")
        except OSError as e:
            fail(f"could not write {args.json}: {e}")

    if unresolved and args.strict:
        print(f"\nRESULT: FAIL ({len(unresolved)} unresolved names)")
        sys.exit(1)
    print(f"\nRESULT: PASS ({len(unresolved)} unresolved names, warn-only)")


if __name__ == "__main__":
    main()
