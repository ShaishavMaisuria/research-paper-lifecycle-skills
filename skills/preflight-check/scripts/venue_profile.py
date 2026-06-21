#!/usr/bin/env python3
"""Load and merge a venue profile YAML (conference + family) — stdlib only.

This module is the shared profile loader for the preflight-check scripts.
It implements a deliberately small YAML-subset parser sufficient for the
files under venues/ (nested mappings, block lists, inline lists, quoted
scalars, `>`/`|` block scalars, comments). It is NOT a general YAML parser.

CLI usage (also doubles as a smoke test):
    python3 venue_profile.py venues/conferences/neurips-2026.yml [--track Main]
prints the merged profile as JSON. Exit codes: 0 ok, 2 failure.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# YAML-subset parsing
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$")


class ProfileError(Exception):
    """Raised on any parse/load problem; message is user-facing."""


def _cut_comment(s: str) -> str:
    """Remove a trailing `# comment` outside of quotes."""
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
                if i + 1 < len(s) and s[i + 1] == "'":
                    out.append("''")
                    i += 2
                    continue
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
    """Parse a leading quoted scalar; returns the unescaped body."""
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
        return [_parse_scalar(p.strip()) for p in inner.split(",")]
    try:
        return int(v)
    except ValueError:
        return v


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_content(lines: list[str], i: int) -> int:
    """Index of the next line that is not blank or comment-only."""
    while i < len(lines):
        cut = _cut_comment(lines[i])
        if cut.strip():
            return i
        i += 1
    return len(lines)


def _consume_block_scalar(lines: list[str], i: int, indent: int, marker: str):
    """Consume a `>` / `|` block scalar starting after line i-1."""
    collected: list[str] = []
    while i < len(lines):
        raw = lines[i]
        if raw.strip() == "":
            collected.append("")
            i += 1
            continue
        if _indent(raw) <= indent:
            break
        collected.append(raw)
        i += 1
    while collected and collected[-1] == "":
        collected.pop()
    nonblank = [ln for ln in collected if ln.strip()]
    if not nonblank:
        return "", i
    dedent = min(_indent(ln) for ln in nonblank)
    body = [ln[dedent:] if ln.strip() else "" for ln in collected]
    if marker.startswith("|"):
        text = "\n".join(body)
    else:  # folded
        text = " ".join(ln.strip() for ln in body if ln.strip())
    return text.strip(), i


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
            raise ProfileError(f"line {j + 1}: cannot parse mapping line: {stripped!r}")
        key, vt = m.group(1), (m.group(2) or "").strip()
        if vt in (">", ">-", "|", "|-"):
            data[key], i = _consume_block_scalar(lines, j + 1, indent, vt)
        elif vt == "":
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
        if content and _KEY_RE.match(content):
            # list item is a mapping: rewrite "- key: v" as an indented key line
            lines[j] = " " * (indent + 2) + content
            item, i = _parse_mapping(lines, j, indent + 2)
            items.append(item)
        else:
            items.append(_parse_scalar(content))
            i = j + 1


def parse_yaml(text: str):
    """Parse the YAML subset used by venues/*.yml into dict/list/scalars."""
    lines = text.splitlines()  # mutable copy; _parse_list rewrites item lines
    value, _ = _parse_node(lines, 0, 0)
    return value


# ---------------------------------------------------------------------------
# Profile loading and family merge
# ---------------------------------------------------------------------------


def _deep_merge(base, over):
    """Conference values win, except explicit nulls fall back to family."""
    if over is None:
        return base
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _deep_merge(base.get(k), v)
        return out
    return over


def find_venues_dir(venue_path: pathlib.Path) -> pathlib.Path | None:
    """Walk up from the venue file looking for the venues/ root."""
    for parent in venue_path.resolve().parents:
        if (parent / "families").is_dir() or (parent / "schema.yml").is_file():
            return parent
        if (parent / "venues" / "families").is_dir():
            return parent / "venues"
    return None


def load_profile(venue_path: str | pathlib.Path, venues_dir: str | None = None):
    """Load a conference profile, merging its family profile if present.

    Returns (profile_dict, notes_list). Raises ProfileError on failure.
    """
    path = pathlib.Path(venue_path)
    if not path.is_file():
        raise ProfileError(f"venue profile not found: {path}")
    try:
        prof = parse_yaml(path.read_text(encoding="utf-8"))
    except ProfileError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ProfileError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(prof, dict):
        raise ProfileError(f"{path}: top level is not a mapping")

    notes: list[str] = []
    family = prof.get("family")
    if family:
        vdir = pathlib.Path(venues_dir) if venues_dir else find_venues_dir(path)
        fam_path = vdir / "families" / f"{family}.yml" if vdir else None
        if fam_path and fam_path.is_file():
            fam = parse_yaml(fam_path.read_text(encoding="utf-8"))
            if isinstance(fam, dict):
                merged = _deep_merge(fam, prof)
                merged["id"] = prof.get("id", merged.get("id"))
                prof = merged
                notes.append(f"merged family profile: {fam_path}")
        else:
            notes.append(
                f"family '{family}' profile not found (pass --venues-dir); "
                "using the conference profile alone"
            )
    return prof, notes


def pick_track(profile: dict, name: str | None):
    """Resolve --track against profile tracks. Returns (track|None, note)."""
    tracks = profile.get("tracks") or []
    tracks = [t for t in tracks if isinstance(t, dict)]
    if not tracks:
        return None, "profile lists no tracks; page-limit checks are skipped"
    if name:
        hits = [t for t in tracks if name.lower() in str(t.get("name", "")).lower()]
        if len(hits) == 1:
            return hits[0], f"track: {hits[0].get('name')}"
        if not hits:
            avail = ", ".join(str(t.get("name")) for t in tracks)
            raise ProfileError(f"no track matches '{name}'; available: {avail}")
        avail = ", ".join(str(t.get("name")) for t in hits)
        raise ProfileError(f"--track '{name}' is ambiguous: {avail}")
    return tracks[0], (
        f"no --track given; defaulted to first track '{tracks[0].get('name')}'"
        + (f" of {len(tracks)}" if len(tracks) > 1 else "")
    )


_DOCCLASS_RE = re.compile(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}")


def expected_documentclass(profile: dict):
    """Parse format.documentclass into (class_name, [options]) or (None, [])."""
    fmt = profile.get("format") or {}
    inv = fmt.get("documentclass") or ""
    m = _DOCCLASS_RE.search(inv)
    if not m:
        return None, []
    opts = [o.strip() for o in (m.group(1) or "").split(",") if o.strip()]
    return m.group(2).strip(), opts


def expected_style_package(profile: dict) -> str | None:
    """For neurips-style venues, the year-versioned .sty token to expect."""
    fmt = profile.get("format") or {}
    if fmt.get("template") != "neurips":
        return None
    pid = str(profile.get("id") or "")
    year = profile.get("year")
    m = re.match(r"(neurips|icml|iclr)-(\d{4})", pid)
    if m:
        venue, yr = m.group(1), m.group(2)
    elif year:
        venue, yr = "neurips", str(year)
    else:
        return None
    return {
        "neurips": f"neurips_{yr}",
        "icml": f"icml{yr}",
        "iclr": f"iclr{yr}_conference",
    }[venue]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Parse a venue profile YAML (merging its family) and print "
        "the result as JSON. Shared loader for the preflight-check scripts."
    )
    ap.add_argument("venue", help="path to venues/conferences/<venue>.yml")
    ap.add_argument("--venues-dir", help="venues/ root (auto-discovered by default)")
    ap.add_argument("--track", help="track name substring to resolve and print")
    args = ap.parse_args()
    try:
        profile, notes = load_profile(args.venue, args.venues_dir)
        track, note = pick_track(profile, args.track)
        notes.append(note)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    json.dump(
        {"profile": profile, "resolved_track": track, "notes": notes},
        sys.stdout,
        indent=2,
        default=str,
    )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
