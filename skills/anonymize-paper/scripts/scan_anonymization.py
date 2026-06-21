#!/usr/bin/env python3
"""Deep anonymization scanner for double-blind LaTeX submissions, plus the
reverse check (clean de-anonymization) for camera-ready.

Two modes:
  --mode submission   (default) find identity leaks before a double-blind
                      submission: author/affiliation/email/orcid/thanks blocks,
                      acknowledgments, funding/grant ids, identifying links,
                      first-person self-citations, hyperref pdfauthor,
                      LaTeX comments, .bib annotations, home-directory paths,
                      compiled-PDF metadata, supplementary directories.
  --mode camera-ready find anonymization LEFTOVERS after acceptance: placeholder
                      author blocks, anonymous repo links, [review,anonymous]
                      class options, \\anontrue toggles, "omitted for review"
                      text, missing acknowledgments.

Check ids and severities are kept in sync with
skills/preflight-check/scripts/check_anonymization.py (same `anonymization/*`
vocabulary, same host/pattern lists) so reports from the two skills compose;
this scanner adds the deeper channels preflight does not look at.

Usage:
    python3 scan_anonymization.py paper.tex --venue venues/conferences/neurips-2026.yml
    python3 scan_anonymization.py paper.tex --blind double --pdf paper.pdf \\
        --supplementary supplementary/ --names "Jane Doe,Example University"
    python3 scan_anonymization.py paper.tex --mode camera-ready --blind double

Stdlib only; no network. Exit codes: 0 clean (or warnings without --strict),
1 ERROR findings (or WARN with --strict), 2 bad arguments / unreadable files.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys

SEVERITIES = ("ERROR", "WARN", "INFO")


@dataclasses.dataclass
class Finding:
    severity: str  # ERROR | WARN | INFO
    check: str  # e.g. "anonymization/author-block"
    file: str
    line: int | None
    message: str

    def format(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity:5}] {self.check:34} {loc} — {self.message}"


# ---------------------------------------------------------------------------
# Pattern tables — kept in sync with preflight-check/check_anonymization.py
# ---------------------------------------------------------------------------

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
_URL_TRAIL = ".,;)]\"'"

_SELF_CITE_PATTERNS = [
    r"\bour (?:previous|prior|earlier|recent|own) (?:work|workshop paper|paper|papers|study|studies|approach|system|method|results?)\b",
    r"\bwe (?:previously|recently|earlier) (?:showed|proposed|presented|introduced|demonstrated|developed|published|reported)\b",
    r"\b(?:extends?|extending|builds? (?:up)?on|building (?:up)?on|follow(?:s|ing)?[- ]up (?:to|on)) our\b",
    r"\bin our (?:previous|prior|earlier) [a-z]+\b",
    r"\bour\b[^.\n]{0,40}?\\cite",
    r"\b(?:our|my) (?:phd |master'?s? |doctoral )?(?:thesis|dissertation)\b",
]

_FUNDING_RES = [
    re.compile(r"\bgrant\s+(?:no\.?|number|agreement)\b", re.I),
    re.compile(r"\b(?:funded|financially supported)\s+by\b", re.I),
    re.compile(r"\b(?:NSF|NIH|ERC|DFG|DARPA|ONR|AFOSR|EPSRC|NSERC|JSPS)\b[^.\n]{0,30}\d"),
]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_OK_EMAIL_RE = re.compile(r"example\.(?:com|org|edu)|anon", re.I)

_HOME_PATH_RE = re.compile(
    r"(?:/(?:Users|home)/([A-Za-z0-9_.-]+)|[A-Za-z]:\\+Users\\+([A-Za-z0-9_.-]+))"
)
_GENERIC_USERS = {
    "user", "username", "you", "yourname", "anon", "anonymous", "runner",
    "ubuntu", "root", "admin", "vagrant", "docker", "ci", "guest",
}

_INSTITUTION_RE = re.compile(
    r"\b(?:our|my) (?:university|institution|institute|lab\b|laboratory|"
    r"research group|group|department|team|company|hospital|campus)",
    re.I,
)

_COPYRIGHT_RE = re.compile(r"\bcopyright\s*(?:\(c\)|\xa9)?\s*\d{4}[,\s]+(\S[^\n]{1,60})", re.I)
_AUTHOR_HEADER_RE = re.compile(r"^\s*[#%/*\s]*@?[Aa]uthors?\s*[:=]\s*(\S[^\n]*)")

# camera-ready leftovers
_PLACEHOLDER_TEXT_RE = re.compile(
    r"anonymi[sz]ed for (?:the )?(?:review|submission)|"
    r"omitted (?:for|due to) (?:double-?blind |anonymous |blind )?(?:review|submission|anonymity)|"
    r"blinded for review|removed for anonymity|hidden for (?:the )?review|"
    r"withheld for (?:double-?blind )?review|under double-?blind review|"
    r"anonymous (?:author|submission)|de-?anonymi[sz]ed version",
    re.I,
)
_ANON_TOGGLE_ON_RE = re.compile(r"\\anontrue\b|\\anonymoustrue\b|\\toggletrue\s*\{\s*anon")
_ANON_TOGGLE_DEF_RE = re.compile(r"\\newif\\ifanon|\\ifanon\b|\\newtoggle\s*\{\s*anon")

_DOCCLASS_RE = re.compile(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}")
_ML_STY_RE = re.compile(
    r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{(neurips_\d{4}|icml\d{4}|iclr\d{4}_conference)\}"
)

_TEXT_EXTS = {
    ".tex", ".bib", ".bbl", ".md", ".txt", ".py", ".sh", ".r", ".jl",
    ".yaml", ".yml", ".cfg", ".toml", ".rst", ".html", ".css", ".js",
}
_MAX_TEXT_BYTES = 2_000_000


# ---------------------------------------------------------------------------
# LaTeX source loading — two channels: code (comment-stripped) and comments.
# Same comment/brace/\input algorithms as preflight-check/scripts/texlib.py.
# ---------------------------------------------------------------------------


def _split_comment(line: str) -> tuple[str, str]:
    """Return (code, comment) for one source line; keeps \\% literals in code."""
    out: list[str] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            out.append(line[i : i + 2])
            i += 2
            continue
        if c == "%":
            return "".join(out), line[i + 1 :]
        out.append(c)
        i += 1
    return "".join(out), ""


@dataclasses.dataclass
class TexLine:
    file: str
    lineno: int
    code: str
    comment: str


_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def _load_lines(path: pathlib.Path, root: pathlib.Path, seen: set,
                notes: list[str], depth: int = 0) -> list[TexLine]:
    if depth > 8:
        notes.append(f"\\input nesting deeper than 8 at {path}; stopped following")
        return []
    key = str(path.resolve())
    if key in seen:
        notes.append(f"circular \\input detected at {path}; skipped")
        return []
    seen.add(key)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        notes.append(f"could not read {path}: {exc}")
        return []
    out: list[TexLine] = []
    rel = str(path)
    for n, raw in enumerate(text.splitlines(), start=1):
        code, comment = _split_comment(raw)
        out.append(TexLine(rel, n, code, comment))
        for m in _INPUT_RE.finditer(code):
            child = m.group(1).strip()
            cpath = root / child
            if cpath.suffix == "":
                cpath = cpath.with_suffix(".tex")
            if cpath.is_file():
                out.extend(_load_lines(cpath, root, seen, notes, depth + 1))
            else:
                notes.append(f"{rel}:{n}: \\input{{{child}}} not found; skipped")
    return out


class TexSource:
    """Flattened LaTeX source with code/comment channels and line mapping."""

    def __init__(self, lines: list[TexLine], notes: list[str], root_dir: pathlib.Path):
        self.lines = lines
        self.notes = notes
        self.root_dir = root_dir
        self.text = "\n".join(ln.code for ln in lines)
        self._starts: list[int] = []
        pos = 0
        for ln in lines:
            self._starts.append(pos)
            pos += len(ln.code) + 1

    @classmethod
    def load(cls, path: str, follow_inputs: bool = True) -> "TexSource":
        p = pathlib.Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"tex file not found: {p}")
        notes: list[str] = []
        if follow_inputs:
            lines = _load_lines(p, p.parent, set(), notes)
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = []
            for n, raw in enumerate(text.splitlines(), start=1):
                code, comment = _split_comment(raw)
                lines.append(TexLine(str(p), n, code, comment))
        return cls(lines, notes, p.parent)

    def loc(self, pos: int) -> tuple[str, int]:
        lo, hi = 0, len(self._starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        ln = self.lines[lo] if self.lines else None
        return (ln.file, ln.lineno) if ln else ("?", 0)

    def extract_braced(self, start: int) -> tuple[str | None, int]:
        if start >= len(self.text) or self.text[start] != "{":
            return None, start
        depth = 0
        i = start
        while i < len(self.text):
            c = self.text[i]
            if c == "\\":
                i += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return self.text[start + 1 : i], i + 1
            i += 1
        return None, start

    def find_commands(self, name: str) -> list[tuple[int, str | None, str | None]]:
        out = []
        boundary = r"\b" if name[-1].isalnum() else ""
        for m in re.finditer(r"\\" + re.escape(name) + boundary + r"\s*", self.text):
            i = m.end()
            opt = None
            if i < len(self.text) and self.text[i] == "[":
                j = self.text.find("]", i)
                if j != -1:
                    opt = self.text[i + 1 : j]
                    i = j + 1
                    while i < len(self.text) and self.text[i] in " \t\n":
                        i += 1
            arg, _ = self.extract_braced(i)
            out.append((m.start(), opt, arg))
        return out

    def env_spans(self, name: str) -> list[tuple[int, int, str]]:
        out = []
        begin = re.compile(r"\\begin\s*\{" + re.escape(name) + r"\}")
        end = re.compile(r"\\end\s*\{" + re.escape(name) + r"\}")
        for m in begin.finditer(self.text):
            e = end.search(self.text, m.end())
            stop = e.start() if e else len(self.text)
            out.append((m.start(), stop, self.text[m.end() : stop]))
        return out


def _clean_arg(arg: str) -> str:
    arg = re.sub(r"\\[a-zA-Z@]+\s*(?:\[[^\]]*\])?", " ", arg)
    return re.sub(r"[{}~\s]+", " ", arg).strip()


def _snippet(s: str, n: int = 60) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 3] + "..."


# ---------------------------------------------------------------------------
# Venue profile (lightweight reader — id, cfp_url, review.blind with family
# fallback; full schema parsing lives in preflight-check/venue_profile.py)
# ---------------------------------------------------------------------------


def _yml_value(text: str, key: str, top_level: bool) -> str | None:
    indent = r"" if top_level else r"[ \t]+"
    m = re.search(rf"^{indent}{re.escape(key)}:\s*([^\n]*)$", text, re.M)
    if not m:
        return None
    val = m.group(1)
    val = re.split(r"\s+#", val)[0].strip().strip("\"'")
    return val or None


def read_venue(venue_path: str, venues_dir: str | None) -> dict:
    p = pathlib.Path(venue_path)
    if not p.is_file():
        raise FileNotFoundError(f"venue profile not found: {p}")
    text = p.read_text(encoding="utf-8", errors="replace")
    info = {
        "id": _yml_value(text, "id", True) or p.stem,
        "cfp_url": _yml_value(text, "cfp_url", True),
        "blind": _yml_value(text, "blind", False),
        "template": _yml_value(text, "template", False),
    }
    if info["blind"] in (None, "null", "~"):
        info["blind"] = None
        family = _yml_value(text, "family", True)
        if family:
            vdir = pathlib.Path(venues_dir) if venues_dir else p.parent.parent
            fam = vdir / "families" / f"{family}.yml"
            if fam.is_file():
                ftext = fam.read_text(encoding="utf-8", errors="replace")
                fb = _yml_value(ftext, "blind", False)
                info["blind"] = None if fb in (None, "null", "~") else fb
                info["template"] = info["template"] or _yml_value(ftext, "template", False)
    return info


# ---------------------------------------------------------------------------
# Submission-mode checks
# ---------------------------------------------------------------------------


def _flag_url(url: str, where: str = "") -> tuple[str, str, str] | None:
    """Classify a URL -> (severity, check, message) or None to ignore."""
    low = url.lower()
    if any(h in low for h in _ANON_OK_HOSTS):
        return ("INFO", "anonymization/link-ok", f"anonymized repo link: {url}")
    if any(h in low for h in _IDENTITY_HOSTS):
        return (
            "ERROR", "anonymization/identifying-link",
            f"link can identify authors{where}: {url} — use an anonymized "
            "mirror (e.g. anonymous.4open.science)",
        )
    if "arxiv.org" in low:
        return (
            "WARN", "anonymization/arxiv-link",
            f"arXiv link{where}: {url} — if this is the authors' own preprint, "
            "cite it in third person instead of linking",
        )
    if re.search(r"/~[a-z]", low) or "people." in low or "homes." in low:
        return ("ERROR", "anonymization/identifying-link",
                f"personal homepage link{where}: {url}")
    return ("INFO", "anonymization/link-review",
            f"verify this link does not identify the authors{where}: {url}")


def scan_submission(src: TexSource, args, template: str | None) -> list[Finding]:
    findings: list[Finding] = []

    def add(sev, check, pos, msg):
        f, ln = src.loc(pos)
        findings.append(Finding(sev, check, f, ln, msg))

    # NeurIPS-style templates hide the author block at submission time:
    # populated \author is a hygiene WARN there, an ERROR elsewhere.
    author_sev = "WARN" if template == "neurips" else "ERROR"
    author_note = (
        " (the venue .sty hides authors at submission, but scrub the source "
        "before uploading or sharing)" if template == "neurips" else ""
    )

    email_lines: set[tuple[str, int]] = set()

    for cmd, check in (
        ("author", "anonymization/author-block"),
        ("affiliation", "anonymization/affiliation"),
        ("institute", "anonymization/affiliation"),
        ("institution", "anonymization/affiliation"),
    ):
        for pos, _opt, arg in src.find_commands(cmd):
            if arg is None:
                continue
            content = _clean_arg(arg)
            if not content or _ANON_OK_RE.search(content):
                continue
            add(author_sev, check, pos,
                f"\\{cmd} contains non-anonymous content: \"{_snippet(content)}\""
                + author_note)

    for pos, _opt, arg in src.find_commands("email"):
        if arg and not _ANON_OK_RE.search(arg) and not _OK_EMAIL_RE.search(arg):
            add("ERROR", "anonymization/email", pos, f"\\email present: \"{_snippet(arg)}\"")
        email_lines.add(src.loc(pos))

    for pos, _opt, arg in src.find_commands("orcid"):
        if arg and arg.strip():
            add("ERROR", "anonymization/orcid", pos, f"ORCID id present: {_snippet(arg)}")

    for pos, _opt, arg in src.find_commands("thanks"):
        if arg and arg.strip():
            add("WARN", "anonymization/thanks", pos,
                f"\\thanks{{...}} often carries funding/affiliation: \"{_snippet(arg)}\"")

    for pos, _opt, arg in src.find_commands("grantsponsor"):
        if arg and arg.strip():
            add("WARN", "anonymization/funding", pos,
                f"\\grantsponsor present: \"{_snippet(arg)}\"")

    # acknowledgments
    for env in ("acks", "ack", "acknowledgments", "acknowledgements"):
        for start, _end, inner in src.env_spans(env):
            if inner.strip():
                add("ERROR", "anonymization/acknowledgments", start,
                    f"\\begin{{{env}}} present — remove acknowledgments from a "
                    "double-blind submission")
    for pos, _opt, arg in src.find_commands("section") + src.find_commands("section*"):
        if arg and re.search(r"acknowledg", arg, re.I):
            add("ERROR", "anonymization/acknowledgments", pos,
                f"section \"{_snippet(arg)}\" — remove acknowledgments from a "
                "double-blind submission")

    # funding / grant identifiers in body text
    for m in re.finditer(r"[^\n]+", src.text):
        line = m.group(0)
        for rex in _FUNDING_RES:
            fm = rex.search(line)
            if fm:
                add("WARN", "anonymization/funding", m.start() + fm.start(),
                    f"possible funding/grant identifier: \"{_snippet(line.strip())}\"")
                break

    # links in body text
    for m in _URL_RE.finditer(src.text):
        url = m.group(0).rstrip(_URL_TRAIL)
        hit = _flag_url(url)
        if hit:
            add(hit[0], hit[1], m.start(), hit[2])

    # bare email addresses outside \email
    for m in _EMAIL_RE.finditer(src.text):
        if _OK_EMAIL_RE.search(m.group(0)):
            continue
        if src.loc(m.start()) in email_lines:
            continue  # already reported via \email
        add("ERROR", "anonymization/email", m.start(),
            f"email address in body text: {m.group(0)}")

    # first-person self-citations (one finding per source line)
    seen_selfcite: set[tuple[str, int]] = set()
    for pat in _SELF_CITE_PATTERNS:
        for m in re.finditer(pat, src.text, re.I):
            where = src.loc(m.start())
            if where in seen_selfcite:
                continue
            seen_selfcite.add(where)
            add("WARN", "anonymization/self-citation", m.start(),
                f"first-person self-citation pattern: \"{_snippet(m.group(0))}\" — "
                "cite your own work in third person (\"As shown by X et al. [n]\")")

    # institutional self-identification
    for m in _INSTITUTION_RE.finditer(src.text):
        add("WARN", "anonymization/institution-mention", m.start(),
            f"institutional self-reference: \"{_snippet(m.group(0))}\" — rewrite "
            "neutrally (\"the university where the study took place\")")

    # hyperref pdfauthor metadata in the source
    for m in re.finditer(r"pdfauthor\s*=\s*\{([^}]*)\}", src.text):
        val = m.group(1).strip()
        if val and not _ANON_OK_RE.search(val):
            add("ERROR", "anonymization/pdf-metadata", m.start(),
                f"hyperref pdfauthor is set: \"{_snippet(val)}\" — writes identity "
                "into the compiled PDF's metadata")

    # documentclass / style-file sanity (light; preflight-check is the
    # authority on the exact invocation)
    dm = _DOCCLASS_RE.search(src.text)
    if dm:
        opts = [o.strip() for o in (dm.group(1) or "").split(",") if o.strip()]
        cls = dm.group(2).strip()
        if cls == "acmart" and "anonymous" not in opts:
            add("WARN", "anonymization/class-option", dm.start(),
                "acmart without the 'anonymous' option — double-blind ACM venues "
                "expect [...,review,anonymous]; verify the exact invocation with "
                "preflight-check")
    sm = _ML_STY_RE.search(src.text)
    if sm and "final" in (sm.group(1) or ""):
        add("WARN", "anonymization/class-option", sm.start(),
            f"{sm.group(2)} loaded with [final] — that option reveals the author "
            "block; submit without it")

    findings.extend(_scan_source_hygiene(src))
    findings.extend(_scan_bib_files(src))

    # user-supplied names/institutions
    names = [n.strip() for n in (args.names or "").split(",") if n.strip()]
    for name in names:
        rex = re.compile(re.escape(name), re.I)
        for m in rex.finditer(src.text):
            add("WARN", "anonymization/name-match", m.start(),
                f"author/institution string \"{name}\" appears in the source — "
                "fine inside a third-person citation of published work, a leak "
                "anywhere else; review this occurrence")

    findings.append(Finding(
        "INFO", "anonymization/manual", args.tex, None,
        "automated scan only: also check figures/screenshots (lab logos, "
        "watermarks, usernames in terminal captures), embedded fonts, dataset "
        "descriptions, and every supplementary file — see "
        "references/leak-catalog.md",
    ))
    return findings


def _scan_source_hygiene(src: TexSource) -> list[Finding]:
    """Home-dir paths in code + leaks in LaTeX comments (both modes)."""
    findings: list[Finding] = []

    for m in _HOME_PATH_RE.finditer(src.text):
        user = (m.group(1) or m.group(2) or "").lower()
        if user in _GENERIC_USERS:
            continue
        f, ln = src.loc(m.start())
        findings.append(Finding(
            "ERROR", "anonymization/home-path", f, ln,
            f"home-directory path leaks a username: \"{_snippet(m.group(0))}\" — "
            "use relative paths"))

    for ln in src.lines:
        c = ln.comment
        if not c.strip():
            continue
        kinds = []
        em = _EMAIL_RE.search(c)
        if em and not _OK_EMAIL_RE.search(em.group(0)):
            kinds.append(f"email {em.group(0)}")
        um = _URL_RE.search(c)
        if um:
            low = um.group(0).lower()
            if any(h in low for h in _IDENTITY_HOSTS) and not any(
                h in low for h in _ANON_OK_HOSTS
            ):
                kinds.append(f"identifying link {um.group(0).rstrip(_URL_TRAIL)}")
        hm = _HOME_PATH_RE.search(c)
        if hm and (hm.group(1) or hm.group(2) or "").lower() not in _GENERIC_USERS:
            kinds.append(f"home path {hm.group(0)}")
        am = _AUTHOR_HEADER_RE.match("%" + c)
        if am and not _ANON_OK_RE.search(am.group(1)):
            kinds.append(f"author header \"{_snippet(am.group(1), 40)}\"")
        cm = _COPYRIGHT_RE.search(c)
        if cm and not _ANON_OK_RE.search(cm.group(1)):
            kinds.append(f"copyright line \"{_snippet(cm.group(1), 40)}\"")
        for kind in kinds:
            findings.append(Finding(
                "WARN", "anonymization/comment-leak", ln.file, ln.lineno,
                f"LaTeX comment carries {kind} — comments travel with uploaded "
                "source (arXiv, TAPS, supplementary zips); delete it"))
    return findings


def _scan_bib_files(src: TexSource) -> list[Finding]:
    findings: list[Finding] = []
    bibs: list[pathlib.Path] = []
    for _pos, _opt, arg in src.find_commands("bibliography"):
        for name in (arg or "").split(","):
            name = name.strip()
            if name:
                p = src.root_dir / name
                bibs.append(p if p.suffix else p.with_suffix(".bib"))
    for _pos, _opt, arg in src.find_commands("addbibresource"):
        if arg:
            bibs.append(src.root_dir / arg.strip())
    self_ref = re.compile(
        r"\b(?:our|my) (?:paper|work|thesis|dissertation)\b|\(ours?\)|self-?citation",
        re.I,
    )
    for bib in dict.fromkeys(bibs):
        if not bib.is_file():
            continue
        try:
            text = bib.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            em = _EMAIL_RE.search(line)
            if em and not _OK_EMAIL_RE.search(em.group(0)):
                findings.append(Finding(
                    "WARN", "anonymization/bib-leak", str(bib), n,
                    f".bib carries an email address: {em.group(0)}"))
            sm = self_ref.search(line)
            if sm:
                findings.append(Finding(
                    "WARN", "anonymization/bib-leak", str(bib), n,
                    f".bib annotation marks a self-citation: "
                    f"\"{_snippet(line.strip())}\" — reviewers may see the .bib "
                    "in supplementary/arXiv source"))
    return findings


# ---------------------------------------------------------------------------
# Camera-ready (reversal) checks
# ---------------------------------------------------------------------------


def scan_camera_ready(src: TexSource, args) -> list[Finding]:
    findings: list[Finding] = []

    def add(sev, check, pos, msg):
        f, ln = src.loc(pos)
        findings.append(Finding(sev, check, f, ln, msg))

    authors = src.find_commands("author")
    if not authors:
        findings.append(Finding(
            "ERROR", "reversal/missing-author", args.tex, None,
            "no \\author command found — restore the real author block (it must "
            "match the eRights/eCF copyright form exactly)"))
    for cmd in ("author", "affiliation", "institute", "institution", "email"):
        for pos, _opt, arg in src.find_commands(cmd):
            content = _clean_arg(arg or "")
            if not content:
                add("ERROR", "reversal/placeholder-author", pos,
                    f"\\{cmd} is empty — restore the real content for camera-ready")
            elif _ANON_OK_RE.search(content) or _OK_EMAIL_RE.search(content):
                add("ERROR", "reversal/placeholder-author", pos,
                    f"\\{cmd} still holds an anonymization placeholder: "
                    f"\"{_snippet(content)}\"")

    for m in _URL_RE.finditer(src.text):
        url = m.group(0).rstrip(_URL_TRAIL)
        if any(h in url.lower() for h in _ANON_OK_HOSTS):
            add("ERROR", "reversal/anon-link", m.start(),
                f"anonymized repo link still present: {url} — point to the real "
                "repository (anonymous mirrors expire)")

    dm = _DOCCLASS_RE.search(src.text)
    if dm:
        opts = [o.strip() for o in (dm.group(1) or "").split(",") if o.strip()]
        leftover = [o for o in opts if o in ("anonymous", "review")]
        if leftover:
            add("ERROR", "reversal/class-option", dm.start(),
                f"documentclass still carries {leftover} — drop the submission "
                "options for camera-ready")
    sm = _ML_STY_RE.search(src.text)
    if sm:
        opts = sm.group(1) or ""
        if "final" not in opts and "preprint" not in opts:
            add("WARN", "reversal/class-option", sm.start(),
                f"{sm.group(2)} loaded without [final] — the camera-ready needs "
                "the final option to show authors")

    for m in _ANON_TOGGLE_ON_RE.finditer(src.text):
        add("ERROR", "reversal/anon-toggle", m.start(),
            f"anonymization toggle still ON: \"{_snippet(m.group(0))}\" — flip it "
            "off for camera-ready")
    if not _ANON_TOGGLE_ON_RE.search(src.text):
        m = _ANON_TOGGLE_DEF_RE.search(src.text)
        if m:
            add("INFO", "reversal/anon-toggle", m.start(),
                "anonymization toggle machinery present (off) — strip dead "
                "branches before uploading source to TAPS/arXiv")

    for m in _PLACEHOLDER_TEXT_RE.finditer(src.text):
        add("WARN", "reversal/placeholder-text", m.start(),
            f"anonymization wording still in the text: \"{_snippet(m.group(0))}\"")

    has_acks = any(
        inner.strip()
        for env in ("acks", "ack", "acknowledgments", "acknowledgements")
        for _s, _e, inner in src.env_spans(env)
    ) or any(
        arg and re.search(r"acknowledg", arg, re.I)
        for _p, _o, arg in src.find_commands("section") + src.find_commands("section*")
    )
    if not has_acks:
        findings.append(Finding(
            "INFO", "reversal/acknowledgments-missing", args.tex, None,
            "no acknowledgments section found — restore the acknowledgments and "
            "funding lines removed for review (check the venue's camera-ready "
            "page allowance first)"))

    findings.extend(_scan_source_hygiene(src))
    findings.append(Finding(
        "INFO", "reversal/manual", args.tex, None,
        "also restore: pdfauthor metadata (optional), ORCID ids where the rail "
        "requires them, and the real dataset/DOI links — see "
        "references/camera-ready-reversal.md, then run prepare-camera-ready",
    ))
    return findings


# ---------------------------------------------------------------------------
# Compiled-PDF metadata scan (byte-level, stdlib only)
# ---------------------------------------------------------------------------


def _pdf_unescape(s: str) -> str:
    return re.sub(r"\\([()\\])", r"\1", s)


def scan_pdf(pdf_path: pathlib.Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        data = pdf_path.read_bytes()
    except OSError as exc:
        return [Finding("WARN", "anonymization/pdf-unreadable", str(pdf_path), None,
                        f"could not read PDF: {exc}")]
    text = data.decode("latin-1", errors="replace")
    found_author = False
    for key in ("Author",):
        for m in re.finditer(r"/" + key + r"\s*\(((?:\\.|[^\\)])*)\)", text):
            val = _pdf_unescape(m.group(1)).strip()
            found_author = True
            if val and not _ANON_OK_RE.search(val):
                findings.append(Finding(
                    "ERROR", "anonymization/pdf-author", str(pdf_path), None,
                    f"PDF /{key} metadata: \"{_snippet(val)}\" — scrub it "
                    "(\\hypersetup{pdfauthor={}} and recompile)"))
        for m in re.finditer(r"/" + key + r"\s*<([0-9A-Fa-f\s]+)>", text):
            hexs = re.sub(r"\s", "", m.group(1))
            try:
                raw = bytes.fromhex(hexs)
                val = raw.decode("utf-16-be").lstrip("﻿") if raw[:2] == b"\xfe\xff" \
                    else raw.decode("latin-1")
            except ValueError:
                continue
            found_author = True
            if val.strip() and not _ANON_OK_RE.search(val):
                findings.append(Finding(
                    "ERROR", "anonymization/pdf-author", str(pdf_path), None,
                    f"PDF /{key} metadata (hex): \"{_snippet(val)}\""))
    for m in re.finditer(r"<dc:creator>(.*?)</dc:creator>", text, re.S):
        for li in re.finditer(r"<rdf:li[^>]*>([^<]+)</rdf:li>", m.group(1)):
            val = li.group(1).strip()
            found_author = True
            if val and not _ANON_OK_RE.search(val):
                findings.append(Finding(
                    "ERROR", "anonymization/pdf-author", str(pdf_path), None,
                    f"PDF XMP dc:creator: \"{_snippet(val)}\""))
    if not found_author and b"/ObjStm" in data:
        findings.append(Finding(
            "INFO", "anonymization/pdf-compressed", str(pdf_path), None,
            "no plaintext Author metadata found, but the PDF uses compressed "
            "object streams — confirm with `pdfinfo` or `exiftool`"))
    findings.append(Finding(
        "INFO", "anonymization/pdf-manual", str(pdf_path), None,
        "byte-level scan only: embedded figures/fonts can carry creator names; "
        "open the PDF properties dialog before submitting"))
    return findings


# ---------------------------------------------------------------------------
# Supplementary directory sweep
# ---------------------------------------------------------------------------


def scan_supplementary(root: pathlib.Path) -> list[Finding]:
    findings: list[Finding] = []
    if not root.is_dir():
        return [Finding("WARN", "anonymization/supplementary", str(root), None,
                        "supplementary path is not a directory; skipped")]
    for path in sorted(root.rglob("*")):
        rel = str(path)
        if path.is_dir() and path.name == ".git":
            findings.append(Finding(
                "ERROR", "anonymization/supplementary-git", rel, None,
                ".git directory inside supplementary material — its config/log "
                "carries the author's name and email; ship an export, not a clone"))
            continue
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix == ".ipynb":
            findings.append(Finding(
                "WARN", "anonymization/supplementary-notebook", rel, None,
                "Jupyter notebook — metadata and output cells often carry "
                "usernames and absolute paths; clear outputs and metadata"))
            continue
        if path.suffix.lower() not in _TEXT_EXTS and path.name not in (
            "LICENSE", "LICENCE", "COPYING", "README", "AUTHORS", "NOTICE",
        ):
            continue
        try:
            if path.stat().st_size > _MAX_TEXT_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if path.name in ("AUTHORS", "NOTICE"):
            findings.append(Finding(
                "ERROR", "anonymization/supplementary-leak", rel, None,
                f"{path.name} file in supplementary material — remove or "
                "anonymize it"))
        for n, line in enumerate(text.splitlines(), start=1):
            em = _EMAIL_RE.search(line)
            if em and not _OK_EMAIL_RE.search(em.group(0)):
                findings.append(Finding(
                    "ERROR", "anonymization/supplementary-leak", rel, n,
                    f"email address: {em.group(0)}"))
                continue
            um = _URL_RE.search(line)
            if um:
                low = um.group(0).lower()
                if any(h in low for h in _IDENTITY_HOSTS) and not any(
                    h in low for h in _ANON_OK_HOSTS
                ):
                    findings.append(Finding(
                        "ERROR", "anonymization/supplementary-leak", rel, n,
                        f"identifying link: {um.group(0).rstrip(_URL_TRAIL)}"))
                    continue
            hm = _HOME_PATH_RE.search(line)
            if hm and (hm.group(1) or hm.group(2) or "").lower() not in _GENERIC_USERS:
                findings.append(Finding(
                    "WARN", "anonymization/supplementary-leak", rel, n,
                    f"home-directory path: {_snippet(hm.group(0))}"))
                continue
            cm = _COPYRIGHT_RE.search(line)
            if cm and not _ANON_OK_RE.search(cm.group(1)):
                findings.append(Finding(
                    "WARN", "anonymization/supplementary-leak", rel, n,
                    f"copyright line names someone: \"{_snippet(cm.group(1), 40)}\""))
                continue
            am = _AUTHOR_HEADER_RE.match(line)
            if am and not _ANON_OK_RE.search(am.group(1)):
                findings.append(Finding(
                    "ERROR", "anonymization/supplementary-leak", rel, n,
                    f"author header: \"{_snippet(am.group(1), 40)}\""))
    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Deep anonymization scanner for double-blind LaTeX "
        "submissions (and the reverse check for camera-ready). Stdlib only; "
        "no network.",
        epilog="examples:\n"
        "  python3 scan_anonymization.py paper.tex --venue venues/conferences/neurips-2026.yml\n"
        "  python3 scan_anonymization.py paper.tex --blind double --pdf paper.pdf --supplementary supp/\n"
        "  python3 scan_anonymization.py paper.tex --mode camera-ready --blind double\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("tex", help="main .tex file of the submission")
    ap.add_argument("--mode", choices=("submission", "camera-ready"),
                    default="submission",
                    help="submission = find identity leaks (default); "
                    "camera-ready = find anonymization leftovers")
    ap.add_argument("--venue", help="venue profile YAML (venues/conferences/<venue>.yml); "
                    "supplies the blind level and the cfp_url reminder")
    ap.add_argument("--venues-dir", help="venues/ root for family lookup "
                    "(default: derived from --venue path)")
    ap.add_argument("--blind", choices=("single", "double", "triple"),
                    help="override/declare the blind level when no --venue is given")
    ap.add_argument("--force", action="store_true",
                    help="scan even when the venue is single-blind")
    ap.add_argument("--pdf", help="compiled PDF to scan for metadata "
                    "(default: <tex basename>.pdf if it exists)")
    ap.add_argument("--no-pdf", action="store_true", help="skip the PDF scan")
    ap.add_argument("--supplementary", metavar="DIR",
                    help="also sweep a supplementary-material directory")
    ap.add_argument("--names", help="comma-separated author/institution strings "
                    "to grep for everywhere (submission mode)")
    ap.add_argument("--no-inputs", action="store_true",
                    help="do not follow \\input/\\include files")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on WARN findings too, not just ERROR")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    notes: list[str] = []

    venue: dict = {}
    if args.venue:
        try:
            venue = read_venue(args.venue, args.venues_dir)
        except (FileNotFoundError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        notes.append(f"venue profile: {venue.get('id')} (blind: {venue.get('blind') or 'unknown'})")
    blind = args.blind or venue.get("blind")

    try:
        src = TexSource.load(args.tex, follow_inputs=not args.no_inputs)
    except (FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    notes.extend(src.notes)

    findings: list[Finding] = []
    if args.mode == "submission":
        if blind == "single" and not args.force:
            findings.append(Finding(
                "INFO", "anonymization/skipped", args.tex, None,
                f"{venue.get('id') or 'this venue'} is SINGLE-blind: author names "
                "should be listed on the submission. Scan skipped (re-run with "
                "--force to scan anyway)."))
        else:
            if blind is None:
                findings.append(Finding(
                    "WARN", "anonymization/blind-unknown", args.tex, None,
                    "blind level unknown — running all checks; pass --venue or "
                    "--blind, and verify against the live CFP"))
            findings.extend(scan_submission(src, args, venue.get("template")))
    else:
        findings.extend(scan_camera_ready(src, args))

    skipped = any(f.check == "anonymization/skipped" for f in findings)
    if not skipped:
        if args.supplementary:
            findings.extend(scan_supplementary(pathlib.Path(args.supplementary)))
        if not args.no_pdf and args.mode == "submission":
            pdf = pathlib.Path(args.pdf) if args.pdf else pathlib.Path(args.tex).with_suffix(".pdf")
            if args.pdf and not pdf.is_file():
                print(f"error: --pdf file not found: {pdf}", file=sys.stderr)
                return 2
            if pdf.is_file():
                findings.extend(scan_pdf(pdf))
            else:
                notes.append(f"no compiled PDF at {pdf}; PDF metadata not checked")

    findings.sort(key=lambda f: (SEVERITIES.index(f.severity), f.file, f.line or 0))
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}
    cfp = venue.get("cfp_url")
    if args.json:
        json.dump({
            "tool": "scan_anonymization",
            "mode": args.mode,
            "tex": args.tex,
            "venue": venue.get("id"),
            "blind": blind,
            "findings": [dataclasses.asdict(f) for f in findings],
            "notes": notes,
            "summary": counts,
            "cfp_url": cfp,
        }, sys.stdout, indent=2, default=str)
        print()
    else:
        print(f"== scan_anonymization [{args.mode}]: {args.tex}"
              + (f" vs {venue.get('id')}" if venue else "")
              + f" (blind: {blind or 'unknown'}) ==")
        for note in notes:
            print(f"  note: {note}")
        if not findings:
            print("  no findings — clean.")
        for f in findings:
            print("  " + f.format())
        print(f"  summary: {counts['ERROR']} error(s), {counts['WARN']} warning(s), "
              f"{counts['INFO']} info")
        if cfp:
            print(f"  reminder: re-verify the blind level and policies against "
                  f"the live CFP: {cfp}")
    if counts["ERROR"] or (args.strict and counts["WARN"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
