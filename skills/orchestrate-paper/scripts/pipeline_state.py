#!/usr/bin/env python3
"""pipeline_state.py — durable goal/stage/checkpoint tracker for orchestrate-paper.

The orchestrator runs a goal -> plan -> execute -> verify -> reflect loop across
the paper lifecycle and CHECKPOINTS with the author at every stage gate. This
script is the durable state store behind that loop: it records the goal, each
stage's status, the verification signal that closed (or blocked) a stage, and
the pending checkpoint question — then prints "what's done / what's next /
blocked-on" so the author (or a resumed session) can see where things stand
WITHOUT re-running any prior sub-skill.

State lives next to the paper in the workspace:
  paper-workspace/
    pipeline-state.json   <- machine state (this script owns it)
    INDEX.md              <- human log; this script APPENDS one line per change

Design notes:
- Stdlib only. No network. JSON + Markdown so a human can read/hand-edit.
- The stage list mirrors references/pipeline-map.md. Stages are advisory: an
  unknown stage name is allowed (papers skip/reorder stages) and just added.
- This script tracks state; it does NOT run sub-skills, fetch anything, or
  judge correctness. Verification is external (see references/verification-
  signals.md) — you PASS the signal in via --signal.

Subcommands:
  init        create pipeline-state.json (and INDEX.md header) in the workspace
  set-goal    set/replace the one-line goal + target venue/track/deadline
  status      print goal, done / in-progress / next / blocked, pending checkpoint
  next        print only the next applicable (not-done, not-blocked) stage
  advance     mark a stage done, recording the external verification signal
  block       mark a stage blocked, recording what it's blocked on
  checkpoint  set the pending checkpoint question awaiting author sign-off
  signoff     clear the pending checkpoint (author approved) and optionally note

Exit codes:
  0  success
  1  a query found a blocking condition the caller should act on:
       - `status`/`next` when the pipeline is BLOCKED or AWAITING a checkpoint
         (lets a wrapper refuse to auto-advance past a gate)
  2  bad arguments / unusable workspace (missing state, write failure)

Examples:
  python3 pipeline_state.py init --workspace paper-workspace
  python3 pipeline_state.py set-goal --workspace paper-workspace \\
      --goal "submission-ready for NeurIPS 2026 main track" \\
      --venue "NeurIPS 2026" --track main --deadline "2026-05-15 AoE"
  python3 pipeline_state.py advance --workspace paper-workspace \\
      --stage preflight-check --signal "check_sections.py exit 0; 9pp <= 9 limit"
  python3 pipeline_state.py block --workspace paper-workspace \\
      --stage simulate-reviewers --on "missing ablation R2 will ask for"
  python3 pipeline_state.py checkpoint --workspace paper-workspace \\
      --stage write-rebuttal --question "Does the rebuttal answer R2 without over-promising?"
  python3 pipeline_state.py status --workspace paper-workspace
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

STATE_FILE = "pipeline-state.json"
INDEX_FILE = "INDEX.md"

# Default stage order, mirroring references/pipeline-map.md. Advisory only:
# unknown stages are accepted and appended (papers skip/reorder stages).
DEFAULT_STAGES = [
    "paper-profile",
    "select-venue",
    "parse-cfp",
    "find-papers",
    "fetch-paper",
    "literature-review",
    "study-exemplars",
    "write-abstract",
    "refactor-structure",
    "draft-related-work",
    "match-style",
    "polish-prose",
    "polish-tables-figures",
    "verify-citations",
    "verify-claims",
    "check-originality",
    "preflight-check",
    "simulate-reviewers",
    "benchmark-paper",
    "assess-paper",
    "tailor-to-venue",
    "anonymize-paper",
    "plan-submission",
    # 4b. artifact / reproducibility track (empirical papers; own deadline)
    "test-research-code",
    "refactor-research-code",
    "verify-results",
    "prepare-artifacts",
    "triage-reviews",
    "write-rebuttal",
    "prepare-camera-ready",
    "make-slides",
    "make-poster",
    "write-talk-script",
    "rehearse-qa",
]

# Stage status values.
PENDING = "pending"
IN_PROGRESS = "in-progress"
DONE = "done"
BLOCKED = "blocked"

INDEX_HEADER = (
    "# paper-workspace INDEX\n\n"
    "Running log of everything the research-paper skills generated for this\n"
    "paper, newest first. Managed in part by orchestrate-paper's\n"
    "pipeline_state.py; safe to hand-edit. Local only.\n\n"
    "Format: `YYYY-MM-DD · <skill> · <path-or-stage> · <one-line summary>`\n\n"
)


def _today() -> str:
    return _dt.date.today().isoformat()


def _die(msg: str, code: int = 2) -> "None":
    sys.stderr.write("pipeline_state: " + msg + "\n")
    sys.exit(code)


def _state_path(ws: str) -> str:
    return os.path.join(ws, STATE_FILE)


def _index_path(ws: str) -> str:
    return os.path.join(ws, INDEX_FILE)


def _new_state() -> dict:
    return {
        "goal": "",
        "target": {"venue": "", "track": "", "deadline": ""},
        "created": _today(),
        "updated": _today(),
        # ordered list of {stage, status, signal, blocked_on, updated}
        "stages": [
            {"stage": s, "status": PENDING, "signal": "",
             "blocked_on": "", "updated": _today()}
            for s in DEFAULT_STAGES
        ],
        # pending checkpoint awaiting author sign-off (None when clear)
        "checkpoint": None,  # {stage, question, raised}
    }


def _load(ws: str) -> dict:
    p = _state_path(ws)
    if not os.path.exists(p):
        _die("no %s in %s — run `init` first" % (STATE_FILE, ws))
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        _die("cannot read %s: %s" % (p, e))
    # tolerate hand-edited / partial files
    data.setdefault("goal", "")
    data.setdefault("target", {"venue": "", "track": "", "deadline": ""})
    data.setdefault("stages", [])
    data.setdefault("checkpoint", None)
    return data


def _save(ws: str, data: dict) -> None:
    data["updated"] = _today()
    p = _state_path(ws)
    try:
        os.makedirs(ws, exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, p)
    except OSError as e:
        _die("cannot write %s: %s" % (p, e))


def _append_index(ws: str, skill: str, where: str, summary: str) -> None:
    """Prepend a dated line under the header (newest first)."""
    p = _index_path(ws)
    line = "%s · %s · %s · %s\n" % (_today(), skill, where, summary)
    try:
        os.makedirs(ws, exist_ok=True)
        if not os.path.exists(p):
            body = INDEX_HEADER + line
        else:
            with open(p, encoding="utf-8") as fh:
                existing = fh.read()
            if existing.startswith(INDEX_HEADER):
                head, rest = INDEX_HEADER, existing[len(INDEX_HEADER):]
            else:
                # unknown/hand-written header: keep it, insert after first blank
                head, rest = "", existing
            body = head + line + rest
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    except OSError as e:
        _die("cannot write %s: %s" % (p, e))


def _find_stage(data: dict, name: str):
    for st in data["stages"]:
        if st["stage"] == name:
            return st
    return None


def _ensure_stage(data: dict, name: str) -> dict:
    st = _find_stage(data, name)
    if st is None:
        st = {"stage": name, "status": PENDING, "signal": "",
              "blocked_on": "", "updated": _today()}
        data["stages"].append(st)
    return st


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_init(args) -> int:
    ws = args.workspace
    p = _state_path(ws)
    if os.path.exists(p) and not args.force:
        _die("%s already exists — pass --force to reset it" % p)
    data = _new_state()
    _save(ws, data)
    if not os.path.exists(_index_path(ws)):
        _append_index(ws, "orchestrate-paper", "pipeline-state.json",
                      "initialized pipeline state")
    print("initialized %s" % p)
    print("next: set the goal —")
    print('  python3 pipeline_state.py set-goal --workspace %s \\' % ws)
    print('      --goal "submission-ready for VENUE TRACK" --venue "VENUE" '
          '--track TRACK --deadline "YYYY-MM-DD AoE"')
    return 0


def cmd_set_goal(args) -> int:
    data = _load(args.workspace)
    data["goal"] = args.goal.strip()
    if args.venue is not None:
        data["target"]["venue"] = args.venue.strip()
    if args.track is not None:
        data["target"]["track"] = args.track.strip()
    if args.deadline is not None:
        data["target"]["deadline"] = args.deadline.strip()
    _save(args.workspace, data)
    _append_index(args.workspace, "orchestrate-paper", "goal",
                  "goal set: " + data["goal"])
    tgt = data["target"]
    print("goal: " + data["goal"])
    if tgt["venue"] or tgt["deadline"]:
        print("target: %s %s (deadline: %s)"
              % (tgt["venue"] or "?", tgt["track"] or "", tgt["deadline"] or "?"))
    return 0


def cmd_advance(args) -> int:
    data = _load(args.workspace)
    st = _ensure_stage(data, args.stage)
    if not args.signal and not args.force:
        _die("refusing to mark '%s' done without --signal "
             "(the external verification signal). Verify on a measurable check, "
             "not self-judgment — see references/verification-signals.md. "
             "Use --force only for a stage with no oracle (then escalate to "
             "the author at the checkpoint)." % args.stage)
    st["status"] = DONE
    st["signal"] = args.signal.strip() if args.signal else "(no oracle; author-judged)"
    st["blocked_on"] = ""
    st["updated"] = _today()
    _save(args.workspace, data)
    _append_index(args.workspace, args.stage, "stage:done", st["signal"])
    print("done: %s  [%s]" % (args.stage, st["signal"]))
    nxt = _next_stage(data)
    if nxt:
        print("next: " + nxt["stage"])
    return 0


def cmd_block(args) -> int:
    data = _load(args.workspace)
    st = _ensure_stage(data, args.stage)
    if not args.on:
        _die("--on is required: say what '%s' is blocked on" % args.stage)
    st["status"] = BLOCKED
    st["blocked_on"] = args.on.strip()
    st["updated"] = _today()
    _save(args.workspace, data)
    _append_index(args.workspace, args.stage, "stage:blocked", args.on.strip())
    print("blocked: %s  -> %s" % (args.stage, args.on.strip()))
    return 0


def cmd_checkpoint(args) -> int:
    data = _load(args.workspace)
    _ensure_stage(data, args.stage)
    if not args.question:
        _die("--question is required: the checkpoint question for the author")
    data["checkpoint"] = {
        "stage": args.stage,
        "question": args.question.strip(),
        "raised": _today(),
    }
    _save(args.workspace, data)
    _append_index(args.workspace, args.stage, "checkpoint",
                  "awaiting author: " + args.question.strip())
    print("checkpoint raised for '%s' — awaiting author sign-off:" % args.stage)
    print("  " + args.question.strip())
    return 0


def cmd_signoff(args) -> int:
    data = _load(args.workspace)
    cp = data.get("checkpoint")
    if not cp:
        print("no pending checkpoint to sign off")
        return 0
    note = (" — " + args.note.strip()) if args.note else ""
    data["checkpoint"] = None
    _save(args.workspace, data)
    _append_index(args.workspace, cp["stage"], "checkpoint:approved",
                  "author signed off" + note)
    print("signed off checkpoint for '%s'%s" % (cp["stage"], note))
    return 0


def _next_stage(data: dict):
    """First stage that is pending or in-progress (not done, not blocked)."""
    for st in data["stages"]:
        if st["status"] in (PENDING, IN_PROGRESS):
            return st
    return None


def cmd_next(args) -> int:
    data = _load(args.workspace)
    cp = data.get("checkpoint")
    if cp:
        print("AWAITING CHECKPOINT (%s): %s" % (cp["stage"], cp["question"]))
        print("(sign off before advancing: `signoff`)")
        return 1
    blocked = [s for s in data["stages"] if s["status"] == BLOCKED]
    if blocked:
        print("BLOCKED:")
        for s in blocked:
            print("  %s -> %s" % (s["stage"], s["blocked_on"]))
        return 1
    nxt = _next_stage(data)
    if nxt is None:
        print("all tracked stages done")
        return 0
    print(nxt["stage"])
    return 0


def cmd_status(args) -> int:
    data = _load(args.workspace)
    tgt = data["target"]
    print("=" * 60)
    print("GOAL: " + (data["goal"] or "(unset — run set-goal)"))
    if tgt.get("venue") or tgt.get("deadline"):
        print("TARGET: %s %s   deadline: %s"
              % (tgt.get("venue") or "?", tgt.get("track") or "",
                 tgt.get("deadline") or "?"))
    print("updated: %s" % data.get("updated", "?"))
    print("=" * 60)

    done = [s for s in data["stages"] if s["status"] == DONE]
    inprog = [s for s in data["stages"] if s["status"] == IN_PROGRESS]
    blocked = [s for s in data["stages"] if s["status"] == BLOCKED]

    print("\nDONE (%d):" % len(done))
    if done:
        for s in done:
            print("  [x] %-22s %s" % (s["stage"], s.get("signal", "")))
    else:
        print("  (none yet)")

    if inprog:
        print("\nIN PROGRESS:")
        for s in inprog:
            print("  [~] " + s["stage"])

    nxt = _next_stage(data)
    print("\nNEXT:")
    print("  -> " + (nxt["stage"] if nxt else "(all tracked stages done)"))

    print("\nBLOCKED-ON (%d):" % len(blocked))
    if blocked:
        for s in blocked:
            print("  [!] %-22s -> %s" % (s["stage"], s["blocked_on"]))
    else:
        print("  (nothing blocked)")

    rc = 0
    cp = data.get("checkpoint")
    if cp:
        print("\nAWAITING AUTHOR CHECKPOINT (%s):" % cp["stage"])
        print("  Q: " + cp["question"])
        print("  (author must sign off before the next stage — `signoff`)")
        rc = 1
    if blocked:
        rc = 1
    print()
    return rc


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipeline_state.py",
        description="Durable goal/stage/checkpoint tracker for orchestrate-paper. "
                    "Prints what's done / what's next / blocked-on. Tracks state "
                    "only; verification is external (--signal).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="State: <workspace>/pipeline-state.json + INDEX.md. Stdlib only, "
               "no network. See references/pipeline-map.md and "
               "references/verification-signals.md.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_ws(sp):
        sp.add_argument("--workspace", "-w", default="paper-workspace",
                        help="workspace dir (default: paper-workspace)")

    sp = sub.add_parser("init", help="create pipeline-state.json in the workspace")
    add_ws(sp)
    sp.add_argument("--force", action="store_true",
                    help="overwrite an existing state file")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("set-goal", help="set the goal + target venue/track/deadline")
    add_ws(sp)
    sp.add_argument("--goal", required=True, help="one-line goal")
    sp.add_argument("--venue", help="target venue, e.g. 'NeurIPS 2026'")
    sp.add_argument("--track", help="target track, e.g. 'main'")
    sp.add_argument("--deadline", help="deadline, e.g. '2026-05-15 AoE'")
    sp.set_defaults(func=cmd_set_goal)

    sp = sub.add_parser("status", help="print done / next / blocked / checkpoint")
    add_ws(sp)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("next", help="print only the next applicable stage")
    add_ws(sp)
    sp.set_defaults(func=cmd_next)

    sp = sub.add_parser("advance", help="mark a stage done with its verification signal")
    add_ws(sp)
    sp.add_argument("--stage", required=True, help="stage name (see pipeline-map.md)")
    sp.add_argument("--signal", default="",
                    help="external verification signal that closed the stage "
                         "(e.g. 'check_bibtex.py exit 0; 42/42 DOIs resolve')")
    sp.add_argument("--force", action="store_true",
                    help="allow advancing without --signal (no-oracle stage; "
                         "still escalate to the author at the checkpoint)")
    sp.set_defaults(func=cmd_advance)

    sp = sub.add_parser("block", help="mark a stage blocked on something")
    add_ws(sp)
    sp.add_argument("--stage", required=True)
    sp.add_argument("--on", required=True, help="what it's blocked on")
    sp.set_defaults(func=cmd_block)

    sp = sub.add_parser("checkpoint", help="raise the author checkpoint question")
    add_ws(sp)
    sp.add_argument("--stage", required=True)
    sp.add_argument("--question", required=True, help="checkpoint question for the author")
    sp.set_defaults(func=cmd_checkpoint)

    sp = sub.add_parser("signoff", help="clear the pending checkpoint (author approved)")
    add_ws(sp)
    sp.add_argument("--note", help="optional note about the decision")
    sp.set_defaults(func=cmd_signoff)

    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
