#!/usr/bin/env python3
"""check_bibtex.py — anti-hallucination gate for BibTeX files.

Parses a .bib file (stdlib-only parser, handles the common BibTeX forms)
and validates every entry against live scholarly indexes:

  - Crossref   (DOI resolution, metadata comparison, retraction notices)
  - DataCite   (fallback for non-Crossref DOIs: Zenodo, arXiv DataCite DOIs)
  - arXiv      (eprint IDs)
  - DBLP       (title resolution for CS papers without a DOI)
  - Semantic Scholar (last-resort title match; optional S2_API_KEY)

Flags raised:
  ERROR : UNRESOLVED (possible fabrication), DOI_NOT_FOUND, ARXIV_NOT_FOUND,
          TITLE_MISMATCH, AUTHOR_MISMATCH, YEAR_MISMATCH, RETRACTED,
          DUPLICATE_KEY, DUPLICATE_DOI, DUPLICATE_TITLE, MALFORMED_DOI,
          MALFORMED_ARXIV_ID
  WARN  : TITLE_PARTIAL_MATCH, AUTHOR_LIST_DIFFERS, VENUE_MISMATCH,
          MISSING_DOI, MISSING_FIELDS, EXPRESSION_OF_CONCERN,
          NOT_IN_INDEXES, IMPLAUSIBLE_YEAR, POSSIBLE_ID_TYPO
  INFO  : UNVERIFIABLE_TYPE, HAS_CORRECTION, RESOLVED_VIA_SEARCH

Politeness: <=1 request/second per host (3 s for arXiv, per their etiquette),
User-Agent "research-paper-skills (mailto:$CONTACT_EMAIL)", exponential
backoff on HTTP 429, responses cached under .cache/verify-citations/
(gitignored), single-item fetches only — never bulk.

Exit codes: 0 = no errors found; 2 = problems found (see report);
1 = operational failure (bad file, network down, missing CONTACT_EMAIL).

Usage:
  export CONTACT_EMAIL=you@university.edu
  python3 scripts/check_bibtex.py refs.bib
  python3 scripts/check_bibtex.py refs.bib --offline          # parse + static checks only
  python3 scripts/check_bibtex.py refs.bib --key smith2024    # check one entry
  python3 scripts/check_bibtex.py refs.bib --json report.json # machine-readable report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

CACHE_DIR = os.path.join(os.getcwd(), ".cache", "verify-citations")
RATELIMIT_FILE = os.path.join(CACHE_DIR, "_ratelimit.json")
DEFAULT_TTL = 24 * 60 * 60   # cache lifetime, seconds
MAX_RETRIES = 4              # attempts when a host answers HTTP 429
TIMEOUT = 30                 # socket timeout, seconds
THIS_YEAR = time.gmtime().tm_year

ARXIV_NEW = re.compile(r"\b(\d{4}\.\d{4,5})(v\d+)?\b")
ARXIV_OLD = re.compile(r"\b([a-z][a-z\-]{1,12}(?:\.[A-Z]{2})?/\d{7})\b")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")

REQUIRED_FIELDS = {
    "article": ["author", "title", "journal", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "incollection": ["author", "title", "booktitle", "year"],
    "book": ["title", "publisher", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "misc": ["title"],
}
# entry types that scholarly indexes simply do not cover well
SOFT_TYPES = {"techreport", "phdthesis", "mastersthesis", "unpublished", "booklet"}
WEB_TYPES = {"misc", "online", "electronic", "webpage", "manual", "software"}
RETRACTION_TYPES = {"retraction", "retraction_and_replacement", "withdrawal", "removal", "partial_retraction"}


def fail(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------
# polite HTTP (rate limit, backoff, cache)
# --------------------------------------------------------------------------

def contact_email() -> str:
    email = os.environ.get("CONTACT_EMAIL", "").strip()
    if email:
        return email
    if sys.stdin.isatty() and sys.stderr.isatty():
        try:
            email = input(
                "CONTACT_EMAIL is not set. Scholarly APIs ask for a contact "
                "address (polite pool).\nEnter your email: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            email = ""
        if email:
            os.environ["CONTACT_EMAIL"] = email
            return email
    fail(
        "CONTACT_EMAIL is not set. Export a real contact email first, e.g.\n"
        "  export CONTACT_EMAIL=you@university.edu\n"
        "It is sent in the User-Agent so API providers can contact you "
        "instead of blocking you. Or run with --offline for static checks only."
    )
    raise AssertionError("unreachable")


def user_agent() -> str:
    return f"research-paper-skills (mailto:{contact_email()})"


def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError:
        pass  # caching is best-effort


def _throttle(host: str, min_interval: float) -> None:
    """At most one request per min_interval seconds per host, persisted
    across invocations via .cache/verify-citations/_ratelimit.json."""
    stamps = _load_json(RATELIMIT_FILE)
    last = stamps.get(host, 0)
    wait = min_interval - (time.time() - float(last))
    if wait > 0:
        time.sleep(wait)
    stamps[host] = time.time()
    _save_json(RATELIMIT_FILE, stamps)


def _cache_path(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    return os.path.join(CACHE_DIR, f"{digest}.json")


def http_get(url, *, min_interval=1.0, headers=None, ttl=DEFAULT_TTL,
             use_cache=True, none_on=()):
    """Polite GET returning the body as text, or None when the status code
    is in `none_on` (negative results are cached too)."""
    cpath = _cache_path(url)
    if use_cache:
        entry = _load_json(cpath)
        if entry and time.time() - entry.get("fetched_at", 0) < ttl:
            return None if entry.get("status") in none_on else entry.get("body")

    host = urllib.parse.urlsplit(url).netloc
    req_headers = {"User-Agent": user_agent(), "Accept": "*/*"}
    if headers:
        req_headers.update(headers)

    delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle(host, min_interval)
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8", "replace")
            if use_cache:
                _save_json(cpath, {"url": url, "status": 200,
                                   "fetched_at": time.time(), "body": body})
            return body
        except urllib.error.HTTPError as e:
            if e.code in none_on:
                if use_cache:
                    _save_json(cpath, {"url": url, "status": e.code,
                                       "fetched_at": time.time()})
                return None
            if e.code == 429 and attempt < MAX_RETRIES:
                sleep_s = delay
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        sleep_s = max(float(retry_after), delay)
                    except ValueError:
                        pass
                print(f"  HTTP 429 from {host}; backing off {sleep_s:.0f}s "
                      f"(attempt {attempt}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(sleep_s)
                delay *= 2
                continue
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            fail(f"HTTP {e.code} from {host}\n  url: {url}\n  {detail}".rstrip())
        except urllib.error.URLError as e:
            fail(f"network error reaching {host}: {e.reason}\n"
                 "Check connectivity, or rerun with --offline.")
        except TimeoutError:
            fail(f"timed out after {TIMEOUT}s talking to {host}")
    fail(f"gave up after {MAX_RETRIES} attempts (persistent HTTP 429) from "
         f"{host}. Wait a minute and retry. For api.semanticscholar.org, a "
         "free key via S2_API_KEY gives a dedicated 1 req/s allowance.")
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------
# BibTeX parser (stdlib only; covers the common cases)
# --------------------------------------------------------------------------

class ParseError(Exception):
    pass


MONTHS = {m: m for m in
          "jan feb mar apr may jun jul aug sep oct nov dec".split()}


def _line_at(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _skip_ws(text: str, i: int) -> int:
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    return i


def _read_braced(text: str, i: int):
    """text[i] == '{'. Return (content, index after closing brace)."""
    assert text[i] == "{"
    depth, start, n = 1, i + 1, len(text)
    i += 1
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    raise ParseError(f"unbalanced braces (opened near line {_line_at(text, start)})")


def _read_quoted(text: str, i: int):
    """text[i] == '"'. Braces protect inner quotes per BibTeX rules."""
    assert text[i] == '"'
    depth, start, n = 0, i + 1, len(text)
    i += 1
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == '"' and depth == 0:
            return text[start:i], i + 1
        i += 1
    raise ParseError(f'unterminated "..." value (opened near line {_line_at(text, start)})')


def _parse_value(text: str, i: int, strings: dict):
    """Parse a field value: {..}, ".." or macro/number, joined by '#'."""
    parts = []
    n = len(text)
    while True:
        i = _skip_ws(text, i)
        if i >= n:
            raise ParseError("unexpected end of file inside a field value")
        c = text[i]
        if c == "{":
            content, i = _read_braced(text, i)
            parts.append(content)
        elif c == '"':
            content, i = _read_quoted(text, i)
            parts.append(content)
        else:
            m = re.match(r"[A-Za-z0-9_.+:\-]+", text[i:])
            if not m:
                raise ParseError(
                    f"cannot parse field value near line {_line_at(text, i)}")
            word = m.group(0)
            i += m.end()
            parts.append(strings.get(word.lower(), word))
        i = _skip_ws(text, i)
        if i < n and text[i] == "#":
            i += 1
            continue
        break
    return re.sub(r"\s+", " ", "".join(parts)).strip(), i


def parse_bibtex(text: str):
    """Return list of entries: {key, type, line, fields{lower:value}}."""
    entries = []
    strings = dict(MONTHS)
    i, n = 0, len(text)
    while True:
        at = text.find("@", i)
        if at == -1:
            break
        i = at + 1
        m = re.match(r"\s*([A-Za-z]+)\s*([{(])", text[i:])
        if not m:
            continue  # stray @ in prose between entries
        etype = m.group(1).lower()
        opener_pos = i + m.end() - 1
        closer = "}" if m.group(2) == "{" else ")"
        i = opener_pos
        if etype in ("comment", "preamble"):
            if text[i] == "{":
                _, i = _read_braced(text, i)
            else:
                end = text.find(closer, i)
                i = n if end == -1 else end + 1
            continue
        if etype == "string":
            inner_start = i + 1
            if text[i] == "{":
                inner, i = _read_braced(text, i)
            else:
                end = text.find(closer, i)
                inner = text[i + 1:end if end != -1 else n]
                i = n if end == -1 else end + 1
            sm = re.match(r'\s*([A-Za-z][\w\-.+]*)\s*=\s*', inner)
            if sm:
                try:
                    val, _ = _parse_value(inner, sm.end(), strings)
                    strings[sm.group(1).lower()] = val
                except ParseError:
                    pass  # tolerate odd @string forms
            continue

        entry_line = _line_at(text, at)
        i += 1  # past opener
        km = re.match(r"\s*([^,\s{}()\"]+)\s*(,|" + re.escape(closer) + ")",
                      text[i:])
        if not km:
            raise ParseError(
                f"cannot read citation key for @{etype} at line {entry_line}")
        key = km.group(1)
        i += km.end()
        fields = {}
        if km.group(2) == closer:
            entries.append({"key": key, "type": etype, "line": entry_line,
                            "fields": fields})
            continue
        while True:
            i = _skip_ws(text, i)
            if i >= n:
                raise ParseError(
                    f"unexpected end of file in entry '{key}' "
                    f"(line {entry_line})")
            if text[i] == ",":
                i += 1
                continue
            if text[i] == closer:
                i += 1
                break
            fm = re.match(r"([A-Za-z][\w\-.+]*)\s*=\s*", text[i:])
            if not fm:
                raise ParseError(
                    f"cannot parse field in entry '{key}' near line "
                    f"{_line_at(text, i)}")
            fname = fm.group(1).lower()
            i += fm.end()
            val, i = _parse_value(text, i, strings)
            fields[fname] = val
        entries.append({"key": key, "type": etype, "line": entry_line,
                        "fields": fields})
    return entries


# --------------------------------------------------------------------------
# normalization and comparison helpers
# --------------------------------------------------------------------------

def norm_text(s: str) -> str:
    """LaTeX-aware normalization for fuzzy comparison."""
    if not s:
        return ""
    s = re.sub(r"\$[^$]*\$", " ", s)          # drop inline math
    s = re.sub(r"\\[a-zA-Z]+", " ", s)        # \textbf, \c, \v ... keep args
    s = re.sub(r"\\.", "", s)                 # \'  \"  \` accent pairs
    s = s.replace("{", "").replace("}", "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return s.strip()


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 15 and shorter in longer:
        ratio = max(ratio, 0.92)  # subtitle / truncation containment
    return ratio


def split_authors(field: str):
    return [a.strip() for a in re.split(r"\s+and\s+", field, flags=re.I)
            if a.strip()]


def family_name(name: str):
    name = name.strip()
    if not name:
        return None
    if name.lower() in ("others", "et al.", "et al"):
        return "others"
    if "," in name:
        fam = name.split(",", 1)[0]
    else:
        toks = name.split()
        fam = toks[-1] if toks else name
        if (fam.lower().strip(".") in ("jr", "sr", "ii", "iii", "iv")
                and len(toks) >= 2):
            fam = toks[-2]
    return norm_text(fam) or None


def families_from_bib(field: str):
    fams, truncated = [], False
    for name in split_authors(field):
        f = family_name(name)
        if f == "others":
            truncated = True
        elif f:
            fams.append(f)
    return fams, truncated


def fam_match(a: str, b: str) -> bool:
    return bool(a and b) and (a == b or a in b or b in a)


def clean_doi(raw: str):
    doi = raw.strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)\s*", "", doi, flags=re.I)
    doi = doi.strip().rstrip(".,;}")
    return doi


def extract_doi(fields: dict):
    if "doi" in fields and fields["doi"].strip():
        return clean_doi(fields["doi"])
    for f in ("url", "note", "howpublished"):
        m = re.search(r"doi\.org/(10\.\d{4,9}/\S+)", fields.get(f, ""), re.I)
        if m:
            return clean_doi(m.group(1))
    return None


def extract_arxiv_id(fields: dict):
    ep = fields.get("eprint", "").strip()
    pfx = (fields.get("archiveprefix", "") or fields.get("eprinttype", "")).lower()
    if ep:
        ep_clean = re.sub(r"^arxiv:\s*", "", ep, flags=re.I)
        if pfx in ("arxiv", "") and (ARXIV_NEW.fullmatch(ep_clean)
                                     or ARXIV_OLD.fullmatch(ep_clean)):
            return ep_clean
        if pfx == "arxiv":
            return ep_clean  # declared arXiv but odd shape; validated later
    for f in ("note", "journal", "url", "howpublished", "volume"):
        blob = fields.get(f, "")
        m = re.search(r"arxiv[:\s/]*(\d{4}\.\d{4,5})(v\d+)?", blob, re.I)
        if m:
            return m.group(1) + (m.group(2) or "")
        m = ARXIV_OLD.search(blob) if "arxiv" in blob.lower() else None
        if m:
            return m.group(1)
    return None


def valid_arxiv_id(aid: str) -> bool:
    return bool(ARXIV_NEW.fullmatch(aid) or ARXIV_OLD.fullmatch(aid))


def bib_year(fields: dict):
    m = re.search(r"\d{4}", fields.get("year", ""))
    return int(m.group(0)) if m else None


def bib_venue(fields: dict):
    return fields.get("journal") or fields.get("booktitle") or ""


def looks_like_preprint(fields: dict) -> bool:
    blob = (bib_venue(fields) + " " + fields.get("note", "")).lower()
    return (not bib_venue(fields)) or "arxiv" in blob or "preprint" in blob


# --------------------------------------------------------------------------
# providers — each returns a source record dict or None
#   {source, title, families, year, venue, doi, url}
# --------------------------------------------------------------------------

def crossref_doi(doi: str):
    url = ("https://api.crossref.org/works/"
           + urllib.parse.quote(doi, safe="")
           + "?mailto=" + urllib.parse.quote(contact_email()))
    body = http_get(url, none_on=(404,))
    if body is None:
        return None
    try:
        msg = json.loads(body)["message"]
    except (ValueError, KeyError):
        return None
    titles = msg.get("title") or []
    subtitles = msg.get("subtitle") or []
    title = (titles[0] if titles else "")
    if subtitles:
        title = f"{title}: {subtitles[0]}" if title else subtitles[0]
    fams = []
    for a in msg.get("author", []) or []:
        f = a.get("family") or a.get("name") or ""
        if norm_text(f):
            fams.append(norm_text(f))
    year = None
    for k in ("issued", "published-print", "published-online", "created"):
        parts = (msg.get(k) or {}).get("date-parts") or [[None]]
        if parts[0] and parts[0][0]:
            year = int(parts[0][0])
            break
    container = (msg.get("container-title") or [""])
    return {"source": "Crossref", "title": title, "families": fams,
            "year": year, "venue": container[0] if container else "",
            "doi": msg.get("DOI", doi),
            "url": f"https://doi.org/{msg.get('DOI', doi)}"}


def datacite_doi(doi: str):
    url = "https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="")
    body = http_get(url, none_on=(404,))
    if body is None:
        return None
    try:
        attrs = json.loads(body)["data"]["attributes"]
    except (ValueError, KeyError, TypeError):
        return None
    titles = attrs.get("titles") or []
    fams = []
    for c in attrs.get("creators", []) or []:
        f = c.get("familyName") or c.get("name") or ""
        f = f.split(",")[0] if "," in f else f
        if norm_text(f):
            fams.append(norm_text(f))
    return {"source": "DataCite", "title": titles[0].get("title", "") if titles else "",
            "families": fams, "year": attrs.get("publicationYear"),
            "venue": (attrs.get("container") or {}).get("title", ""),
            "doi": doi, "url": f"https://doi.org/{doi}"}


def arxiv_by_id(aid: str):
    url = ("https://export.arxiv.org/api/query?id_list="
           + urllib.parse.quote(aid) + "&max_results=1")
    body = http_get(url, min_interval=3.0)  # arXiv etiquette: 3 s between calls
    if body is None:
        return None
    try:
        feed = ET.fromstring(body)
    except ET.ParseError:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = feed.find("a:entry", ns)
    if entry is None:
        return None
    eid = (entry.findtext("a:id", "", ns) or "")
    title = re.sub(r"\s+", " ", entry.findtext("a:title", "", ns) or "").strip()
    if "api/errors" in eid or title.lower() == "error":
        return None
    fams = []
    for author in entry.findall("a:author", ns):
        name = author.findtext("a:name", "", ns) or ""
        toks = name.split()
        if toks:
            fams.append(norm_text(toks[-1]))
    published = entry.findtext("a:published", "", ns) or ""
    year = int(published[:4]) if published[:4].isdigit() else None
    return {"source": "arXiv", "title": title, "families": fams,
            "year": year, "venue": "arXiv",
            "doi": None, "url": f"https://arxiv.org/abs/{aid}"}


def dblp_title_search(title: str, year=None):
    q = norm_text(title)
    if not q:
        return None
    url = ("https://dblp.org/search/publ/api?format=json&h=10&q="
           + urllib.parse.quote(q))
    body = http_get(url)
    if body is None:
        return None
    try:
        hits = json.loads(body)["result"]["hits"].get("hit", [])
    except (ValueError, KeyError):
        return None
    best, best_ratio = None, 0.0
    for h in hits:
        info = h.get("info", {})
        r = similarity(q, norm_text(info.get("title", "")))
        if year and str(info.get("year", "")).isdigit():
            if abs(int(info["year"]) - year) > 2:
                r -= 0.15  # likely a different edition/version
        if r > best_ratio:
            best, best_ratio = info, r
    if not best or best_ratio < 0.85:
        return None
    raw_auth = (best.get("authors") or {}).get("author", [])
    if isinstance(raw_auth, dict):
        raw_auth = [raw_auth]
    fams = []
    for a in raw_auth:
        text = a.get("text", "") if isinstance(a, dict) else str(a)
        text = re.sub(r"\s+\d{4}$", "", text)  # dblp disambiguation suffix
        toks = text.split()
        if toks:
            fams.append(norm_text(toks[-1]))
    venue = best.get("venue", "")
    if isinstance(venue, list):
        venue = ", ".join(venue)
    return {"source": "DBLP", "title": best.get("title", ""), "families": fams,
            "year": int(best["year"]) if str(best.get("year", "")).isdigit() else None,
            "venue": venue, "doi": clean_doi(best["doi"]) if best.get("doi") else None,
            "url": best.get("url", "")}


def crossref_title_search(title: str):
    q = norm_text(title)
    if not q:
        return None
    url = ("https://api.crossref.org/works?rows=5"
           "&select=DOI,title,author,issued,container-title"
           "&query.bibliographic=" + urllib.parse.quote(q)
           + "&mailto=" + urllib.parse.quote(contact_email()))
    body = http_get(url)
    if body is None:
        return None
    try:
        items = json.loads(body)["message"].get("items", [])
    except (ValueError, KeyError):
        return None
    best, best_ratio = None, 0.0
    for it in items:
        t = (it.get("title") or [""])[0]
        r = similarity(q, norm_text(t))
        if r > best_ratio:
            best, best_ratio = it, r
    if not best or best_ratio < 0.85:
        return None
    return crossref_doi(best["DOI"])  # full record (served from cache logic)


def s2_title_match(title: str):
    q = norm_text(title)
    if not q:
        return None
    url = ("https://api.semanticscholar.org/graph/v1/paper/search/match"
           "?fields=title,year,authors,externalIds,venue"
           "&query=" + urllib.parse.quote(q))
    headers = {}
    if os.environ.get("S2_API_KEY"):
        headers["x-api-key"] = os.environ["S2_API_KEY"]
    body = http_get(url, headers=headers, none_on=(404,))  # 404 = no match
    if body is None:
        return None
    try:
        data = json.loads(body).get("data", [])
    except ValueError:
        return None
    if not data:
        return None
    p = data[0]
    if similarity(q, norm_text(p.get("title", ""))) < 0.85:
        return None
    fams = []
    for a in p.get("authors", []) or []:
        toks = (a.get("name") or "").split()
        if toks:
            fams.append(norm_text(toks[-1]))
    ext = p.get("externalIds") or {}
    return {"source": "Semantic Scholar", "title": p.get("title", ""),
            "families": fams, "year": p.get("year"),
            "venue": p.get("venue", ""),
            "doi": clean_doi(ext["DOI"]) if ext.get("DOI") else None,
            "url": ("https://doi.org/" + ext["DOI"]) if ext.get("DOI") else ""}


def crossref_retraction_check(doi: str):
    """Return list of (severity, code, message) for editorial updates
    (retractions, expressions of concern, corrections) targeting this DOI."""
    url = ("https://api.crossref.org/works?rows=10"
           "&select=DOI,title,type,update-to"
           "&filter=" + urllib.parse.quote(f"updates:{doi}")
           + "&mailto=" + urllib.parse.quote(contact_email()))
    body = http_get(url, none_on=(400, 404))
    if body is None:
        return []
    try:
        items = json.loads(body)["message"].get("items", [])
    except (ValueError, KeyError):
        return []
    flags = []
    for it in items:
        for upd in it.get("update-to", []) or []:
            if clean_doi(upd.get("DOI", "")).lower() != doi.lower():
                continue
            utype = (upd.get("type") or "").lower()
            notice = it.get("DOI", "")
            if utype in RETRACTION_TYPES:
                flags.append(("ERROR", "RETRACTED",
                              f"Crossref records a {utype} notice for this DOI "
                              f"(notice: https://doi.org/{notice})"))
            elif utype == "expression_of_concern":
                flags.append(("WARN", "EXPRESSION_OF_CONCERN",
                              f"expression of concern issued "
                              f"(notice: https://doi.org/{notice})"))
            elif utype in ("erratum", "correction"):
                flags.append(("INFO", "HAS_CORRECTION",
                              f"a {utype} exists "
                              f"(notice: https://doi.org/{notice})"))
    return flags


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def static_checks(entry: dict):
    flags = []
    fields = entry["fields"]
    req = REQUIRED_FIELDS.get(entry["type"])
    if req:
        missing = [f for f in req if not fields.get(f, "").strip()]
        if entry["type"] == "book" and "author" not in fields and "editor" in fields:
            pass  # editor satisfies book authorship
        if missing:
            flags.append(("WARN", "MISSING_FIELDS",
                          f"missing required field(s) for @{entry['type']}: "
                          + ", ".join(missing)))
    year = bib_year(fields)
    if fields.get("year") and year is None:
        flags.append(("WARN", "IMPLAUSIBLE_YEAR",
                      f"year is not a 4-digit number: {fields['year']!r}"))
    elif year is not None and not (1900 <= year <= THIS_YEAR + 1):
        flags.append(("WARN", "IMPLAUSIBLE_YEAR",
                      f"year {year} is outside 1900..{THIS_YEAR + 1}"))
    doi = extract_doi(fields)
    if doi and not DOI_RE.match(doi):
        flags.append(("ERROR", "MALFORMED_DOI",
                      f"DOI does not match 10.NNNN/suffix: {doi!r}"))
    aid = extract_arxiv_id(fields)
    if aid and not valid_arxiv_id(aid):
        flags.append(("ERROR", "MALFORMED_ARXIV_ID",
                      f"not a valid arXiv identifier: {aid!r}"))
    auth = fields.get("author", "")
    if re.search(r"\bet al\b", auth, re.I):
        flags.append(("WARN", "MISSING_FIELDS",
                      "author field uses 'et al.' — BibTeX wants the full "
                      "list, or '... and others'"))
    return flags


def duplicate_checks(entries):
    """Cross-entry duplicate detection. Returns a list of flag-lists
    parallel to `entries` (indexed by position, since keys may collide)."""
    out = [[] for _ in entries]
    seen_keys = {}
    seen_dois = {}
    seen_titles = {}
    for idx, e in enumerate(entries):
        k = e["key"]
        if k in seen_keys:
            out[idx].append(("ERROR", "DUPLICATE_KEY",
                             f"key also defined at line {seen_keys[k]}; BibTeX "
                             "silently drops one of them"))
        else:
            seen_keys[k] = e["line"]
        doi = extract_doi(e["fields"])
        if doi:
            d = doi.lower()
            if d in seen_dois and seen_dois[d] != k:
                out[idx].append(("ERROR", "DUPLICATE_DOI",
                                 f"same DOI as entry '{seen_dois[d]}'"))
            else:
                seen_dois.setdefault(d, k)
        t = norm_text(e["fields"].get("title", ""))
        if len(t) >= 15:
            if t in seen_titles and seen_titles[t] != k:
                out[idx].append(("ERROR", "DUPLICATE_TITLE",
                                 f"same title as entry '{seen_titles[t]}' — "
                                 "likely the same paper cited twice"))
            else:
                seen_titles.setdefault(t, k)
    return out


def compare_with_source(entry: dict, src: dict):
    """Compare bib fields against an authoritative record."""
    flags = []
    fields = entry["fields"]

    # --- title ---
    bib_t = norm_text(fields.get("title", ""))
    src_t_raw = src.get("title", "")
    src_t = norm_text(src_t_raw)
    if src_t.startswith(("retracted", "withdrawn")):
        flags.append(("ERROR", "RETRACTED",
                      f"{src['source']} title is marked retracted/withdrawn: "
                      f"{src_t_raw[:90]!r}"))
        src_t = re.sub(r"^(retracted( article)?|withdrawn)\s*", "", src_t)
    if bib_t and src_t:
        r = similarity(bib_t, src_t)
        if r < 0.60:
            flags.append(("ERROR", "TITLE_MISMATCH",
                          f"{src['source']} record has a different title: "
                          f"{src_t_raw[:90]!r} (similarity {r:.2f})"))
        elif r < 0.85:
            flags.append(("WARN", "TITLE_PARTIAL_MATCH",
                          f"title differs from {src['source']}: "
                          f"{src_t_raw[:90]!r} (similarity {r:.2f})"))

    # --- authors ---
    bib_fams, truncated = families_from_bib(fields.get("author", ""))
    src_fams = src.get("families") or []
    if bib_fams and src_fams:
        if not fam_match(bib_fams[0], src_fams[0]):
            flags.append(("ERROR", "AUTHOR_MISMATCH",
                          f"first author differs: .bib says "
                          f"{bib_fams[0]!r}, {src['source']} says {src_fams[0]!r}"))
        else:
            unmatched = [b for b in bib_fams
                         if not any(fam_match(b, s) for s in src_fams)]
            count_off = (not truncated) and len(bib_fams) != len(src_fams)
            if unmatched or count_off:
                detail = []
                if unmatched:
                    detail.append("not in source record: " + ", ".join(unmatched))
                if count_off:
                    detail.append(f".bib lists {len(bib_fams)} authors, "
                                  f"{src['source']} lists {len(src_fams)}")
                flags.append(("WARN", "AUTHOR_LIST_DIFFERS",
                              "; ".join(detail)))

    # --- year ---
    by, sy = bib_year(fields), src.get("year")
    if by and sy and abs(by - sy) > 1:
        if src["source"] == "arXiv" and 0 < by - sy <= 3:
            pass  # citing the later published version of an old preprint
        else:
            flags.append(("ERROR", "YEAR_MISMATCH",
                          f".bib says {by}, {src['source']} says {sy}"))

    # --- venue (warn-only: venue aliasing is genuinely messy) ---
    bv, sv = norm_text(bib_venue(fields)), norm_text(src.get("venue", ""))
    if bv and sv and src["source"] != "arXiv":
        toks_b = {t for t in bv.split() if len(t) > 3}
        toks_s = {t for t in sv.split() if len(t) > 3}
        if similarity(bv, sv) < 0.5 and not (toks_b & toks_s):
            flags.append(("WARN", "VENUE_MISMATCH",
                          f".bib venue {bib_venue(fields)[:60]!r} vs "
                          f"{src['source']} {src.get('venue', '')[:60]!r} — "
                          "may be an alias; see references/triage-guide.md"))
    return flags


def verify_online(entry: dict, check_retractions: bool):
    """Resolve the entry against live indexes. Returns (src|None, flags)."""
    fields = entry["fields"]
    flags = []
    doi = extract_doi(fields)
    aid = extract_arxiv_id(fields)
    title = fields.get("title", "")
    src = None

    if doi and DOI_RE.match(doi):
        m = re.match(r"^10\.48550/arxiv\.(.+)$", doi, re.I)
        if m:  # arXiv DataCite DOI — arXiv API is the authority
            aid = aid or m.group(1)
        else:
            src = crossref_doi(doi)
            if src is None:
                src = datacite_doi(doi)
            if src is None:
                flags.append(("ERROR", "DOI_NOT_FOUND",
                              f"DOI {doi} resolves in neither Crossref nor "
                              "DataCite — fabricated or mistyped"))

    if src is None and aid and valid_arxiv_id(aid):
        if looks_like_preprint(fields) or not title:
            src = arxiv_by_id(aid)
            if src is None:
                flags.append(("ERROR", "ARXIV_NOT_FOUND",
                              f"arXiv ID {aid} not found on arXiv — "
                              "fabricated or mistyped"))
        else:
            # cites the published version; prefer venue-bearing indexes
            src = (dblp_title_search(title, bib_year(fields))
                   or crossref_title_search(title)
                   or arxiv_by_id(aid))

    id_failed = any(c in ("DOI_NOT_FOUND", "ARXIV_NOT_FOUND")
                    for _, c, _ in flags)
    if src is None and title and (not flags or id_failed):
        src = (dblp_title_search(title, bib_year(fields))
               or crossref_title_search(title)
               or s2_title_match(title))
        if src and id_failed:
            hint = f" (correct DOI: {src['doi']})" if src.get("doi") else ""
            flags.append(("WARN", "POSSIBLE_ID_TYPO",
                          f"a paper with this title does exist in "
                          f"{src['source']}: {src['url']}{hint} — replace the "
                          "bad identifier with the canonical one"))
        elif src:
            flags.append(("INFO", "RESOLVED_VIA_SEARCH",
                          f"matched by title in {src['source']}: {src['url']}"))
            if src.get("doi") and not doi:
                flags.append(("WARN", "MISSING_DOI",
                              f"add doi = {{{src['doi']}}} so the entry is "
                              "unambiguous"))

    if src is None and not flags:
        if entry["type"] in SOFT_TYPES:
            flags.append(("WARN", "NOT_IN_INDEXES",
                          f"@{entry['type']} not found in Crossref/DBLP/"
                          "Semantic Scholar — these types are often "
                          "unindexed; verify manually against the source"))
        else:
            flags.append(("ERROR", "UNRESOLVED",
                          "not found in Crossref, DBLP, Semantic Scholar or "
                          "arXiv — possible fabricated/hallucinated citation. "
                          "Verify by hand before keeping it."))

    if src is not None:
        flags.extend(compare_with_source(entry, src))
        check_doi = src.get("doi") or (doi if doi and DOI_RE.match(doi) else None)
        if (check_retractions and check_doi
                and src["source"] in ("Crossref", "DBLP", "Semantic Scholar")):
            flags.extend(crossref_retraction_check(check_doi))
    return src, flags


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def entry_status(flags, online: bool, entry_type: str):
    codes = {c for _, c, _ in flags}
    errors = [c for s, c, _ in flags if s == "ERROR"]
    if "RETRACTED" in codes:
        return "RETRACTED"
    if {"UNRESOLVED", "DOI_NOT_FOUND", "ARXIV_NOT_FOUND"} & codes:
        return "UNRESOLVED"
    if errors:
        return "MISMATCH"
    if not online:
        return "PARSED_ONLY"
    if "UNVERIFIABLE_TYPE" in codes or "NOT_IN_INDEXES" in codes:
        return "UNVERIFIED"
    warns = [c for s, c, _ in flags if s == "WARN"]
    return "VERIFIED*" if warns else "VERIFIED"


def main():
    ap = argparse.ArgumentParser(
        prog="check_bibtex.py",
        description="Validate every entry of a .bib file against Crossref, "
                    "DBLP, Semantic Scholar, arXiv and DataCite; flag "
                    "unresolvable/fabricated entries, metadata mismatches, "
                    "duplicates and retractions.",
        epilog="Exit codes: 0 = clean, 2 = problems found, 1 = operational "
               "failure. Requires CONTACT_EMAIL (or interactive prompt) "
               "unless --offline.")
    ap.add_argument("bibfile", help="path to the .bib file to verify")
    ap.add_argument("--offline", action="store_true",
                    help="parse + static/duplicate checks only; no network")
    ap.add_argument("--key", action="append", default=[],
                    help="only verify this citation key (repeatable)")
    ap.add_argument("--json", metavar="PATH",
                    help="also write a machine-readable JSON report")
    ap.add_argument("--limit", type=int, default=0, metavar="N",
                    help="verify at most N entries online (0 = all)")
    ap.add_argument("--no-retraction-check", action="store_true",
                    help="skip the per-DOI Crossref retraction lookup "
                    "(halves the request count)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 on warnings too, not just errors")
    ap.add_argument("--refresh", action="store_true",
                    help="bypass the response cache under .cache/")
    args = ap.parse_args()

    try:
        with open(args.bibfile, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        fail(f"cannot read {args.bibfile}: {e}")

    try:
        entries = parse_bibtex(text)
    except ParseError as e:
        fail(f"BibTeX parse error in {args.bibfile}: {e}")
    if not entries:
        fail(f"no BibTeX entries found in {args.bibfile}")

    if args.refresh:
        global DEFAULT_TTL
        DEFAULT_TTL = 0

    if args.key:
        wanted = set(args.key)
        unknown = wanted - {e["key"] for e in entries}
        if unknown:
            fail("key(s) not found in file: " + ", ".join(sorted(unknown)))

    if not args.offline:
        contact_email()  # resolve early so the failure is up front

    dup_flags = duplicate_checks(entries)
    results = []
    online_done = 0
    total = len(entries)
    print(f"verify-citations — {args.bibfile} ({total} entries, "
          f"{'offline' if args.offline else 'online'} mode)\n")

    for idx, entry in enumerate(entries, 1):
        key, fields = entry["key"], entry["fields"]
        flags = list(dup_flags[idx - 1]) + static_checks(entry)
        src = None
        selected = (not args.key) or (key in set(args.key))
        do_online = (not args.offline and selected
                     and (args.limit == 0 or online_done < args.limit))
        if do_online:
            has_id = extract_doi(fields) or extract_arxiv_id(fields)
            if entry["type"] in WEB_TYPES and not has_id:
                flags.append(("INFO", "UNVERIFIABLE_TYPE",
                              f"@{entry['type']} without DOI/arXiv ID "
                              "(website/software?) — check the URL by hand"))
            else:
                src, online_flags = verify_online(
                    entry, check_retractions=not args.no_retraction_check)
                flags.extend(online_flags)
                online_done += 1

        flags = list(dict.fromkeys(flags))  # dedupe identical flags
        status = entry_status(flags, do_online, entry["type"])
        via = f" via {src['source']} ({src['url']})" if src else ""
        print(f"[{idx}/{total}] {key} (@{entry['type']}, line {entry['line']})"
              f" ... {status}{via}")
        for sev, code, msg in flags:
            print(f"    {sev:5s} {code}: {msg}")
        results.append({"key": key, "type": entry["type"],
                        "line": entry["line"], "status": status,
                        "resolved": ({"source": src["source"], "url": src["url"],
                                      "doi": src.get("doi")} if src else None),
                        "flags": [{"severity": s, "code": c, "message": m}
                                  for s, c, m in flags]})

    n_err = sum(1 for r in results
                if any(f["severity"] == "ERROR" for f in r["flags"]))
    n_warn = sum(1 for r in results
                 if any(f["severity"] == "WARN" for f in r["flags"])
                 and not any(f["severity"] == "ERROR" for f in r["flags"]))
    n_retracted = sum(1 for r in results if r["status"] == "RETRACTED")
    n_unresolved = sum(1 for r in results if r["status"] == "UNRESOLVED")
    n_verified = sum(1 for r in results
                     if r["status"] in ("VERIFIED", "VERIFIED*"))

    print(f"\nSummary: {total} entries — {n_verified} verified, "
          f"{n_err} with errors ({n_unresolved} unresolved, "
          f"{n_retracted} retracted), {n_warn} with warnings only.")
    if n_err:
        print("Entries with ERROR flags must be fixed or removed before "
              "submission. Never invent a replacement citation: fix from the "
              "canonical record (see references/triage-guide.md).")

    if args.json:
        report = {"file": args.bibfile,
                  "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "mode": "offline" if args.offline else "online",
                  "entries": results,
                  "summary": {"total": total, "verified": n_verified,
                              "errors": n_err, "warnings_only": n_warn,
                              "unresolved": n_unresolved,
                              "retracted": n_retracted}}
        try:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"JSON report written to {args.json}")
        except OSError as e:
            fail(f"cannot write JSON report: {e}")

    if n_err or (args.strict and n_warn):
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
