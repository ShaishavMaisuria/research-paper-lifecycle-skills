#!/usr/bin/env python3
"""Canonical-instance guard for title lookups (Python 3 stdlib only).

The search scripts answer "does a paper by this title exist?" — they rank by
the provider's relevance, so they happily return an *adjacent* instance of a
named work: an older edition when a community-canonical successor exists
(version drift), or a different paper that shares a first author and a
near-duplicate title stem (title collision). Both pass a bare existence check
yet are the wrong citation.

This module does NOT fetch anything. It takes candidate records you already
retrieved (the `--json` output of dblp/crossref/s2/arxiv search, or any list
of {title, authors, year, ...} dicts) and applies three GENERIC heuristics so
the author resolves the instance *deliberately*:

  1. version-successor detection — flags when a title carries an explicit
     version/edition/reissue marker (v2, II, ++, "revised", "extended", a year
     in the title...) and prefers the latest canonical version, noting any
     older sibling in the same cluster;
  2. title-collision detection — clusters candidates that share a first-author
     surname AND a near-duplicate title stem, and surfaces the whole cluster
     instead of silently picking one;
  3. de-duplication by impact — within an ambiguous cluster, ranks by impact
     signal (citation count, then earliest year as a seminal-venue proxy) and
     marks one PREFERRED, the rest as siblings to weigh.

It never decides for you: every ambiguous cluster prints a one-line
`CHOOSE:` note so you pick. No venue, author, or paper is hardcoded — the
markers and stop-words below are domain-general.

Usage:
  # pipe candidates straight from a search:
  python3 scripts/s2_search.py --query "<the named title>" --json \\
      | python3 scripts/resolve_canonical.py --stdin

  # or against a saved JSON file, optionally anchoring to the queried title:
  python3 scripts/resolve_canonical.py --in cands.json --title "<the named title>"

Input shapes accepted: a JSON list of records, or a dict with a "results"
(or "data"/"items") list — i.e. exactly what the four search scripts emit
with --json. Records need at least a "title"; "authors", "year",
"citationCount"/"cited_by"/"is-referenced-by-count", "venue"/"container",
"doi"/"arxiv_id" are used when present.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# --- generic, domain-agnostic vocab (NOT venue/paper specific) -------------

# Words that mark a record as an explicit later edition of an earlier work.
# Kept general: these recur across every field, never name a paper.
VERSION_WORDS = (
    "revised", "revisited", "extended", "updated", "improved", "enhanced",
    "second edition", "third edition", "new edition", "reissue", "redux",
    "continued", "part ii", "part iii", "vol. 2", "vol. ii",
)
# Trailing version tokens: v2, V3, ++, 2.0, II/III as a suffix, "(2)".
VERSION_SUFFIX_RE = re.compile(
    r"(?:"
    r"\bv\.?\s?[2-9]\d*\b"          # v2, V3, v.4
    r"|\+\+"                          # ++ (Algo++)
    r"|\b[2-9]\.\d\b"               # 2.0, 3.1
    r"|\b(?:ii|iii|iv|v|vi)\b\s*$"  # trailing roman numeral
    r"|\(\s*[2-9]\d*\s*\)\s*$"      # trailing (2)
    r")",
    re.IGNORECASE,
)
YEAR_IN_TITLE_RE = re.compile(r"\b(19|20)\d{2}\b")

# Title-stem stop-words so "A Survey of X" and "X" cluster together. Generic
# function words only — no field terms, so this never over-merges by topic.
STOPWORDS = {
    "a", "an", "the", "of", "for", "on", "in", "to", "and", "or", "with",
    "via", "using", "toward", "towards", "by", "from", "at", "as", "is",
    "survey", "study", "approach", "method", "framework", "system", "model",
    "learning", "deep", "neural", "network", "networks", "scalable", "fast",
    "efficient", "novel", "new", "improved", "robust", "general", "simple",
}

IMPACT_KEYS = ("citationCount", "cited_by", "is-referenced-by-count",
               "citation_count", "citations")


def eprint(*a):
    print(*a, file=sys.stderr)


# --- record normalization ---------------------------------------------------

def first_author_surname(rec: dict) -> str:
    authors = rec.get("authors") or []
    if not authors:
        return ""
    a = authors[0]
    if isinstance(a, dict):
        a = a.get("name") or " ".join(
            x for x in (a.get("given"), a.get("family")) if x)
    a = (a or "").strip()
    if not a:
        return ""
    # Surname = last whitespace-separated token (handles "Jane Q. Public" and
    # "J. Public"); lowercased for comparison. Pure-initial tokens dropped.
    toks = [t for t in re.split(r"\s+", a) if t]
    for t in reversed(toks):
        clean = re.sub(r"[^\w-]", "", t)
        if len(clean) > 1 and not clean.replace("-", "").isupper():
            return clean.lower()
    return re.sub(r"[^\w-]", "", toks[-1]).lower() if toks else ""


def impact_of(rec: dict):
    for k in IMPACT_KEYS:
        v = rec.get(k)
        if isinstance(v, (int, float)):
            return int(v)
    return None


def year_of(rec: dict):
    y = rec.get("year")
    try:
        return int(str(y)[:4])
    except (TypeError, ValueError):
        m = YEAR_IN_TITLE_RE.search(rec.get("title") or "")
        return int(m.group(0)) if m else None


def id_of(rec: dict) -> str:
    ext = rec.get("externalIds") or {}
    return (rec.get("doi") or ext.get("DOI") or rec.get("arxiv_id")
            or ("arXiv:" + ext["ArXiv"] if ext.get("ArXiv") else "")
            or rec.get("dblp_key") or "")


def venue_of(rec: dict) -> str:
    return (rec.get("venue") or rec.get("container") or "").strip()


# --- title analysis ---------------------------------------------------------

def title_stem(title: str) -> tuple:
    """Order-independent content-word signature of a title (for clustering).

    Lowercases, strips a trailing version marker, drops punctuation and
    stop-words, returns a frozenset of remaining tokens. Version-only
    differences therefore collapse to the same stem so editions cluster.
    """
    t = (title or "").lower()
    t = VERSION_SUFFIX_RE.sub(" ", t)
    t = re.sub(r"[^\w\s+-]", " ", t)
    toks = [w for w in re.split(r"\s+", t)
            if w and w not in STOPWORDS and not w.isdigit()]
    return frozenset(toks)


def version_marker(title: str):
    """Return a short human label if the title looks like a later edition."""
    low = (title or "").lower()
    for w in VERSION_WORDS:
        if w in low:
            return w
    m = VERSION_SUFFIX_RE.search(title or "")
    if m:
        return m.group(0).strip()
    return None


def stems_collide(a: frozenset, b: frozenset, same_author: bool = False) -> bool:
    """Near-duplicate title stems: one is a subset of the other, or they
    overlap heavily. Both stems must be non-trivial.

    The Jaccard bar is 0.6 in general, but relaxes to 0.45 when the records
    share a first author — a shared surname is itself strong evidence of a
    same-author title collision, so a slightly looser stem overlap (e.g.
    "finding/evaluating community structure" vs "modularity and community
    structure") should still surface for a deliberate choice. Two distinctive
    content words in common are also enough under the same-author guard.
    """
    if not a or not b:
        return False
    if a == b or a <= b or b <= a:
        return True
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return False
    threshold = 0.45 if same_author else 0.6
    if inter / union >= threshold:
        return True
    return same_author and inter >= 2


# --- clustering -------------------------------------------------------------

def cluster(records: list) -> list:
    """Group records into title-collision clusters.

    Two records join the same cluster when their title stems collide AND they
    share a first-author surname (the title-collision signature), OR their
    stems are identical/subset (an edition of the same work regardless of
    authorship changes). Greedy single-link over a small candidate set.
    """
    nodes = []
    for r in records:
        nodes.append({
            "rec": r,
            "stem": title_stem(r.get("title", "")),
            "surname": first_author_surname(r),
        })
    clusters: list = []
    for n in nodes:
        placed = False
        for c in clusters:
            for m in c:
                same_work = (n["stem"] and m["stem"]
                             and (n["stem"] <= m["stem"] or m["stem"] <= n["stem"]))
                same_author = bool(n["surname"]) and n["surname"] == m["surname"]
                collide = same_author and stems_collide(
                    n["stem"], m["stem"], same_author=True)
                if same_work or collide:
                    c.append(n)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            clusters.append([n])
    return clusters


def rank_cluster(nodes: list) -> list:
    """Order a cluster's members by canonical preference.

    Rule order (de-duplication by impact + prefer-latest-canonical):
      1. If any member carries an explicit version marker, the highest such
         version (proxied by latest year, then by impact) is the canonical
         successor — prefer-latest-canonical.
      2. Otherwise prefer the highest impact signal (citation count).
      3. Ties / missing impact fall back to the earliest year (seminal-venue
         proxy: the first-published instance of a colliding title is usually
         the one the community cites).
    """
    versioned = [n for n in nodes if version_marker(n["rec"].get("title", ""))]
    has_version = bool(versioned)

    def key(n):
        rec = n["rec"]
        impact = impact_of(rec)
        impact_k = impact if impact is not None else -1
        yr = year_of(rec) or 0
        is_ver = 1 if version_marker(rec.get("title", "")) else 0
        if has_version:
            # latest canonical version first: version-marked, then newest,
            # then most-cited.
            return (-is_ver, -yr, -impact_k)
        # no explicit successor: impact, then earliest (seminal) year.
        return (-impact_k, yr)

    return sorted(nodes, key=key)


# --- output -----------------------------------------------------------------

def brief(rec: dict) -> str:
    a = first_author_surname(rec) or "?"
    yr = year_of(rec)
    parts = [rec.get("title", "(untitled)").strip()]
    tail = " | ".join(x for x in (
        f"{a} et al.",
        str(yr) if yr else "",
        venue_of(rec),
        (lambda i: f"cites:{i}" if i is not None else "")(impact_of(rec)),
        id_of(rec),
    ) if x)
    return f"{parts[0]} — {tail}" if tail else parts[0]


def report(clusters: list, anchor: str, as_json: bool):
    out_clusters = []
    flags = 0
    for c in clusters:
        ranked = rank_cluster(c)
        recs = [n["rec"] for n in ranked]
        ambiguous = len(recs) > 1
        ver = [version_marker(r.get("title", "")) for r in recs]
        any_version = any(ver)
        note = None
        if ambiguous:
            flags += 1
            if any_version:
                note = ("version/edition siblings detected — preferring the "
                        "latest canonical version; confirm you do not mean an "
                        "earlier edition")
            else:
                note = ("title collision: same first author + near-duplicate "
                        "title — preferring the higher-impact instance; pick "
                        "the one you actually mean")
        out_clusters.append({
            "preferred": recs[0],
            "siblings": recs[1:],
            "ambiguous": ambiguous,
            "version_drift": any_version and ambiguous,
            "note": note,
        })

    if as_json:
        json.dump({"clusters": out_clusters, "flagged": flags},
                  sys.stdout, indent=2, default=str)
        print()
        return

    if anchor:
        print(f"resolving against: \"{anchor}\"\n")
    if not out_clusters:
        print("no candidates to resolve.")
        return
    print(f"{len(out_clusters)} distinct work(s); {flags} need a deliberate "
          f"choice.\n")
    for i, c in enumerate(out_clusters, 1):
        tag = ""
        if c["version_drift"]:
            tag = "  [VERSION DRIFT]"
        elif c["ambiguous"]:
            tag = "  [TITLE COLLISION]"
        print(f"#{i}{tag}")
        print(f"  PREFERRED: {brief(c['preferred'])}")
        for s in c["siblings"]:
            print(f"  sibling:   {brief(s)}")
        if c["note"]:
            print(f"  CHOOSE: {c['note']}")
        print()
    print("This is a copilot, not autopilot: the PREFERRED pick is a ranked "
          "suggestion, not a decision. Verify the instance you cite via "
          "verify-citations before it enters a bibliography.")


# --- input ------------------------------------------------------------------

def load_records(raw: str) -> list:
    try:
        data = json.loads(raw)
    except ValueError:
        eprint("ERROR: input is not valid JSON (pipe a search script's --json "
               "output, or pass --in <file.json>).")
        sys.exit(1)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("results", "data", "items", "clusters"):
            if isinstance(data.get(k), list):
                return data[k]
        if data.get("title"):
            return [data]
    eprint("ERROR: could not find a record list in the input (expected a JSON "
           "array, or an object with a 'results'/'data'/'items' list).")
    sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--stdin", action="store_true",
                     help="read candidate JSON from stdin (pipe a search's --json)")
    src.add_argument("--in", dest="infile", metavar="FILE",
                     help="read candidate JSON from a file")
    p.add_argument("--title", metavar="TEXT",
                   help="the title you were looking for (anchors the report; "
                        "does not filter)")
    p.add_argument("--json", action="store_true",
                   help="emit the resolution as JSON instead of text")
    return p.parse_args()


def main():
    args = parse_args()
    if args.stdin:
        raw = sys.stdin.read()
    else:
        try:
            with open(args.infile, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            eprint(f"ERROR: cannot read {args.infile}: {e}")
            sys.exit(1)
    records = load_records(raw)
    records = [r for r in records if isinstance(r, dict) and r.get("title")]
    if not records:
        print("no candidate records with a title found in the input.")
        return
    clusters = cluster(records)
    report(clusters, args.title or "", args.json)


if __name__ == "__main__":
    main()
