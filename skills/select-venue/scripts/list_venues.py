#!/usr/bin/env python3
"""List machine-readable venue profiles with deadline proximity.

Reads every profile in venues/conferences/*.yml (schema: venues/schema.yml),
computes days-until-deadline for the abstract/paper deadlines, and prints a
table sorted by next upcoming submission deadline (or JSON with --json).

Stdlib only — ships a minimal YAML-subset parser tuned to the venue schema
(nested maps, lists of maps, inline lists, quoted scalars, '>' folded blocks,
comments). It is NOT a general YAML parser.

IMPORTANT: profiles are a starting point, never ground truth. Re-verify every
deadline and page limit against the live `cfp_url` before relying on it.

Examples:
  python3 scripts/list_venues.py
  python3 scripts/list_venues.py --upcoming-only
  python3 scripts/list_venues.py --family acm-sigconf --json
  python3 scripts/list_venues.py --today 2026-06-11   # reproducible runs
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# --------------------------------------------------------------------------
# Minimal YAML-subset parser (venue-profile schema only)
# --------------------------------------------------------------------------

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INT_RE = re.compile(r"^-?\d+$")
_KEY_RE = re.compile(r"^([A-Za-z0-9_\-]+):\s*(.*)$")


def _strip_comment(s):
    """Strip an inline ' # ...' comment, respecting single/double quotes."""
    in_single = in_double = False
    for i, c in enumerate(s):
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == "#" and not in_single and not in_double:
            if i == 0 or s[i - 1] in " \t":
                return s[:i].rstrip()
    return s.rstrip()


def _parse_scalar(v):
    v = v.strip()
    if v == "" or v in ("null", "~", "Null", "NULL"):
        return None
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        inner = v[1:-1]
        if v[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in inner.split(",")]
    if _INT_RE.match(v):
        return int(v)
    return v  # dates and bare strings stay strings


class _MiniYaml:
    def __init__(self, text):
        self.lines = []
        for raw in text.splitlines():
            stripped = raw.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            self.lines.append([len(raw) - len(stripped), stripped])
        self.i = 0

    def parse(self):
        if not self.lines:
            return {}
        return self._block(self.lines[0][0])

    def _block(self, indent):
        if self.i >= len(self.lines):
            return None
        if self.lines[self.i][1].startswith("- "):
            return self._list(indent)
        return self._map(indent)

    def _map(self, indent):
        result = {}
        while self.i < len(self.lines):
            ind, content = self.lines[self.i]
            if ind < indent or content.startswith("- "):
                break
            if ind > indent:  # stray continuation; skip defensively
                self.i += 1
                continue
            m = _KEY_RE.match(content)
            if not m:
                self.i += 1
                continue
            key, rest = m.group(1), _strip_comment(m.group(2)).strip()
            self.i += 1
            if rest in (">", "|", ">-", "|-", ">+", "|+"):
                result[key] = self._block_scalar(indent, fold=rest[0] == ">")
            elif rest == "":
                if self.i < len(self.lines) and self.lines[self.i][0] > indent:
                    result[key] = self._block(self.lines[self.i][0])
                else:
                    result[key] = None
            else:
                result[key] = _parse_scalar(rest)
        return result

    def _list(self, indent):
        items = []
        while self.i < len(self.lines):
            ind, content = self.lines[self.i]
            if ind != indent or not content.startswith("- "):
                break
            inner = content[2:].strip()
            if _KEY_RE.match(inner):
                # dict item: re-home the inline 'key: value' two columns deeper
                self.lines[self.i] = [indent + 2, inner]
                items.append(self._map(indent + 2))
            else:
                items.append(_parse_scalar(_strip_comment(inner)))
                self.i += 1
        return items

    def _block_scalar(self, key_indent, fold):
        parts = []
        while self.i < len(self.lines) and self.lines[self.i][0] > key_indent:
            parts.append(self.lines[self.i][1])
            self.i += 1
        return (" " if fold else "\n").join(parts).strip()


def load_profile(path):
    return _MiniYaml(path.read_text(encoding="utf-8")).parse()


# --------------------------------------------------------------------------
# Deadline math
# --------------------------------------------------------------------------

def _to_date(value):
    if isinstance(value, str) and _DATE_RE.match(value):
        return datetime.strptime(value, "%Y-%m-%d").date()
    return None


def deadline_summary(profile, today):
    """Compute days-until for submission-relevant deadlines."""
    dl = profile.get("deadlines") or {}
    out = {}
    for kind in ("abstract", "paper", "notification", "camera_ready"):
        d = _to_date(dl.get(kind))
        if d is None:
            out[kind] = None
        else:
            out[kind] = {
                "date": d.isoformat(),
                "days": (d - today).days,
                "passed": d < today,
            }
    nxt = None
    for kind in ("abstract", "paper"):  # only submission gates count as "next"
        info = out.get(kind)
        if info and not info["passed"]:
            if nxt is None or info["days"] < nxt["days"]:
                nxt = dict(info, kind=kind)
    out["next_submission"] = nxt
    out["timezone"] = dl.get("timezone")
    return out


def tracks_summary(profile):
    parts = []
    for t in profile.get("tracks") or []:
        if not isinstance(t, dict):
            continue
        name = t.get("name", "?")
        limit = t.get("page_limit")
        excl = t.get("page_limit_excludes") or []
        if limit is None:
            parts.append(name)
        elif excl:
            parts.append("%s %sp excl %s" % (name, limit, "/".join(map(str, excl))))
        else:
            parts.append("%s %sp incl refs" % (name, limit))
    return "; ".join(parts)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def find_venues_dir(explicit):
    if explicit:
        p = Path(explicit).expanduser()
        if (p / "conferences").is_dir():
            return p
        sys.exit("error: %s does not contain a conferences/ directory" % p)
    candidates = [Path(__file__).resolve().parent, Path.cwd()]
    for start in candidates:
        for anc in [start] + list(start.parents):
            v = anc / "venues"
            if (v / "conferences").is_dir():
                return v
    sys.exit(
        "error: could not locate a venues/ directory. Run from inside the "
        "research-paper-skills repo or pass --venues-dir /path/to/venues"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="List venue profiles with deadline proximity (stdlib only).",
        epilog="Profiles are a starting point — ALWAYS re-verify deadlines and "
        "page limits against the live cfp_url before relying on them.",
    )
    ap.add_argument("--venues-dir", help="path to the venues/ directory (auto-detected by default)")
    ap.add_argument("--family", help="only venues whose family matches this substring")
    ap.add_argument("--track", help="only venues having a track whose name matches this substring (case-insensitive)")
    ap.add_argument("--upcoming-only", action="store_true", help="only venues with an abstract/paper deadline still in the future")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD) for reproducible output")
    ap.add_argument("--json", action="store_true", help="emit full machine-readable JSON instead of a table")
    args = ap.parse_args(argv)

    if args.today:
        d = _to_date(args.today)
        if d is None:
            sys.exit("error: --today must be YYYY-MM-DD, got %r" % args.today)
        today = d
    else:
        today = date.today()

    venues_dir = find_venues_dir(args.venues_dir)
    files = sorted((venues_dir / "conferences").glob("*.yml"))
    if not files:
        sys.exit("error: no *.yml profiles found in %s/conferences" % venues_dir)

    rows, errors = [], []
    for f in files:
        try:
            p = load_profile(f)
        except Exception as e:  # surface parse failures loudly, keep going
            errors.append("%s: %s" % (f.name, e))
            continue
        if not p.get("id"):
            errors.append("%s: missing id field" % f.name)
            continue
        dls = deadline_summary(p, today)
        review = p.get("review") or {}
        verified = p.get("verified") or {}
        row = {
            "id": p["id"],
            "name": p.get("name"),
            "family": p.get("family"),
            "year": p.get("year"),
            "cfp_url": p.get("cfp_url"),
            "deadlines": dls,
            "tracks": p.get("tracks") or [],
            "tracks_summary": tracks_summary(p),
            "blind": review.get("blind"),
            "submission_system": review.get("submission_system"),
            "rebuttal_format": review.get("rebuttal_format"),
            "verified_date": verified.get("date"),
            "verified_confidence": verified.get("confidence"),
        }
        if args.family and args.family.lower() not in str(row["family"] or "").lower():
            continue
        if args.track:
            names = " ".join(str(t.get("name", "")) for t in row["tracks"] if isinstance(t, dict))
            if args.track.lower() not in names.lower():
                continue
        if args.upcoming_only and not dls["next_submission"]:
            continue
        rows.append(row)

    # sort: venues with an upcoming submission deadline first (soonest first)
    rows.sort(key=lambda r: (r["deadlines"]["next_submission"] is None,
                             (r["deadlines"]["next_submission"] or {}).get("days", 10**6),
                             r["id"]))

    if args.json:
        print(json.dumps({"today": today.isoformat(), "venues": rows,
                          "parse_errors": errors}, indent=2))
    else:
        fmt = "%-18s %-26s %4s  %-3s %-7s %-11s %s"
        print("today: %s   (profiles last verified per-venue; re-verify against each cfp_url)" % today.isoformat())
        print(fmt % ("ID", "NEXT SUBMISSION DEADLINE", "IN", "TZ", "BLIND", "SYSTEM", "TRACKS"))
        for r in rows:
            nxt = r["deadlines"]["next_submission"]
            if nxt:
                nxt_s = "%s %s" % (nxt["kind"], nxt["date"])
                days = "%dd" % nxt["days"]
            else:
                paper = r["deadlines"].get("paper")
                nxt_s = "PASSED (paper %s)" % paper["date"] if paper else "none on file"
                days = "-"
            print(fmt % (r["id"], nxt_s, days, r["deadlines"]["timezone"] or "?",
                         r["blind"] or "?", r["submission_system"] or "?",
                         r["tracks_summary"]))
        if errors:
            print("\nparse errors:", file=sys.stderr)
            for e in errors:
                print("  " + e, file=sys.stderr)

    if errors and not rows:
        sys.exit("error: every profile failed to parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
