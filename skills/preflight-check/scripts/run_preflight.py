#!/usr/bin/env python3
"""Run the full desk-reject preflight: all four checkers in one report.

Equivalent to running check_template, check_anonymization, check_sections,
and check_abstract individually, but loads the source and venue profile once
and emits a single combined report (text or --json).

Usage:
    python3 run_preflight.py paper.tex --venue venues/conferences/neurips-2026.yml [--track NAME]

Exit codes: 0 no ERRORs (warnings allowed unless --strict), 1 ERROR findings,
2 usage/load failure.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_abstract
import check_anonymization
import check_sections
import check_template
import texlib
import venue_profile as vp

CHECKERS = [
    ("template", check_template.collect),
    ("anonymization", check_anonymization.collect),
    ("sections", check_sections.collect),
    ("abstract", check_abstract.collect),
]


def main() -> int:
    ap = texlib.base_parser(__doc__.splitlines()[0])
    ap.add_argument(
        "--force", action="store_true",
        help="run anonymization checks even at single-blind venues",
    )
    args = ap.parse_args()
    try:
        profile, pnotes = vp.load_profile(args.venue, args.venues_dir)
        track, tnote = vp.pick_track(profile, args.track)
        pnotes.append(tnote)
        doc = texlib.TexDoc.load(args.tex, follow_inputs=not args.no_inputs)
    except (vp.ProfileError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    sections = {}
    all_findings: list[texlib.Finding] = []
    for name, fn in CHECKERS:
        findings = fn(doc, profile, track, args)
        sections[name] = findings
        all_findings.extend(findings)

    counts = {s: sum(1 for f in all_findings if f.severity == s) for s in texlib.SEVERITIES}
    if args.json:
        json.dump(
            {
                "tool": "run_preflight",
                "tex": args.tex,
                "venue": profile.get("id"),
                "track": (track or {}).get("name"),
                "notes": pnotes + doc.notes,
                "checks": {
                    name: [dataclasses.asdict(f) for f in fs]
                    for name, fs in sections.items()
                },
                "summary": counts,
                "verdict": "FAIL" if counts["ERROR"] else "PASS-WITH-WARNINGS"
                if counts["WARN"] else "PASS",
            },
            sys.stdout,
            indent=2,
            default=str,
        )
        print()
    else:
        print("=" * 78)
        print(f"PREFLIGHT REPORT  {args.tex}")
        print(f"venue: {profile.get('id')}   track: {(track or {}).get('name', 'n/a')}")
        print("=" * 78)
        for note in pnotes + doc.notes:
            print(f"note: {note}")
        for name, fs in sections.items():
            print(f"\n-- {name} " + "-" * (74 - len(name)))
            if not fs:
                print("   clean.")
            for f in sorted(
                fs, key=lambda x: (texlib.SEVERITIES.index(x.severity), x.file, x.line or 0)
            ):
                print("   " + f.format())
        verdict = (
            "FAIL — fix ERRORs before submitting"
            if counts["ERROR"]
            else "PASS with warnings — review WARNs"
            if counts["WARN"]
            else "PASS"
        )
        print("\n" + "=" * 78)
        print(
            f"VERDICT: {verdict}   "
            f"({counts['ERROR']} error(s), {counts['WARN']} warning(s), {counts['INFO']} info)"
        )
        cfp = profile.get("cfp_url")
        if cfp:
            print(f"Profiles can go stale: re-verify limits/policies at {cfp}")
        print("=" * 78)
    return 1 if counts["ERROR"] or (args.strict and counts["WARN"]) else 0


if __name__ == "__main__":
    sys.exit(main())
