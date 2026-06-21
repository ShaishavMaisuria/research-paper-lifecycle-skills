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
                   help="per-cluster verified-citation floor (default: from "
                        "the plan's `floor`, else 2). Clusters below this WARN; "
                        "clusters at zero FAIL.")
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


def _as_refs(val) -> list:
    """Normalize a refs value (list, or comma/space string) to clean keys."""
    if val is None:
        return []
    if isinstance(val, list):
        items = val
    else:
        items = re.split(r"[,\s]+", str(val))
    out, seen = [], set()
    for it in items:
        k = str(it).strip().strip(",")
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
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
                cur["refs"].extend(_as_refs(line))
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
            cur["refs"] = _as_refs(val)
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
    results, empty, thin, singleton = [], [], [], []
    for c in clusters:
        name = (c.get("name") or "(unnamed)").strip()
        refs = _as_refs(c.get("refs"))
        n = len(refs)
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
            "refs": refs,
            "status": "ok",
        }
        if n == 0:
            rec["status"] = "EMPTY" if expected else "EMPTY-OPT"
            if expected:
                empty.append(rec)
        elif n < floor:
            rec["status"] = "THIN" if expected else "THIN-OPT"
            if expected:
                thin.append(rec)
                if n == 1:
                    singleton.append(rec)
        results.append(rec)
    return results, empty, thin, singleton


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
            f"add {floor - g['n_refs']}+ more verified ref(s)"
        lines.append(f"- [{g['status']}] {g['name']}{kind}{why}: {need}")
    return lines


def main():
    args = parse_args()
    plan = load_plan(args.plan)
    floor = args.floor if args.floor is not None else int(plan.get("floor", 2))
    if floor < 1:
        fail("--floor must be >= 1")
    venue_family = (plan.get("venue_family") or "").strip()

    results, empty, thin, singleton = evaluate(plan, floor)
    gaps = empty + thin
    blocking = bool(empty)

    if args.json:
        json.dump({
            "floor": floor,
            "venue_family": venue_family,
            "n_clusters": len(results),
            "clusters": results,
            "empty": [r["name"] for r in empty],
            "thin": [r["name"] for r in thin],
            "singleton": [r["name"] for r in singleton],
            "worklist": worklist_lines(gaps, venue_family, floor) if gaps else [],
            "blocking": blocking,
        }, sys.stdout, indent=2)
        print()
    else:
        print(f"coverage: {len(results)} required cluster(s), citation floor "
              f"= {floor}\n")
        marks = {"ok": "ok  ", "THIN": "WARN", "EMPTY": "FAIL",
                 "THIN-OPT": "note", "EMPTY-OPT": "note"}
        for r in results:
            mark = marks[r["status"]]
            req = f"  (required by {r['required_by']})" if r["required_by"] else ""
            opt = "  [optional]" if not r["expected"] else ""
            print(f"  [{mark}] {r['name']}: {r['n_refs']} ref(s){req}{opt}")
        if empty:
            print("\nFAIL — required clusters with ZERO verified citations "
                  "(structural hole; do NOT draft over it):")
            for r in empty:
                print(f"  - {r['name']}")
        if thin:
            print(f"\nWARN — clusters below the floor of {floor} "
                  "(a cluster resting on one citation is a reviewer target):")
            for r in thin:
                print(f"  - {r['name']} ({r['n_refs']} ref)")
        if gaps:
            print()
            for ln in worklist_lines(gaps, venue_family, floor):
                print(ln)
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
            print("CLEAN — every required cluster meets the citation floor.")

    sys.exit(3 if blocking else 0)


if __name__ == "__main__":
    main()
