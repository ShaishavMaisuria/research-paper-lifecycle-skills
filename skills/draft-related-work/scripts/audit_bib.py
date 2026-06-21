#!/usr/bin/env python3
"""Audit a Related Work draft's citations against its BibTeX file. Offline.

Deterministic checks (no network, stdlib only):
  1. cite keys used in the .tex but missing from the .bib  (blocking)
  2. duplicate bib entries (same DOI, or same normalized title) (blocking)
  3. bib entries with NO verification handle (no doi/eprint/url field) —
     these cannot be checked by verify-citations and are the classic shape
     of a hallucinated reference                                (blocking)
  4. bib entries missing basic fields (title/author/year)      (blocking)
  5. bib entries never cited in the given .tex files           (info)
  6. citation-command census: natbib author-year (\\citet/\\citep) vs plain
     numeric \\cite vs biblatex (\\autocite/\\parencite/\\textcite) — so the
     draft can match the target venue's citation style          (info)

Exit codes: 0 = clean, 3 = blocking findings, 2 = bad input.

Examples:
  python3 scripts/audit_bib.py refs.bib --tex related-work.tex
  python3 scripts/audit_bib.py refs.bib --tex main.tex --tex sections/related.tex --json
  python3 scripts/audit_bib.py refs.bib          # bib-only audit, no tex checks
"""
import argparse
import json
import re
import sys

NATBIB_CMDS = ("citet", "citep", "citealt", "citealp", "citeauthor",
               "citeyear", "citeyearpar", "citenum", "citetext")
BIBLATEX_CMDS = ("autocite", "parencite", "textcite", "footcite",
                 "smartcite", "cites", "autocites")
CITE_RE = re.compile(
    r"\\([A-Za-z]*[Cc]ite[a-z]*)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^{}]*)\}")
COMMENT_RE = re.compile(r"(?<!\\)%.*")


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("bibfile", help="BibTeX file (.bib) backing the draft")
    p.add_argument("--tex", action="append", default=[], metavar="FILE",
                   help="LaTeX file(s) to scan for \\cite commands "
                        "(repeatable; typically the Related Work section "
                        "and/or main.tex)")
    p.add_argument("--json", action="store_true",
                   help="emit findings as JSON instead of a report")
    return p.parse_args()


def fail(msg: str, code: int = 2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        fail(f"cannot read {path}: {e}")
    raise AssertionError("unreachable")


# --- BibTeX parsing (pragmatic, brace-balanced, stdlib only) -----------------

def _split_fields(body: str) -> dict:
    """Parse `name = value` pairs from an entry body (after the key comma)."""
    fields = {}
    i, n = 0, len(body)
    while i < n:
        m = re.match(r"\s*([\w\-+:.]+)\s*=\s*", body[i:])
        if not m:
            break
        name = m.group(1).lower()
        i += m.end()
        if i < n and body[i] == "{":
            depth, j = 0, i
            while j < n:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            val, i = body[i + 1:j], j + 1
        elif i < n and body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                j += 1
            val, i = body[i + 1:j], j + 1
        else:
            m2 = re.match(r"[^,]*", body[i:])
            val = m2.group(0).strip()
            i += m2.end()
        fields[name] = re.sub(r"\s+", " ", val.strip())
        m3 = re.match(r"\s*,", body[i:])
        if not m3:
            break
        i += m3.end()
    return fields


def parse_bib(text: str):
    """Return (entries, problems). entries: list of dicts with key/type/fields."""
    entries, problems = [], []
    i = 0
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        m = re.match(r"@(\w+)\s*\{", text[at:])
        if not m:
            i = at + 1
            continue
        etype = m.group(1).lower()
        body_start = at + m.end()
        depth, j = 1, body_start
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        if depth:
            problems.append(f"unbalanced braces in @{etype} entry near "
                            f"character {at} — entry skipped")
            break
        body = text[body_start:j - 1]
        i = j
        if etype in ("comment", "preamble", "string"):
            continue
        km = re.match(r"\s*([^,\s{}]+)\s*,", body)
        if not km:
            problems.append(f"@{etype} entry near character {at} has no "
                            "citation key — entry skipped")
            continue
        key = km.group(1)
        fields = _split_fields(body[km.end():])
        entries.append({"key": key, "type": etype, "fields": fields})
    return entries, problems


def norm_doi(doi: str) -> str:
    d = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi.org/", "doi:"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


# --- LaTeX side ---------------------------------------------------------------

def scan_tex(text: str):
    """Return (used_keys_in_order, command_counts)."""
    used, counts = [], {}
    for line in text.splitlines():
        line = COMMENT_RE.sub("", line)
        for m in CITE_RE.finditer(line):
            cmd = m.group(1).lower()
            counts[cmd] = counts.get(cmd, 0) + 1
            for key in m.group(2).split(","):
                key = key.strip()
                if key and key != "*":
                    used.append(key)
    return used, counts


def style_census(counts: dict) -> dict:
    natbib = sum(v for c, v in counts.items() if c in NATBIB_CMDS)
    biblatex = sum(v for c, v in counts.items() if c in BIBLATEX_CMDS)
    plain = sum(v for c, v in counts.items()
                if c not in NATBIB_CMDS and c not in BIBLATEX_CMDS)
    dominant = "none"
    if natbib or biblatex or plain:
        dominant = max(
            (("natbib-author-year", natbib),
             ("biblatex", biblatex),
             ("plain-\\cite (numeric-style)", plain)),
            key=lambda t: t[1],
        )[0]
    return {"natbib_author_year": natbib, "biblatex": biblatex,
            "plain_cite": plain, "dominant": dominant,
            "by_command": dict(sorted(counts.items()))}


# --- main ---------------------------------------------------------------------

def main():
    args = parse_args()
    if not args.bibfile.endswith(".bib"):
        print(f"note: {args.bibfile} does not end in .bib — parsing anyway",
              file=sys.stderr)
    entries, parse_problems = parse_bib(read_file(args.bibfile))
    if not entries:
        fail(f"no BibTeX entries found in {args.bibfile}")

    keys = [e["key"] for e in entries]
    dup_keys = sorted({k for k in keys if keys.count(k) > 1})

    by_doi, by_title = {}, {}
    dup_pairs = []
    for e in entries:
        doi = norm_doi(e["fields"].get("doi", ""))
        if doi:
            if doi in by_doi:
                dup_pairs.append((by_doi[doi], e["key"], f"same DOI {doi}"))
            else:
                by_doi[doi] = e["key"]
        t = norm_title(e["fields"].get("title", ""))
        if t:
            if t in by_title and (by_title[t], e["key"]) not in [
                    (a, b) for a, b, _ in dup_pairs]:
                dup_pairs.append((by_title[t], e["key"], "same title"))
            else:
                by_title.setdefault(t, e["key"])

    no_handle = []
    incomplete = []
    for e in entries:
        f = e["fields"]
        has_handle = bool(
            f.get("doi") or f.get("eprint") or f.get("url") or f.get("ee")
            or f.get("archiveprefix"))
        if not has_handle:
            no_handle.append(e["key"])
        missing = [name for name in ("title", "author", "year")
                   if not f.get(name) and not (name == "author" and f.get("editor"))]
        if missing:
            incomplete.append({"key": e["key"], "missing": missing})

    used, counts = [], {}
    for tex in args.tex:
        u, c = scan_tex(read_file(tex))
        used.extend(u)
        for cmd, v in c.items():
            counts[cmd] = counts.get(cmd, 0) + v
    used_set = set(used)
    defined = set(keys)
    undefined = sorted(used_set - defined)
    unused = sorted(defined - used_set) if args.tex else []

    findings = {
        "bibfile": args.bibfile,
        "tex_files": args.tex,
        "entry_count": len(entries),
        "citations_in_tex": len(used),
        "unique_keys_cited": len(used_set),
        "blocking": {
            "undefined_keys": undefined,
            "duplicate_keys": dup_keys,
            "duplicate_entries": [
                {"a": a, "b": b, "reason": r} for a, b, r in dup_pairs],
            "no_verification_handle": sorted(no_handle),
            "incomplete_entries": incomplete,
            "parse_problems": parse_problems,
        },
        "info": {
            "uncited_entries": unused,
            "citation_style": style_census(counts) if args.tex else None,
        },
    }
    blocking = any(v for v in findings["blocking"].values())

    if args.json:
        json.dump(findings, sys.stdout, indent=2)
        print()
    else:
        print(f"audit: {len(entries)} bib entries, {len(used)} citations "
              f"({len(used_set)} unique keys) in {len(args.tex)} tex file(s)\n")
        if undefined:
            print("BLOCKING — cited but missing from the .bib "
                  "(broken \\cite or invented key):")
            for k in undefined:
                print(f"  - {k}")
        if dup_keys:
            print("BLOCKING — duplicate citation keys:")
            for k in dup_keys:
                print(f"  - {k}")
        if dup_pairs:
            print("BLOCKING — duplicate entries (merge and keep one key):")
            for a, b, r in dup_pairs:
                print(f"  - {a} <-> {b} ({r})")
        if no_handle:
            print("BLOCKING — no DOI/eprint/URL; verify-citations cannot check "
                  "these (classic hallucinated-reference shape):")
            for k in sorted(no_handle):
                print(f"  - {k}")
        if incomplete:
            print("BLOCKING — entries missing basic fields:")
            for it in incomplete:
                print(f"  - {it['key']}: missing {', '.join(it['missing'])}")
        if parse_problems:
            print("BLOCKING — bib parse problems:")
            for pr in parse_problems:
                print(f"  - {pr}")
        if unused:
            print("info — defined but never cited in the given tex "
                  "(prune or cite):")
            for k in unused:
                print(f"  - {k}")
        if args.tex and findings["info"]["citation_style"]:
            cs = findings["info"]["citation_style"]
            print(f"info — citation-command census: natbib author-year="
                  f"{cs['natbib_author_year']}, plain \\cite={cs['plain_cite']}, "
                  f"biblatex={cs['biblatex']} (dominant: {cs['dominant']})")
            print("       match this to the target venue's style — see "
                  "references/placement-conventions.md")
        print()
        print("CLEAN — no blocking findings." if not blocking else
              "RESULT: blocking findings above must be fixed, then every "
              "entry verified via the verify-citations skill.")

    sys.exit(3 if blocking else 0)


if __name__ == "__main__":
    main()
