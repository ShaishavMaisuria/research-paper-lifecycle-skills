#!/usr/bin/env python3
"""Consistency audit: do the artifact's produced metrics MATCH the paper?

Given (a) a claims ledger from extract_claims.py (or a hand-written one) and
(b) a metrics file the AUTHOR's run produced (JSON or CSV), this compares each
paper-reported number to the corresponding produced number with a tolerance
that does not change the paper's claim — never bit-exact (ACM/SIGMOD/ETAPS all
require only agreement within tolerance). It reports MATCH / MISMATCH / MISSING.

It does NOT run anything and does NOT judge correctness by self-reflection —
the comparison is a concrete numeric diff against an external file the author
generated. Garbage in (wrong ledger / wrong metrics file) is reported, not
hidden.

Ledger format (JSON): {"claims": [{"id","metric","value","is_percent",
"scale_hint","source"}, ...]}  (extract_claims.py emits exactly this).

Metrics file:
  - JSON: a flat or nested object of name->number (nesting is flattened with
    dotted keys), or a list of {"metric"/"name": ..., "value": ...} records.
  - CSV: a header row; either columns metric,value or one row of name->number.

Matching: a claim is matched to a produced metric by (1) explicit --map
name=claimid pairs, else (2) the claim's `metric` label appearing in a produced
key (case-insensitive), else (3) left UNMATCHED (reported, never guessed).

Usage:
    python3 compare_metrics.py --ledger claims.json --metrics run.json \
        [--rel-tol 0.01] [--abs-tol 0.005] [--map test_acc=c1 --map f1=c3] [--json]

Exit codes: 0 all matched claims agree (mismatches/missing => 1), 1 any
MISMATCH or unmatched ERROR, 2 usage/load failure. --strict makes WARN fail too.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verifylib as vl


def _flatten(obj, prefix="") -> dict:
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                out.update(_flatten(v, key))
            else:
                out[key] = v
    elif isinstance(obj, list):
        # list of {name,value} records is the common case
        named = False
        for item in obj:
            if isinstance(item, dict):
                name = item.get("metric") or item.get("name") or item.get("key")
                if name is not None and ("value" in item or "val" in item):
                    out[str(name)] = item.get("value", item.get("val"))
                    named = True
                else:
                    out.update(_flatten(item, prefix))
        if not named and not out:
            for i, item in enumerate(obj):
                out.update(_flatten(item, f"{prefix}[{i}]" if prefix else f"[{i}]"))
    return out


def load_metrics(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"metrics file not found: {path}")
    text = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() == ".json":
        flat = _flatten(json.loads(text))
    elif p.suffix.lower() in (".csv", ".tsv"):
        delim = "\t" if p.suffix.lower() == ".tsv" else ","
        rows = list(csv.reader(io.StringIO(text), delimiter=delim))
        flat = {}
        if rows:
            header = [h.strip().lower() for h in rows[0]]
            if "metric" in header and "value" in header:
                mi, vi = header.index("metric"), header.index("value")
                for r in rows[1:]:
                    if len(r) > max(mi, vi):
                        flat[r[mi].strip()] = r[vi].strip()
            elif len(rows) >= 2:  # name,name,... / val,val,... layout
                for h, v in zip(rows[0], rows[1]):
                    flat[h.strip()] = v.strip()
            else:
                raise ValueError("CSV needs metric,value columns or a header+value row")
    else:
        raise ValueError(f"unsupported metrics format: {p.suffix} (use .json/.csv)")

    # coerce values to (float, is_percent) via verifylib's parser; keep raw too
    parsed = {}
    for k, v in flat.items():
        pv = vl.parse_number(str(v))
        if pv is not None:
            parsed[k] = (pv[0], pv[1], str(v))
    return parsed


def _match_key(claim: dict, metrics: dict, manual: dict[str, str]) -> str | None:
    # 1. explicit map: metricname=claimid
    for mk, cid in manual.items():
        if cid == claim["id"] and mk in metrics:
            return mk
    # 2. label substring match
    label = (claim.get("metric") or "").lower()
    if label:
        cands = [k for k in metrics if label in k.lower()]
        if len(cands) == 1:
            return cands[0]
        if len(cands) > 1:
            # prefer an exact case-insensitive hit
            exact = [k for k in cands if k.lower() == label]
            if len(exact) == 1:
                return exact[0]
    return None


def compare(claims: list[dict], metrics: dict, *, rel_tol: float, abs_tol: float,
            manual: dict[str, str]) -> tuple[list[vl.Finding], list[str], dict]:
    findings: list[vl.Finding] = []
    notes: list[str] = []
    used_keys = set()
    n_match = n_mismatch = n_missing = 0

    for c in claims:
        if c.get("confirmed") is False:
            notes.append(f"{c['id']} is unconfirmed in the ledger — confirm or "
                         "drop it before trusting the comparison")
        pv = c.get("value")
        if pv is None:
            continue
        key = _match_key(c, metrics, manual)
        loc = c.get("source", c["id"])
        if key is None:
            n_missing += 1
            findings.append(vl.Finding(
                "ERROR", "metric/no-produced-value", f"{c['id']} @ {loc}",
                f"paper reports {c.get('metric') or 'value'}={c.get('raw', pv)} "
                "but the run produced no matching metric — missing repro step or "
                "metric not emitted (or add --map name=" + c["id"] + ")"))
            continue
        used_keys.add(key)
        rv, rpct, rraw = metrics[key]
        status, diff = vl.compare_values(
            pv, bool(c.get("is_percent")), rv, rpct,
            rel_tol=rel_tol, abs_tol=abs_tol, scale_hint=c.get("scale_hint"))
        if status == "match":
            n_match += 1
            findings.append(vl.Finding(
                "INFO", "metric/match", f"{c['id']} @ {loc}",
                f"{c.get('metric') or 'value'}: paper {c.get('raw', pv)} ~= "
                f"run '{key}'={rraw} (|d|={diff:.4g} within tol)"))
        else:
            n_mismatch += 1
            findings.append(vl.Finding(
                "ERROR", "metric/mismatch", f"{c['id']} @ {loc}",
                f"{c.get('metric') or 'value'}: PAPER SAYS {c.get('raw', pv)} but "
                f"run '{key}'={rraw} (|d|={diff:.4g} exceeds tol) — paper/code "
                "inconsistency"))

    unused = sorted(set(metrics) - used_keys)
    for k in unused:
        findings.append(vl.Finding(
            "WARN", "metric/unclaimed", k,
            f"produced metric '{k}'={metrics[k][2]} did not match any paper claim "
            "(extra output, or a claim the ledger missed)"))

    summary = {"matched": n_match, "mismatched": n_mismatch, "missing": n_missing,
               "unclaimed": len(unused), "produced_total": len(metrics)}
    notes.append(f"verdict: {n_match} match, {n_mismatch} MISMATCH, "
                 f"{n_missing} missing produced value, {len(unused)} unclaimed; "
                 f"tolerance rel={rel_tol} abs={abs_tol}")
    notes.append("MATCH = consistent within tolerance, NOT independently "
                 "reproduced; tighten/loosen tolerance to your metric's scale")
    return findings, notes, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", required=True, help="claims ledger JSON (from extract_claims.py)")
    ap.add_argument("--metrics", required=True, help="produced metrics file (.json/.csv) from the run")
    ap.add_argument("--rel-tol", type=float, default=0.01,
                    help="relative tolerance (default 0.01 = 1%% of the paper value)")
    ap.add_argument("--abs-tol", type=float, default=0.005,
                    help="absolute tolerance floor (default 0.005)")
    ap.add_argument("--map", action="append", default=[], metavar="NAME=CLAIMID",
                    help="force-map a produced metric name to a claim id (repeatable)")
    vl.add_common_args(ap)
    args = ap.parse_args()

    manual = {}
    for pair in args.map:
        if "=" not in pair:
            print(f"error: bad --map '{pair}', expected NAME=CLAIMID", file=sys.stderr)
            return 2
        name, cid = pair.split("=", 1)
        manual[name.strip()] = cid.strip()

    try:
        ledger = json.loads(pathlib.Path(args.ledger).read_text(encoding="utf-8"))
        if isinstance(ledger, dict):
            claims = ledger.get("claims", [])
        elif isinstance(ledger, list):
            claims = ledger
        else:
            claims = []
        metrics = load_metrics(args.metrics)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: could not parse inputs: {exc}", file=sys.stderr)
        return 2

    if not claims:
        print("error: ledger has no claims to compare", file=sys.stderr)
        return 2
    if not metrics:
        print("error: no numeric metrics parsed from the metrics file", file=sys.stderr)
        return 2

    findings, notes, summary = compare(
        claims, metrics, rel_tol=args.rel_tol, abs_tol=args.abs_tol, manual=manual)
    return vl.report("compare_metrics", findings, notes, args, extra={"summary": summary})


if __name__ == "__main__":
    sys.exit(main())
