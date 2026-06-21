#!/usr/bin/env python3
"""Anonymization (double-blind) leak checker for LaTeX submissions.

Scans a .tex file (following \\input) against a venue profile and reports
identity leaks that venues desk-reject for: populated \\author/\\affiliation/
\\email blocks, \\thanks, acknowledgments sections, funding/grant lines,
identifying repository or personal links, first-person self-citations, and
pdfauthor metadata set via hyperref.

Usage:
    python3 check_anonymization.py paper.tex --venue venues/conferences/neurips-2026.yml

Exit codes: 0 clean (or warnings without --strict), 1 ERROR findings, 2 failure.
At single-blind venues the check is skipped (use --force to run it anyway).
"""
from __future__ import annotations

import re
import sys

import texlib
from texlib import Finding

_ANON_OK_RE = re.compile(
    r"anon|blind|omitted|hidden|redacted|withheld|paper\s*(?:id|#|number)|"
    r"submission\s*(?:id|#|number)|under\s+review",
    re.I,
)

_IDENTITY_HOSTS = (
    "github.com", "gitlab.com", "bitbucket.org", "huggingface.co",
    "sites.google.com", "drive.google.com", "dropbox.com", "onedrive",
    "kaggle.com", "linkedin.com", "twitter.com", "x.com", "youtube.com",
    "youtu.be", "zenodo.org", "osf.io", "figshare.com",
)
_ANON_OK_HOSTS = ("anonymous.4open.science", "anonymous.science")

_URL_RE = re.compile(r"(?:https?://|www\.)[^\s{}\\%]+", re.I)

_SELF_CITE_PATTERNS = [
    r"\bour (?:previous|prior|earlier|recent|own) (?:work|workshop paper|paper|papers|study|studies|approach|system|method|results?)\b",
    r"\bwe (?:previously|recently|earlier) (?:showed|proposed|presented|introduced|demonstrated|developed|published|reported)\b",
    r"\b(?:extends?|extending|builds? (?:up)?on|building (?:up)?on|follow(?:s|ing)?[- ]up (?:to|on)) our\b",
    r"\bin our (?:previous|prior|earlier) [a-z]+\b",
    r"\bour\b[^.\n]{0,40}?\\cite",
]

_FUNDING_RES = [
    re.compile(r"\bgrant\s+(?:no\.?|number|agreement)\b", re.I),
    re.compile(r"\b(?:funded|financially supported)\s+by\b", re.I),
    re.compile(r"\b(?:NSF|NIH|ERC|DFG|DARPA|ONR|AFOSR|EPSRC|NSERC|JSPS)\b[^.\n]{0,30}\d"),
]


def _clean_arg(arg: str) -> str:
    """Strip inner commands/braces from a command argument for inspection."""
    arg = re.sub(r"\\[a-zA-Z@]+\s*(?:\[[^\]]*\])?", " ", arg)
    return re.sub(r"[{}~\s]+", " ", arg).strip()


def _snippet(s: str, n: int = 60) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 3] + "..."


def collect(doc: texlib.TexDoc, profile: dict, track: dict | None, args) -> list[Finding]:
    findings: list[Finding] = []
    review = profile.get("review") or {}
    blind = review.get("blind")
    force = getattr(args, "force", False)
    template = (profile.get("format") or {}).get("template")

    def add(sev, check, pos, msg):
        f, ln = doc.loc(pos)
        findings.append(Finding(sev, check, f, ln, msg))

    if blind == "single" and not force:
        findings.append(
            Finding(
                "INFO",
                "anonymization/skipped",
                args.tex,
                None,
                f"{profile.get('id')} is SINGLE-blind: author names should be "
                "listed on the submission. Anonymization checks skipped "
                "(re-run with --force to scan anyway).",
            )
        )
        return findings
    if blind is None:
        findings.append(
            Finding(
                "WARN",
                "anonymization/blind-unknown",
                args.tex,
                None,
                "profile does not state the blind level — running all checks; "
                f"verify against the live CFP: {profile.get('cfp_url')}",
            )
        )

    # NeurIPS-style templates hide the author block at submission time, so a
    # populated \author is a hygiene WARN there, an ERROR elsewhere.
    author_sev = "WARN" if template == "neurips" else "ERROR"
    author_note = (
        " (the venue .sty hides authors at submission, but scrub the source "
        "before uploading or sharing)"
        if template == "neurips"
        else ""
    )

    for cmd, check in (
        ("author", "anonymization/author-block"),
        ("affiliation", "anonymization/affiliation"),
        ("institute", "anonymization/affiliation"),
        ("institution", "anonymization/affiliation"),
    ):
        for pos, _opt, arg in doc.find_commands(cmd):
            if arg is None:
                continue
            content = _clean_arg(arg)
            if not content or _ANON_OK_RE.search(content):
                continue
            findings_sev = author_sev
            add(
                findings_sev,
                check,
                pos,
                f"\\{cmd} contains non-anonymous content: \"{_snippet(content)}\""
                + author_note,
            )

    for pos, _opt, arg in doc.find_commands("email"):
        if arg and not _ANON_OK_RE.search(arg) and "example.com" not in arg:
            add("ERROR", "anonymization/email", pos, f"\\email present: \"{_snippet(arg)}\"")

    for pos, _opt, arg in doc.find_commands("orcid"):
        if arg and arg.strip():
            add("ERROR", "anonymization/orcid", pos, f"ORCID id present: {_snippet(arg)}")

    for pos, _opt, arg in doc.find_commands("thanks"):
        if arg and arg.strip():
            add(
                "WARN",
                "anonymization/thanks",
                pos,
                f"\\thanks{{...}} often carries funding/affiliation: \"{_snippet(arg)}\"",
            )

    # acknowledgments: forbidden in double-blind submissions (e.g. NeurIPS)
    for env in ("acks", "ack", "acknowledgments", "acknowledgements"):
        for start, _end, inner in doc.env_spans(env):
            if inner.strip():
                add(
                    "ERROR",
                    "anonymization/acknowledgments",
                    start,
                    f"\\begin{{{env}}} present — remove acknowledgments from a "
                    "double-blind submission",
                )
    for pos, _opt, arg in doc.find_commands("section") + doc.find_commands("section*"):
        if arg and re.search(r"acknowledg", arg, re.I):
            add(
                "ERROR",
                "anonymization/acknowledgments",
                pos,
                f"section \"{_snippet(arg)}\" — remove acknowledgments from a "
                "double-blind submission",
            )

    # funding / grant identifiers
    for m in re.finditer(r"[^\n]+", doc.text):
        line = m.group(0)
        for rex in _FUNDING_RES:
            fm = rex.search(line)
            if fm:
                add(
                    "WARN",
                    "anonymization/funding",
                    m.start() + fm.start(),
                    f"possible funding/grant identifier: \"{_snippet(line.strip())}\"",
                )
                break

    # links
    for m in _URL_RE.finditer(doc.text):
        url = m.group(0).rstrip(".,;)")
        low = url.lower()
        if any(h in low for h in _ANON_OK_HOSTS):
            add("INFO", "anonymization/link-ok", m.start(), f"anonymized repo link: {url}")
        elif any(h in low for h in _IDENTITY_HOSTS):
            add(
                "ERROR",
                "anonymization/identifying-link",
                m.start(),
                f"link can identify authors: {url} — use an anonymized mirror "
                "(e.g. anonymous.4open.science)",
            )
        elif "arxiv.org" in low:
            add(
                "WARN",
                "anonymization/arxiv-link",
                m.start(),
                f"arXiv link: {url} — if this is the authors' own preprint, "
                "cite it in third person instead of linking",
            )
        elif re.search(r"/~[a-z]", low) or "people." in low or "homes." in low:
            add("ERROR", "anonymization/identifying-link", m.start(),
                f"personal homepage link: {url}")
        else:
            add(
                "INFO",
                "anonymization/link-review",
                m.start(),
                f"verify this link does not identify the authors: {url}",
            )

    # first-person self-citations
    for pat in _SELF_CITE_PATTERNS:
        for m in re.finditer(pat, doc.text, re.I):
            add(
                "WARN",
                "anonymization/self-citation",
                m.start(),
                f"first-person self-citation pattern: \"{_snippet(m.group(0))}\" — "
                "cite your own work in third person (\"As shown by X et al. [n]\")",
            )

    # hyperref pdfauthor metadata
    for m in re.finditer(r"pdfauthor\s*=\s*\{([^}]*)\}", doc.text):
        val = m.group(1).strip()
        if val and not _ANON_OK_RE.search(val):
            add(
                "ERROR",
                "anonymization/pdf-metadata",
                m.start(),
                f"hyperref pdfauthor is set: \"{_snippet(val)}\" — clears identity "
                "into the compiled PDF's metadata",
            )

    findings.append(
        Finding(
            "INFO",
            "anonymization/manual",
            args.tex,
            None,
            "source-level scan only: also check compiled-PDF metadata, figures, "
            "and supplementary files — see references/manual-checks.md",
        )
    )
    return findings


def main() -> int:
    ap = texlib.base_parser(__doc__.splitlines()[0])
    ap.add_argument(
        "--force", action="store_true", help="run checks even at single-blind venues"
    )
    # re-parse with the extra flag via run_checker-compatible wrapper
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import venue_profile as vp

    args = ap.parse_args()
    try:
        profile, pnotes = vp.load_profile(args.venue, args.venues_dir)
        track, tnote = vp.pick_track(profile, args.track)
        pnotes.append(tnote)
        doc = texlib.TexDoc.load(args.tex, follow_inputs=not args.no_inputs)
    except (vp.ProfileError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = collect(doc, profile, track, args)
    return texlib.report(
        "check_anonymization", findings, doc.notes, pnotes, args, profile, track
    )


if __name__ == "__main__":
    sys.exit(main())
