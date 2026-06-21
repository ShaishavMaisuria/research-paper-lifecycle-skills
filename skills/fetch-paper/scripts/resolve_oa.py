#!/usr/bin/env python3
"""Resolve ONE DOI or arXiv ID to a LEGAL open-access copy of a paper.

Part of the fetch-paper skill (research-paper-skills). Stdlib only.

Resolution order:
  - arXiv IDs (incl. 10.48550/arXiv.* DOIs)  -> arxiv.org PDF + HTML + abs page
  - DOIs -> Unpaywall v2 best_oa_location (the standard DOI->legal-OA resolver)
  - 10.1145/* DOIs Unpaywall can't resolve  -> dl.acm.org open-access fallback
    (the ACM Digital Library is fully open access since Jan 1, 2026)

Politeness contract (do not weaken):
  - resolves exactly one identifier per invocation -- never bulk
  - >= 1 second between requests per host (3 s for arxiv.org, per their policy),
    persisted across runs
  - User-Agent: "research-paper-skills (mailto:$CONTACT_EMAIL)"
  - exponential backoff on HTTP 429/503, honoring Retry-After
  - API responses cached under .cache/fetch-paper/ (gitignored), 24h reuse

Legal contract (do not weaken):
  - only ever returns URLs that the source itself declares open access
  - never suggests shadow libraries
  - downloaded PDFs go to a temp dir by default: transient use only,
    never committed to a repo, never redistributed

Exit codes: 0 OA copy found | 1 fetch/network failure | 2 usage/config error
            | 3 identifier resolved but no legal OA copy exists.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MIN_INTERVAL = 1.0          # seconds between requests to the same host
HOST_MIN_INTERVAL = {               # arXiv asks for 3 s between requests
    "arxiv.org": 3.0,
    "export.arxiv.org": 3.0,
}
MAX_RETRIES = 4                     # extra attempts after the first, on HTTP 429/503
MAX_API_BYTES = 4 * 1024 * 1024     # cap on API/HTML-probe responses
MAX_PDF_BYTES = 64 * 1024 * 1024    # cap on --download
ATOM = "{http://www.w3.org/2005/Atom}"

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ARXIV_NEW_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_OLD_RE = re.compile(r"^[a-z][a-z-]*(\.[A-Z]{2})?/\d{7}(v\d+)?$")


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# --- contact / Unpaywall email -------------------------------------------------

def looks_like_email(s: str) -> bool:
    return "@" in s and "." in s.rsplit("@", 1)[-1]


def resolve_emails() -> tuple[str, str]:
    """Return (contact_email for User-Agent, email for the Unpaywall param)."""
    contact = os.environ.get("CONTACT_EMAIL", "").strip()
    upw = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if not contact and upw:
        contact = upw
    if not contact and sys.stdin.isatty():
        try:
            contact = input(
                "CONTACT_EMAIL is not set. Contact email for polite API access: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            contact = ""
    if not looks_like_email(contact):
        fail(
            "a real contact email is required (Unpaywall rejects placeholder "
            "addresses with HTTP 422, and API operators may need to reach you). "
            "Set CONTACT_EMAIL=you@university.edu (and optionally "
            "UNPAYWALL_EMAIL) and re-run.",
            code=2,
        )
    if not upw:
        upw = contact
    return contact, upw


# --- identifier classification ---------------------------------------------------

def classify(raw: str) -> tuple[str, str]:
    """Return ("doi"|"arxiv", normalized_id). Exits 2 on anything else."""
    s = raw.strip()
    if any(ch.isspace() for ch in s) or "," in s:
        fail("one identifier per run -- this script never bulk-fetches. "
             f"Got: {raw!r}", code=2)
    # unwrap URLs / prefixes
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
                   "http://dx.doi.org/", "doi:"):
        if s.lower().startswith(prefix):
            s = s[len(prefix):]
            break
    m = re.match(r"^https?://(?:www\.)?arxiv\.org/(?:abs|pdf|html)/(.+?)(?:\.pdf)?(?:[?#].*)?$", s)
    if m:
        s = m.group(1)
    if s.lower().startswith("arxiv:"):
        s = s[len("arxiv:"):]
    # arXiv-issued DOIs are really arXiv IDs
    m = re.match(r"^10\.48550/arxiv\.(.+)$", s, re.IGNORECASE)
    if m:
        s = m.group(1)
    if ARXIV_NEW_RE.match(s) or ARXIV_OLD_RE.match(s):
        return "arxiv", s
    if DOI_RE.match(s):
        return "doi", s
    fail(
        f"could not recognize {raw!r} as a DOI or arXiv ID. Expected forms: "
        "10.1145/3589132.3625571, https://doi.org/10.1145/..., 2403.12345, "
        "arXiv:2403.12345v2, cs/0309136, or an arxiv.org URL. "
        "If you only have a title, use the find-papers skill first.",
        code=2,
    )
    raise AssertionError("unreachable")


# --- rate limiting (persisted per host across invocations) ------------------------

def _host_stamp(cache_dir: Path, host: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9.-]", "_", host) or "unknown-host"
    return cache_dir / "hosts" / safe


def respect_rate_limit(cache_dir: Path, host: str) -> None:
    min_interval = HOST_MIN_INTERVAL.get(host, DEFAULT_MIN_INTERVAL)
    stamp = _host_stamp(cache_dir, host)
    try:
        last = float(stamp.read_text().strip())
    except (OSError, ValueError):
        last = 0.0
    wait = min_interval - (time.time() - last)
    if wait > 0:
        print(f"[rate-limit] waiting {wait:.1f}s before contacting {host}", file=sys.stderr)
        time.sleep(wait)


def mark_request(cache_dir: Path, host: str) -> None:
    stamp = _host_stamp(cache_dir, host)
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(str(time.time()), encoding="utf-8")


# --- HTTP -------------------------------------------------------------------------

def request(url: str, contact: str, timeout: int, cache_dir: Path,
            max_bytes: int = MAX_API_BYTES) -> tuple[int, bytes, str]:
    """Rate-limited GET with 429/503 backoff.

    Returns (status, body, content_type). Non-retryable HTTP errors are
    returned (not raised) so callers can interpret 404/422 etc.
    Network-level failures exit 1.
    """
    host = urllib.parse.urlsplit(url).netloc
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"research-paper-skills (mailto:{contact})",
            "Accept": "application/json,application/atom+xml;q=0.9,*/*;q=0.5",
        },
        method="GET",
    )
    delay = 2.0
    for attempt in range(MAX_RETRIES + 1):
        respect_rate_limit(cache_dir, host)
        mark_request(cache_dir, host)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    print(f"[warn] response exceeded {max_bytes} bytes; truncated",
                          file=sys.stderr)
                    raw = raw[:max_bytes]
                if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                    try:
                        raw = gzip.decompress(raw)
                    except OSError as exc:
                        fail(f"could not decompress gzip response from {host} "
                             f"(possibly truncated at {max_bytes} bytes): {exc}")
                return resp.status, raw, resp.headers.get_content_type()
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < MAX_RETRIES:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    pause = min(float(retry_after), 120.0) if retry_after else delay
                except ValueError:
                    pause = delay
                print(f"[backoff] HTTP {exc.code} from {host}; retrying in {pause:.0f}s "
                      f"(attempt {attempt + 1}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(pause)
                delay *= 2
                continue
            try:
                body = exc.read(max_bytes)
            except OSError:
                body = b""
            ctype = exc.headers.get_content_type() if exc.headers else "application/octet-stream"
            return exc.code, body, ctype
        except urllib.error.URLError as exc:
            fail(f"network error fetching {url}: {exc.reason}")
        except TimeoutError:
            fail(f"timed out after {timeout}s fetching {url}")
    fail(f"gave up after {MAX_RETRIES + 1} attempts (persistent 429/503) fetching {url}")
    raise AssertionError("unreachable")


def cached_request(key: str, url: str, contact: str, timeout: int, cache_dir: Path,
                   max_age_h: float, refresh: bool,
                   store_body: bool = True) -> tuple[int, str]:
    """request() with a JSON text cache under cache_dir, keyed by `key`.

    Only used for small text responses (JSON / Atom XML / HTML probes).
    Returns (status, body_text). With store_body=False only the status is
    persisted (used for HTML existence probes, so full paper text never
    lands on disk -- transient processing only).
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", key).strip("-")[:60]
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    path = cache_dir / f"{slug}-{digest}.json"
    if not refresh and path.is_file():
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - entry.get("fetched_epoch", 0) <= max_age_h * 3600:
                print(f"[cache] {key}: using copy fetched {entry['fetched_at']} "
                      f"(pass --refresh to refetch)", file=sys.stderr)
                return entry["status"], entry["body"]
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    status, raw, _ctype = request(url, contact, timeout, cache_dir)
    body = raw.decode("utf-8", errors="replace")
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "key": key,
        "url": url,
        "status": status,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetched_epoch": time.time(),
        "body": body if store_body else "",
    }, indent=2), encoding="utf-8")
    print(f"[fetch] GET {url} -> {status}", file=sys.stderr)
    return status, body


# --- resolvers ---------------------------------------------------------------------

def blank_result(raw: str, kind: str, ident: str) -> dict:
    return {
        "input": raw, "kind": kind, "id": ident, "title": None,
        "is_oa": False, "oa_status": None, "license": None, "version": None,
        "pdf_url": None, "html_url": None, "landing_url": None,
        "source": None, "notes": [],
    }


def arxiv_id_from_url(url: str) -> str | None:
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/([^\s?#]+?)(?:\.pdf)?(?:$|[?#])", url)
    return m.group(1) if m else None


def resolve_arxiv(raw: str, ident: str, contact: str, args) -> dict:
    res = blank_result(raw, "arxiv", ident)
    api = ("http://export.arxiv.org/api/query?"
           + urllib.parse.urlencode({"id_list": ident, "max_results": 1}))
    status, body = cached_request(f"arxiv-api:{ident}", api, contact,
                                  args.timeout, args.cache_dir, args.max_age, args.refresh)
    if status != 200:
        fail(f"arXiv API returned HTTP {status} for id {ident}")
    try:
        feed = ET.fromstring(body)
    except ET.ParseError as exc:
        fail(f"could not parse arXiv API response: {exc}")
    entry = feed.find(f"{ATOM}entry")
    entry_id = entry.findtext(f"{ATOM}id", "") if entry is not None else ""
    if entry is None or "api/errors" in entry_id or not entry_id:
        fail(f"arXiv has no paper with id {ident!r}. Double-check the ID "
             "(versions like v2 are optional).", code=2)
    res["title"] = " ".join((entry.findtext(f"{ATOM}title") or "").split()) or None
    res["is_oa"] = True
    res["oa_status"] = "green"
    res["version"] = "submittedVersion"
    res["source"] = "arxiv"
    res["pdf_url"] = f"https://arxiv.org/pdf/{ident}"
    res["landing_url"] = f"https://arxiv.org/abs/{ident}"
    html_url = f"https://arxiv.org/html/{ident}"
    if args.no_html_check:
        res["html_url"] = html_url
        res["notes"].append("HTML URL not probed (--no-html-check); it 404s for "
                            "papers without an arXiv HTML rendering.")
    else:
        h_status, _ = cached_request(f"arxiv-html-probe:{ident}", html_url, contact,
                                     args.timeout, args.cache_dir, args.max_age,
                                     args.refresh, store_body=False)
        if h_status == 200:
            res["html_url"] = html_url
        else:
            res["notes"].append(f"no arXiv HTML rendering (HTTP {h_status}); "
                                "use the PDF.")
    res["notes"].append("arXiv version is the preprint; the published version "
                        "may differ. Cite the published DOI when one exists.")
    return res


def resolve_doi(raw: str, doi: str, contact: str, upw_email: str, args) -> dict:
    res = blank_result(raw, "doi", doi)
    url = ("https://api.unpaywall.org/v2/" + urllib.parse.quote(doi, safe="/")
           + "?" + urllib.parse.urlencode({"email": upw_email}))
    status, body = cached_request(f"unpaywall:{doi}", url, contact,
                                  args.timeout, args.cache_dir, args.max_age, args.refresh)
    if status == 422:
        fail("Unpaywall rejected the email address (HTTP 422). Placeholder "
             "addresses like *@example.com are refused -- set UNPAYWALL_EMAIL "
             "to a real address and re-run.", code=2)
    if status == 404:
        res["notes"].append("DOI not found in Unpaywall (covers ~50M Crossref DOIs).")
        return acm_fallback(res, doi) if doi.startswith("10.1145/") else res
    if status != 200:
        fail(f"Unpaywall returned HTTP {status} for DOI {doi}")
    try:
        rec = json.loads(body)
    except json.JSONDecodeError as exc:
        fail(f"could not parse Unpaywall response: {exc}")
    res["title"] = rec.get("title")
    res["is_oa"] = bool(rec.get("is_oa"))
    res["oa_status"] = rec.get("oa_status")
    best = rec.get("best_oa_location") or {}
    if res["is_oa"] and best:
        res["source"] = "unpaywall"
        res["license"] = best.get("license")
        res["version"] = best.get("version")
        res["pdf_url"] = best.get("url_for_pdf")
        res["landing_url"] = best.get("url_for_landing_page")
        # derive an arXiv HTML rendering when any OA location lives on arXiv
        for loc in [best] + (rec.get("oa_locations") or []):
            aid = arxiv_id_from_url((loc.get("url_for_pdf") or "")
                                    + " " + (loc.get("url_for_landing_page") or ""))
            if aid:
                res["html_url"] = f"https://arxiv.org/html/{aid}"
                res["notes"].append(f"also on arXiv as {aid} (HTML link not probed).")
                break
        if not res["pdf_url"] and res["landing_url"]:
            res["notes"].append("no direct PDF URL; the landing page hosts the OA copy.")
        return res
    # closed or no OA location
    if doi.startswith("10.1145/"):
        return acm_fallback(res, doi)
    res["notes"] += [
        "No legal open-access copy found. Legal next steps: search the authors' "
        "homepages or institutional repository for a preprint (find-papers skill), "
        "check arXiv by title, use your library's access, or email the authors -- "
        "most happily share their accepted manuscript.",
        "Do NOT use shadow-library sites; this skill only handles legal copies.",
    ]
    return res


def acm_fallback(res: dict, doi: str) -> dict:
    """ACM DL is fully open access since Jan 1, 2026 -- construct the DL PDF URL."""
    res["is_oa"] = True
    res["oa_status"] = res["oa_status"] or "bronze"
    res["source"] = "acm-dl-open-access"
    res["pdf_url"] = f"https://dl.acm.org/doi/pdf/{doi}"
    res["landing_url"] = f"https://dl.acm.org/doi/{doi}"
    res["notes"] += [
        "Resolved via the ACM Digital Library, fully open access since Jan 1, 2026 "
        "(URL constructed from the 10.1145 prefix, not verified by this script).",
        "dl.acm.org blocks most scripted downloads -- open the URL in a browser. "
        "ACM's terms prohibit bulk/robotic downloading; fetch single papers only.",
    ]
    return res


# --- output / download ---------------------------------------------------------------

def print_human(res: dict) -> None:
    lines = [f"identifier : {res['id']}  ({res['kind']})"]
    if res["title"]:
        lines.append(f"title      : {res['title']}")
    lines.append(f"open access: {'YES' if res['is_oa'] else 'NO'}"
                 + (f"  (status: {res['oa_status']})" if res["oa_status"] else ""))
    for field in ("source", "license", "version", "pdf_url", "html_url", "landing_url"):
        if res[field]:
            lines.append(f"{field:<11}: {res[field]}")
    for note in res["notes"]:
        lines.append(f"note       : {note}")
    print("\n".join(lines))


def download_pdf(res: dict, dest: str, contact: str, args) -> None:
    if not res["pdf_url"]:
        print("[download] skipped: no direct PDF URL to download.", file=sys.stderr)
        return
    out_dir = Path(dest) if dest else Path(tempfile.mkdtemp(prefix="fetch-paper-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", res["id"]).strip("-") + ".pdf"
    out = out_dir / name
    status, raw, ctype = request(res["pdf_url"], contact, args.timeout,
                                 args.cache_dir, max_bytes=MAX_PDF_BYTES)
    if status != 200:
        print(f"[download] HTTP {status} fetching the PDF ({ctype}). Some hosts "
              "(e.g. dl.acm.org) block scripts -- open the URL in a browser instead.",
              file=sys.stderr)
        return
    if not raw[:5] == b"%PDF-":
        print(f"[download] response is not a PDF ({ctype}); not saved. "
              "Open the landing page in a browser.", file=sys.stderr)
        return
    out.write_bytes(raw)
    print(f"[download] saved {len(raw)} bytes -> {out}", file=sys.stderr)
    print("[download] TRANSIENT COPY: read it, then delete it. Never commit it "
          "to a repository or redistribute it.", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Resolve ONE DOI or arXiv ID to a LEGAL open-access copy "
                    "(Unpaywall best_oa_location, arXiv PDF/HTML, ACM DL open access).",
        epilog="examples:\n"
               "  UNPAYWALL_EMAIL=you@uni.edu python3 resolve_oa.py 10.1145/3589132.3625571\n"
               "  python3 resolve_oa.py arXiv:1706.03762 --json\n"
               "  python3 resolve_oa.py 10.1038/nature12373 --download\n"
               "exit codes: 0 OA found | 1 fetch failure | 2 usage/config | 3 no legal OA copy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("identifier",
                    help="a DOI (10.xxxx/..., doi.org URL) or arXiv ID "
                         "(2403.12345, arXiv:..., arxiv.org URL) -- ONE per run")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON")
    ap.add_argument("--download", nargs="?", const="", default=None, metavar="DIR",
                    help="also download the PDF (default: a fresh temp dir; "
                         "transient use only -- never commit or redistribute)")
    ap.add_argument("--no-html-check", action="store_true",
                    help="skip probing arxiv.org/html availability (one fewer request)")
    ap.add_argument("--refresh", action="store_true", help="bypass the response cache")
    ap.add_argument("--max-age", type=float, default=24.0, metavar="HOURS",
                    help="reuse cached API responses younger than this (default: 24)")
    ap.add_argument("--cache-dir", type=Path,
                    default=Path(os.environ.get("FETCH_PAPER_CACHE_DIR",
                                                ".cache/fetch-paper")),
                    help="cache directory (default: .cache/fetch-paper, gitignored)")
    ap.add_argument("--timeout", type=int, default=30,
                    help="per-request timeout in seconds (default: 30)")
    args = ap.parse_args()

    kind, ident = classify(args.identifier)
    contact, upw_email = resolve_emails()

    if kind == "arxiv":
        res = resolve_arxiv(args.identifier, ident, contact, args)
    else:
        res = resolve_doi(args.identifier, ident, contact, upw_email, args)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print_human(res)

    if args.download is not None and res["is_oa"]:
        download_pdf(res, args.download, contact, args)

    if not res["is_oa"]:
        sys.exit(3)


if __name__ == "__main__":
    main()
