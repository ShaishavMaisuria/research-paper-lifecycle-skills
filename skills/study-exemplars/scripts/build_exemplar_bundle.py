#!/usr/bin/env python3
"""Aggregate per-exemplar measurements into a cached exemplar_distribution block.

Why this exists
---------------
study-exemplars analyzes a venue's strongest papers transiently and then the
file is discarded. The measurable facts it observed (section skeletons,
figure/table counts, abstract lengths, citation density, teaser/badge
presence) are NOT copyrightable expression and ARE worth keeping — they are
the on-family distribution that benchmark-paper scores a draft against.

Without a cache, a downstream skill whose live exemplar fetch is skipped or
rate-limited falls back to a hand-written family description that was never
measured against real papers. This script turns one study session into a
MEASURED `exemplar_distribution:` block (schema: venues/schema.yml) so that
fallback rests on real observed exemplars instead, and stamps provenance
(`measured: true`, `n`, `recency`, `as_of` date) so every score derived from
it can be labelled cache-vs-live.

What it does and does NOT do
----------------------------
- Input is a JSON file of PER-PAPER MEASUREMENTS that the agent recorded from
  its transient reads (rubric dims 3,4,8,9,10) — counts, lengths, section
  names, booleans. Never paper text, abstracts, figures, or pseudocode.
- It aggregates: density bands as [low,high] percentile ranges (never a
  fabricated single point), rates as fractions, the modal section skeleton.
- It validates the input is real measurement (n>=3, no all-equal stub bands,
  every paper carries a verified id) and refuses to emit a confident bundle
  from a thin or fabricated set — it downgrades confidence instead.
- It does NOT fetch anything, invent any number, or write into a venue
  profile. It prints the block to stdout (or --out); the agent pastes it into
  venues/.../<id>.yml under review, replacing any hand-estimated block.

Input schema (papers[]: one object per analyzed exemplar)
---------------------------------------------------------
  {
    "venue": "SIGSPATIAL/GIS",            # free label, for the basis line
    "recency": "2021-2025",               # window the set spans
    "basis": "best-paper awardees + top-cited",
    "source_urls": ["https://...", ...],  # award lists / proceedings indexes
    "papers": [
      {
        "id": "doi:10.1145/...",          # DOI or arXiv id (provenance, required)
        "pages": 12,                      # body page count (>0)
        "refs": 58,                       # reference count
        "figures": 9,                     # figure count
        "tables": 4,                      # table count
        "abstract_words": 187,            # abstract length in words
        "teaser_figure": true,            # page-1 whole-idea figure present?
        "artifact_badge": true,           # artifact/availability badge present?
        "sections": ["Introduction", "Related Work", "Method",
                     "Experiments", "Conclusion"]  # top-level skeleton, in order
      }
    ]
  }

Per-paper fields are optional EXCEPT id; a band is emitted only from papers
that supplied both the numerator and `pages`. Coverage is disclosed per band.

Example
-------
  python3 scripts/build_exemplar_bundle.py measurements.json
  python3 scripts/build_exemplar_bundle.py measurements.json --out block.yml

Exit codes: 0 emitted; 2 bad/insufficient input. Pure stdlib; offline.
This script invents nothing — it only summarizes numbers you measured.
"""
import argparse
import datetime
import json
import sys
from collections import Counter

MIN_PAPERS = 3          # below this, no defensible "convention"
MIN_BAND_COVERAGE = 3   # papers needed to emit a density/length band


def fail(msg: str, code: int = 2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("measurements", metavar="JSON",
                   help="path to the per-paper measurements JSON (see header)")
    p.add_argument("--out", metavar="PATH",
                   help="write the YAML block here instead of stdout")
    p.add_argument("--json", action="store_true",
                   help="emit the aggregated bundle as JSON, not a YAML block")
    return p.parse_args()


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except OSError as e:
        fail(f"cannot read {path}: {e}")
    except ValueError as e:
        fail(f"{path} is not valid JSON: {e}")
    if not isinstance(obj, dict) or not isinstance(obj.get("papers"), list):
        fail("input must be a JSON object with a top-level `papers` array "
             "(see this script's header for the schema)")
    bad = [i for i, pp in enumerate(obj["papers"]) if not isinstance(pp, dict)]
    if bad:
        fail(f"papers at index {bad} are not JSON objects — each exemplar must "
             "be an object of measurements (see this script's header)")
    return obj


def _nums(papers, field):
    """Per-paper values of `field`, paired with the paper for ratio bands."""
    out = []
    for pp in papers:
        v = pp.get(field)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append((pp, float(v)))
    return out


def _percentile_band(values):
    """[p10, p90] rounded to 1 decimal — a robust range, never a single point.

    Uses the 10th/90th percentiles so one outlier paper doesn't blow the band
    out. With few points it degrades gracefully to [min, max]."""
    xs = sorted(values)
    n = len(xs)

    def pct(q):
        if n == 1:
            return xs[0]
        pos = q * (n - 1)
        lo = int(pos)
        frac = pos - lo
        hi = min(lo + 1, n - 1)
        return xs[lo] + (xs[hi] - xs[lo]) * frac

    return [round(pct(0.10), 1), round(pct(0.90), 1)]


def ratio_band(papers, numer_field):
    """Band of (numer_field / pages) across papers that supplied both.

    Returns (band_or_None, coverage_count). Per-page densities are what
    benchmark-paper scores against, so each paper contributes numer/pages."""
    ratios = []
    for pp, num in _nums(papers, numer_field):
        pages = pp.get("pages")
        if isinstance(pages, (int, float)) and not isinstance(pages, bool) and pages > 0:
            ratios.append(num / float(pages))
    if len(ratios) < MIN_BAND_COVERAGE:
        return None, len(ratios)
    return _percentile_band(ratios), len(ratios)


def value_band(papers, field):
    """Band of a raw per-paper quantity (e.g. abstract_words)."""
    vals = [v for _, v in _nums(papers, field)]
    if len(vals) < MIN_BAND_COVERAGE:
        return None, len(vals)
    return [int(round(b)) for b in _percentile_band(vals)], len(vals)


def rate(papers, field):
    """Fraction of papers (that reported the boolean) where field is true."""
    seen = [pp[field] for pp in papers if isinstance(pp.get(field), bool)]
    if not seen:
        return None, 0
    return round(sum(1 for b in seen if b) / len(seen), 2), len(seen)


def modal_sections(papers):
    """The most common top-level skeleton (exact ordered list), with support.

    A skeleton is a "convention" only if at least half the reporting papers
    share it; otherwise we return the most common but flag low agreement."""
    skeletons = [tuple(str(s) for s in pp["sections"]) for pp in papers
                 if isinstance(pp.get("sections"), list) and pp["sections"]]
    if not skeletons:
        return None, 0, 0.0
    counts = Counter(skeletons)
    skel, support = counts.most_common(1)[0]
    return list(skel), support, round(support / len(skeletons), 2)


def validate(obj):
    """Return (problems, stub_fields): a list of measurement-quality problems
    (empty == clean) and the set of input fields that look like a stub."""
    papers = obj["papers"]
    problems = []
    stub_fields = set()
    if len(papers) < MIN_PAPERS:
        problems.append(
            f"only {len(papers)} papers — a convention needs >= {MIN_PAPERS}; "
            "the block will be marked low-confidence")
    missing_id = [i for i, pp in enumerate(papers) if not str(pp.get("id", "")).strip()]
    if missing_id:
        fail(f"papers at index {missing_id} have no `id` — every exemplar must "
             "carry a verified DOI/arXiv id for provenance (no anonymous rows)")
    # Stub detection: identical numbers across all papers signal a hand-filled
    # template rather than real measurement. A stubbed field's band is also
    # suppressed to null in build() — we never emit a fabricated point.
    for f in ("refs", "figures", "tables", "abstract_words", "pages"):
        vals = [v for _, v in _nums(papers, f)]
        if len(vals) >= MIN_PAPERS and len(set(vals)) == 1:
            stub_fields.add(f)
            problems.append(
                f"every paper reports the same `{f}` ({vals[0]}) — looks like a "
                "stub, not measurement; its band is suppressed (null) — "
                "re-measure or drop this field")
    return problems, stub_fields


def build(obj) -> dict:
    papers = obj["papers"]
    problems, stub_fields = validate(obj)

    refs_b, refs_n = ratio_band(papers, "refs")
    figs_b, figs_n = ratio_band(papers, "figures")
    tabs_b, tabs_n = ratio_band(papers, "tables")
    abs_b, abs_n = value_band(papers, "abstract_words")
    teaser, teaser_n = rate(papers, "teaser_figure")
    badge, badge_n = rate(papers, "artifact_badge")
    skel, skel_support, skel_agree = modal_sections(papers)

    # A stubbed field (identical everywhere) is not real measurement — null its
    # band and leave it for a live fetch rather than emit a zero-width [x, x].
    if "refs" in stub_fields:
        refs_b = None
    if "figures" in stub_fields:
        figs_b = None
    if "tables" in stub_fields:
        tabs_b = None
    if "abstract_words" in stub_fields:
        abs_b = None

    confident = len(papers) >= MIN_PAPERS and not problems
    confidence = "measured" if confident else "measured-low-confidence"

    bundle = {
        "n": len(papers),
        "basis": obj.get("basis", "best-paper awardees + top-cited"),
        "recency": obj.get("recency", ""),
        "source_urls": obj.get("source_urls", []),
        "measured": True,                       # vs a hand-estimated block
        "as_of": datetime.date.today().isoformat(),
        "confidence": confidence,
        "refs_per_page": refs_b,
        "figs_per_page": figs_b,
        "tables_per_page": tabs_b,
        "abstract_words": abs_b,
        "teaser_figure_rate": teaser,
        "artifact_badge_rate": badge,
        "modal_sections": skel,
        # Disclosure so a consumer can label every derived score cache-vs-live
        # and know how thin each band is.
        "_coverage": {
            "refs_per_page": refs_n, "figs_per_page": figs_n,
            "tables_per_page": tabs_n, "abstract_words": abs_n,
            "teaser_figure_rate": teaser_n, "artifact_badge_rate": badge_n,
            "modal_sections_support": skel_support,
            "modal_sections_agreement": skel_agree,
        },
        "_problems": problems,
    }
    return bundle


def _yv(v) -> str:
    if v is None:
        return "null  # not enough papers reported this — leave for a live fetch"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ", ".join(_yv(x) for x in v) + "]"
    if isinstance(v, str):
        return v if v else '""'
    return str(v)


def to_yaml_block(b: dict) -> str:
    cov = b["_coverage"]
    lines = [
        "exemplar_distribution:",
        f"  n: {b['n']}",
        f"  basis: {json.dumps(b['basis'])}",
        f"  recency: {json.dumps(b['recency'])}",
        "  source_urls:",
    ]
    for u in b["source_urls"] or []:
        lines.append(f"    - {u}")
    if not b["source_urls"]:
        lines.append("    []  # record the award lists / proceedings indexes used")
    lines += [
        f"  measured: {_yv(b['measured'])}            "
        "# measured from real exemplars, not hand-estimated",
        f"  as_of: {b['as_of']}              "
        "# snapshot date — a consumer labels scores cache-vs-live against this",
        f"  confidence: {b['confidence']}",
        f"  refs_per_page: {_yv(b['refs_per_page'])}"
        f"      # citation-density band (dim 5); from {cov['refs_per_page']} papers",
        f"  figs_per_page: {_yv(b['figs_per_page'])}"
        f"      # figure density (dim 7); from {cov['figs_per_page']} papers",
        f"  tables_per_page: {_yv(b['tables_per_page'])}"
        f"    # table density (dim 7); from {cov['tables_per_page']} papers",
        f"  abstract_words: {_yv(b['abstract_words'])}"
        f"     # observed abstract length (dim 6); from {cov['abstract_words']} papers",
        f"  teaser_figure_rate: {_yv(b['teaser_figure_rate'])}"
        f"   # page-1 teaser fraction (dim 7); from {cov['teaser_figure_rate']} papers",
        f"  artifact_badge_rate: {_yv(b['artifact_badge_rate'])}"
        f"  # artifact-badge fraction (dim 4); from {cov['artifact_badge_rate']} papers",
        "  modal_sections:"
        f"            # most common skeleton (dim 1); "
        f"{cov['modal_sections_support']}/{b['n']} papers agree "
        f"({cov['modal_sections_agreement']:.0%})",
    ]
    for s in b["modal_sections"] or []:
        # Quote so names with a colon/number always parse back as a string
        # (schema: modal_sections is [string]).
        lines.append(f"    - {json.dumps(str(s))}")
    if not b["modal_sections"]:
        lines.append("    []  # no skeleton reported — leave for a live fetch")
    if b["_problems"]:
        lines.append("  # MEASUREMENT WARNINGS — resolve before relying on this block:")
        for pr in b["_problems"]:
            lines.append(f"  #   - {pr}")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    obj = load(args.measurements)
    bundle = build(obj)
    out = (json.dumps(bundle, indent=2) + "\n") if args.json else to_yaml_block(bundle)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out)
        except OSError as e:
            fail(f"cannot write {args.out}: {e}")
        print(f"wrote exemplar_distribution block to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    if bundle["_problems"]:
        print("\nNOTE: measurement warnings above — the block is marked "
              f"{bundle['confidence']}. Add more exemplars or re-measure the "
              "flagged fields before a consumer treats this as a confident "
              "fallback.", file=sys.stderr)


if __name__ == "__main__":
    main()
