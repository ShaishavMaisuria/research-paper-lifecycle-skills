#!/usr/bin/env python3
"""Manage a literature-review corpus (corpus.json). Stdlib only, no network.

The corpus tracks METADATA AND PIPELINE STATE ONLY -- titles, DOIs, venues,
screening decisions, verification flags. Never paper text or abstracts.

Subcommands:
  add       add one paper by hand (--key --title [--doi --arxiv --year ...])
  import    bulk-add papers from a JSON array (find-papers --json output)
  set       update one paper's status/theme (screened, fetched, extracted,
            verified, theme, reason)
  list      list papers, filterable by status/theme; --json for machine use
  stats     pipeline progress counts (found/included/fetched/extracted/verified)
  bibtex    emit skeleton BibTeX from corpus metadata (stdout). Fields come
            from search metadata and MUST then be checked with the
            verify-citations skill before use.

Examples:
  python3 corpus.py add --corpus lit-review/x/corpus.json \\
      --key li2024learned --title "Learned Spatial Indexes" \\
      --doi 10.1145/3589132.3625571 --year 2024 --venue SIGSPATIAL
  python3 corpus.py import --corpus c.json --source dblp hits.json
  python3 corpus.py set --corpus c.json li2024learned --screened included
  python3 corpus.py set --corpus c.json li2024learned --verified yes
  python3 corpus.py list --corpus c.json --screened included --json
  python3 corpus.py bibtex --corpus c.json > references.bib

Exit codes: 0 ok | 1 data error (missing corpus, duplicate/unknown key)
            | 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
YESNO = {"yes": True, "no": False, "true": True, "false": False}
SCREENED_VALUES = ("pending", "included", "excluded")


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_corpus(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        fail(
            f"corpus not found: {path}\n"
            "Create a workspace first: python3 scripts/init_review.py \"TOPIC\""
        )
    try:
        corpus = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        fail(f"{path} is not valid JSON: {e}")
    if not isinstance(corpus.get("papers"), dict):
        fail(f"{path} has no 'papers' map -- not a literature-review corpus")
    return corpus


def save_corpus(path: str, corpus: dict) -> None:
    try:
        Path(path).write_text(
            json.dumps(corpus, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        fail(f"could not write {path}: {e}")


def new_paper(**kw) -> dict:
    return {
        "title": kw.get("title", ""),
        "authors": kw.get("authors", []),
        "year": kw.get("year"),
        "venue": kw.get("venue"),
        "doi": kw.get("doi"),
        "arxiv": kw.get("arxiv"),
        "url": kw.get("url"),
        "source": kw.get("source"),
        "added": date.today().isoformat(),
        "theme": None,
        "reason": None,
        "status": {
            "screened": "pending",
            "fetched": False,
            "extracted": False,
            "verified": False,
        },
    }


def make_key(rec: dict, existing: dict) -> str:
    """firstauthorlastname + year + first significant title word."""
    authors = rec.get("authors") or []
    last = "anon"
    if authors:
        tokens = re.findall(r"[A-Za-z]+", str(authors[0]))
        if tokens:
            last = tokens[-1].lower()
    year = str(rec.get("year") or "n.d.").replace(".", "")
    stop = {"a", "an", "the", "on", "of", "for", "and", "with", "towards", "toward"}
    word = "untitled"
    for w in re.findall(r"[A-Za-z]+", rec.get("title", "")):
        if w.lower() not in stop:
            word = w.lower()
            break
    base = f"{last}{year}{word}"[:60]
    key, n = base, 2
    while key in existing:
        key, n = f"{base}-{n}", n + 1
    return key


def cmd_add(args) -> None:
    corpus = load_corpus(args.corpus)
    key = args.key
    if not KEY_RE.match(key):
        fail(f"bad key '{key}': lowercase letters/digits/hyphens, 2-63 chars", 2)
    if key in corpus["papers"] and not args.update:
        fail(f"key '{key}' already in corpus (use --update to overwrite metadata)")
    rec = corpus["papers"].get(key) or new_paper()
    for field in ("title", "year", "venue", "doi", "arxiv", "url", "source"):
        val = getattr(args, field)
        if val is not None:
            rec[field] = val
    if args.authors:
        rec["authors"] = [a.strip() for a in args.authors.split(";") if a.strip()]
    if not rec.get("title"):
        fail("--title is required for a new paper", 2)
    corpus["papers"][key] = rec
    save_corpus(args.corpus, corpus)
    print(f"added {key}: {rec['title']}")


def cmd_import(args) -> None:
    corpus = load_corpus(args.corpus)
    raw = sys.stdin.read() if args.file == "-" else None
    if raw is None:
        p = Path(args.file)
        if not p.exists():
            fail(f"file not found: {args.file}")
        raw = p.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except ValueError as e:
        fail(f"input is not valid JSON: {e}")
    if isinstance(data, dict):
        for k in ("results", "papers", "hits", "items"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        fail("expected a JSON array of paper records (find-papers --json output)")
    added, skipped = 0, 0
    for rec in data:
        if not isinstance(rec, dict) or not rec.get("title"):
            skipped += 1
            continue
        doi = rec.get("doi")
        if doi and any(
            p.get("doi") == doi for p in corpus["papers"].values()
        ):
            skipped += 1  # dedupe on DOI
            continue
        paper = new_paper(
            title=str(rec.get("title", "")).strip(),
            authors=rec.get("authors") or [],
            year=rec.get("year"),
            venue=rec.get("venue"),
            doi=doi,
            arxiv=rec.get("arxiv") or rec.get("arxiv_id"),
            url=rec.get("url") or rec.get("ee"),
            source=args.source,
        )
        corpus["papers"][make_key(paper, corpus["papers"])] = paper
        added += 1
    if args.query:
        corpus.setdefault("search_log", []).append(
            {
                "date": date.today().isoformat(),
                "source": args.source,
                "query": args.query,
                "added": added,
            }
        )
    save_corpus(args.corpus, corpus)
    print(f"imported {added} papers ({skipped} skipped: no title or duplicate DOI)")
    if added == 0 and skipped == 0:
        fail("input array was empty -- nothing to import")


def cmd_set(args) -> None:
    corpus = load_corpus(args.corpus)
    rec = corpus["papers"].get(args.key)
    if rec is None:
        fail(f"unknown key '{args.key}' -- see: python3 corpus.py list")
    changed = []
    if args.screened:
        rec["status"]["screened"] = args.screened
        changed.append(f"screened={args.screened}")
    for flag in ("fetched", "extracted", "verified"):
        val = getattr(args, flag)
        if val is not None:
            rec["status"][flag] = YESNO[val]
            changed.append(f"{flag}={val}")
    if args.theme is not None:
        rec["theme"] = args.theme or None
        changed.append(f"theme={args.theme}")
    if args.reason is not None:
        rec["reason"] = args.reason
        changed.append("reason set")
    if not changed:
        fail("nothing to set -- pass at least one of --screened/--fetched/"
             "--extracted/--verified/--theme/--reason", 2)
    save_corpus(args.corpus, corpus)
    print(f"{args.key}: " + ", ".join(changed))


def matches(rec: dict, args) -> bool:
    if args.screened and rec["status"]["screened"] != args.screened:
        return False
    for flag in ("fetched", "extracted", "verified"):
        want = getattr(args, flag)
        if want is not None and rec["status"][flag] is not YESNO[want]:
            return False
    if args.theme and (rec.get("theme") or "") != args.theme:
        return False
    return True


def cmd_list(args) -> None:
    corpus = load_corpus(args.corpus)
    rows = {k: r for k, r in sorted(corpus["papers"].items()) if matches(r, args)}
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        print("(no papers match)")
        return
    for key, r in rows.items():
        s = r["status"]
        flags = "".join(
            c if s[f] else "-"
            for c, f in (("F", "fetched"), ("X", "extracted"), ("V", "verified"))
        )
        print(
            f"{key:<28} {s['screened']:<9} {flags}  "
            f"{r.get('year') or '----'}  {r.get('title', '')[:70]}"
        )
    print(f"\n{len(rows)} papers (flags: F fetched, X extracted, V verified)")


def cmd_stats(args) -> None:
    corpus = load_corpus(args.corpus)
    papers = corpus["papers"].values()
    n = len(corpus["papers"])
    inc = [p for p in papers if p["status"]["screened"] == "included"]
    counts = {
        "in corpus": n,
        "screened: included": len(inc),
        "screened: excluded": sum(
            1 for p in papers if p["status"]["screened"] == "excluded"
        ),
        "screened: pending": sum(
            1 for p in papers if p["status"]["screened"] == "pending"
        ),
        "fetched (of included)": sum(1 for p in inc if p["status"]["fetched"]),
        "extracted (of included)": sum(1 for p in inc if p["status"]["extracted"]),
        "verified (of included)": sum(1 for p in inc if p["status"]["verified"]),
        "themed (of included)": sum(1 for p in inc if p.get("theme")),
    }
    print(f"Corpus: {corpus.get('topic', '?')}")
    for label, c in counts.items():
        print(f"  {label:<24} {c}")


BIB_TYPE_HINTS = ("journal", "transactions", "tods", "tkde", "vldb j")


def bib_escape(s: str) -> str:
    return str(s).replace("\\", "").replace("{", "").replace("}", "")


def cmd_bibtex(args) -> None:
    corpus = load_corpus(args.corpus)
    rows = [
        (k, r)
        for k, r in sorted(corpus["papers"].items())
        if r["status"]["screened"] == "included"
    ]
    if not rows:
        fail("no included papers in the corpus -- screen first (corpus.py set)")
    print("% Skeleton BibTeX generated from corpus metadata by corpus.py.")
    print("% NOT yet trustworthy: run the verify-citations skill on this file")
    print("% to confirm every entry against Crossref/DBLP/Semantic Scholar.")
    for key, r in rows:
        venue = (r.get("venue") or "").lower()
        if r.get("arxiv") and not r.get("doi"):
            entry, vfield = "misc", None
        elif any(h in venue for h in BIB_TYPE_HINTS):
            entry, vfield = "article", "journal"
        else:
            entry, vfield = "inproceedings", "booktitle"
        print(f"\n@{entry}{{{key},")
        print(f"  title = {{{bib_escape(r.get('title', ''))}}},")
        if r.get("authors"):
            print(f"  author = {{{bib_escape(' and '.join(r['authors']))}}},")
        if vfield and r.get("venue"):
            print(f"  {vfield} = {{{bib_escape(r['venue'])}}},")
        if r.get("year"):
            print(f"  year = {{{r['year']}}},")
        if r.get("doi"):
            print(f"  doi = {{{r['doi']}}},")
        if r.get("arxiv"):
            print(f"  eprint = {{{r['arxiv']}}},")
            print("  archivePrefix = {arXiv},")
        print("}")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--corpus",
        default="corpus.json",
        help="path to corpus.json (default: ./corpus.json)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add", help="add one paper by hand")
    pa.add_argument("--key", required=True, help="cite key, e.g. li2024learned")
    pa.add_argument("--title")
    pa.add_argument("--authors", help="semicolon-separated author names")
    pa.add_argument("--year", type=int)
    pa.add_argument("--venue")
    pa.add_argument("--doi")
    pa.add_argument("--arxiv")
    pa.add_argument("--url")
    pa.add_argument("--source", help="where this hit came from (dblp/s2/...)")
    pa.add_argument("--update", action="store_true",
                    help="allow updating an existing key")
    pa.set_defaults(func=cmd_add)

    pi = sub.add_parser("import", help="bulk-add from a JSON array of records")
    pi.add_argument("file", help="JSON file from find-papers --json, or - for stdin")
    pi.add_argument("--source", default="search",
                    help="provenance label (dblp/crossref/s2/arxiv/snowball)")
    pi.add_argument("--query", help="the search query, recorded in search_log")
    pi.set_defaults(func=cmd_import)

    ps = sub.add_parser("set", help="update status/theme of one paper")
    ps.add_argument("key")
    ps.add_argument("--screened", choices=SCREENED_VALUES)
    ps.add_argument("--fetched", choices=sorted(YESNO))
    ps.add_argument("--extracted", choices=sorted(YESNO))
    ps.add_argument("--verified", choices=sorted(YESNO))
    ps.add_argument("--theme", help="theme slug (empty string clears)")
    ps.add_argument("--reason", help="screening reason, e.g. 'out of scope: not spatial'")
    ps.set_defaults(func=cmd_set)

    pl = sub.add_parser("list", help="list papers with filters")
    pl.add_argument("--screened", choices=SCREENED_VALUES)
    pl.add_argument("--fetched", choices=sorted(YESNO))
    pl.add_argument("--extracted", choices=sorted(YESNO))
    pl.add_argument("--verified", choices=sorted(YESNO))
    pl.add_argument("--theme")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    pt = sub.add_parser("stats", help="pipeline progress counts")
    pt.set_defaults(func=cmd_stats)

    pb = sub.add_parser("bibtex", help="emit skeleton BibTeX for included papers")
    pb.set_defaults(func=cmd_bibtex)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
