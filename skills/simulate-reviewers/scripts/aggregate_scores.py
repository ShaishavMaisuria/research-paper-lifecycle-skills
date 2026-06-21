#!/usr/bin/env python3
"""Aggregate simulated reviewer scores into a decision-risk report — stdlib only.

Takes the filled scores.json produced from review_form.py's template
(per-reviewer overall score + confidence + rubric subscores) and computes:

- plain and confidence-weighted mean overall score
- normalized distance from the venue's borderline threshold
- reviewer-disagreement and champion/detractor flags
- per-dimension rubric means and the dimensions dragging the score down
- a decision-risk band: likely-reject | borderline-reject |
  borderline-accept | likely-accept

Deterministic, offline. The output is a SIMULATION readout, never a
prediction of the real review outcome.

Usage:
    python3 aggregate_scores.py scores.json [--json]
    python3 aggregate_scores.py --example     # print a sample input file

Exit codes: 0 ok, 2 invalid input / missing file.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

EXAMPLE = {
    "scale": {"min": 1, "max": 10, "borderline_threshold": 6},
    "rubric_scale": {"min": 1, "max": 5},
    "reviews": [
        {
            "id": "R1",
            "persona": "The Methods Purist",
            "overall": 5,
            "confidence": 4,
            "scores": {"novelty": 3, "soundness": 2, "reproducibility": 3, "clarity": 4},
        },
        {
            "id": "R2",
            "persona": "The Empirical Skeptic",
            "overall": 4,
            "confidence": 5,
            "scores": {"novelty": 3, "soundness": 2, "reproducibility": 2, "clarity": 3},
        },
        {
            "id": "R3",
            "persona": "The Overloaded Skimmer",
            "overall": 6,
            "confidence": 2,
            "scores": {"novelty": 4, "soundness": 3, "reproducibility": 3, "clarity": 4},
        },
        {
            "id": "R4",
            "persona": "The Adjacent-Field Expert",
            "overall": 5,
            "confidence": 4,
            "scores": {"novelty": 2, "soundness": 3, "reproducibility": 3, "clarity": 4},
        },
    ],
}


class InputError(Exception):
    """Invalid scores file; message is user-facing."""


def _num(x, what):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise InputError(f"{what} must be a number, got {x!r}")
    return float(x)


def load_scores(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.is_file():
        raise InputError(f"scores file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"{p}: not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise InputError(f"{p}: top level must be an object")

    scale = data.get("scale")
    if not isinstance(scale, dict):
        raise InputError("missing 'scale' object with min/max/borderline_threshold")
    smin = _num(scale.get("min"), "scale.min")
    smax = _num(scale.get("max"), "scale.max")
    thr = _num(scale.get("borderline_threshold"), "scale.borderline_threshold")
    if not (smin < smax):
        raise InputError(f"scale.min ({smin}) must be < scale.max ({smax})")
    if not (smin <= thr <= smax):
        raise InputError(f"borderline_threshold {thr} outside scale [{smin}, {smax}]")

    reviews = data.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise InputError("'reviews' must be a non-empty list")
    for i, r in enumerate(reviews):
        if not isinstance(r, dict):
            raise InputError(f"reviews[{i}] must be an object")
        ov = _num(r.get("overall"), f"reviews[{i}].overall")
        if not (smin <= ov <= smax):
            raise InputError(
                f"reviews[{i}].overall = {ov} outside scale [{smin}, {smax}]"
            )
        if r.get("confidence") is not None:
            _num(r.get("confidence"), f"reviews[{i}].confidence")
        scores = r.get("scores") or {}
        if not isinstance(scores, dict):
            raise InputError(f"reviews[{i}].scores must be an object")
        for dim, val in scores.items():
            if val is not None:
                _num(val, f"reviews[{i}].scores.{dim}")
    return data


def aggregate(data: dict) -> dict:
    scale = data["scale"]
    smin, smax = float(scale["min"]), float(scale["max"])
    thr = float(scale["borderline_threshold"])
    span = smax - smin
    reviews = data["reviews"]

    overalls = [float(r["overall"]) for r in reviews]
    confs = [float(r.get("confidence") or 3.0) for r in reviews]
    mean = sum(overalls) / len(overalls)
    wmean = sum(o * c for o, c in zip(overalls, confs)) / sum(confs)
    spread = max(overalls) - min(overalls)

    norm = lambda x: (x - smin) / span  # noqa: E731
    delta = norm(wmean) - norm(thr)
    disagreement = spread >= 0.3 * span
    champion = any(o >= thr + 0.2 * span for o in overalls)
    detractor = any(o <= thr - 0.2 * span for o in overalls)

    if delta < -0.15:
        band = "likely-reject"
    elif delta < 0:
        band = "borderline-reject"
    elif delta < 0.10:
        band = "borderline-accept"
    else:
        band = "likely-accept"

    flags: list[str] = []
    if len(reviews) < 3:
        flags.append(
            f"only {len(reviews)} review(s) — real panels have 3+; treat the band as noisy"
        )
    if disagreement:
        flags.append(
            f"high reviewer disagreement (spread {spread:g} on a {span:g}-point span)"
        )
    if band == "borderline-accept" and disagreement and not champion:
        band = "borderline-reject"
        flags.append(
            "downgraded borderline-accept -> borderline-reject: at borderline, "
            "score spreads without a champion usually resolve downward in the "
            "PC discussion"
        )
    if champion:
        flags.append("a champion reviewer is present (scores well above threshold)")
    if detractor:
        flags.append(
            "a strong detractor is present (scores well below threshold) — "
            "their core objection must be rebuttal-proof"
        )

    # Rubric dimensions
    rubric = data.get("rubric_scale") or {"min": 1, "max": 5}
    rmin = float(rubric.get("min", 1))
    rmax = float(rubric.get("max", 5))
    rmid = (rmin + rmax) / 2.0
    dim_values: dict[str, list[float]] = {}
    for r in reviews:
        for dim, val in (r.get("scores") or {}).items():
            if val is not None:
                dim_values.setdefault(dim, []).append(float(val))
    dim_means = {d: sum(v) / len(v) for d, v in sorted(dim_values.items())}
    drag = [d for d, m in dim_means.items() if m < rmid]
    drag.sort(key=lambda d: dim_means[d])

    return {
        "n_reviews": len(reviews),
        "scale": {"min": smin, "max": smax, "borderline_threshold": thr},
        "mean_overall": round(mean, 2),
        "confidence_weighted_mean": round(wmean, 2),
        "spread": round(spread, 2),
        "normalized_delta_from_threshold": round(delta, 3),
        "reviewer_disagreement": disagreement,
        "champion_present": champion,
        "strong_detractor_present": detractor,
        "decision_risk": band,
        "rubric_means": {d: round(m, 2) for d, m in dim_means.items()},
        "drag_dimensions": drag,
        "flags": flags,
        "disclaimer": (
            "Simulated-panel readout only — not a prediction of the real "
            "review outcome."
        ),
    }


def render_text(rep: dict) -> str:
    s = rep["scale"]
    lines = [
        "Simulated-panel score aggregation",
        "=" * 40,
        f"reviews:            {rep['n_reviews']}",
        f"scale:              {s['min']:g}..{s['max']:g} "
        f"(borderline threshold {s['borderline_threshold']:g})",
        f"mean overall:       {rep['mean_overall']}",
        f"conf-weighted mean: {rep['confidence_weighted_mean']}",
        f"spread:             {rep['spread']}",
        f"delta vs threshold: {rep['normalized_delta_from_threshold']:+} (normalized)",
        "",
        f"DECISION RISK:      {rep['decision_risk'].upper()}",
        "",
    ]
    if rep["rubric_means"]:
        lines.append("rubric dimension means:")
        for d, m in rep["rubric_means"].items():
            mark = "  <-- drags the score" if d in rep["drag_dimensions"] else ""
            lines.append(f"  {d:<16} {m}{mark}")
        lines.append("")
    if rep["flags"]:
        lines.append("flags:")
        for f in rep["flags"]:
            lines.append(f"  - {f}")
        lines.append("")
    lines.append(rep["disclaimer"])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Aggregate simulated reviewer scores (scores.json from "
            "review_form.py's template) into a decision-risk report: "
            "confidence-weighted mean, disagreement/champion flags, drag "
            "dimensions, and a likely/borderline accept-reject band. "
            "Deterministic and offline; the result is a simulation readout, "
            "not a prediction."
        )
    )
    ap.add_argument("scores", nargs="?", help="path to the filled scores.json")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument(
        "--example",
        action="store_true",
        help="print a valid example scores.json and exit",
    )
    args = ap.parse_args()
    if args.example:
        json.dump(EXAMPLE, sys.stdout, indent=2)
        print()
        return 0
    if not args.scores:
        print("error: missing scores.json path (or use --example)", file=sys.stderr)
        return 2
    try:
        data = load_scores(args.scores)
        report = aggregate(data)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
