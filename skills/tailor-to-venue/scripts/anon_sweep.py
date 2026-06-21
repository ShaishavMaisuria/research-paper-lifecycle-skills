#!/usr/bin/env python3
"""Anonymization leak scan for a LaTeX draft at a given blind level (stdlib only).

Scans the resolved .tex sources (and optionally a compiled PDF's metadata and
.bib files) for the leak categories that get papers desk-rejected at
double/triple-blind venues: author blocks, acknowledgments and grant numbers,
identifying repository links, first-person self-citations, \\thanks/emails,
and PDF Author/Creator metadata. For single-blind venues it checks the
opposite direction: that author names are actually present.

This is a SIGNAL scanner, not a verdict machine — every finding needs a human
look. Fix strategies per category: references/anonymization-sweep.md.

Usage:
    python3 anon_sweep.py <main.tex> --level double [--pdf paper.pdf] [--bib refs.bib]
    python3 anon_sweep.py <main.tex> --venue venues/conferences/kdd-2026.yml

Exit codes: 0 scan completed, 1 desk-reject-risk findings present AND
--strict given, 2 bad input.
"""

import argparse
import os
import re
import sys

import texscan
import venueyaml

RISK = "DESK-REJECT RISK"
REVIEW = "REVIEW"
INFO = "INFO"

ANON_HINT = re.compile(r"(?i)anonym|blinded|omitted for (?:blind )?review")


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    sys.exit(2)


def snippet(text, start, end, width=70):
    s = max(0, start - 25)
    frag = re.sub(r"\s+", " ", text[s:end + 35]).strip()
    return (frag[:width] + "...") if len(frag) > width else frag


def scan_tex(text, level):
    """Return list of (severity, category, message)."""
    findings = []

    def grab(pattern, flags=0):
        return list(re.finditer(pattern, text, flags))

    # -- author block ------------------------------------------------------
    author_ms = grab(r"\\author\s*(?:\[[^\]]*\])?\s*\{((?:[^{}]|\{[^{}]*\})*)\}", re.DOTALL) \
        + grab(r"\\IEEEauthorblockN\s*\{([^}]*)\}")
    named = []
    for m in author_ms:
        content = re.sub(r"\\[A-Za-z]+", " ", m.group(1))
        content = re.sub(r"\s+", " ", content).strip()
        if content and not ANON_HINT.search(content):
            named.append(content[:60])
    if level in ("double", "triple"):
        if named:
            findings.append((RISK, "author-block",
                             "author block contains names: \"%s\" — replace with "
                             "Anonymous Author(s) or rely on the template's "
                             "anonymous option" % named[0]))
        elif author_ms:
            findings.append((INFO, "author-block", "author block present and looks anonymized"))
    else:  # single
        if named:
            findings.append((INFO, "author-block", "authors listed (required for single-blind)"))
        elif author_ms:
            findings.append((RISK, "author-block",
                             "venue is single-blind but the author block looks "
                             "anonymized — restore real names and affiliations"))
        else:
            findings.append((REVIEW, "author-block", "no author block found — single-blind "
                             "venues require names on the submission"))

    if level == "single":
        return findings  # remaining categories only matter when hiding identity

    # -- affiliation / email / thanks / orcid -------------------------------
    for pat, cat, msg in [
        (r"\\affiliation\s*\{|\\institution\s*\{|\\IEEEauthorblockA\s*\{",
         "affiliation", "affiliation block present — must not name the institution"),
        (r"\\email\s*\{[^}]+\}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?:edu|org|com|ac\.[a-z]{2}|[a-z]{2})\b",
         "email", "email address found"),
        (r"\\thanks\s*\{|\\titlenote\s*\{",
         "thanks", "\\thanks/\\titlenote present (often carries funding or affiliation)"),
        (r"\\orcid\s*\{|orcid\.org/\d", "orcid", "ORCID identifier found"),
    ]:
        ms = grab(pat)
        if ms:
            findings.append((RISK, cat, "%s: \"%s\"" % (msg, snippet(text, ms[0].start(), ms[0].end()))))

    # -- acknowledgments & funding -------------------------------------------
    ack = grab(r"\\begin\{acks\}|\\section\*?\{\s*Acknowledg|\\acknowledgments\b", re.IGNORECASE)
    if ack:
        findings.append((RISK, "acknowledgments",
                         "acknowledgments section present — remove entirely for "
                         "double/triple-blind submission (restore at camera-ready)"))
    fund = grab(r"(?i)\b(?:funded by|supported by|grant\s+(?:no\.?|number)|"
                r"NSF\s*(?:award|grant)?\s*#?\s*\d|ERC\b|DARPA|Horizon\s*(?:2020|Europe))")
    if fund:
        findings.append((RISK, "funding",
                         "funding/grant language found: \"%s\"" % snippet(text, fund[0].start(), fund[0].end())))

    # -- identifying links ------------------------------------------------------
    for m in grab(r"https?://(?:www\.)?(github\.com|gitlab\.com|bitbucket\.org|"
                  r"huggingface\.co|sites\.google\.com|drive\.google\.com|"
                  r"[A-Za-z0-9.-]+\.github\.io)/[^\s}\\%]*"):
        url = m.group(0)
        if re.search(r"(?i)anonymous|anon\b|4open\.science", url):
            findings.append((INFO, "repo-link", "anonymized link OK: %s" % url))
        else:
            findings.append((RISK, "repo-link",
                             "identifying link: %s — swap for an anonymized mirror "
                             "(e.g. anonymous.4open.science) or remove" % url))
    for m in grab(r"https?://[^\s}\\%]*~[A-Za-z][^\s}\\%]*"):
        findings.append((RISK, "personal-page", "personal homepage URL: %s" % m.group(0)))

    # -- first-person self-citation ------------------------------------------
    selfcite = grab(r"(?i)\b(?:our|my)\s+(?:previous|prior|earlier|recent|own)\s+"
                    r"(?:work|paper|study|system|approach|results?)[^.\n]{0,80}?\\cite")
    selfcite += grab(r"(?i)\bwe\s+(?:previously|earlier)\s+"
                     r"(?:showed|proposed|presented|introduced|developed)[^.\n]{0,80}?\\cite")
    selfcite += grab(r"(?i)\b(?:extends?|extending|builds? on)\s+our\b")
    for m in selfcite:
        findings.append((RISK, "self-citation",
                         "first-person self-citation: \"%s\" — rewrite in third person "
                         "(\"As described by X et al. [n]\")" % snippet(text, m.start(), m.end())))

    # -- soft identity signals -------------------------------------------------
    for pat, msg in [
        (r"(?i)\bIRB\b[^.\n]{0,40}(?:#|no\.?|number|approval)", "IRB approval number can identify the institution"),
        (r"(?i)\b(?:our|the)\s+(?:university|institution|lab|laboratory|company)['s]*\s+(?:cluster|server|campus|students|employees)", "institution-describing phrase"),
        (r"(?i)in\s+submission\s+to|under\s+review\s+at", "mentions of concurrent submissions can deanonymize"),
    ]:
        ms = grab(pat)
        if ms:
            findings.append((REVIEW, "soft-signal",
                             "%s: \"%s\"" % (msg, snippet(text, ms[0].start(), ms[0].end()))))
    if level == "triple":
        findings.append((INFO, "triple-blind",
                         "triple-blind: identity must also be hidden from chairs/ACs — "
                         "scrub submission-system fields and any response-to-reviewers text"))
    return findings


def scan_pdf(path, level):
    findings = []
    hiding = level in ("double", "triple")  # at single-blind, named authors are expected
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        fail("cannot read PDF %s: %s" % (path, exc))
    for key in (b"Author", b"Creator", b"Producer", b"Title"):
        for m in re.finditer(rb"/" + key + rb"\s*\(((?:[^()\\]|\\.){1,200})\)", raw):
            val = m.group(1).decode("latin-1", "replace").strip()
            if not val:
                continue
            if key == b"Author":
                sev = RISK if hiding else INFO
            else:
                sev = REVIEW if hiding else INFO
            findings.append((sev, "pdf-metadata", "PDF /%s = \"%s\"%s"
                             % (key.decode(), val[:80],
                                "" if hiding or key != b"Author"
                                else " (fine at single-blind)")))
    for m in re.finditer(rb"<dc:creator>(.{1,300}?)</dc:creator>", raw, re.DOTALL):
        val = re.sub(rb"<[^>]+>", b" ", m.group(1)).decode("latin-1", "replace")
        val = re.sub(r"\s+", " ", val).strip()
        if val:
            findings.append((RISK if hiding else INFO, "pdf-metadata",
                             "XMP dc:creator = \"%s\"%s"
                             % (val[:80], "" if hiding else " (fine at single-blind)")))
    if not findings:
        findings.append((INFO, "pdf-metadata",
                         "no uncompressed Author/Creator metadata found — metadata may "
                         "live in compressed object streams; confirm with "
                         "`pdfinfo`/`exiftool` before submission"))
    return findings


def scan_bib(path):
    findings = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        fail("cannot read bib %s: %s" % (path, exc))
    for m in re.finditer(r"(?i)note\s*=\s*[{\"]([^}\"]*(?:our|anonym)[^}\"]*)[}\"]", raw):
        findings.append((REVIEW, "bib-note", "%s: note field: \"%s\""
                         % (os.path.basename(path), m.group(1)[:70])))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scan a LaTeX draft for anonymization leaks (double/triple "
        "blind) or for missing author info (single blind). Prints a Markdown report.")
    parser.add_argument("main_tex", help="main .tex file")
    parser.add_argument("--level", choices=["single", "double", "triple"],
                        help="blind level (or derive it via --venue)")
    parser.add_argument("--venue", help="venues/conferences/<id>.yml to read the blind level")
    parser.add_argument("--pdf", help="compiled PDF to scan for metadata leaks")
    parser.add_argument("--bib", action="append", default=[],
                        help="BibTeX file(s) to scan (repeatable)")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any DESK-REJECT RISK finding is present")
    args = parser.parse_args(argv)

    level = args.level
    if level is None and args.venue:
        try:
            profile = venueyaml.load_with_family(args.venue)
        except venueyaml.VenueYamlError as exc:
            fail(str(exc))
        level = (profile.get("review") or {}).get("blind")
        if level not in ("single", "double", "triple"):
            fail("profile %s does not state a usable blind level (%r); pass --level"
                 % (args.venue, level))
    if level is None:
        fail("pass --level single|double|triple or --venue <profile.yml>")

    try:
        text, files, warnings = texscan.read_tex(args.main_tex)
    except texscan.TexScanError as exc:
        fail(str(exc))

    findings = scan_tex(text, level)
    if args.pdf:
        findings.extend(scan_pdf(args.pdf, level))
    for bib in args.bib:
        findings.extend(scan_bib(bib))

    print("# Anonymization sweep: %s (blind level: %s)" % (args.main_tex, level))
    print()
    print("Scanned %d source file(s)%s%s." % (
        len(files),
        " + PDF metadata" if args.pdf else "",
        " + %d bib file(s)" % len(args.bib) if args.bib else ""))
    for w in warnings:
        print("_warning: %s_" % w)
    print()
    order = {RISK: 0, REVIEW: 1, INFO: 2}
    n_risk = 0
    for sev in (RISK, REVIEW, INFO):
        group = [f for f in findings if f[0] == sev]
        if not group:
            continue
        print("## %s (%d)" % (sev, len(group)))
        print()
        for _, cat, msg in sorted(group, key=lambda f: f[1]):
            print("- [%s] %s" % (cat, msg))
        print()
        if sev == RISK:
            n_risk = len(group)
    if not findings:
        print("No findings — still hand-check supplementary materials, video "
              "figures, and the submission-system form fields.")
    print("_Signals only — see references/anonymization-sweep.md for the fix "
          "strategy per category, and re-verify the venue's anonymization policy "
          "on the live CFP._")

    if args.strict and n_risk:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
