#!/usr/bin/env python3
"""Build a phase-aware, backwards submission timeline from a venue profile.

Part of the plan-submission skill (research-paper-skills). Stdlib only; NO
network access. Reads venues/conferences/<venue>.yml (merging its family via
the vendored venue_profile loader) and emits a dated milestone plan.

Phases (auto-detected from --today vs the profile deadlines):
  pre-submission : backwards offsets from the paper deadline — dual-submission
                   audit and reciprocal-reviewing check (T-21d), system
                   accounts (T-14d), author-list freeze (T-10d), abstract
                   registration (its real date, else T-7d), supplementary
                   (T-5d), preflight (T-3d), draft upload (T-2d), final
                   upload (T-1d), deadline (T-0).
  under-review   : rebuttal-window preparation + notification countdown.
  camera-ready   : rail lead times (start at C-14d; registration at C-7d).

The profile is a STARTING POINT, never ground truth — re-verify deadlines
against the live CFP (the profile's cfp_url) before relying on this plan.
This script never invents a date: null deadlines stay unknown, with a note.

Usage:
    python3 build_timeline.py venues/conferences/neurips-2026.yml \
        [--track Main] [--today YYYY-MM-DD] [--format md|json] \
        [--camera-ready YYYY-MM-DD] [--phase auto|pre|review|camera] \
        [--venues-dir DIR]

Exit codes: 0 ok | 1 no plannable dates (all in the past / none set) |
            2 usage or profile error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from venue_profile import ProfileError, load_profile, pick_track  # noqa: E402

HARD, PREP = "HARD", "PREP"

SYSTEM_HINTS = {
    "openreview": (
        "OpenReview: new profiles with non-institutional emails go through "
        "moderation that can take up to ~2 weeks — every author registers "
        "NOW with an institutional email and completes the profile "
        "(affiliation history, DBLP import, conflict domains)."
    ),
    "cmt": (
        "Microsoft CMT: accounts are instant, but every author must be added "
        "by the exact email their CMT account uses, and conflict-of-interest "
        "entry against the PC/domain lists is manual — missing COI "
        "declarations are a desk-reject at ICDE-style venues."
    ),
    "easychair": (
        "EasyChair: accounts are instant; author entries are typed by hand — "
        "a typo'd co-author email orphans the paper. Confirm the right TRACK "
        "before submitting; multi-track installs make mis-filing easy."
    ),
    "hotcrp": (
        "HotCRP: accounts are instant. Signature gotcha: the 'submission is "
        "ready for review' checkbox — papers left in draft state are NOT "
        "submitted. Fill topics + collaborators/conflicts exhaustively."
    ),
    "pcs": (
        "PCS: one account covers SIGCHI venues; title/abstract/authors/"
        "subcommittee LOCK at the metadata (abstract) deadline — the "
        "subcommittee choice is strategic, decide it with co-authors early."
    ),
}

RAIL_HINTS = {
    "acm-taps": (
        "ACM rail: eRights form (needs ORCIDs for ALL authors) -> insert the "
        "returned rights/DOI block -> upload SOURCE to TAPS. End-to-end can "
        "take weeks — start at C-14d."
    ),
    "ieee-pdfexpress": (
        "IEEE rail: validate via PDF eXpress with the conference ID, follow "
        "the file-naming convention, complete the eCF (title/authors must "
        "match the PDF exactly; the form cannot be redone)."
    ),
    "openreview-direct": (
        "OpenReview rail: recompile with the camera-ready/[final] style "
        "option, restore names/acknowledgments, upload via the camera-ready "
        "task."
    ),
    "springer": (
        "Springer rail: stay in LNCS format, complete the license-to-publish "
        "form, upload source + final PDF per the volume editors' "
        "instructions."
    ),
}


def fail(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_iso(value, label: str, notes: list[str]):
    """Parse a profile/CLI date; None passes through, junk becomes a note."""
    if value is None:
        return None
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        notes.append(f"{label} = {value!r} is not YYYY-MM-DD; treated as unknown")
        return None


def status_of(date: dt.date, today: dt.date, kind: str) -> str:
    if date < today:
        return "PASSED" if kind == HARD else "OVERDUE"
    if date == today:
        return "TODAY"
    return f"in {(date - today).days}d"


def milestone(date: dt.date, offset: str, kind: str, action: str) -> dict:
    return {"date": date, "offset": offset, "kind": kind, "action": action}


def pre_submission_milestones(dl: dict, profile: dict, notes: list[str]) -> list[dict]:
    paper = dl["paper"]
    system = str((profile.get("review") or {}).get("submission_system") or "").lower()
    sys_hint = SYSTEM_HINTS.get(
        system, "Confirm the submission system and its account requirements in the CFP."
    )
    day = dt.timedelta(days=1)
    ms = [
        milestone(
            paper - 21 * day, "T-21d", PREP,
            "Dual-submission audit: inventory every overlapping manuscript by "
            "ANY co-author under review or planned elsewhere during this "
            "venue's whole review period; check it against the policy gate "
            "below.",
        ),
        milestone(
            paper - 21 * day, "T-21d", PREP,
            "Reciprocal-reviewing check: if the venue requires an author to "
            "review (NeurIPS/ICML/CVPR-style — negligent reviewing can "
            "desk-reject your own paper), name the reviewing author and "
            "block their calendar now.",
        ),
        milestone(
            paper - 14 * day, "T-14d", PREP,
            f"Create/verify submission-system accounts for EVERY author. {sys_hint}",
        ),
        milestone(
            paper - 10 * day, "T-10d", PREP,
            "Freeze the author list and order (most venues forbid changes "
            "after the deadline); collect ORCIDs, exact account emails, "
            "affiliation history, and conflict-of-interest data.",
        ),
    ]
    if dl["abstract"]:
        gap = (paper - dl["abstract"]).days
        ms.append(milestone(
            dl["abstract"], f"T-{gap}d", HARD,
            "ABSTRACT REGISTRATION DEADLINE: title, abstract, full author "
            "list, subject areas, and conflicts in the submission system. "
            "Miss this and the paper cannot be submitted at all.",
        ))
    else:
        ms.append(milestone(
            paper - 7 * day, "T-7d", PREP,
            "Register title/abstract/authors in the submission system. The "
            "profile lists NO separate abstract deadline — confirm in the "
            "CFP whether one exists (most ML/data venues have one).",
        ))
        notes.append(
            "deadlines.abstract is null — confirm on the live CFP whether a "
            "separate abstract-registration deadline exists"
        )
    ms += [
        milestone(
            paper - 5 * day, "T-5d", PREP,
            "Package supplementary material and code within the venue's size "
            "limits; anonymize the package itself for double-blind venues "
            "(PDF metadata, README author lines, git history, hardcoded "
            "paths).",
        ),
        milestone(
            paper - 3 * day, "T-3d", PREP,
            "Run the desk-reject preflight (preflight-check skill): page "
            "budget vs profile, documentclass options, anonymization leaks, "
            "required checklist/declaration sections.",
        ),
        milestone(
            paper - 2 * day, "T-2d", PREP,
            "Upload a COMPLETE draft PDF + supplementary as a placeholder — "
            "submission systems slow down or fail near the deadline; verify "
            "form metadata matches the PDF.",
        ),
        milestone(
            paper - 1 * day, "T-1d", PREP,
            "Final PDF + supplementary re-upload; run the day-before "
            "checklist (status is 'ready', confirmation email archived, "
            "declarations answered).",
        ),
        milestone(
            paper, "T-0", HARD,
            f"PAPER DEADLINE ({dl['timezone'] or 'timezone unstated — confirm'}).",
        ),
    ]
    return ms


def under_review_milestones(dl: dict, profile: dict, notes: list[str]) -> list[dict]:
    review = profile.get("review") or {}
    day = dt.timedelta(days=1)
    ms: list[dict] = []
    rs, re_, notif = dl["rebuttal_start"], dl["rebuttal_end"], dl["notification"]
    if rs:
        fmt = review.get("rebuttal_format") or "format unstated"
        lim = review.get("rebuttal_limit") or "limit unstated"
        ms += [
            milestone(
                rs - 7 * day, "RS-7d", PREP,
                "Pre-rebuttal prep: block the rebuttal window on every "
                "author's calendar; decide who runs any extra experiments; "
                "re-read the venue's rebuttal rules.",
            ),
            milestone(
                rs - 2 * day, "RS-2d", PREP,
                "Clear calendars; set up the shared rebuttal doc; agree on "
                "the response strategy roles (triage-reviews skill when "
                "reviews land).",
            ),
            milestone(
                rs, "RS", HARD,
                f"Rebuttal window OPENS ({fmt}; {lim}).",
            ),
        ]
    else:
        notes.append(
            "no rebuttal_start in profile — either the venue has no rebuttal "
            "phase or the date is unpublished; confirm on the CFP/dates page"
        )
    if re_:
        ms += [
            milestone(
                re_ - 1 * day, "RE-1d", PREP,
                "Internal rebuttal freeze: final read-through against the "
                "character/page limit; submit a day early, not at the buzzer.",
            ),
            milestone(re_, "RE", HARD, "REBUTTAL DEADLINE."),
        ]
    if notif:
        ms.append(milestone(
            notif, "N", HARD,
            "Notification. On acceptance, re-run this script for the "
            "camera-ready phase (use --camera-ready if the profile lacks "
            "the date).",
        ))
    else:
        notes.append("notification date not in profile — check the venue dates page")
    return ms


def camera_ready_milestones(dl: dict, profile: dict, notes: list[str]) -> list[dict]:
    cam = dl["camera_ready"]
    cr = profile.get("camera_ready") or {}
    rail = str(cr.get("rail") or "").lower()
    rail_hint = RAIL_HINTS.get(
        rail, "Rail unknown — follow the acceptance email's instructions."
    )
    day = dt.timedelta(days=1)
    ms = [
        milestone(
            cam - 14 * day, "C-14d", PREP,
            f"Start the camera-ready rail. {rail_hint} (prepare-camera-ready "
            "skill has the step-by-step.)",
        ),
        milestone(
            cam - 7 * day, "C-7d", PREP,
            "De-anonymize; apply the extra-page budget "
            f"({cr.get('extra_pages') or 'none stated'}); insert the "
            "rights/DOI block or copyright notice; REGISTER an author "
            "(no-show policies exclude unregistered papers).",
        ),
        milestone(
            cam - 2 * day, "C-2d", PREP,
            "Final validation (PDF eXpress / TAPS compile / format check), "
            "file naming per the venue convention, upload.",
        ),
        milestone(cam, "C", HARD, "CAMERA-READY DEADLINE."),
    ]
    reqs = cr.get("requirements") or []
    if reqs:
        notes.append(
            "profile camera_ready.requirements checklist: "
            + " | ".join(str(r) for r in reqs)
        )
    return ms


def detect_phase(dl: dict, today: dt.date) -> str | None:
    if dl["paper"] and today <= dl["paper"]:
        return "pre-submission"
    review_end = dl["notification"] or dl["rebuttal_end"]
    if review_end and today <= review_end:
        return "under-review"
    if dl["camera_ready"] and today <= dl["camera_ready"]:
        return "camera-ready"
    return None


def render_md(plan: dict) -> str:
    out = [f"# Submission plan — {plan['venue']}", ""]
    out.append(f"- Profile: `{plan['profile_path']}` (verified {plan['verified_date']}, "
               f"confidence: {plan['confidence']})")
    out.append(f"- Track: {plan['track']}")
    out.append(f"- Today: {plan['today']}  |  Phase: **{plan['phase']}**")
    out.append(f"- Deadline timezone: {plan['timezone']}")
    if plan["timezone"] == "AoE":
        out.append("  - AoE = UTC-12: the deadline date ends at 11:59 UTC the "
                   "NEXT calendar day. Safe rule: treat it as your local "
                   "midnight on the deadline date.")
    out += ["", "## Key dates", "", "| Deadline | Date | Status |", "|---|---|---|"]
    for label, date, st in plan["key_dates"]:
        out.append(f"| {label} | {date} | {st} |")
    out += ["", f"## Milestones ({plan['phase']})", "",
            "| Date | Offset | Kind | Status | Action |", "|---|---|---|---|---|"]
    for m in plan["milestones"]:
        out.append(f"| {m['date']} | {m['offset']} | {m['kind']} | "
                   f"{m['status']} | {m['action']} |")
    overdue = [m for m in plan["milestones"] if m["status"] == "OVERDUE"]
    if overdue:
        out += ["", f"**{len(overdue)} milestone(s) OVERDUE — do these first:**"]
        out += [f"- {m['offset']}: {m['action']}" for m in overdue]
    if plan["gates"]:
        out += ["", "## Policy gates (verbatim from the profile — re-verify at the CFP)", ""]
        for label, text in plan["gates"]:
            out.append(f"- **{label}:** {text}")
    if plan["notes"]:
        out += ["", "## Notes", ""]
        out += [f"- {n}" for n in plan["notes"]]
    out += ["", "---",
            f"Dates come from the bundled profile, NOT from the live CFP. "
            f"Re-verify every deadline at {plan['cfp_url'] or 'the venue CFP'} "
            f"before relying on this plan — deadlines change mid-cycle.", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a phase-aware, backwards submission timeline from "
                    "a venues/conferences/<venue>.yml profile. Offline and "
                    "deterministic; never invents a date.",
        epilog="examples:\n"
               "  python3 build_timeline.py venues/conferences/neurips-2026.yml "
               "--today 2026-04-01\n"
               "  python3 build_timeline.py venues/conferences/icml-2026.yml "
               "--phase camera --format json\n"
               "exit codes: 0 ok | 1 no plannable dates | 2 usage/profile error",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("venue", help="path to venues/conferences/<venue>.yml")
    ap.add_argument("--track", help="track name substring (default: first track)")
    ap.add_argument("--today", help="plan as of this date, YYYY-MM-DD (default: today)")
    ap.add_argument("--camera-ready", dest="camera_ready", metavar="YYYY-MM-DD",
                    help="override/supply the camera-ready deadline when the "
                         "profile lists null (e.g. from the acceptance email)")
    ap.add_argument("--phase", choices=["auto", "pre", "review", "camera"],
                    default="auto", help="force a phase instead of auto-detecting")
    ap.add_argument("--format", choices=["md", "json"], default="md",
                    help="output format (default: md)")
    ap.add_argument("--venues-dir", help="venues/ root (auto-discovered by default)")
    args = ap.parse_args()

    notes: list[str] = []
    today = parse_iso(args.today, "--today", notes) if args.today else dt.date.today()
    if args.today and today is None:
        fail(f"--today must be YYYY-MM-DD, got {args.today!r}")

    try:
        profile, load_notes = load_profile(args.venue, args.venues_dir)
        track, track_note = pick_track(profile, args.track)
    except ProfileError as exc:
        fail(str(exc))
    notes += load_notes + [track_note]

    raw = profile.get("deadlines") or {}
    dl = {k: parse_iso(raw.get(k), f"deadlines.{k}", notes)
          for k in ("abstract", "paper", "rebuttal_start", "rebuttal_end",
                    "notification", "camera_ready")}
    dl["timezone"] = raw.get("timezone")
    if args.camera_ready:
        cam = parse_iso(args.camera_ready, "--camera-ready", notes)
        if cam is None:
            fail(f"--camera-ready must be YYYY-MM-DD, got {args.camera_ready!r}")
        if dl["camera_ready"] and dl["camera_ready"] != cam:
            notes.append(f"camera-ready overridden: profile says "
                         f"{dl['camera_ready']}, using {cam} from --camera-ready")
        dl["camera_ready"] = cam
    if not dl["timezone"]:
        notes.append("deadlines.timezone unstated in profile — confirm on the "
                     "CFP; do NOT assume AoE")

    phase = {"pre": "pre-submission", "review": "under-review",
             "camera": "camera-ready"}.get(args.phase) or detect_phase(dl, today)
    if phase is None:
        known = {k: v for k, v in dl.items() if k != "timezone" and v}
        if known:
            print("ERROR: every deadline in this profile "
                  f"({', '.join(f'{k}={v}' for k, v in known.items())}) is in "
                  f"the past relative to {today}. The profile is for a "
                  "finished cycle — refresh it via parse-cfp for the next "
                  "edition, or pass --camera-ready/--phase if a date is "
                  "merely unpublished.", file=sys.stderr)
        else:
            print("ERROR: this profile contains no usable deadlines at all — "
                  "re-run parse-cfp against the live CFP first.",
                  file=sys.stderr)
        return 1
    if phase == "pre-submission" and not dl["paper"]:
        fail("cannot plan pre-submission: deadlines.paper is null in the "
             "profile — refresh it via parse-cfp")
    if phase == "under-review" and not any(
            (dl["rebuttal_start"], dl["rebuttal_end"], dl["notification"])):
        fail("cannot plan under-review: no rebuttal/notification dates in the "
             "profile — check the venue dates page and refresh the profile")
    if phase == "camera-ready" and not dl["camera_ready"]:
        fail("cannot plan camera-ready: deadlines.camera_ready is null — pass "
             "--camera-ready YYYY-MM-DD from the acceptance email or venue "
             "dates page")

    builder = {"pre-submission": pre_submission_milestones,
               "under-review": under_review_milestones,
               "camera-ready": camera_ready_milestones}[phase]
    ms = builder(dl, profile, notes)
    ms.sort(key=lambda m: (m["date"], m["kind"] != HARD))
    for m in ms:
        m["status"] = status_of(m["date"], today, m["kind"])

    key_dates = []
    for label, key in (("Abstract registration", "abstract"), ("Paper", "paper"),
                       ("Rebuttal opens", "rebuttal_start"),
                       ("Rebuttal ends", "rebuttal_end"),
                       ("Notification", "notification"),
                       ("Camera-ready", "camera_ready")):
        d = dl[key]
        key_dates.append((label, str(d) if d else "unknown (null in profile)",
                          status_of(d, today, HARD) if d else "—"))

    review = profile.get("review") or {}
    gates = [(label, str(review[k]).strip())
             for label, k in (("Dual submission", "dual_submission"),
                              ("LLM policy", "llm_policy"))
             if review.get(k)]
    if review.get("submission_system"):
        sys_name = str(review["submission_system"]).lower()
        gates.append(("Submission system",
                      f"{review['submission_system']} — "
                      f"{review.get('submission_url') or 'URL not in profile'}. "
                      + SYSTEM_HINTS.get(sys_name, "See references/submission-systems.md.")))

    verified = profile.get("verified") or {}
    plan = {
        "venue": profile.get("name") or profile.get("id") or args.venue,
        "profile_path": args.venue,
        "track": (track or {}).get("name") if track else "n/a",
        "today": str(today),
        "phase": phase,
        "timezone": dl["timezone"] or "unstated",
        "cfp_url": profile.get("cfp_url"),
        "verified_date": str(verified.get("date") or "unknown"),
        "confidence": str(verified.get("confidence") or "unknown"),
        "key_dates": key_dates,
        "milestones": [{**m, "date": str(m["date"])} for m in ms],
        "gates": gates,
        "notes": notes,
    }

    if args.format == "json":
        json.dump(plan, sys.stdout, indent=2, default=str)
        print()
    else:
        sys.stdout.write(render_md(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
