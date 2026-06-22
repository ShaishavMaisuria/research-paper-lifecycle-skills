#!/usr/bin/env python3
"""Check Related Work cluster coverage against the paper's CLAIMED scope. Offline.

The failure this guards against: a Related Work outline built only from
whatever find-papers happened to return. The retrieved corpus positions the
paper confidently against retrieved-but-peripheral work while leaving a
structural hole exactly where the paper lives — a missing direct-competitor
cluster, or a whole expected sub-area with zero citations, shipped silently as
an author to-do instead of being routed back to retrieval.

This script makes the coverage gate DETERMINISTIC. You declare the clusters
the paper's OWN claimed scope requires (one direct-prior-approach cluster per
contribution/sub-task, plus any canonical lineage a reviewer expects), tag
each with the verified references assigned to it, and the script reports:

  * EMPTY clusters (zero verified refs)               -> FAIL  (blocking)
  * THIN clusters (below the per-cluster citation floor, default 2) -> WARN
  * clusters resting on a single citation                          -> WARN
  * a ready-to-paste second-pass retrieval worklist for find-papers,
    targeting exactly the empty/thin clusters (not a vague author to-do).

PRECISION, NOT JUST RECALL. The floor is a RECALL gate: it asks "does each
required cluster have >= N refs?". On its own it silently rewards PADDING a
thin cluster with plausible-but-uncited works (a recurring failure: clusters
met the floor only via speculative anchors, inflating false positives). To
keep precision visible, refs may be tagged by evidence tier so a cluster that
clears the floor with confirmed cites is distinguishable from one that clears
it only with speculative fillers. Mark a ref's tier with a suffix on the key:

    li2018deep            # untagged -> treated as the default tier 'cited'
    smith2023!graph       # '!graph'  -> speculative citation-graph neighbor
    jones2024!keyword     # '!keyword'-> surfaced by keyword search only
    doe2022!heuristic     # '!heuristic' -> 'a strong paper would cite this'

Recognized tiers (case-insensitive), in descending confidence:
    cited      the paper is known/confirmed to cite it (default; counts toward
               the floor AND the precision-confident count)
    graph      a citation-graph edge (co-citation) suggests it — plausible
    keyword    a keyword/topic search surfaced it — plausible
    heuristic  added on a 'a strong paper would cite these' hunch — weakest

Only `cited`-tier refs count toward the per-cluster FLOOR. Speculative-tier
refs are reported (so they are auditable and prunable) but a cluster resting
ONLY on speculative refs is treated as THIN — it cannot satisfy the floor by
padding. The report prints a per-cluster confirmed/speculative split and an
overall precision estimate (confirmed / total). Heuristic-only additions are
capped (default 2 across the whole plan, --heuristic-cap) so the core set
stays scope-justified. Tiers are optional: an all-untagged plan behaves
exactly as before, so existing plans keep working.

It enforces NOTHING about a specific venue or paper: you supply the required
clusters (derived from the brief), the script only checks the floor and emits
the worklist. It never invents a cluster, a reference, or a search query.

Input is a small JSON or YAML-ish plan file (stdlib only — a minimal block
parser, no PyYAML dependency). Schema (JSON shown; the lightweight text form
is documented in --help):

  {
    "floor": 2,                       # optional; per-cluster citation floor
    "venue_family": "neurips-style",  # optional; only echoed into the worklist
    "clusters": [
      {
        "name": "learned trajectory similarity",
        "required_by": "Contribution 1 (sub-trajectory index)",
        "kind": "direct-prior-approach",   # or "foundational-lineage" / "adjacent"
        "refs": ["li2018deep", "yao2019computing"],   # VERIFIED cite keys only
        "expected": true                # default true; a cluster a reviewer
                                         # would fault as missing. Only expected
                                         # clusters drive the blocking gate —
                                         # set false for an optional adjacent
                                         # area you track but won't block on.
      },
      ...
    ]
  }

A reference counts toward the floor only if it is a non-empty cite key. The
script does NOT verify the keys resolve — chain it after audit_bib.py /
verify-citations, which is where reference reality is established. Here a key
is a placeholder for "a verified reference assigned to this cluster".

Exit codes: 0 = every required cluster meets the floor; 3 = at least one
EMPTY required cluster (blocking gap — route to find-papers before drafting);
2 = bad input.

Examples:
  python3 scripts/check_coverage.py plan.json
  python3 scripts/check_coverage.py plan.txt --floor 2 --json
"""
import argparse
import json
import re
import sys


def fail(msg: str, code: int = 2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Lightweight text plan format (one cluster per block, blank line "
            "between blocks; '#' comments ignored):\n\n"
            "  floor: 2\n"
            "  venue_family: neurips-style\n\n"
            "  name: learned trajectory similarity\n"
            "  required_by: Contribution 1\n"
            "  kind: direct-prior-approach\n"
            "  expected: yes\n"
            "  refs: li2018deep, yao2019computing\n\n"
            "  name: covariate-shift conformal prediction\n"
            "  required_by: Contribution 2\n"
            "  kind: foundational-lineage\n"
            "  expected: yes\n"
            "  refs:\n"   # an empty refs value -> blocking EMPTY cluster
        ),
    )
    p.add_argument("plan", help="cluster plan file (.json, or the text form; "
                                "see --help)")
    p.add_argument("--floor", type=int, default=None,
                   help="per-cluster CONFIRMED-citation floor (default: from "
                        "the plan's `floor`, else 2). Only 'cited'-tier refs "
                        "count toward it; clusters below this WARN; clusters "
                        "with zero confirmed cites FAIL.")
    p.add_argument("--heuristic-cap", type=int, default=None,
                   help="max heuristic-tier ('key!heuristic') refs allowed "
                        "across the whole plan (default: from the plan's "
                        "`heuristic_cap`, else 2). Above this, WARN so the core "
                        "set stays scope-justified instead of hunch-padded.")
    p.add_argument("--json", action="store_true",
                   help="emit findings as JSON instead of a report")
    return p.parse_args()


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        fail(f"cannot read {path}: {e}")
    raise AssertionError("unreachable")


# Evidence tiers in descending confidence. Only CITED counts toward the floor.
TIER_ALIASES = {
    "cited": "cited", "confirmed": "cited", "core": "cited",
    "graph": "graph", "cocitation": "graph", "co-citation": "graph",
    "keyword": "keyword", "topic": "keyword", "search": "keyword",
    "heuristic": "heuristic", "guess": "heuristic", "speculative": "heuristic",
}
CONFIRMED_TIER = "cited"
SPECULATIVE_TIERS = ("graph", "keyword", "heuristic")


def split_tier(key: str):
    """Split a 'key!tier' marker into (clean_key, tier).

    Untagged keys default to the CITED tier so existing plans are unchanged.
    An unrecognized tier is preserved verbatim and treated as speculative
    (it does not count toward the floor) — never silently promoted to cited.
    """
    raw = str(key).strip().strip(",")
    if "!" in raw:
        base, marker = raw.split("!", 1)
        base = base.strip()
        tier = TIER_ALIASES.get(marker.strip().lower())
        if tier is None:
            # unknown marker: keep it visible, treat as speculative
            return base, marker.strip().lower() or "heuristic"
        return base, tier
    return raw, CONFIRMED_TIER


def _raw_refs(val) -> list:
    """Split a refs value into raw tokens, PRESERVING any '!tier' markers.

    Used by the text-plan parser so tier markers survive into evaluate().
    """
    if val is None:
        return []
    items = val if isinstance(val, list) else re.split(r"[,\s]+", str(val))
    out, seen = [], set()
    for it in items:
        k = str(it).strip().strip(",")
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
    return out


def _as_tiered_refs(val) -> list:
    """Normalize a refs value to [(key, tier), ...], deduped on the clean key.

    Accepts a list or a comma/space-separated string. Tier markers ('key!graph')
    are parsed via split_tier(); untagged keys default to the CITED tier. Empty
    keys are dropped.
    """
    if val is None:
        return []
    if isinstance(val, list):
        items = val
    else:
        items = re.split(r"[,\s]+", str(val))
    out, seen = [], set()
    for it in items:
        k = str(it).strip().strip(",")
        if not k:
            continue
        key, tier = split_tier(k)
        if key and key.lower() not in seen:
            seen.add(key.lower())
            out.append((key, tier))
    return out


def _truthy(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("yes", "true", "1", "y")


def parse_text_plan(text: str) -> dict:
    """Parse the lightweight block format into the same dict JSON would give."""
    plan = {"clusters": []}
    cur = None
    pending_refs = False  # 'refs:' with value on following indented lines
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            if cur is not None:
                plan["clusters"].append(cur)
                cur = None
            pending_refs = False
            continue
        m = re.match(r"\s*([\w\-]+)\s*:\s*(.*)$", line)
        if not m:
            # continuation line under 'refs:'
            if pending_refs and cur is not None:
                cur.setdefault("refs", [])
                cur["refs"].extend(_raw_refs(line))
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key in ("floor", "venue_family"):
            plan[key] = int(val) if key == "floor" and val else val or plan.get(key)
            pending_refs = False
            continue
        if key == "name":
            if cur is not None:
                plan["clusters"].append(cur)
            cur = {"name": val}
            pending_refs = False
            continue
        if cur is None:
            cur = {}
        if key == "refs":
            cur["refs"] = _raw_refs(val)
            pending_refs = (val == "")
        else:
            cur[key] = val
            pending_refs = False
    if cur is not None:
        plan["clusters"].append(cur)
    return plan


def load_plan(path: str) -> dict:
    text = read_text(path)
    if path.endswith(".json"):
        try:
            return json.loads(text)
        except ValueError as e:
            fail(f"{path} is not valid JSON: {e}")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            return json.loads(text)
        except ValueError:
            pass  # fall through to the text parser
    return parse_text_plan(text)


def evaluate(plan: dict, floor: int):
    clusters = plan.get("clusters") or []
    if not clusters:
        fail("plan has no clusters. Enumerate the REQUIRED clusters from the "
             "paper's claimed scope first (one direct-prior-approach cluster "
             "per contribution/sub-task) — see references/clustering-and-deltas.md.")
    results, empty, thin, singleton, padded = [], [], [], [], []
    for c in clusters:
        name = (c.get("name") or "(unnamed)").strip()
        tiered = _as_tiered_refs(c.get("refs"))
        refs = [k for k, _ in tiered]
        n = len(refs)
        # Only CITED-tier refs count toward the recall floor; speculative-tier
        # refs (graph/keyword/heuristic) are tracked separately so a cluster
        # cannot satisfy the floor by padding with plausible-but-uncited works.
        confirmed = [k for k, t in tiered if t == CONFIRMED_TIER]
        speculative = [(k, t) for k, t in tiered if t != CONFIRMED_TIER]
        n_conf = len(confirmed)
        # `expected` (default true) marks a cluster a reviewer would fault as
        # missing. Only expected clusters drive the blocking gate; a cluster
        # explicitly flagged `expected: false` (an optional adjacent area the
        # author chose to track) is surfaced but never blocks — keeping the
        # field live and matching the "empty EXPECTED clusters" contract.
        expected = _truthy(c.get("expected", True))
        rec = {
            "name": name,
            "required_by": c.get("required_by", ""),
            "kind": c.get("kind", ""),
            "expected": expected,
            "n_refs": n,
            "n_confirmed": n_conf,
            "n_speculative": len(speculative),
            "refs": refs,
            "speculative_refs": [f"{k} ({t})" for k, t in speculative],
            "status": "ok",
        }
        # The floor is measured on CONFIRMED refs only.
        if n_conf == 0:
            rec["status"] = "EMPTY" if expected else "EMPTY-OPT"
            if expected:
                empty.append(rec)
                # A cluster with zero confirmed but some speculative refs is a
                # PADDED hole: it would have looked "covered" under the old
                # key-count floor. Flag it distinctly so it is never mistaken
                # for genuine coverage.
                if speculative:
                    padded.append(rec)
        elif n_conf < floor:
            rec["status"] = "THIN" if expected else "THIN-OPT"
            if expected:
                thin.append(rec)
                if n_conf == 1:
                    singleton.append(rec)
        results.append(rec)
    return results, empty, thin, singleton, padded


def worklist_lines(gaps: list, venue_family: str, floor: int) -> list:
    """A targeted second-pass retrieval worklist for find-papers."""
    lines = ["# Second-pass retrieval worklist for find-papers",
             "# Each line is a cluster the paper's scope REQUIRES but the",
             "# retrieved corpus underfills. Run find-papers to fill it, then",
             "# re-run check_coverage.py. Do NOT ship these as silent to-dos."]
    if venue_family:
        lines.append(f"# venue_family: {venue_family} (scope queries to its norms)")
    for g in gaps:
        why = f" — required by {g['required_by']}" if g.get("required_by") else ""
        kind = f" [{g['kind']}]" if g.get("kind") else ""
        need = "find direct prior approaches + canonical anchor" \
            if g["status"] == "EMPTY" else \
            f"add {floor - g['n_confirmed']}+ more CONFIRMED-cited ref(s)"
        lines.append(f"- [{g['status']}] {g['name']}{kind}{why}: {need}")
    return lines


def precision_estimate(results: list):
    """Overall confirmed/total split across all clusters (precision proxy)."""
    total = sum(r["n_refs"] for r in results)
    conf = sum(r["n_confirmed"] for r in results)
    spec = total - conf
    ratio = (conf / total) if total else None
    return conf, spec, total, ratio


def main():
    args = parse_args()
    plan = load_plan(args.plan)
    floor = args.floor if args.floor is not None else int(plan.get("floor", 2))
    if floor < 1:
        fail("--floor must be >= 1")
    cap = (args.heuristic_cap if args.heuristic_cap is not None
           else int(plan.get("heuristic_cap", 2)))
    venue_family = (plan.get("venue_family") or "").strip()

    results, empty, thin, singleton, padded = evaluate(plan, floor)
    gaps = empty + thin
    blocking = bool(empty)
    conf, spec, total, ratio = precision_estimate(results)
    # Count heuristic-tier refs across the whole plan against the cap.
    n_heur = sum(1 for r in results for s in r["speculative_refs"]
                 if s.endswith("(heuristic)"))
    heuristic_over_cap = n_heur > cap

    if args.json:
        json.dump({
            "floor": floor,
            "heuristic_cap": cap,
            "venue_family": venue_family,
            "n_clusters": len(results),
            "clusters": results,
            "empty": [r["name"] for r in empty],
            "thin": [r["name"] for r in thin],
            "singleton": [r["name"] for r in singleton],
            "padded_with_speculative_only": [r["name"] for r in padded],
            "precision_estimate": {
                "confirmed": conf, "speculative": spec, "total": total,
                "ratio": round(ratio, 3) if ratio is not None else None,
            },
            "heuristic_refs": n_heur,
            "heuristic_over_cap": heuristic_over_cap,
            "worklist": worklist_lines(gaps, venue_family, floor) if gaps else [],
            "blocking": blocking,
        }, sys.stdout, indent=2)
        print()
    else:
        print(f"coverage: {len(results)} required cluster(s), confirmed-citation "
              f"floor = {floor}\n")
        marks = {"ok": "ok  ", "THIN": "WARN", "EMPTY": "FAIL",
                 "THIN-OPT": "note", "EMPTY-OPT": "note"}
        for r in results:
            mark = marks[r["status"]]
            req = f"  (required by {r['required_by']})" if r["required_by"] else ""
            opt = "  [optional]" if not r["expected"] else ""
            split = (f"{r['n_confirmed']} cited"
                     + (f" + {r['n_speculative']} speculative"
                        if r["n_speculative"] else ""))
            print(f"  [{mark}] {r['name']}: {split}{req}{opt}")
        if padded:
            print("\nFAIL — required clusters with ZERO confirmed cites, "
                  "'covered' ONLY by speculative refs (padding masks a real "
                  "hole — do NOT count these as coverage):")
            for r in padded:
                print(f"  - {r['name']} ({', '.join(r['speculative_refs'])})")
        empty_no_pad = [r for r in empty if r not in padded]
        if empty_no_pad:
            print("\nFAIL — required clusters with ZERO citations "
                  "(structural hole; do NOT draft over it):")
            for r in empty_no_pad:
                print(f"  - {r['name']}")
        if thin:
            print(f"\nWARN — clusters below the confirmed floor of {floor} "
                  "(a cluster resting on one cite is a reviewer target):")
            for r in thin:
                extra = (f"; {r['n_speculative']} speculative not counted"
                         if r["n_speculative"] else "")
                print(f"  - {r['name']} ({r['n_confirmed']} cited{extra})")
        if gaps:
            print()
            for ln in worklist_lines(gaps, venue_family, floor):
                print(ln)
        # Precision line: visible over-inclusion signal alongside recall.
        if total:
            pct = f"{ratio*100:.0f}%" if ratio is not None else "n/a"
            print(f"\nprecision estimate: {conf}/{total} refs are confirmed-cited "
                  f"({pct}); {spec} speculative (graph/keyword/heuristic).")
            if spec:
                print("  speculative refs are PLAUSIBLE, not confirmed — label "
                      "them in the output and let the user prune before submit.")
        if heuristic_over_cap:
            print(f"\nWARN — {n_heur} heuristic-tier ref(s) exceed the cap of "
                  f"{cap}. 'A strong paper would cite these' is the weakest "
                  "evidence path; trim to the cap so the core set stays "
                  "scope-justified.")
        print()
        if blocking:
            print("RESULT: blocking gap(s). Route the worklist above back to "
                  "find-papers (targeted second pass), then re-run this check. "
                  "Do not ship an empty required cluster as an author to-do.")
        elif thin:
            print("RESULT: no empty clusters, but thin ones remain — strengthen "
                  "them via a second find-papers pass before drafting, or "
                  "justify the thinness to the user explicitly.")
        else:
            print("CLEAN — every required cluster meets the confirmed-citation "
                  "floor.")

    sys.exit(3 if blocking else 0)


if __name__ == "__main__":
    main()
