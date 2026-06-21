#!/usr/bin/env python3
"""Read, write, validate, and template .paper-memory/profile.yml — stdlib only.

`profile.yml` records the author's paper positioning so every other skill in
this repo can behave context-awarely (see SKILL.md). This module is the single
deterministic gate for that file: it parses a small YAML subset, validates
every field against a closed vocabulary, writes a profile back out as
canonical YAML (no third-party emitter), and can emit a blank annotated
template for a human to fill in.

It does NOT interview the user — the skill (the agent) does that, then calls
`--write` (or hands fields to write_profile) to persist the answers. Keeping
the I/O here means validation is identical no matter which skill touches the
file.

Subcommands:
    template            print a blank annotated profile.yml to stdout
    validate <path>     load + validate; report problems; exit 1 if invalid
    show <path>         load, validate, print normalized JSON
    write <path>        build/update a profile from --field key=value pairs
    schema              print the field vocabulary as JSON (for agents/tools)

Exit codes: 0 ok, 1 validation failed, 2 bad arguments / IO error.

Examples:
    python3 profile_io.py template > .paper-memory/profile.yml
    python3 profile_io.py validate .paper-memory/profile.yml
    python3 profile_io.py write .paper-memory/profile.yml \\
        --field vertical=systems --field risk_appetite=ambitious \\
        --field contribution_type=system --field venue_tier=top \\
        --field paper_title="Planet-scale map matching"
    python3 profile_io.py show .paper-memory/profile.yml
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from datetime import date

SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Closed vocabularies. These are the "verticals" / positioning axes that
# downstream skills branch on. Keep them small and stable; changing a token
# is a breaking change for consumers, so prefer adding over renaming.
# ---------------------------------------------------------------------------

VERTICALS = {
    "systems": "Systems/tech-heavy: built artifact, architecture, engineering, scale.",
    "theory": "Theory-heavy: proofs/analysis are the contribution.",
    "applied": "Applied/domain: method applied to a real domain problem.",
    "empirical": "Empirical/measurement: the study/measurement is the contribution.",
    "survey": "Survey/review: synthesizes a body of work.",
    "position": "Position/vision: argues a stance or research agenda.",
}

CONTRIBUTION_TYPES = {
    "method": "New method/algorithm/model.",
    "system": "System/tool/artifact.",
    "theory": "Theorem/analysis/lower-bound.",
    "dataset": "Dataset/benchmark.",
    "empirical": "Measurement/empirical study or reproducibility.",
    "application": "Application of known methods to a new domain.",
    "survey": "Survey/review.",
    "position": "Position/vision paper.",
}

VENUE_TIERS = {
    "top": "Top-tier / flagship (e.g. NeurIPS, SIGMOD, CHI main track).",
    "specialized": "Strong specialized venue or top workshop.",
    "regional": "Regional / second-tier conference.",
    "journal": "Journal (no fixed page limit, slower cycle).",
    "workshop": "Workshop / short paper.",
    "preprint": "Preprint / arXiv only for now.",
    "undecided": "Not chosen yet — keep options open.",
}

RISK_APPETITES = {
    "safe": "Safe/incremental: defensible delta, minimize reviewer attack surface.",
    "balanced": "Balanced: solid core with one ambitious claim.",
    "ambitious": "Ambitious/high-variance: big claim, accept polarized reviews.",
}

AUDIENCES = {
    "specialists": "Sub-field specialists who know the area deeply.",
    "broad-field": "The broad field (cross-area readers at a flagship).",
    "practitioners": "Practitioners/industry.",
    "interdisciplinary": "Readers from adjacent disciplines.",
}

# writing_preferences sub-vocabularies
PERSON = {"first-person-we", "first-person-i", "impersonal-passive", "venue-default"}
TONE = {"formal", "plain", "assertive", "hedged", "venue-default"}
NOTATION = {"heavy", "light", "venue-default"}

# Fields that may be free text (validated only for type=string, length).
FREE_TEXT_FIELDS = {
    "paper_title",
    "topic",
    "one_line_pitch",
    "key_claim",
}
# Free-text list fields.
FREE_LIST_FIELDS = {
    "constraints",
    "preferred_terms",
    "avoid_terms",
    "prior_papers",
    "target_venues",
}

MAX_TEXT = 500  # generous cap; this is positioning notes, not the paper.


class ProfileError(Exception):
    """User-facing validation/IO error."""


# ---------------------------------------------------------------------------
# Tiny YAML-subset parser (mappings, block lists, inline [..] lists, quoted
# scalars, comments). Sufficient for profile.yml, which this module also
# writes — so the round-trip is closed. Not a general YAML parser.
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$")


def _cut_comment(s: str) -> str:
    out: list[str] = []
    in_s = in_d = False
    i = 0
    while i < len(s):
        c = s[i]
        if in_d:
            if c == "\\" and i + 1 < len(s):
                out.append(s[i : i + 2])
                i += 2
                continue
            if c == '"':
                in_d = False
            out.append(c)
        elif in_s:
            if c == "'":
                in_s = False
            out.append(c)
        else:
            if c == '"':
                in_d = True
            elif c == "'":
                in_s = True
            elif c == "#" and (not out or out[-1] in " \t"):
                break
            out.append(c)
        i += 1
    return "".join(out)


def _read_quoted(v: str) -> str:
    q = v[0]
    body: list[str] = []
    i = 1
    while i < len(v):
        c = v[i]
        if q == '"' and c == "\\" and i + 1 < len(v):
            nxt = v[i + 1]
            body.append(nxt if nxt in ('"', "\\") else "\\" + nxt)
            i += 2
            continue
        if q == "'" and c == "'":
            if i + 1 < len(v) and v[i + 1] == "'":
                body.append("'")
                i += 2
                continue
            break
        if q == '"' and c == '"':
            break
        body.append(c)
        i += 1
    return "".join(body)


def _parse_scalar(v: str):
    v = v.strip()
    if v == "" or v in ("~", "null", "Null", "NULL"):
        return None
    if v[0] in ("'", '"'):
        return _read_quoted(v)
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in _split_inline(inner)]
    try:
        return int(v)
    except ValueError:
        return v


def _split_inline(inner: str) -> list[str]:
    """Split an inline-list body on commas not inside quotes."""
    parts: list[str] = []
    cur: list[str] = []
    in_s = in_d = False
    for c in inner:
        if in_d:
            cur.append(c)
            if c == '"':
                in_d = False
        elif in_s:
            cur.append(c)
            if c == "'":
                in_s = False
        elif c == '"':
            in_d = True
            cur.append(c)
        elif c == "'":
            in_s = True
            cur.append(c)
        elif c == ",":
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    parts.append("".join(cur))
    return parts


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_content(lines: list[str], i: int) -> int:
    while i < len(lines):
        if _cut_comment(lines[i]).strip():
            return i
        i += 1
    return len(lines)


def _parse_node(lines: list[str], i: int, min_indent: int):
    j = _next_content(lines, i)
    if j >= len(lines):
        return None, j
    ind = _indent(_cut_comment(lines[j]))
    if ind < min_indent:
        return None, j
    stripped = _cut_comment(lines[j]).strip()
    if stripped == "-" or stripped.startswith("- "):
        return _parse_list(lines, j, ind)
    return _parse_mapping(lines, j, ind)


def _parse_mapping(lines: list[str], i: int, indent: int):
    data: dict = {}
    while True:
        j = _next_content(lines, i)
        if j >= len(lines):
            return data, j
        cut = _cut_comment(lines[j])
        ind = _indent(cut)
        if ind != indent:
            return data, j
        stripped = cut.strip()
        if stripped.startswith("- "):
            return data, j
        m = _KEY_RE.match(stripped)
        if not m:
            raise ProfileError(f"line {j + 1}: cannot parse: {stripped!r}")
        key, vt = m.group(1), (m.group(2) or "").strip()
        if vt == "":
            k = _next_content(lines, j + 1)
            if k < len(lines) and _indent(_cut_comment(lines[k])) > indent:
                data[key], i = _parse_node(lines, j + 1, indent + 1)
            else:
                data[key], i = None, j + 1
        else:
            data[key], i = _parse_scalar(vt), j + 1


def _parse_list(lines: list[str], i: int, indent: int):
    items: list = []
    while True:
        j = _next_content(lines, i)
        if j >= len(lines):
            return items, j
        cut = _cut_comment(lines[j])
        ind = _indent(cut)
        stripped = cut.strip()
        if ind != indent or not (stripped == "-" or stripped.startswith("- ")):
            return items, j
        content = stripped[1:].strip()
        items.append(_parse_scalar(content))
        i = j + 1


def parse_yaml(text: str):
    lines = text.splitlines()
    value, _ = _parse_node(lines, 0, 0)
    return value if value is not None else {}


# ---------------------------------------------------------------------------
# Canonical YAML emitter (so we never depend on PyYAML).
# ---------------------------------------------------------------------------

_BARE_RE = re.compile(r"^[A-Za-z0-9 ./_+()&,'%-]*$")


def _emit_scalar(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    s = str(v)
    if s == "" or not _BARE_RE.match(s) or s.lower() in (
        "null",
        "true",
        "false",
        "yes",
        "no",
        "~",
    ):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def emit_yaml(data: dict) -> str:
    """Emit a profile dict as canonical, comment-free YAML (stable key order)."""
    lines: list[str] = []
    for key in TEMPLATE_ORDER:
        if key not in data:
            continue
        val = data[key]
        if isinstance(val, dict):
            lines.append(f"{key}:")
            for sk in WRITING_PREF_ORDER:
                if sk in val:
                    lines.append(f"  {sk}: {_emit_scalar(val[sk])}")
            for sk, sv in val.items():  # any extra keys, stable-ish
                if sk not in WRITING_PREF_ORDER:
                    lines.append(f"  {sk}: {_emit_scalar(sv)}")
        elif isinstance(val, list):
            if not val:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in val:
                    lines.append(f"  - {_emit_scalar(item)}")
        else:
            lines.append(f"{key}: {_emit_scalar(val)}")
    return "\n".join(lines) + "\n"


# Stable key order for emission/template.
TEMPLATE_ORDER = [
    "schema_version",
    "updated",
    "paper_title",
    "topic",
    "one_line_pitch",
    "key_claim",
    "vertical",
    "contribution_type",
    "audience",
    "venue_tier",
    "target_venues",
    "risk_appetite",
    "writing_preferences",
    "preferred_terms",
    "avoid_terms",
    "prior_papers",
    "constraints",
    "notes",
]
WRITING_PREF_ORDER = ["person", "tone", "notation", "british_spelling"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

ENUM_FIELDS = {
    "vertical": VERTICALS,
    "contribution_type": CONTRIBUTION_TYPES,
    "audience": AUDIENCES,
    "venue_tier": VENUE_TIERS,
    "risk_appetite": RISK_APPETITES,
}

REQUIRED = ["vertical", "contribution_type", "venue_tier", "risk_appetite"]


def validate(profile) -> list[str]:
    """Return a list of human-readable problems; empty list means valid."""
    problems: list[str] = []
    if not isinstance(profile, dict):
        return ["top level of profile.yml is not a mapping"]

    sv = profile.get("schema_version")
    if sv is not None and sv != SCHEMA_VERSION:
        problems.append(
            f"schema_version is {sv!r}; this tool understands {SCHEMA_VERSION}"
        )

    for field in REQUIRED:
        if not profile.get(field):
            problems.append(f"required field '{field}' is missing or empty")

    for field, vocab in ENUM_FIELDS.items():
        val = profile.get(field)
        if val is None:
            continue
        if not isinstance(val, str) or val not in vocab:
            problems.append(
                f"{field}={val!r} is not one of: {', '.join(sorted(vocab))}"
            )

    for field in FREE_TEXT_FIELDS:
        val = profile.get(field)
        if val is None:
            continue
        if not isinstance(val, (str, int)):
            problems.append(f"{field} should be text, got {type(val).__name__}")
        elif len(str(val)) > MAX_TEXT:
            problems.append(f"{field} is too long (>{MAX_TEXT} chars)")

    for field in FREE_LIST_FIELDS:
        val = profile.get(field)
        if val is None:
            continue
        if not isinstance(val, list):
            problems.append(f"{field} should be a list")
        else:
            for item in val:
                if not isinstance(item, (str, int)):
                    problems.append(f"{field} has a non-text item: {item!r}")

    wp = profile.get("writing_preferences")
    if wp is not None:
        if not isinstance(wp, dict):
            problems.append("writing_preferences should be a mapping")
        else:
            _check_enum(wp, "person", PERSON, problems)
            _check_enum(wp, "tone", TONE, problems)
            _check_enum(wp, "notation", NOTATION, problems)
            bs = wp.get("british_spelling")
            if bs is not None and not isinstance(bs, bool):
                problems.append("writing_preferences.british_spelling must be true/false")

    return problems


def _check_enum(d: dict, key: str, vocab: set, problems: list[str]) -> None:
    val = d.get(key)
    if val is None:
        return
    if val not in vocab:
        problems.append(
            f"writing_preferences.{key}={val!r} not one of: {', '.join(sorted(vocab))}"
        )


# ---------------------------------------------------------------------------
# Load / write
# ---------------------------------------------------------------------------


def load_profile(path: str | pathlib.Path) -> dict:
    p = pathlib.Path(path)
    if not p.is_file():
        raise ProfileError(f"profile not found: {p}")
    try:
        data = parse_yaml(p.read_text(encoding="utf-8"))
    except ProfileError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ProfileError(f"failed to parse {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"{p}: top level is not a mapping")
    return data


def write_profile(path: str | pathlib.Path, profile: dict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    profile.setdefault("schema_version", SCHEMA_VERSION)
    profile["updated"] = date.today().isoformat()
    p.write_text(emit_yaml(profile), encoding="utf-8")


# Keys that live under writing_preferences when set via --field wp.<key>=...
_WP_PREFIX = "wp."


def apply_fields(profile: dict, pairs: list[str]) -> dict:
    """Apply key=value pairs (CLI --field). Lists use comma-separation.

    `wp.<key>=...` and `writing_preferences.<key>=...` target the nested map.
    """
    for pair in pairs:
        if "=" not in pair:
            raise ProfileError(f"--field expects key=value, got {pair!r}")
        key, _, raw = pair.partition("=")
        key = key.strip()
        raw = raw.strip()
        if key.startswith(_WP_PREFIX) or key.startswith("writing_preferences."):
            sub = key.split(".", 1)[1]
            wp = profile.setdefault("writing_preferences", {})
            if not isinstance(wp, dict):
                raise ProfileError("writing_preferences is not a mapping")
            wp[sub] = _coerce(sub, raw)
        elif key in FREE_LIST_FIELDS:
            profile[key] = [x.strip() for x in raw.split(",") if x.strip()]
        else:
            profile[key] = _coerce(key, raw)
    return profile


def _coerce(key: str, raw: str):
    if key == "british_spelling":
        return raw.lower() in ("true", "1", "yes")
    if raw.lower() in ("true", "false") and key not in FREE_TEXT_FIELDS:
        return raw.lower() == "true"
    return raw


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


def blank_template() -> str:
    """An annotated blank profile.yml a human can fill in by hand."""
    def opts(d: dict) -> str:
        return " | ".join(sorted(d))

    return f"""\
# .paper-memory/profile.yml — author/paper positioning (schema v{SCHEMA_VERSION})
# Written by the paper-profile skill; read by benchmark-paper,
# simulate-reviewers, polish-prose, match-style, tailor-to-venue, write-abstract.
# It is LOCAL to your paper directory. Add `.paper-memory/` to .gitignore
# unless you deliberately want to version it. Never uploaded anywhere.
# Fill in the values; delete the option you don't want. Required fields are
# marked REQUIRED. Re-run `paper-profile` to update as the paper evolves.

schema_version: {SCHEMA_VERSION}
updated: {date.today().isoformat()}        # auto-set on write

# --- what the paper is ------------------------------------------------------
paper_title:                # working title (free text)
topic:                      # one phrase: the area/problem
one_line_pitch:             # the elevator pitch in one sentence
key_claim:                  # the single most important claim reviewers must believe

# --- positioning axes (downstream skills branch on these) -------------------
vertical:                   # REQUIRED — one of: {opts(VERTICALS)}
contribution_type:          # REQUIRED — one of: {opts(CONTRIBUTION_TYPES)}
audience:                   # one of: {opts(AUDIENCES)}
venue_tier:                 # REQUIRED — one of: {opts(VENUE_TIERS)}
target_venues: []           # e.g. [sigspatial-2026, vldb-2027]
risk_appetite:              # REQUIRED — one of: {opts(RISK_APPETITES)}

# --- writing preferences (consumed by polish-prose / match-style) -----------
writing_preferences:
  person:                   # {opts(PERSON)}
  tone:                     # {opts(TONE)}
  notation:                 # {opts(NOTATION)}
  british_spelling:         # true | false
preferred_terms: []         # terms/acronyms to use consistently
avoid_terms: []             # words to avoid (e.g. AI tells, banned jargon)

# --- context ----------------------------------------------------------------
prior_papers: []            # paths/ids of your earlier papers (for match-style)
constraints: []             # hard limits: deadline, anonymized, no new experiments
notes:                      # anything else a skill should know
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _schema_json() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "required": REQUIRED,
        "enums": {
            "vertical": VERTICALS,
            "contribution_type": CONTRIBUTION_TYPES,
            "audience": AUDIENCES,
            "venue_tier": VENUE_TIERS,
            "risk_appetite": RISK_APPETITES,
            "writing_preferences.person": sorted(PERSON),
            "writing_preferences.tone": sorted(TONE),
            "writing_preferences.notation": sorted(NOTATION),
        },
        "free_text": sorted(FREE_TEXT_FIELDS),
        "free_lists": sorted(FREE_LIST_FIELDS),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Read/write/validate .paper-memory/profile.yml (stdlib only).",
        epilog="Exit codes: 0 ok, 1 validation failed, 2 bad args / IO error.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("template", help="print a blank annotated profile.yml")
    sub.add_parser("schema", help="print the field vocabulary as JSON")

    p_val = sub.add_parser("validate", help="validate an existing profile.yml")
    p_val.add_argument("path")

    p_show = sub.add_parser("show", help="validate then print normalized JSON")
    p_show.add_argument("path")

    p_wr = sub.add_parser("write", help="create/update a profile from --field pairs")
    p_wr.add_argument("path")
    p_wr.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="key=value",
        help="set a field; repeatable. Lists are comma-separated. "
        "Nested: wp.person=first-person-we",
    )
    p_wr.add_argument(
        "--from",
        dest="from_path",
        help="start from an existing profile and update it",
    )
    p_wr.add_argument(
        "--allow-invalid",
        action="store_true",
        help="write even if validation fails (still prints problems)",
    )

    args = ap.parse_args(argv)

    try:
        if args.cmd == "template":
            sys.stdout.write(blank_template())
            return 0

        if args.cmd == "schema":
            json.dump(_schema_json(), sys.stdout, indent=2)
            print()
            return 0

        if args.cmd == "validate":
            profile = load_profile(args.path)
            problems = validate(profile)
            if problems:
                print(f"INVALID — {len(problems)} problem(s):", file=sys.stderr)
                for pr in problems:
                    print(f"  - {pr}", file=sys.stderr)
                return 1
            print(f"VALID — {args.path} ({_summary(profile)})")
            return 0

        if args.cmd == "show":
            profile = load_profile(args.path)
            problems = validate(profile)
            json.dump(
                {"profile": profile, "valid": not problems, "problems": problems},
                sys.stdout,
                indent=2,
                default=str,
            )
            print()
            return 0 if not problems else 1

        if args.cmd == "write":
            base = load_profile(args.from_path) if args.from_path else {}
            profile = apply_fields(base, args.field)
            problems = validate(profile)
            if problems and not args.allow_invalid:
                print(
                    f"NOT written — {len(problems)} validation problem(s):",
                    file=sys.stderr,
                )
                for pr in problems:
                    print(f"  - {pr}", file=sys.stderr)
                print(
                    "Fix the --field values, or pass --allow-invalid to write a "
                    "partial draft.",
                    file=sys.stderr,
                )
                return 1
            write_profile(args.path, profile)
            if problems:
                print("WROTE (with problems):", file=sys.stderr)
                for pr in problems:
                    print(f"  - {pr}", file=sys.stderr)
            print(f"wrote {args.path} ({_summary(profile)})")
            return 0

    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 2  # pragma: no cover


def _summary(p: dict) -> str:
    bits = [str(p.get(f)) for f in ("vertical", "contribution_type", "venue_tier", "risk_appetite") if p.get(f)]
    return ", ".join(bits) if bits else "empty"


if __name__ == "__main__":
    sys.exit(main())
