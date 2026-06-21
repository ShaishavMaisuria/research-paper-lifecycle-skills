#!/usr/bin/env python3
"""Validate a venue-profile YAML against venues/schema.yml before opening a PR.

Part of the add-venue-profile skill (research-paper-skills). Stdlib only:
uses PyYAML when it happens to be installed, otherwise falls back to a
built-in reader for the YAML subset the venue profiles actually use
(nested mappings, lists, inline lists, quoted strings, `>` / `|` block
scalars, comments). No network access; purely local checks.

Checks (ERROR = blocks the PR, WARN = fix or justify in the PR body):
  - parses, is a mapping, no unknown top-level keys (typo catcher)
  - required fields: id, name, family, year, verified (+ cfp_url or website)
  - id == filename stem, kebab-case, year suffix matches `year:`
  - family file exists under venues/families/
  - deadlines are ISO dates in a sane order, with a stated timezone
  - tracks have names, integer/null page limits, list-typed exclusions
  - enum sanity: blind level, submission system, rebuttal format, CR rail
  - documentclass `anonymous` option consistent with the blind level
  - verified: block complete, confidence in the allowed set, date not in
    the future, source_urls present, profile not stale

Exit codes: 0 ok | 1 validation errors (or warnings with --strict) | 2 usage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

KNOWN_TOP_KEYS = {
    "id", "name", "family", "year", "cfp_url", "website",
    "aliases", "deadlines", "tracks", "format", "review",
    "camera_ready", "verified",
}
REQUIRED_KEYS = ["id", "name", "family", "year", "verified"]
CONFIDENCE = {"verified-live", "inferred-from-family", "needs-verification"}
BLIND = {"single", "double", "triple"}
SUBMISSION_SYSTEMS = {"openreview", "cmt", "easychair", "hotcrp", "pcs", "scholarone"}
REBUTTAL_FORMATS = {"none", "openreview-thread", "one-page-pdf", "revise-and-resubmit"}
CR_RAILS = {"acm-taps", "ieee-pdfexpress", "springer", "openreview-direct",
            "scholarone-final-files"}
EXCLUDE_VOCAB = {"references", "appendix", "checklist", "bios",
                 "acknowledgments", "impact-statement"}
DEADLINE_KEYS = ["abstract", "paper", "rebuttal_start", "rebuttal_end",
                 "notification", "camera_ready"]
STALE_DAYS = 180
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DBLP_KEY = re.compile(r"^(conf|journals)/[A-Za-z0-9_-]+$")


# --- minimal YAML-subset reader (stdlib fallback) ------------------------------

class YAMLSubsetError(ValueError):
    pass


def _strip_comment(s: str) -> str:
    """Remove a trailing ` # comment` outside quotes ('#' inside URLs survives)."""
    in_s = in_d = False
    prev = " "
    for i, ch in enumerate(s):
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d and (i == 0 or prev in " \t"):
            return s[:i].rstrip()
        prev = ch
    return s.rstrip()


def _unquote_double(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(s[i + 1])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _split_inline_list(body: str) -> list[str]:
    parts, depth, in_s, in_d, cur = [], 0, False, False, []
    for ch in body:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d:
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append("".join(cur).strip())
                cur = []
                continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def _scalar(s: str):
    s = s.strip()
    if s == "" or s in ("null", "~", "Null", "NULL"):
        return None
    if s.startswith("[") and s.endswith("]"):
        body = s[1:-1].strip()
        return [_scalar(p) for p in _split_inline_list(body)] if body else []
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return _unquote_double(s[1:-1])
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if re.fullmatch(r"[+-]?\d+", s):
        return int(s)
    if re.fullmatch(r"[+-]?\d*\.\d+", s):
        return float(s)
    return s


class _SubsetParser:
    """Indentation-based parser for the profile subset of YAML."""

    _KEY = re.compile(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$")
    _BLOCK = re.compile(r"^[>|][+-]?$")

    def __init__(self, text: str):
        text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
        self.lines = text.split("\n")
        self.i = 0

    def _effective_indent(self, j: int):
        line = self.lines[j]
        if not line.strip() or line.lstrip(" ").startswith("#"):
            return None
        if "\t" in line[: len(line) - len(line.lstrip())]:
            raise YAMLSubsetError(f"line {j + 1}: tabs in indentation are not allowed")
        return len(line) - len(line.lstrip(" "))

    def _next(self):
        while self.i < len(self.lines):
            ind = self._effective_indent(self.i)
            if ind is not None:
                return ind
            self.i += 1
        return None

    def parse(self):
        doc = self._node(0)
        if self._next() is not None:
            raise YAMLSubsetError(
                f"line {self.i + 1}: content outside the document structure")
        return doc

    def _node(self, min_indent: int):
        ind = self._next()
        if ind is None or ind < min_indent:
            return None
        content = self.lines[self.i].strip()
        if content == "-" or content.startswith("- "):
            return self._list(ind)
        return self._map(ind)

    def _map(self, indent: int) -> dict:
        out: dict = {}
        while True:
            ind = self._next()
            if ind is None or ind < indent:
                return out
            if ind > indent:
                raise YAMLSubsetError(
                    f"line {self.i + 1}: unexpected indent {ind} (expected {indent})")
            content = self.lines[self.i][indent:]
            if content.startswith("- "):
                return out
            m = self._KEY.match(_strip_comment(content))
            if not m:
                raise YAMLSubsetError(
                    f"line {self.i + 1}: expected `key: value`, got {content!r}")
            key, rest = m.group(1), (m.group(2) or "").strip()
            if key in out:
                raise YAMLSubsetError(f"line {self.i + 1}: duplicate key {key!r}")
            self.i += 1
            if rest == "":
                out[key] = self._node(indent + 1)
            elif self._BLOCK.match(rest):
                out[key] = self._block(indent, rest[0])
            else:
                out[key] = _scalar(rest)

    def _list(self, indent: int) -> list:
        items: list = []
        while True:
            ind = self._next()
            if ind is None or ind != indent:
                return items
            line = self.lines[self.i]
            content = line[indent:]
            if not (content == "-" or content.startswith("- ")):
                return items
            if content == "-":
                self.i += 1
                items.append(self._node(indent + 1))
                continue
            # rewrite "- foo" as "  foo" and parse in place
            rewritten = line[:indent] + " " + line[indent + 1:]
            inner = _strip_comment(rewritten.strip())
            if self._KEY.match(inner):
                self.lines[self.i] = rewritten
                item_indent = len(rewritten) - len(rewritten.lstrip(" "))
                items.append(self._map(item_indent))
            else:
                self.i += 1
                items.append(_scalar(inner))

    def _block(self, key_indent: int, style: str) -> str:
        raw: list[str] = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip() == "":
                raw.append("")
                self.i += 1
                continue
            ind = len(line) - len(line.lstrip(" "))
            if ind <= key_indent:
                break
            raw.append(line)
            self.i += 1
        body = [ln for ln in raw if ln.strip()]
        if not body:
            return ""
        base = min(len(ln) - len(ln.lstrip(" ")) for ln in body)
        if style == "|":
            return "\n".join(ln[base:] if ln.strip() else "" for ln in raw).strip("\n")
        return " ".join(ln.strip() for ln in body)


def load_profile(path: Path, engine: str = "auto") -> tuple[dict, str]:
    """Returns (data, engine_used). Raises ValueError on parse failure."""
    text = path.read_text(encoding="utf-8")
    if engine in ("auto", "pyyaml"):
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text), "pyyaml"
        except ImportError:
            if engine == "pyyaml":
                raise ValueError("--engine pyyaml requested but PyYAML is not installed")
    return _SubsetParser(text).parse(), "builtin"


# --- validation ------------------------------------------------------------------

def norm(v):
    """Normalize PyYAML dates to ISO strings so both engines compare alike."""
    if isinstance(v, (dt.date, dt.datetime)):
        return v.date().isoformat() if isinstance(v, dt.datetime) else v.isoformat()
    return v


def find_repo_root(start: Path) -> Path | None:
    for cand in [start, *start.parents]:
        if (cand / "venues" / "schema.yml").is_file():
            return cand
    script_guess = Path(__file__).resolve()
    if len(script_guess.parents) >= 4:
        cand = script_guess.parents[3]
        if (cand / "venues" / "schema.yml").is_file():
            return cand
    return None


def as_date(v):
    v = norm(v)
    if isinstance(v, str) and ISO_DATE.match(v):
        try:
            return dt.date.fromisoformat(v)
        except ValueError:
            return None
    return None


class Report:
    def __init__(self, name: str):
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def check_deadlines(data: dict, rep: Report) -> None:
    deadlines = data.get("deadlines")
    if deadlines is None:
        rep.warn("no `deadlines:` block — add it (all-null is fine for rolling journals)")
        return
    if not isinstance(deadlines, dict):
        rep.error("`deadlines` must be a mapping")
        return
    parsed: dict[str, dt.date] = {}
    for key in DEADLINE_KEYS:
        val = norm(deadlines.get(key))
        if val is None:
            continue
        d = as_date(val)
        if d is None:
            rep.error(f"deadlines.{key}: {val!r} is not an ISO date (YYYY-MM-DD)")
        else:
            parsed[key] = d
    if parsed and not deadlines.get("timezone"):
        rep.warn("deadlines.timezone is unset but dated deadlines exist — "
                 "record the CFP's stated timezone (AoE is common, not universal)")
    order = ["abstract", "paper", "rebuttal_start", "rebuttal_end",
             "notification", "camera_ready"]
    prev_key = prev_date = None
    for key in order:
        if key in parsed:
            if prev_date is not None and parsed[key] < prev_date:
                rep.warn(f"deadlines.{key} ({parsed[key]}) is before "
                         f"deadlines.{prev_key} ({prev_date}) — double-check the CFP")
            prev_key, prev_date = key, parsed[key]


def check_tracks(data: dict, rep: Report) -> None:
    tracks = data.get("tracks")
    if tracks is None:
        rep.warn("no `tracks:` block — conference profiles should list at least one track")
        return
    if not isinstance(tracks, list):
        rep.error("`tracks` must be a list")
        return
    for idx, track in enumerate(tracks, 1):
        label = f"tracks[{idx}]"
        if not isinstance(track, dict):
            rep.error(f"{label}: each track must be a mapping")
            continue
        if not track.get("name"):
            rep.error(f"{label}: missing `name`")
        limit = track.get("page_limit")
        if limit is not None and not isinstance(limit, int):
            rep.error(f"{label}: page_limit must be an integer or null, got {limit!r}")
        excludes = track.get("page_limit_excludes")
        if excludes is None:
            rep.warn(f"{label}: page_limit_excludes is missing — use [] only when the "
                     "limit explicitly includes references, and say so in notes")
        elif not isinstance(excludes, list):
            rep.error(f"{label}: page_limit_excludes must be a list (use [] for "
                      "limits that include everything)")
        else:
            for token in excludes:
                if token not in EXCLUDE_VOCAB:
                    rep.warn(f"{label}: unusual page_limit_excludes token {token!r} "
                             f"(known: {sorted(EXCLUDE_VOCAB)})")


def check_review_format(data: dict, rep: Report) -> None:
    review = data.get("review") or {}
    fmt = data.get("format") or {}
    if not isinstance(review, dict):
        rep.error("`review` must be a mapping")
        review = {}
    if not isinstance(fmt, dict):
        rep.error("`format` must be a mapping")
        fmt = {}
    blind = review.get("blind")
    if blind is not None and blind not in BLIND:
        rep.warn(f"review.blind {blind!r} not in {sorted(BLIND)}")
    system = review.get("submission_system")
    if system is not None and system not in SUBMISSION_SYSTEMS:
        rep.warn(f"review.submission_system {system!r} not in known set "
                 f"{sorted(SUBMISSION_SYSTEMS)} — fine if genuinely new, say so in the PR")
    rformat = review.get("rebuttal_format")
    if rformat is not None and rformat not in REBUTTAL_FORMATS:
        rep.warn(f"review.rebuttal_format {rformat!r} not in {sorted(REBUTTAL_FORMATS)}")
    docclass = fmt.get("documentclass")
    if isinstance(docclass, str) and "acmart" in docclass:
        if blind in ("double", "triple") and "anonymous" not in docclass:
            rep.warn("blind is double/triple but documentclass lacks the "
                     "`anonymous` option — submissions would leak author names")
        if blind == "single" and "anonymous" in docclass:
            rep.warn("blind is single but documentclass has `anonymous` — "
                     "single-blind venues expect author names on the submission")
    cr = data.get("camera_ready") or {}
    if isinstance(cr, dict):
        rail = cr.get("rail")
        if rail is not None and rail not in CR_RAILS:
            rep.warn(f"camera_ready.rail {rail!r} not in known set {sorted(CR_RAILS)}")
    elif cr is not None:
        rep.error("`camera_ready` must be a mapping")


def check_aliases(data: dict, rep: Report) -> None:
    aliases = data.get("aliases")
    if aliases is None:
        rep.warn("no `aliases:` block — the alias table (dblp_key, s2_venue, "
                 "crossref_container) is what makes the profile searchable; add it")
        return
    if not isinstance(aliases, dict):
        rep.error("`aliases` must be a mapping")
        return
    if all(norm(v) is None for v in aliases.values()):
        rep.warn("every alias is null — fill at least dblp_key (DBLP venue API) "
                 "or explain in the PR why none could be verified")
    dblp = aliases.get("dblp_key")
    if isinstance(dblp, str) and not DBLP_KEY.match(dblp):
        rep.warn(f"aliases.dblp_key {dblp!r} does not look like conf/<key> or "
                 "journals/<key> (e.g. SIGSPATIAL is conf/gis)")


def check_verified(data: dict, rep: Report, today: dt.date) -> None:
    ver = data.get("verified")
    if not isinstance(ver, dict):
        rep.error("`verified` must be a mapping with date, source_urls, confidence")
        return
    d = as_date(ver.get("date"))
    if d is None:
        rep.error(f"verified.date {norm(ver.get('date'))!r} must be an ISO date")
    else:
        if d > today + dt.timedelta(days=1):
            rep.error(f"verified.date {d} is in the future")
        elif (today - d).days > STALE_DAYS:
            rep.warn(f"verified.date {d} is over {STALE_DAYS} days old — "
                     "re-verify every fact against the live CFP before the PR")
    conf = ver.get("confidence")
    if conf not in CONFIDENCE:
        rep.error(f"verified.confidence {conf!r} must be one of {sorted(CONFIDENCE)}")
    urls = ver.get("source_urls")
    if not isinstance(urls, list) or not urls:
        rep.error("verified.source_urls must be a non-empty list of the pages checked")
    else:
        for u in urls:
            if not (isinstance(u, str) and u.startswith(("http://", "https://"))):
                rep.error(f"verified.source_urls entry {u!r} is not an http(s) URL")


def validate(path: Path, repo_root: Path | None, today: dt.date) -> Report:
    rep = Report(path.name)
    try:
        data, engine = load_profile(path)
    except (OSError, ValueError, YAMLSubsetError) as exc:
        rep.error(f"cannot parse: {exc}")
        return rep
    except Exception as exc:  # PyYAML raises its own hierarchy
        rep.error(f"cannot parse: {exc}")
        return rep
    print(f"[engine] {path.name}: parsed with {engine}", file=sys.stderr)
    if not isinstance(data, dict):
        rep.error("profile must be a YAML mapping")
        return rep

    for key in data:
        if key not in KNOWN_TOP_KEYS:
            rep.warn(f"unknown top-level key {key!r} — typo? Schema keys: "
                     f"{sorted(KNOWN_TOP_KEYS)}")
    for key in REQUIRED_KEYS:
        if data.get(key) in (None, ""):
            rep.error(f"missing required field `{key}`")
    if not data.get("cfp_url") and not data.get("website"):
        rep.error("at least one of `cfp_url` or `website` is required")
    for key in ("cfp_url", "website"):
        val = data.get(key)
        if val is not None and not (isinstance(val, str)
                                    and val.startswith(("http://", "https://"))):
            rep.error(f"`{key}` must be an http(s) URL, got {val!r}")

    pid = data.get("id")
    if isinstance(pid, str):
        if pid != path.stem:
            rep.error(f"id {pid!r} != filename stem {path.stem!r}")
        if not KEBAB.match(pid):
            rep.error(f"id {pid!r} is not kebab-case (lowercase letters, digits, hyphens)")
        year = data.get("year")
        m = re.search(r"-(\d{4})$", pid)
        if m and isinstance(year, int) and int(m.group(1)) != year:
            rep.error(f"id year suffix {m.group(1)} != year field {year}")
        if not m:
            rep.warn(f"id {pid!r} has no year suffix — fine for rolling journals "
                     "(tkde), but conference profiles are year-versioned "
                     "(e.g. sigspatial-2026)")
    year = data.get("year")
    if year is not None and not isinstance(year, int):
        rep.error(f"`year` must be an integer, got {year!r}")
    elif isinstance(year, int) and not 2000 <= year <= 2100:
        rep.warn(f"`year` {year} looks implausible")

    fam = data.get("family")
    if isinstance(fam, str) and repo_root is not None:
        if not (repo_root / "venues" / "families" / f"{fam}.yml").is_file():
            rep.error(f"family {fam!r} has no venues/families/{fam}.yml — "
                      "pick an existing family or add the family file first")
    elif isinstance(fam, str):
        rep.warn(f"could not locate the repo root, so family {fam!r} was not "
                 "checked against venues/families/ (pass --repo-root)")

    check_aliases(data, rep)
    check_deadlines(data, rep)
    check_tracks(data, rep)
    check_review_format(data, rep)
    check_verified(data, rep, today)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate venue-profile YAML(s) against the venues/schema.yml "
                    "contract. Stdlib only (PyYAML used when available); offline.",
        epilog="examples:\n"
               "  python3 validate_profile.py venues/conferences/sigspatial-2026.yml\n"
               "  python3 validate_profile.py venues/conferences/*.yml --strict\n"
               "exit codes: 0 ok | 1 errors (or warnings with --strict) | 2 usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("profiles", nargs="+", type=Path,
                    help="venue-profile YAML file(s) to validate")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as errors (recommended before a PR)")
    ap.add_argument("--repo-root", type=Path, default=None,
                    help="repo root containing venues/ (default: auto-detected "
                         "from the profile path)")
    args = ap.parse_args()

    today = dt.date.today()
    total_err = total_warn = 0
    for path in args.profiles:
        if not path.is_file():
            print(f"ERROR {path}: file not found", file=sys.stderr)
            return 2
        root = args.repo_root or find_repo_root(path.resolve().parent)
        if args.repo_root and not (args.repo_root / "venues" / "schema.yml").is_file():
            print(f"ERROR --repo-root {args.repo_root} has no venues/schema.yml",
                  file=sys.stderr)
            return 2
        rep = validate(path, root, today)
        for w in rep.warnings:
            print(f"WARN  {rep.name}: {w}")
        for e in rep.errors:
            print(f"ERROR {rep.name}: {e}")
        total_err += len(rep.errors)
        total_warn += len(rep.warnings)

    print(f"\nchecked {len(args.profiles)} profile(s): "
          f"{total_err} errors, {total_warn} warnings"
          + (" (strict: warnings fail)" if args.strict else ""))
    if total_err or (args.strict and total_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
