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
  bibtex    emit skeleton BibTeX from corpus metadata (stdout), using the
            corpus's own cite keys verbatim. Fields come from search metadata
            and MUST then be checked with the verify-citations skill before
            use.
  check-keys assert references.bib uses exactly the corpus's included-paper
            keys (no drift, no duplicates) -- the cross-file consistency gate
            that keeps the corpus, the .bib, and the review's [@key]s aligned.
  verify-audit reconcile 'verified' flags against a verify-citations --json
            report: verifies ONLY entries the report confirmed, clears the
            rest, and echoes the verdict (PASS/PARTIAL-PASS/FAIL) verbatim so
            no prose can launder it into "verified, 0 errors".

Setting "verified" carries PROVENANCE. `set --verified yes` requires --source
(the index whose canonical record confirmed the entry) and records when; or
use `verify-audit` to set it from an actual verify-citations artifact. A
verified flag with no provenance is a broken gate, not a pass.

corpus.py is the SINGLE SOURCE OF TRUTH for cite keys (see make_key): keys are
minted on import and reused by `bibtex`; never hand-edit a key in the .bib.

Examples:
  python3 corpus.py add --corpus lit-review/x/corpus.json \\
      --key li2024learned --title "Learned Spatial Indexes" \\
      --doi 10.1145/3589132.3625571 --year 2024 --venue SIGSPATIAL
  python3 corpus.py import --corpus c.json --source dblp hits.json
  python3 corpus.py set --corpus c.json li2024learned --screened included
  python3 corpus.py set --corpus c.json li2024learned --verified yes --source dblp
  python3 corpus.py verify-audit --corpus c.json --report citecheck.json
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
            # Provenance for the verified flag. "verified": true is ONLY
            # trustworthy when an actual verify-citations round-trip set these:
            # which provider's canonical record confirmed the entry, and when.
            # A verified flag with no verified_via is a broken gate, not a pass.
            "verified_via": None,
            "verified_at": None,
        },
    }


def make_key(rec: dict, existing: dict) -> str:
    """firstauthorlastname + year + first significant title word.

    This is the SINGLE SOURCE OF TRUTH for cite keys. Every key in the corpus
    is minted here (on import) or supplied by hand (cmd_add); `cmd_bibtex`
    then emits references.bib using *exactly* those corpus keys, and
    `cmd_check_keys` asserts the .bib has not drifted from the corpus. Never
    hand-edit a key in references.bib -- change it here (corpus.py add
    --update) so the corpus, the .bib, and the review's [@key]s stay in lock
    step and the verified-citation chain is not silently broken."""
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
    for flag in ("fetched", "extracted"):
        val = getattr(args, flag)
        if val is not None:
            rec["status"][flag] = YESNO[val]
            changed.append(f"{flag}={val}")
    if args.verified is not None:
        want = YESNO[args.verified]
        if want:
            # "verified": true must carry provenance from an actual
            # verify-citations round-trip THIS session -- the provider whose
            # canonical record confirmed the entry. Flipping the flag without
            # provenance is exactly the broken gate (verified:true with no
            # artifact) this enforcement exists to prevent. Refuse it.
            if not args.source:
                fail("--verified yes requires --source <provider> (the index "
                     "whose canonical record confirmed this entry: "
                     "dblp/crossref/s2/arxiv/datacite). A verified flag with "
                     "no provenance is a broken gate, not a pass. Set it from "
                     "an actual verify-citations run -- or use the audit path: "
                     "corpus.py verify-audit --report citecheck.json", 2)
            rec["status"]["verified"] = True
            rec["status"]["verified_via"] = args.source
            rec["status"]["verified_at"] = date.today().isoformat()
            changed.append(f"verified=yes (via {args.source})")
        else:
            rec["status"]["verified"] = False
            rec["status"]["verified_via"] = None
            rec["status"]["verified_at"] = None
            changed.append("verified=no")
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
    # A verified flag with no recorded provenance is a broken gate -- surface it
    # rather than letting it read as a clean "verified" count.
    no_prov = sorted(
        k for k, p in corpus["papers"].items()
        if p["status"]["verified"] and not p["status"].get("verified_via")
    )
    if no_prov:
        print(f"\n  WARNING: {len(no_prov)} entr"
              f"{'y' if len(no_prov) == 1 else 'ies'} marked verified with NO "
              f"provenance (verified_via unset) -- a broken gate, not a pass. "
              f"Re-confirm via verify-citations: {', '.join(no_prov)}")


# Generic, field-agnostic words in a venue string that mark a journal (so the
# skeleton entry is @article, not @inproceedings). Container-kind words only --
# never a specific venue/journal name -- so this stays portable across fields.
# verify-citations reconciles the type against the canonical record anyway.
BIB_TYPE_HINTS = ("journal", "transactions", "letters", "review",
                  "quarterly", "annals", "acta")


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


BIB_KEY_RE = re.compile(r"@\s*[A-Za-z]+\s*[{(]\s*([^,\s{}()\"]+)")


def bib_keys(path: str) -> list[str]:
    """Cite keys defined in a .bib file (stdlib regex scan; tolerant of the
    common forms). Used only for the cross-file consistency assertion."""
    text = Path(path).read_text(encoding="utf-8")
    keys = []
    for m in BIB_KEY_RE.finditer(text):
        # skip @string/@comment/@preamble pseudo-entries
        head = text[m.start():m.start() + 40].lower().lstrip("@ ")
        if head.startswith(("string", "comment", "preamble")):
            continue
        keys.append(m.group(1))
    return keys


def cmd_check_keys(args) -> None:
    """Assert references.bib uses exactly the corpus's included-paper keys.

    Catches the silent failure where corpus.json and references.bib drift
    apart (a .bib entry hand-renamed, an included paper missing from the
    .bib), which breaks the verified-citation chain because check_review.py
    gates on corpus keys while pandoc/LaTeX resolves against the .bib."""
    corpus = load_corpus(args.corpus)
    included = {
        k for k, r in corpus["papers"].items()
        if r["status"]["screened"] == "included"
    }
    bibpath = Path(args.bib)
    if not bibpath.exists():
        fail(f"bib file not found: {args.bib}\n"
             "Generate it from the corpus: corpus.py bibtex > references.bib")
    bkeys = bib_keys(args.bib)
    bset = set(bkeys)
    dups = sorted({k for k in bkeys if bkeys.count(k) > 1})
    missing = sorted(included - bset)   # in corpus, absent from .bib
    extra = sorted(bset - included)     # in .bib, not an included corpus key

    print(f"check-keys: {args.bib} against {args.corpus}")
    print(f"  {len(included)} included corpus keys, {len(bset)} .bib keys")
    problems = 0
    for k in dups:
        print(f"  FAIL  duplicate key in .bib: {k}")
        problems += 1
    for k in missing:
        print(f"  FAIL  included paper has no .bib entry: {k} "
              "(re-run: corpus.py bibtex > references.bib)")
        problems += 1
    for k in extra:
        print(f"  FAIL  .bib key not an included corpus paper: {k} "
              "(hand-edited key? regenerate the .bib from the corpus)")
        problems += 1
    if problems:
        print(f"\nRESULT: FAIL ({problems} key mismatches) -- corpus.json is "
              "the source of truth; regenerate references.bib with "
              "corpus.py bibtex.")
        sys.exit(1)
    print("\nRESULT: PASS (corpus keys and .bib keys are in lock step)")


def cmd_verify_audit(args) -> None:
    """Reconcile corpus 'verified' flags against an actual verify-citations
    JSON report (check_bibtex.py --json), and echo the verdict verbatim.

    This is the honest, batchable path to setting 'verified': instead of
    flipping flags by hand, point at the machine artifact. The audit:
      - sets verified:true ONLY for entries the report confirmed (status
        VERIFIED/VERIFIED*, no ERROR flag), recording
        verified_via='verify-citations' + the date for provenance;
      - clears verified for every entry the report did NOT confirm --
        errored, unresolved, skipped, or absent from the report alike;
      - REFUSES to treat a PARTIAL-PASS or FAIL report as a clean pass --
        it mirrors the report's exact verdict_line so no prose can launder
        'PARTIAL-PASS, N WARN, K skipped' into 'verified, 0 errors'.
    """
    corpus = load_corpus(args.corpus)
    rp = Path(args.report)
    if not rp.exists():
        fail(f"report not found: {args.report}\n"
             "Produce it first: check_bibtex.py refs.bib --json citecheck.json")
    try:
        report = json.loads(rp.read_text(encoding="utf-8"))
    except ValueError as e:
        fail(f"report is not valid JSON: {e}")
    if not isinstance(report, dict) or "entries" not in report:
        fail("report is not a check_bibtex.py --json report (no 'entries')")

    verdict = report.get("verdict", "UNKNOWN")
    verdict_line = report.get("verdict_line") or verdict
    # Per-entry status keyed by cite key. check_bibtex entries carry a "key".
    by_key = {}
    for e in report.get("entries", []):
        k = e.get("key")
        if k:
            by_key[k] = e

    verified_now, cleared, missing = [], [], []
    today = date.today().isoformat()
    for key, rec in corpus["papers"].items():
        if rec["status"]["screened"] != "included":
            continue
        e = by_key.get(key)
        if e is None:
            missing.append(key)
            continue
        status = e.get("status", "")
        has_error = any(f.get("severity") == "ERROR" for f in e.get("flags", []))
        if status in ("VERIFIED", "VERIFIED*") and not has_error:
            rec["status"]["verified"] = True
            rec["status"]["verified_via"] = "verify-citations"
            rec["status"]["verified_at"] = today
            verified_now.append(key)
        else:
            # Not confirmed by the report -> not verified, no matter what the
            # flag said before. A skipped/errored/unresolved entry is NOT a pass.
            if rec["status"]["verified"]:
                cleared.append(key)
            rec["status"]["verified"] = False
            rec["status"]["verified_via"] = None
            rec["status"]["verified_at"] = None

    corpus.setdefault("verify_runs", []).append(
        {"date": today, "report": args.report, "verdict": verdict,
         "verdict_line": verdict_line, "verified": len(verified_now)})
    save_corpus(args.corpus, corpus)

    print(f"verify-audit: {args.report} against {args.corpus}")
    print(f"  VERDICT (verbatim from report): {verdict_line}")
    print(f"  {len(verified_now)} entr"
          f"{'y' if len(verified_now) == 1 else 'ies'} marked verified "
          f"(via verify-citations).")
    if cleared:
        print(f"  {len(cleared)} previously-verified entr"
              f"{'y' if len(cleared) == 1 else 'ies'} CLEARED (the report did "
              f"not confirm them): {', '.join(sorted(cleared))}")
    if missing:
        print(f"  {len(missing)} included corpus key(s) absent from the report "
              f"-- NOT verified: {', '.join(sorted(missing))}")
    if verdict != "PASS":
        print(f"\n  {verdict} is NOT a clean pass. Mirror the verdict line "
              "above verbatim in the review's prose -- do not collapse it into "
              "'verified, 0 errors'. Re-run verify-citations on the open items "
              "before declaring the bibliography verified.")
        sys.exit(2)
    print("\nRESULT: PASS -- every included entry confirmed by the report.")


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
    ps.add_argument("--source",
                    help="provider whose canonical record confirmed the entry "
                    "(dblp/crossref/s2/arxiv/datacite); REQUIRED with "
                    "--verified yes so the verified flag carries provenance")
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

    pck = sub.add_parser(
        "check-keys",
        help="assert references.bib uses exactly the corpus's included keys")
    pck.add_argument("bib", help="path to references.bib")
    pck.set_defaults(func=cmd_check_keys)

    pva = sub.add_parser(
        "verify-audit",
        help="reconcile verified flags against a verify-citations --json "
        "report; mirrors the verdict verbatim, refuses to pass a "
        "PARTIAL-PASS/FAIL")
    pva.add_argument("--report", required=True,
                     help="path to check_bibtex.py --json output")
    pva.set_defaults(func=cmd_verify_audit)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
