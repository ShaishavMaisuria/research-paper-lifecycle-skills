#!/usr/bin/env python3
"""Compute and render a venue-fit conformance scorecard.

Deterministic. Stdlib only. The model extracts features (draft values +
exemplar ranges) into a JSON file; this script scores each dimension against
the conformance bands, applies weights and the citation-integrity gate, and
renders scorecard.md. Keeping the aggregation here stops the model from
eyeballing a number.

Input JSON shape (see --emit-template):
{
  "venue": "sigspatial-2026",
  "corpus": {"n": 8, "basis": "5 best-paper awardees + 3 top-cited",
             "recency": "2021-2025"},
  "weights": {"evaluation_rigor": 1.5, "contribution_framing": 1.3},  # optional override
  "dimensions": [
    {"key": "section_architecture", "label": "Section architecture",
     "draft_value": "all expected sections present, standard order",
     "exemplar_range": "all winners use this skeleton",
     "band": 9, "basis": "matches modal SIGSPATIAL research layout"},
    ...
    {"key": "citation_integrity", "label": "Citation integrity",
     "draft_value": "2 unresolved entries", "exemplar_range": "0 expected",
     "band": 3, "basis": "verify-citations flagged 2 fabricated DOIs",
     "citation_gate_failed": true}
  ]
}

Each dimension carries a 0-10 `band` (assigned by the model per
references/scoring-rubric.md) plus the basis. This script does NOT invent
bands — it validates, weights, gates, and renders them.
"""
import argparse
import json
import sys

DEFAULT_WEIGHTS = {
    "evaluation_rigor": 1.5,
    "contribution_framing": 1.3,
}
CITATION_GATE_CAP = 4.0  # index cannot exceed this while a citation gate is failed

TEMPLATE = {
    "venue": "sigspatial-2026",
    "corpus": {"n": 8, "basis": "5 best-paper awardees + 3 top-cited",
               "recency": "2021-2025"},
    "weights": {},
    "dimensions": [
        {"key": "section_architecture", "label": "Section architecture",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": ""},
        {"key": "contribution_framing", "label": "Contribution framing",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": ""},
        {"key": "evaluation_rigor", "label": "Evaluation rigor signals",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": ""},
        {"key": "reproducibility", "label": "Reproducibility artifacts",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": ""},
        {"key": "citation_integrity", "label": "Claim & citation density / integrity",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": "",
         "citation_gate_failed": False},
        {"key": "abstract_structure", "label": "Abstract structure",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": ""},
        {"key": "figures_tables", "label": "Figure/table conventions",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": ""},
        {"key": "writing_register", "label": "Writing register",
         "draft_value": "", "exemplar_range": "", "band": 0, "basis": ""},
    ],
}

BANDS = [
    (9, "matches or exceeds the exemplar median"),
    (7, "within exemplar range, below median"),
    (5, "just outside exemplar range; reviewers would notice"),
    (3, "clearly below exemplar norms"),
    (0, "absent or far off"),
]


def band_label(score: float) -> str:
    for threshold, label in BANDS:
        if score >= threshold:
            return label
    return BANDS[-1][1]


def validate(data: dict) -> list[str]:
    errs = []
    if not data.get("venue"):
        errs.append("missing 'venue'")
    dims = data.get("dimensions")
    if not isinstance(dims, list) or not dims:
        errs.append("'dimensions' must be a non-empty list")
        return errs
    for i, d in enumerate(dims):
        where = f"dimension[{i}] ({d.get('key', '?')})"
        if not isinstance(d.get("band"), (int, float)) or not 0 <= d["band"] <= 10:
            errs.append(f"{where}: 'band' must be a number 0-10")
        if not d.get("basis"):
            errs.append(f"{where}: 'basis' is required — no bare scores")
    corpus = data.get("corpus") or {}
    if not corpus.get("n"):
        errs.append("corpus.n (number of exemplars) is required for honest disclosure")
    return errs


def compute(data: dict) -> dict:
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(data.get("weights") or {})
    dims = data["dimensions"]

    num = den = 0.0
    gate_failed = False
    for d in dims:
        w = weights.get(d["key"], 1.0)
        num += d["band"] * w
        den += 10 * w
        if d.get("citation_gate_failed"):
            gate_failed = True
    raw_index = round(10 * num / den, 1) if den else 0.0

    index = min(raw_index, CITATION_GATE_CAP) if gate_failed else raw_index

    ranked = sorted(dims, key=lambda d: d["band"])[:3]
    return {
        "index": index,
        "raw_index": raw_index,
        "gate_failed": gate_failed,
        "weakest": ranked,
        "weights": weights,
    }


def render(data: dict, result: dict) -> str:
    corpus = data.get("corpus") or {}
    L = []
    L.append(f"# Venue-fit scorecard — {data['venue']}\n")
    L.append(f"**Venue-fit index (conformance): {result['index']}/10** — "
             f"{band_label(result['index'])}.\n")
    if result["gate_failed"]:
        L.append(f"> ⚠️ Citation-integrity gate FAILED — index capped at "
                 f"{CITATION_GATE_CAP} (raw {result['raw_index']}). "
                 f"Fix fabricated/unresolved citations first.\n")
    L.append("> This measures how closely the draft matches the *form* of strong "
             "recent papers at this venue. It is **not** a prediction of "
             "acceptance, a best-paper forecast, or a judgment of scientific "
             "merit.\n")

    L.append("\n## Per-dimension\n")
    L.append("| Dimension | Score | Your value | Exemplar range | Basis |")
    L.append("|---|---|---|---|---|")
    for d in data["dimensions"]:
        L.append(f"| {d['label']} | {d['band']}/10 | {d.get('draft_value','')} | "
                 f"{d.get('exemplar_range','')} | {d.get('basis','')} |")

    L.append("\n## Top fixes (weakest dimensions first)\n")
    for d in result["weakest"]:
        L.append(f"- **{d['label']}** ({d['band']}/10): {d.get('basis','')}")

    L.append("\n## Corpus basis\n")
    L.append(f"- Exemplars: {corpus.get('n','?')} "
             f"({corpus.get('basis','basis not disclosed')})")
    L.append(f"- Recency window: {corpus.get('recency','unspecified')}")
    if corpus.get("n", 0) and corpus["n"] < 5:
        L.append(f"- ⚠️ Small corpus (n={corpus['n']}): treat scores as indicative only.")

    L.append("\n## Caveats\n")
    L.append("- Conformance to form is not quality of substance — a paper can look "
             "like a winner and still be wrong. This finds gaps to fix; it does not "
             "bless the paper.")
    L.append("- No tool predicts acceptance or awards; novelty, timing, and luck "
             "are not measurable here.")
    L.append("- Use `simulate-reviewers` for content critique and `preflight-check` "
             "for desk-reject defects.")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compute and render a venue-fit conformance scorecard "
                    "from extracted features.")
    ap.add_argument("features", nargs="?",
                    help="path to the features JSON (see --emit-template)")
    ap.add_argument("--venue", help="override/confirm the venue id")
    ap.add_argument("--out", default="scorecard.md",
                    help="output markdown path (default: scorecard.md)")
    ap.add_argument("--json", metavar="PATH",
                    help="also write the computed result as JSON")
    ap.add_argument("--emit-template", action="store_true",
                    help="print a blank features JSON template and exit")
    args = ap.parse_args()

    if args.emit_template:
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if not args.features:
        ap.error("features JSON path required (or use --emit-template)")

    try:
        with open(args.features, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR cannot read/parse {args.features}: {exc}", file=sys.stderr)
        return 1
    if args.venue:
        data["venue"] = args.venue

    errs = validate(data)
    if errs:
        for e in errs:
            print(f"ERROR {e}", file=sys.stderr)
        return 1

    result = compute(data)
    md = render(data, result)
    try:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
    except OSError as exc:
        print(f"ERROR cannot write {args.out}: {exc}", file=sys.stderr)
        return 1
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"venue": data["venue"], **result,
                       "weakest": [d["key"] for d in result["weakest"]]},
                      fh, indent=2)
    print(f"venue-fit index {result['index']}/10 "
          f"({'GATE FAILED, capped' if result['gate_failed'] else 'no gate'}) "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
