#!/usr/bin/env python3
"""Explain artifact badge families/tiers and the Reproduced/Replicated era swap.

Part of the prepare-artifacts skill (research-paper-skills). Stdlib only, no
network. It is a REFERENCE-DATA helper, not a source of truth: it prints the
ACM v1.1 badge taxonomy (the structure that USENIX/ETAPS/SIGMOD ARI follow)
and, critically, resolves what 'Reproduced' vs 'Replicated' MEAN for a given
badge era — ACM SWAPPED these two terms on 2020-05-14, so a pre-2020 badge
means the inverse of a current one.

It does NOT know any venue's CURRENT badge offering (those change per venue PER
YEAR — OSDI '26 offers only 'Artifacts Available'). Always re-verify against
the live Call for Artifacts; this tool just keeps the terminology straight.

Usage:
    python3 badge_advisor.py [--era current|pre-2020] [--badge available|
                              functional|reusable|reproduced|replicated|all]
                              [--json]

Exit codes: 0 ok | 2 usage.
"""
from __future__ import annotations

import argparse
import json
import sys

SWAP_DATE = "2020-05-14"

# ACM Artifact Review and Badging v1.1 (current). Three INDEPENDENT families.
FAMILIES = {
    "available": {
        "family": "Artifacts Available",
        "tiers": ["(single badge)"],
        "summary": (
            "Author-created artifacts placed on a publicly accessible ARCHIVAL "
            "repository with a DOI / persistent identifier (NOT just a personal "
            "or GitHub URL). Independent of whether the artifacts were evaluated."
        ),
        "bar": [
            "Deposit to an archival repo: Zenodo / FigShare / Dryad (version DOI) "
            "or Software Heritage (SWHID). USENIX-family REJECT GitHub/personal "
            "sites for the permanent copy.",
            "Use a VERSION-specific DOI for the final; a concept DOI is OK only "
            "during evaluation.",
        ],
    },
    "functional": {
        "family": "Artifacts Evaluated",
        "tiers": ["Functional (lower tier)"],
        "summary": (
            "Artifacts are documented, consistent, complete, and exercisable, "
            "with evidence of verification/validation. Reviewers may inspect "
            "privately; public availability is NOT required for this badge."
        ),
        "bar": [
            "Documented: an inventory + how to obtain/install/run.",
            "Consistent: the artifacts are relevant to and produce the paper's "
            "results.",
            "Complete: all key components are included.",
            "Exercisable: scripts/data are included and the included scripts run.",
        ],
    },
    "reusable": {
        "family": "Artifacts Evaluated",
        "tiers": ["Reusable (HIGHER tier; subsumes Functional)"],
        "summary": (
            "Everything in Functional, PLUS carefully documented and "
            "well-structured so that others can REUSE / repurpose it beyond the "
            "paper. The higher of the two Evaluated tiers."
        ),
        "bar": [
            "All Functional criteria.",
            "Careful documentation enabling reuse (clear structure, a README "
            "that explains components, build, and how to adapt).",
            "Norms a reviewer expects of well-engineered research software.",
        ],
    },
    "reproduced": {
        "family": "Results Validated",
        "tiers": ["Reproduced"],
        "summary": (
            "CURRENT (v1.1) meaning: the paper's main results were obtained by a "
            "DIFFERENT team USING, in part, the author-supplied artifacts. "
            "Exact numerical match is NEVER required — agreement within a "
            "tolerance that does not change the paper's main claims."
        ),
        "bar": [
            "A different team re-runs the author artifacts and gets results that "
            "agree within tolerance.",
            "Provide a per-claim reproduction procedure + a result-comparison "
            "method (what counts as 'agrees').",
        ],
    },
    "replicated": {
        "family": "Results Validated",
        "tiers": ["Replicated"],
        "summary": (
            "CURRENT (v1.1) meaning: the paper's main results were obtained by a "
            "DIFFERENT team WITHOUT the author-supplied artifacts (an "
            "independent re-implementation). Again, agreement within tolerance, "
            "not exact match."
        ),
        "bar": [
            "An independent re-implementation reproduces the main claims.",
            "Usually outside the author's control; relevant when a venue or "
            "third party replicates the work.",
        ],
    },
}

# The ONE thing this tool exists to keep straight.
ERA_NOTE = {
    "current": (
        f"CURRENT era (badges issued AFTER {SWAP_DATE}, ACM v1.1, aligned with "
        "NISO RP-31-2021): 'Reproduced' = a DIFFERENT team USING the author "
        "artifacts; 'Replicated' = a different team WITHOUT them (independent "
        "re-implementation)."
    ),
    "pre-2020": (
        f"PRE-2020 era (badges issued UP TO {SWAP_DATE}, ACM v1.0): the terms "
        "are INVERTED. 'Replicated' meant a different team USING the author "
        "artifacts; 'Reproduced' meant WITHOUT them. ACM swapped the two on "
        "NISO's advice. If you are reading an older paper's badge, apply the "
        "inverse of the current definitions."
    ),
}


def resolve_validated(era: str) -> dict:
    """Return the era-correct mapping of the two Results-Validated terms."""
    if era == "pre-2020":
        return {
            "Reproduced (pre-2020 v1.0)": "a DIFFERENT team WITHOUT author artifacts",
            "Replicated (pre-2020 v1.0)": "a different team USING author artifacts",
        }
    return {
        "Reproduced (current v1.1)": "a DIFFERENT team USING author artifacts",
        "Replicated (current v1.1)": "a different team WITHOUT author artifacts",
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Print the ACM v1.1 artifact-badge taxonomy and resolve the "
        "Reproduced/Replicated terms for a badge era (they were SWAPPED on "
        f"{SWAP_DATE}). Reference data only — re-verify each venue's CURRENT "
        "badge offering against its live Call for Artifacts.",
        epilog="examples:\n"
        "  python3 badge_advisor.py\n"
        "  python3 badge_advisor.py --badge available\n"
        "  python3 badge_advisor.py --era pre-2020 --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--era", choices=["current", "pre-2020"], default="current",
                    help=f"badge era; terms swapped on {SWAP_DATE} (default current)")
    ap.add_argument("--badge",
                    choices=["available", "functional", "reusable",
                             "reproduced", "replicated", "all"],
                    default="all", help="which badge to explain (default all)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    selected = (list(FAMILIES) if args.badge == "all" else [args.badge])
    validated = resolve_validated(args.era)

    if args.json:
        json.dump({
            "standard": "ACM Artifact Review and Badging v1.1 (current)",
            "policy_url": "https://www.acm.org/publications/policies/"
                          "artifact-review-and-badging-current",
            "era": args.era,
            "era_note": ERA_NOTE[args.era],
            "swap_date": SWAP_DATE,
            "results_validated_terms": validated,
            "badges": {k: FAMILIES[k] for k in selected},
            "reminder": "Badge offerings vary per venue PER YEAR — re-verify the "
                        "live Call for Artifacts (e.g. OSDI '26 offers ONLY "
                        "Artifacts Available).",
        }, sys.stdout, indent=2)
        print()
        return 0

    print("ACM Artifact Review and Badging v1.1 (current) — three INDEPENDENT "
          "badge families")
    print("policy: https://www.acm.org/publications/policies/"
          "artifact-review-and-badging-current")
    print()
    print(f"[era: {args.era}] {ERA_NOTE[args.era]}")
    print()
    for key in selected:
        b = FAMILIES[key]
        print(f"== {key.upper()} — {b['family']} :: {', '.join(b['tiers'])} ==")
        print(f"  {b['summary']}")
        for item in b["bar"]:
            print(f"   - {item}")
        print()
    print("Results-Validated terms for this era:")
    for term, meaning in validated.items():
        print(f"   - {term}: {meaning}")
    print()
    print("reminder: badge offerings change per venue PER YEAR. Always re-verify "
          "the live Call for Artifacts — e.g. OSDI '26 evaluates ONLY 'Artifacts "
          "Available'; SOSP '26 offers all three. NISO RP-31-2021 underpins the "
          "current terminology.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
