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
             "recency": "2021-2025",
             "distribution_source": "live"},  # live | family-prior | none
  "format_basis": {"profile_in_window": true,   # did the profile's valid_window
                                                 # cover the target cycle?
                   "cfp_rechecked": true,        # was a fresh CFP check done?
                   "note": ""},                  # how hard constraints were sourced
  "weights": {"evaluation_rigor": 1.5, "contribution_framing": 1.3},  # optional override
  "dimensions": [
    {"key": "section_architecture", "label": "Section architecture",
     "draft_value": "all expected sections present, standard order",
     "exemplar_range": "all winners use this skeleton",
     "band": 9, "realization": "complete",
     "basis": "matches modal SIGSPATIAL research layout"},
    {"key": "figures_tables", "label": "Figure/table conventions",
     "draft_value": "0.9 figs/page, no teaser", "exemplar_range": "n/a",
     "band": 4, "realization": "complete",
     "no_on_family_distribution": true,  # no on-family corpus/family prior:
                                         # scored on presence/absence only, N reduced
     "basis": "no on-family exemplar distribution — scored on teaser presence only"},
    {"key": "evaluation_rigor", "label": "Evaluation rigor signals",
     "draft_value": "3 named baselines, 2 datasets, ablation list, "
                    "matched-budget + 5-seed CI policy; results are [RESULT] slots",
     "exemplar_range": "4-6 baselines, 3 datasets, error bars",
     "band": 6, "realization": "planned",
     "basis": "deferred-but-specified — complete design, full marks once slots filled"},
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

Realization mode (plan vs. executed): each dimension may carry a
`realization` of absent | planned | drafted | complete (default complete).
A planned/absent dimension is scored on the COMPLETENESS and SPECIFICITY of
its design (per the rubric), is CAPPED at PLANNED_BAND_CAP (so it can never
claim the 7-8 "within range" band it hasn't earned), and flips the whole
index label to "plan-conformance" so it is never silently compared against
executed papers. This keeps the honesty rule intact while making the gap read
as "experiments not run", not "design is weak".

On-family distribution honesty: dims 1/5/6/7 must be scored against an
ON-FAMILY exemplar distribution (a live study-exemplars corpus or the venue
family's `exemplar_distribution` prior), never an off-family proxy. A dimension
with no on-family distribution carries `no_on_family_distribution: true`; the
script then disclaims it (does NOT silently treat the band as a true
conformance number) and the corpus block records `distribution_source`
(live | family-prior | none). When source is `none`, the scorecard says
"no on-family exemplar distribution" per the rubric's honesty rule.

Staleness gate: hard format constraints (page limit, columns, mandatory
sections, deadlines) must not be asserted from a year-mismatched profile
without a fresh CFP check. The optional `format_basis` block records whether
the profile's valid_window covered the target cycle and whether the CFP was
re-checked; if a year-mismatched profile was used WITHOUT a recheck, the
script renders a needs-verification warning rather than letting the format
basis pass silently.
"""
import argparse
import json
import sys

DEFAULT_WEIGHTS = {
    "evaluation_rigor": 1.5,
    "contribution_framing": 1.3,
}
CITATION_GATE_CAP = 4.0  # index cannot exceed this while a citation gate is failed
PLANNED_BAND_CAP = 6  # a planned/absent dimension cannot reach the 7-8 "within range" band
# Realization levels, ordered weakest -> fullest.
REALIZATION_LEVELS = ("absent", "planned", "drafted", "complete")
PLAN_LEVELS = ("absent", "planned")  # treated as not-yet-realized for capping/labeling

TEMPLATE = {
    "venue": "sigspatial-2026",
    "corpus": {"n": 8, "basis": "5 best-paper awardees + 3 top-cited",
               "recency": "2021-2025",
               "distribution_source": "live"},  # live | family-prior | none
    "format_basis": {"profile_in_window": True, "cfp_rechecked": True,
                     "note": ""},
    "weights": {},
    "dimensions": [
        {"key": "section_architecture", "label": "Section architecture",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": ""},
        {"key": "contribution_framing", "label": "Contribution framing",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": ""},
        {"key": "evaluation_rigor", "label": "Evaluation rigor signals",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": ""},
        {"key": "reproducibility", "label": "Reproducibility artifacts",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": ""},
        {"key": "citation_integrity", "label": "Claim & citation density / integrity",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": "",
         "citation_gate_failed": False},
        {"key": "abstract_structure", "label": "Abstract structure",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": ""},
        {"key": "figures_tables", "label": "Figure/table conventions",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": ""},
        {"key": "writing_register", "label": "Writing register",
         "draft_value": "", "exemplar_range": "", "band": 0,
         "realization": "complete", "basis": ""},
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
        realization = d.get("realization", "complete")
        if realization not in REALIZATION_LEVELS:
            errs.append(f"{where}: 'realization' must be one of "
                        f"{', '.join(REALIZATION_LEVELS)} (default complete)")
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
    plan_mode = False
    capped_dims = []  # dims whose band was lowered by the planned cap
    off_family_dims = []  # dims scored with NO on-family distribution
    for d in dims:
        realization = d.get("realization", "complete")
        d["realization"] = realization  # normalize for render
        # A planned/absent dimension cannot claim the 7-8 "within range" band:
        # cap its EFFECTIVE band at PLANNED_BAND_CAP. We record the cap rather
        # than mutating the reported band so the table still shows the design score.
        effective_band = d["band"]
        if realization in PLAN_LEVELS:
            plan_mode = True
            if effective_band > PLANNED_BAND_CAP:
                effective_band = PLANNED_BAND_CAP
                capped_dims.append(d["key"])
        d["effective_band"] = effective_band
        if d.get("no_on_family_distribution"):
            off_family_dims.append(d["key"])
        w = weights.get(d["key"], 1.0)
        num += effective_band * w
        den += 10 * w
        if d.get("citation_gate_failed"):
            gate_failed = True
    raw_index = round(10 * num / den, 1) if den else 0.0

    index = min(raw_index, CITATION_GATE_CAP) if gate_failed else raw_index

    # Staleness gate: a hard format constraint asserted from a year-mismatched
    # profile WITHOUT a fresh CFP recheck is not safe. format_basis is optional;
    # when absent we don't warn (no hard-constraint claim is being made here).
    fb = data.get("format_basis") or {}
    format_basis_stale = bool(fb) and (
        fb.get("profile_in_window") is False and not fb.get("cfp_rechecked"))

    # Rank weakest by EFFECTIVE band so capped planned dims surface as fixes too.
    ranked = sorted(dims, key=lambda d: d.get("effective_band", d["band"]))[:3]
    return {
        "index": index,
        "raw_index": raw_index,
        "gate_failed": gate_failed,
        "plan_mode": plan_mode,
        "capped_dims": capped_dims,
        "off_family_dims": off_family_dims,
        "format_basis_stale": format_basis_stale,
        "weakest": ranked,
        "weights": weights,
    }


def render(data: dict, result: dict) -> str:
    corpus = data.get("corpus") or {}
    plan_mode = result.get("plan_mode")
    index_label = "Plan-conformance index" if plan_mode else "Venue-fit index"
    L = []
    L.append(f"# {'Plan-conformance' if plan_mode else 'Venue-fit'} scorecard "
             f"— {data['venue']}\n")
    L.append(f"**{index_label} (conformance): {result['index']}/10** — "
             f"{band_label(result['index'])}.\n")
    if plan_mode:
        L.append("> 📝 PLAN MODE — one or more dimensions are *planned/absent* "
                 "(experiments not yet run). This is a **plan-conformance** index: "
                 "it scores the completeness and specificity of the design and is "
                 "capped on not-yet-realized dimensions. **Do not compare it against "
                 "an executed paper's venue-fit index** — the gap below means "
                 "*experiments not run*, not *design is weak*.\n")
        if result.get("capped_dims"):
            L.append(f"> Capped at {PLANNED_BAND_CAP} (planned, can't claim the 7-8 "
                     f"'within range' band): "
                     f"{', '.join(result['capped_dims'])}.\n")
    if result["gate_failed"]:
        L.append(f"> ⚠️ Citation-integrity gate FAILED — index capped at "
                 f"{CITATION_GATE_CAP} (raw {result['raw_index']}). "
                 f"Fix fabricated/unresolved citations first.\n")
    if result.get("off_family_dims"):
        L.append(f"> ⚠️ No on-family exemplar distribution for: "
                 f"{', '.join(result['off_family_dims'])}. These were scored on "
                 f"presence/absence only (N reduced), NOT against an off-family "
                 f"proxy. Build a live on-family corpus via study-exemplars, or add "
                 f"an `exemplar_distribution` to the venue family profile, to score "
                 f"them properly.\n")
    if result.get("format_basis_stale"):
        fb = data.get("format_basis") or {}
        L.append(f"> ⚠️ Format basis NEEDS VERIFICATION — hard format constraints "
                 f"were sourced from a year-mismatched profile without a fresh CFP "
                 f"check (staleness gate). Re-verify page limit/columns/required "
                 f"sections against the live CFP before relying on them."
                 + (f" Note: {fb['note']}" if fb.get('note') else "") + "\n")
    L.append("> This measures how closely the draft matches the *form* of strong "
             "recent papers at this venue. It is **not** a prediction of "
             "acceptance, a best-paper forecast, or a judgment of scientific "
             "merit.\n")

    L.append("\n## Per-dimension\n")
    L.append("| Dimension | Score | Realization | Your value | Exemplar range | Basis |")
    L.append("|---|---|---|---|---|---|")
    for d in data["dimensions"]:
        realization = d.get("realization", "complete")
        eff = d.get("effective_band", d["band"])
        # Show the design score and, when capped, the effective (post-cap) score.
        score = (f"{d['band']}/10 → {eff}/10 (capped)"
                 if eff != d["band"] else f"{d['band']}/10")
        exemplar = (d.get("exemplar_range", "")
                    or ("*no on-family distribution*"
                        if d.get("no_on_family_distribution") else ""))
        L.append(f"| {d['label']} | {score} | {realization} | "
                 f"{d.get('draft_value','')} | "
                 f"{exemplar} | {d.get('basis','')} |")

    L.append("\n## Top fixes (weakest dimensions first)\n")
    for d in result["weakest"]:
        realization = d.get("realization", "complete")
        eff = d.get("effective_band", d["band"])
        hint = (" — design is specified; run the experiments to lift this"
                if realization in PLAN_LEVELS else "")
        L.append(f"- **{d['label']}** ({eff}/10, {realization}): "
                 f"{d.get('basis','')}{hint}")

    L.append("\n## Corpus basis\n")
    L.append(f"- Exemplars: {corpus.get('n','?')} "
             f"({corpus.get('basis','basis not disclosed')})")
    L.append(f"- Recency window: {corpus.get('recency','unspecified')}")
    src = corpus.get("distribution_source")
    if src:
        src_label = {
            "live": "live on-family corpus (study-exemplars)",
            "family-prior": "venue-family `exemplar_distribution` prior "
                            "(not a live corpus — typically inferred-from-family)",
            "none": "NONE — no on-family exemplar distribution available",
        }.get(src, src)
        L.append(f"- Distribution source: {src_label}")
    if corpus.get("n", 0) and corpus["n"] < 5:
        L.append(f"- ⚠️ Small corpus (n={corpus['n']}): treat scores as indicative only.")

    L.append("\n## Caveats\n")
    if plan_mode:
        L.append("- This is a **plan-conformance** score: planned/absent dimensions "
                 "are graded on design completeness and specificity, not on numbers "
                 "the draft honestly hasn't produced. Deferred `[RESULT]` slots are "
                 "scored as deferred-but-specified (full marks once filled), not as "
                 "run-and-weak. Never compare it against an executed paper's index.")
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
                       "mode": "plan-conformance" if result["plan_mode"]
                               else "venue-fit",
                       "weakest": [d["key"] for d in result["weakest"]]},
                      fh, indent=2)
    label = "plan-conformance" if result["plan_mode"] else "venue-fit"
    flags = []
    if result["gate_failed"]:
        flags.append("CITATION GATE FAILED, capped")
    if result.get("off_family_dims"):
        flags.append(f"no on-family dist: {len(result['off_family_dims'])} dim(s)")
    if result.get("format_basis_stale"):
        flags.append("format basis needs-verification")
    print(f"{label} index {result['index']}/10 "
          f"({'; '.join(flags) if flags else 'no gate'}) "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
