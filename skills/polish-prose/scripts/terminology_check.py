#!/usr/bin/env python3
"""Deterministic terminology-consistency checker for the polish-prose skill.

Finds, with line numbers:

  - compound-term variants: the same concept written as 'dataset',
    'data set', and 'data-set' (or 'runtime' / 'run time' / 'run-time')
    in one document — pick one form;
  - acronym discipline: acronyms used before their '(ABC)' definition,
    defined more than once, used but never defined, or defined but never
    used again;
  - British/American spelling mixing: -ise/-ize (and -yse/-yze) families
    plus a pair list (behaviour/behavior, modelling/modeling, ...);
  - optional glossary enforcement (--glossary): flag every occurrence of a
    non-canonical variant. Glossary lines look like
        canonical term = variant one | variant two
    ('#' comments and blank lines allowed).

The checker reports inconsistencies; it never decides which form is right —
that is a one-line decision for the author, recorded in the terminology
table the skill produces.

Usage:
    python3 terminology_check.py <main.tex|draft.txt|-> [--glossary FILE]
        [--allow ACRO[,ACRO...]] [--strict] [--json]

Exit codes: 0 ok; 1 with --strict when any WARN remains; 2 bad input.
"""

import argparse
import json
import re
import sys

import texprose

# acronyms nobody needs to define in a CS paper — extend with --allow
ACRO_WHITELIST = {
    "USA", "UK", "EU", "US", "CPU", "GPU", "TPU", "RAM", "SSD", "API",
    "URL", "URI", "HTTP", "HTTPS", "PDF", "HTML", "JSON", "XML", "YAML",
    "SQL", "AI", "ML", "IEEE", "ACM", "DOI", "ORCID", "ISBN", "ISSN",
    "OS", "IO", "ID", "IDS", "GB", "MB", "KB", "TB", "MS", "FPS", "RGB",
    "PC", "IT", "NLP", "PHD",
}

STOPWORDS = {"of", "the", "and", "for", "in", "on", "a", "an", "to",
             "with", "by", "at", "or"}

# explicit British/American pairs not covered by the suffix families
SPELLING_PAIRS = [
    ("behaviour", "behavior"), ("colour", "color"), ("favour", "favor"),
    ("flavour", "flavor"), ("neighbour", "neighbor"), ("centre", "center"),
    ("metre", "meter"), ("fibre", "fiber"), ("modelling", "modeling"),
    ("modelled", "modeled"), ("labelling", "labeling"),
    ("labelled", "labeled"), ("cancelled", "canceled"), ("grey", "gray"),
    ("artefact", "artifact"), ("catalogue", "catalog"),
    ("licence", "license"), ("defence", "defense"), ("offence", "offense"),
]

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")


class Report:
    def __init__(self):
        self.findings = []

    def add(self, sev, tag, line, msg):
        self.findings.append(
            {"severity": sev, "tag": tag, "line": line, "message": msg})

    def count(self, sev):
        return sum(1 for f in self.findings if f["severity"] == sev)


def fmt_lines(lns, cap=6):
    shown = ", ".join(str(x) for x in lns[:cap])
    if len(lns) > cap:
        shown += ", ..."
    return shown


def tokenize(plines):
    """[(lineno, token), ...] preserving case."""
    toks = []
    for ln, text in plines:
        for m in WORD_RE.finditer(text):
            toks.append((ln, m.group(0)))
    return toks


def check_compound_variants(rep, toks):
    """dataset vs data set vs data-set — keyed on the dehyphenated form."""
    single = {}   # normkey -> {form: [lines]}
    for ln, tok in toks:
        low = tok.lower()
        if "-" in low:
            key = low.replace("-", "")
            if len(key) >= 6 and key.isalpha():
                single.setdefault(key, {}).setdefault(low, []).append(ln)
        elif low.isalpha() and len(low) >= 6:
            single.setdefault(low, {}).setdefault(low, []).append(ln)

    spaced = {}   # normkey -> {“a b”: [lines]}
    for i in range(len(toks) - 1):
        ln_a, a = toks[i]
        ln_b, b = toks[i + 1]
        la, lb = a.lower(), b.lower()
        if not (la.isalpha() and lb.isalpha()):
            continue
        if len(la) < 2 or len(lb) < 2 or la in STOPWORDS or lb in STOPWORDS:
            continue
        key = la + lb
        if len(key) >= 6:
            spaced.setdefault(key, {}).setdefault(
                "%s %s" % (la, lb), []).append(ln_a)

    for key in sorted(set(single) & set(spaced)):
        forms = dict(single[key])
        forms.update(spaced[key])
        if len(forms) < 2:
            continue
        parts = ["'%s' (x%d, lines %s)" % (f, len(lns), fmt_lines(lns))
                 for f, lns in sorted(forms.items())]
        rep.add("WARN", "compound-variant", min(min(l) for l in
                                                forms.values()),
                "one concept, %d spellings: %s — pick one form and use it "
                "everywhere" % (len(forms), "; ".join(parts)))


def find_acronym_definitions(plines):
    """'Long Form Name (LFN)' occurrences whose initials match.

    Returns {ACRO: [(line, expansion)]}."""
    defs = {}
    def_re = re.compile(
        r"((?:[A-Za-z][A-Za-z'\-]*[ \t]+){1,7})\(\s*([A-Z][A-Za-z0-9]{1,9})s?\s*\)")
    for ln, text in plines:
        for m in def_re.finditer(text):
            words = m.group(1).split()
            acro = m.group(2)
            if not re.fullmatch(r"[A-Z]{2,10}", acro.upper()):
                continue
            sig = [w for w in words if w.lower() not in STOPWORDS]
            # try suffixes of the significant words, longest first
            target = acro.lower()
            for start in range(len(sig)):
                cand = "".join(w[0].lower() for w in sig[start:])
                if cand == target:
                    expansion = " ".join(words[len(words) - len(sig)
                                               + start:]) \
                        if False else " ".join(sig[start:])
                    defs.setdefault(acro.upper(), []).append(
                        (ln, expansion))
                    break
    return defs


def check_acronyms(rep, plines, allow):
    defs = find_acronym_definitions(plines)
    uses = {}    # ACRO -> [lines] (uses outside the defining parenthetical)
    use_re = re.compile(r"\b([A-Z][A-Z0-9]{1,9})\b")
    for ln, text in plines:
        # drop the "(ABC)" definitional parentheticals before counting uses
        scrub = re.sub(r"\(\s*[A-Z][A-Za-z0-9]{1,9}s?\s*\)", " ", text)
        for m in use_re.finditer(scrub):
            tok = m.group(1)
            if sum(c.isupper() for c in tok) >= 2:
                uses.setdefault(tok, []).append(ln)

    whitelist = ACRO_WHITELIST | {a.upper() for a in allow}

    for acro, places in sorted(defs.items()):
        if len(places) > 1:
            rep.add("WARN", "acronym-redefined", places[0][0],
                    "%s defined %d times (lines %s) — define once at first "
                    "use" % (acro, len(places),
                             fmt_lines([ln for ln, _ in places])))
        expansions = {e.lower() for _, e in places}
        if len(expansions) > 1:
            rep.add("WARN", "acronym-expansion-drift", places[0][0],
                    "%s expanded differently: %s — keep one expansion"
                    % (acro, "; ".join(sorted(repr(e) for _, e in places))))
        first_def = min(ln for ln, _ in places)
        early = [ln for ln in uses.get(acro, []) if ln < first_def]
        if early:
            rep.add("WARN", "acronym-before-definition", early[0],
                    "%s used on line%s %s before its definition on line %d"
                    % (acro, "s" if len(early) > 1 else "",
                       fmt_lines(early), first_def))
        later = [ln for ln in uses.get(acro, []) if ln > first_def]
        if not later and not early:
            rep.add("INFO", "acronym-unused", first_def,
                    "%s defined on line %d but never used again — drop the "
                    "definition (or the acronym)" % (acro, first_def))

    for acro, lns in sorted(uses.items()):
        if acro in defs or acro in whitelist:
            continue
        if len(acro) < 2 or not any(c.isalpha() for c in acro):
            continue
        rep.add("WARN", "acronym-undefined", lns[0],
                "%s used (x%d, lines %s) but never defined — define at "
                "first use or add to --allow if it is universally known"
                % (acro, len(lns), fmt_lines(lns)))


def check_spelling(rep, toks):
    # suffix families
    fams = {"british": {}, "american": {}}
    pats = [
        ("british", re.compile(r"[a-z]+(?:ise|ised|ising|iser|isation|isations)$")),
        ("american", re.compile(r"[a-z]+(?:ize|ized|izing|izer|ization|izations)$")),
        ("british", re.compile(r"[a-z]+(?:yse|ysed|ysing)$")),
        ("american", re.compile(r"[a-z]+(?:yze|yzed|yzing)$")),
    ]
    # words that end in -ise but are not British variants
    ise_ok = {"otherwise", "likewise", "wise", "rise", "arise", "raise",
              "noise", "premise", "promise", "exercise", "comprise",
              "precise", "concise", "expertise", "compromise", "disguise",
              "revise", "devise", "supervise", "advise", "improvise",
              "franchise", "surprise", "paradise", "merchandise", "anise",
              "advertise", "demise", "despise", "turquoise", "clockwise",
              "stepwise", "pairwise", "elementwise", "pointwise"}

    def ise_exempt(low):
        """True for whitelist words and their -d/-s/-ing inflections."""
        if low in ise_ok:
            return True
        for strip, add in (("d", ""), ("s", ""), ("ing", "e")):
            if low.endswith(strip) and (low[:-len(strip)] + add) in ise_ok:
                return True
        return False

    for ln, tok in toks:
        low = tok.lower()
        if ise_exempt(low) or not low.isalpha():
            continue
        for fam, rx in pats:
            if rx.fullmatch(low):
                fams[fam].setdefault(low, []).append(ln)
                break
    if fams["british"] and fams["american"]:
        b = sorted(fams["british"])[:5]
        a = sorted(fams["american"])[:5]
        rep.add("WARN", "spelling-mix", min(min(l) for l in
                                            fams["british"].values()),
                "British and American -ise/-ize spellings mixed: %s vs %s "
                "— pick the convention your venue family uses and stick to "
                "it" % (", ".join(b), ", ".join(a)))

    index = {}
    for ln, tok in toks:
        index.setdefault(tok.lower(), []).append(ln)
    for brit, amer in SPELLING_PAIRS:
        if brit in index and amer in index:
            rep.add("WARN", "spelling-mix", index[brit][0],
                    "'%s' (lines %s) and '%s' (lines %s) both appear — "
                    "pick one spelling"
                    % (brit, fmt_lines(index[brit]),
                       amer, fmt_lines(index[amer])))


def load_glossary(path):
    """canonical = variant | variant  ->  [(canonical, [variants])]"""
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if "=" not in line:
                raise ValueError("glossary line %d has no '=': %r"
                                 % (i, line))
            canon, rest = line.split("=", 1)
            variants = [v.strip() for v in rest.split("|") if v.strip()]
            if not canon.strip() or not variants:
                raise ValueError("glossary line %d is incomplete: %r"
                                 % (i, line))
            entries.append((canon.strip(), variants))
    return entries


def check_glossary(rep, plines, entries):
    for canon, variants in entries:
        for var in variants:
            rx = re.compile(r"\b%s\b" % re.escape(var), re.I)
            hits = [ln for ln, text in plines if rx.search(text)]
            if hits:
                rep.add("WARN", "glossary", hits[0],
                        "non-canonical term '%s' (x%d, lines %s) — the "
                        "agreed term is '%s'"
                        % (var, len(hits), fmt_lines(hits), canon))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check a draft for inconsistent terminology: compound-"
        "term variants (dataset/data set/data-set), acronym discipline, "
        "British/American spelling mixing, and optional glossary "
        "enforcement. Prints a Markdown report with line numbers.")
    parser.add_argument("source", help="main .tex file, plain text, or - "
                        "for stdin")
    parser.add_argument("--glossary", default=None,
                        help="glossary file: 'canonical = variant | variant' "
                        "per line")
    parser.add_argument("--allow", default="",
                        help="comma-separated acronyms to treat as "
                        "universally known (skip undefined-acronym check)")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any WARN finding")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    args = parser.parse_args(argv)

    try:
        raw, label = texprose.read_source(args.source)
    except texprose.SourceError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    entries = []
    if args.glossary:
        try:
            entries = load_glossary(args.glossary)
        except (OSError, ValueError) as exc:
            sys.stderr.write("error: cannot read glossary: %s\n" % exc)
            return 2

    tex = texprose.is_tex(args.source, raw)
    plines = texprose.prose_lines(raw, tex=tex)
    if not texprose.word_count(plines):
        sys.stderr.write("error: no prose found in %s\n" % label)
        return 2
    toks = tokenize(plines)

    rep = Report()
    check_compound_variants(rep, toks)
    check_acronyms(rep, plines,
                   [a for a in args.allow.split(",") if a.strip()])
    check_spelling(rep, toks)
    if entries:
        check_glossary(rep, plines, entries)

    order = {"RISK": 0, "WARN": 1, "INFO": 2}
    rep.findings.sort(key=lambda f: (order[f["severity"]],
                                     f["line"] if f["line"] else 0))
    if args.json:
        print(json.dumps({"source": label, "findings": rep.findings,
                          "summary": {s: rep.count(s)
                                      for s in ("RISK", "WARN", "INFO")}},
                         indent=2))
    else:
        print("# Terminology check — %s\n" % label)
        print("## Findings\n")
        if not rep.findings:
            print("- nothing to report")
        for f in rep.findings:
            loc = ("line %d: " % f["line"]) if f["line"] else ""
            print("- %s [%s] %s%s" % (f["severity"], f["tag"], loc,
                                      f["message"]))
        print("\n## Summary\n")
        print("RISK: %d, WARN: %d, INFO: %d"
              % (rep.count("RISK"), rep.count("WARN"), rep.count("INFO")))

    if args.strict and (rep.count("RISK") or rep.count("WARN")):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
