#!/usr/bin/env python3
"""Generate an ordered camera-ready checklist from a venue profile — stdlib only.

Part of the prepare-camera-ready skill (research-paper-skills). Reads a
venues/conferences/<venue>.yml profile (merging its family file), resolves the
camera-ready rail (acm-taps | ieee-pdfexpress | openreview-direct | other),
and prints the ordered step list for that rail plus the venue-specific
requirements, deadline, extra-page rule, and a mandatory re-verify warning.

No network access. The checklist is a starting point, never ground truth:
always re-verify against the venue's live camera-ready instructions.

Usage:
    python3 camera_ready_checklist.py venues/conferences/sigspatial-2026.yml --track Research
    python3 camera_ready_checklist.py venues/conferences/icde-2026.yml --json

Exit codes: 0 ok | 2 usage/profile error.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap

from venue_profile import ProfileError, load_profile, pick_track

# ---------------------------------------------------------------------------
# Canonical rail steps (kept in sync with references/*.md and the verified
# family profiles under venues/families/). Venue-specific overrides come from
# the profile's camera_ready.requirements list and are printed separately.
# ---------------------------------------------------------------------------

RAIL_STEPS: dict[str, list[str]] = {
    "acm-taps": [
        "Watch for the eRights email from rightsreview@acm.org (sent to the "
        "CORRESPONDING author days-to-weeks after acceptance) — check spam; "
        "nothing else in the rail unlocks until this form is done.",
        "Collect ORCID iDs for ALL authors before opening the form (free at "
        "orcid.org); ACM requires every author's ORCID to complete eRights.",
        "Complete the eRights form using the EXACT final title and author "
        "list/order of the camera-ready paper — the form's metadata overrides "
        "your source files in TAPS.",
        "Copy the rights/DOI block the completed form returns (\\setcopyright, "
        "\\acmConference/\\acmJournal, \\acmYear, \\acmISBN, \\acmDOI, ...) "
        "into the LaTeX preamble before \\begin{document} (Word: paste the "
        "copyright strip text).",
        "Switch to the camera-ready documentclass: drop the review/anonymous "
        "options, restore author names, affiliations, emails, ORCIDs, and "
        "acknowledgments/funding.",
        "Add mandatory CCS concepts (CCSXML + \\ccsdesc via dl.acm.org/ccs) "
        "and free-text \\keywords; confirm the ACM Reference Format block "
        "renders on page 1.",
        "Restrict the source to TAPS-accepted LaTeX packages and compile "
        "cleanly against the current acmart release.",
        "Wait for the TAPS email with your submission ID and unique upload "
        "link; upload ONE zip of ALL source files (.tex, .bib, .sty, figures), "
        "named as the email instructs (typically <acronym>-<paperid>.zip).",
        "Review BOTH the PDF and the HTML5 proofs TAPS generates (~24h), then "
        "approve — or reject with fixes and re-check — inside TAPS before the "
        "camera-ready deadline.",
        "Budget lead time: eRights -> rights block -> TAPS -> proofs can take "
        "WEEKS end-to-end. Start the day the acceptance email arrives.",
    ],
    "ieee-pdfexpress": [
        "Find the PDF eXpress Conference ID in the acceptance email or the "
        "venue's camera-ready instructions (looks like '61234X'); without it "
        "you cannot enroll the paper.",
        "Produce the final IEEEtran paper: de-anonymize if the venue was "
        "blind, remove page numbers/headers/footers and any line numbers, and "
        "add the page-1 copyright notice if the venue requires one (exact "
        "string is in the camera-ready instructions).",
        "Create an account / log in at ieee-pdf-express.org using that "
        "Conference ID and create a title record for the paper.",
        "Validate your final PDF (or upload source for conversion) until PDF "
        "eXpress emails the 'passed' Xplore-compatibility certificate — "
        "font-embedding failures are the usual culprit.",
        "Rename the certified PDF per the venue's file-naming convention "
        "(e.g. PID<number>.pdf at CMT venues) — wrong names get rejected or "
        "lost in production.",
        "Upload the certified PDF to the venue's DESIGNATED collection site "
        "(IEEE CPS portal, CyberChair, EDAS, ...) — often NOT the review "
        "system you submitted to; follow the camera-ready email exactly.",
        "Complete the IEEE electronic Copyright Form (eCF) as the "
        "corresponding author: title and author list must EXACTLY match the "
        "final PDF, the form cannot be redone after submission, and an "
        "incomplete eCF blocks IEEE Xplore indexing.",
        "Register at least one author at the required (usually full/member) "
        "rate by the author-registration deadline and present the paper — "
        "IEEE's no-show policy excludes unpresented papers from Xplore.",
    ],
    "openreview-direct": [
        "Recompile with the CURRENT year's official style file in "
        "camera-ready mode (e.g. \\usepackage[final]{neurips_2026}); never "
        "reuse a prior year's .sty.",
        "De-anonymize: restore author names, affiliations, acknowledgments, "
        "funding, and replace anonymized repository links with the real ones.",
        "Respect the camera-ready page cap (commonly +1 content page over the "
        "submission limit; references/appendix/checklist stay excluded where "
        "they were excluded at submission).",
        "Keep every mandatory section (e.g. the NeurIPS paper checklist) with "
        "final answers.",
        "Upload the final PDF (and any required source/supplementary bundle) "
        "via the OpenReview camera-ready task before the deadline.",
    ],
}

GENERIC_STEPS = [
    "This venue does not use the ACM TAPS or IEEE PDF eXpress rail. Fetch the "
    "venue's official camera-ready instructions page and follow it exactly.",
    "De-anonymize if the venue reviewed blind; restore acknowledgments and "
    "real artifact links.",
    "Complete whatever copyright/rights form the publisher issues — with the "
    "exact final title and author list.",
    "Confirm the camera-ready page limit and any extra-page allowance before "
    "cutting or adding content.",
    "Check registration/presentation requirements: many venues drop "
    "no-show papers from the proceedings.",
]


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def wrap(text: str, indent: str) -> str:
    return textwrap.fill(
        " ".join(str(text).split()),
        width=78,
        initial_indent=indent,
        subsequent_indent=" " * len(indent),
    )


def build(profile: dict, track: dict | None, notes: list[str]) -> dict:
    cam = profile.get("camera_ready") or {}
    fmt = profile.get("format") or {}
    review = profile.get("review") or {}
    deadlines = profile.get("deadlines") or {}
    verified = profile.get("verified") or {}

    rail = cam.get("rail")
    if not rail:
        template = str(fmt.get("template") or "")
        rail = {
            "acmart": "acm-taps",
            "IEEEtran": "ieee-pdfexpress",
            "neurips": "openreview-direct",
        }.get(template, "unknown")
        notes.append(f"profile has no camera_ready.rail; inferred '{rail}' "
                     f"from format.template={template!r}")

    blind = str(review.get("blind") or "unknown")
    deanon = blind.lower() in ("double", "triple")

    return {
        "venue": profile.get("name") or profile.get("id"),
        "venue_id": profile.get("id"),
        "rail": rail,
        "track": (track or {}).get("name"),
        "track_page_limit": (track or {}).get("page_limit"),
        "track_notes": (track or {}).get("notes"),
        "camera_ready_deadline": deadlines.get("camera_ready"),
        "deadline_timezone": deadlines.get("timezone"),
        "extra_pages": cam.get("extra_pages"),
        "blind": blind,
        "deanonymization_required": deanon,
        "steps": RAIL_STEPS.get(rail, GENERIC_STEPS),
        "venue_requirements": cam.get("requirements") or [],
        "reverify": {
            "cfp_url": profile.get("cfp_url"),
            "verified_date": verified.get("date"),
            "confidence": verified.get("confidence"),
        },
        "notes": notes,
    }


def render(data: dict) -> str:
    out: list[str] = []
    out.append(f"Camera-ready checklist — {data['venue']}")
    deadline = data["camera_ready_deadline"] or (
        "NOT in the profile — get it from the acceptance email / venue site")
    tz = f" ({data['deadline_timezone']})" if (
        data["camera_ready_deadline"] and data["deadline_timezone"]) else ""
    out.append(f"Rail: {data['rail']}   Track: {data['track'] or '-'}   "
               f"Deadline: {deadline}{tz}")
    rv = data["reverify"]
    out.append(f"Profile last verified: {rv['verified_date'] or 'unknown'} "
               f"({rv['confidence'] or 'unknown confidence'})")
    out.append("")
    out.append(wrap(
        "RE-VERIFY FIRST (mandatory): camera-ready instructions are issued "
        "per venue and change every cycle (some venues even switch rails). "
        "Before relying on anything below, open the acceptance email and the "
        f"venue's camera-ready page, and re-check the CFP: {rv['cfp_url']}",
        "!! "))
    out.append("")
    out.append("Steps:")
    for i, step in enumerate(data["steps"], 1):
        out.append(wrap(step, f"{i:3d}. [ ] "))
    if data["venue_requirements"]:
        out.append("")
        out.append("Venue-specific requirements (from the profile):")
        for req in data["venue_requirements"]:
            out.append(wrap(req, "  - [ ] "))
    out.append("")
    extra = data["extra_pages"] or (
        "not stated in the profile — NEVER assume an allowance; check the "
        "venue's camera-ready instructions")
    out.append(wrap(f"Extra pages: {extra}", ""))
    if data["track_page_limit"]:
        out.append(wrap(
            f"Track page limit at submission: {data['track_page_limit']} "
            f"(track: {data['track']})", ""))
    if data["track_notes"]:
        out.append(wrap(f"Track notes: {data['track_notes']}", ""))
    if data["deanonymization_required"]:
        out.append(wrap(
            f"De-anonymization: REQUIRED ({data['blind']}-blind venue) — work "
            "through references/deanonymize-and-extra-pages.md before any "
            "rights form (forms need the final author list).", ""))
    elif data["blind"] == "single":
        out.append(wrap(
            "De-anonymization: not needed (single-blind venue); just drop any "
            "review-mode options and restore acknowledgments if trimmed.", ""))
    else:
        out.append(wrap(
            f"De-anonymization: blind level is '{data['blind']}' in the "
            "profile — confirm against the CFP, then see "
            "references/deanonymize-and-extra-pages.md if it was blind.", ""))
    if data["notes"]:
        out.append("")
        for n in data["notes"]:
            out.append(wrap(n, "note: "))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Print the ordered camera-ready checklist for a venue "
        "profile (ACM TAPS / IEEE PDF eXpress / OpenReview rails).",
        epilog="examples:\n"
        "  python3 camera_ready_checklist.py venues/conferences/sigspatial-2026.yml --track Research\n"
        "  python3 camera_ready_checklist.py venues/conferences/icde-2026.yml --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("venue", help="path to venues/conferences/<venue>.yml")
    ap.add_argument("--track", help="track name substring (page limits and "
                    "camera-ready dates differ per track)")
    ap.add_argument("--venues-dir", help="venues/ root (auto-discovered by default)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    try:
        profile, notes = load_profile(args.venue, args.venues_dir)
        track, note = pick_track(profile, args.track)
        notes.append(note)
    except ProfileError as exc:
        fail(str(exc))
        return 2  # unreachable
    data = build(profile, track, notes)
    if args.json:
        json.dump(data, sys.stdout, indent=2, default=str)
        print()
    else:
        print(render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
