#!/usr/bin/env python3
"""Politely fetch ONE conference CFP page, cache it, and print readable text.

Part of the parse-cfp skill (research-paper-skills). Stdlib only.

Politeness contract (do not weaken):
  - fetches exactly one URL per invocation — never bulk-crawls
  - >= 1 second between requests to the same host (persisted across runs)
  - User-Agent: "research-paper-skills (mailto:$CONTACT_EMAIL)"
  - exponential backoff on HTTP 429/503, honoring Retry-After
  - responses cached under .cache/parse-cfp/ (gitignored), default 24h reuse

Exit codes: 0 ok | 1 fetch failed | 2 usage/config error | 3 non-HTML content.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

MIN_INTERVAL = 1.0   # seconds between requests to the same host
MAX_RETRIES = 4      # extra attempts after the first, on HTTP 429/503
MAX_BYTES = 8 * 1024 * 1024

HEADINGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "head"}
BLOCK_TAGS = {
    "p", "div", "section", "article", "ul", "ol", "table", "thead", "tbody",
    "blockquote", "pre", "dt", "dd", "dl", "figure", "figcaption", "header",
    "footer", "nav", "main", "aside", "form", "fieldset",
}


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def contact_email() -> str:
    email = os.environ.get("CONTACT_EMAIL", "").strip()
    if not email and sys.stdin.isatty():
        try:
            email = input("CONTACT_EMAIL is not set. Contact email for the polite User-Agent: ").strip()
        except (EOFError, KeyboardInterrupt):
            email = ""
    if not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        fail(
            "a real contact email is required for the polite User-Agent "
            "(API/site operators may need to reach you). "
            "Set CONTACT_EMAIL=you@example.org and re-run.",
            code=2,
        )
    return email


# --- rate limiting (persisted per host across invocations) --------------------

def _host_stamp(cache_dir: Path, host: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9.-]", "_", host) or "unknown-host"
    return cache_dir / "hosts" / safe


def respect_rate_limit(cache_dir: Path, host: str) -> None:
    stamp = _host_stamp(cache_dir, host)
    try:
        last = float(stamp.read_text().strip())
    except (OSError, ValueError):
        last = 0.0
    wait = MIN_INTERVAL - (time.time() - last)
    if wait > 0:
        print(f"[rate-limit] waiting {wait:.1f}s before contacting {host}", file=sys.stderr)
        time.sleep(wait)


def mark_request(cache_dir: Path, host: str) -> None:
    stamp = _host_stamp(cache_dir, host)
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(str(time.time()), encoding="utf-8")


# --- fetching ------------------------------------------------------------------

def fetch(url: str, email: str, timeout: int) -> tuple[str, int, str, bytes, str]:
    """GET one URL with backoff. Returns (final_url, status, content_type, raw, charset)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"research-paper-skills (mailto:{email})",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        },
        method="GET",
    )
    delay = 2.0
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    print(f"[warn] response exceeded {MAX_BYTES} bytes; truncated", file=sys.stderr)
                    raw = raw[:MAX_BYTES]
                if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                    try:
                        raw = gzip.decompress(raw)
                    except OSError as exc:
                        fail(f"could not decompress gzip response from {url}: {exc}")
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.geturl(), resp.status, resp.headers.get_content_type(), raw, charset
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < MAX_RETRIES:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    pause = min(float(retry_after), 120.0) if retry_after else delay
                except ValueError:
                    pause = delay
                print(
                    f"[backoff] HTTP {exc.code}; retrying in {pause:.0f}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(pause)
                delay *= 2
                continue
            fail(f"HTTP {exc.code} {exc.reason} fetching {url}")
        except urllib.error.URLError as exc:
            fail(f"network error fetching {url}: {exc.reason}")
        except TimeoutError:
            fail(f"timed out after {timeout}s fetching {url}")
    fail(f"gave up after {MAX_RETRIES + 1} attempts (persistent 429/503) fetching {url}")
    raise AssertionError("unreachable")


# --- HTML -> readable text -------------------------------------------------------

class TextExtractor(HTMLParser):
    """Markdown-ish text: headings kept, list bullets kept, table cells piped,
    absolute link targets appended as [url] (submission-system URLs matter)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.href: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in HEADINGS:
            self.out.append(f"\n\n{HEADINGS[tag]} ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag == "tr":
            self.out.append("\n| ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag == "br":
            self.out.append("\n")
        elif tag in BLOCK_TAGS:
            self.out.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith(("http://", "https://")):
                self.href = href

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "a" and self.href:
            self.out.append(f" [{self.href}]")
            self.href = None
        elif tag in BLOCK_TAGS or tag in HEADINGS:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip and data:
            self.out.append(data)


def to_text(doc: str) -> str:
    parser = TextExtractor()
    parser.feed(doc)
    parser.close()
    text = "".join(parser.out)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# --- cache -----------------------------------------------------------------------

def cache_base(cache_dir: Path, url: str) -> Path:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    parts = urllib.parse.urlsplit(url)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", parts.netloc + parts.path).strip("-")[:60] or "page"
    return cache_dir / f"{slug}-{key}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Politely fetch ONE conference CFP page and print readable text to stdout. "
                    "Politeness: rate-limited to 1 request/second per host (persisted across "
                    "runs), exponential backoff on HTTP 429/503 honoring Retry-After, "
                    "User-Agent 'research-paper-skills (mailto:$CONTACT_EMAIL)' (set the "
                    "CONTACT_EMAIL env var), responses cached under .cache/parse-cfp/ "
                    "(gitignored) and reused for 24h.",
        epilog="examples:\n"
               "  CONTACT_EMAIL=you@uni.edu python3 fetch_cfp.py "
               "https://sigspatial2026.sigspatial.org/research-submission.html\n"
               "  python3 fetch_cfp.py <url> --html      # raw HTML instead of text\n"
               "  python3 fetch_cfp.py <url> --refresh   # bypass the 24h cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("url", help="the CFP / author-instructions page (one URL per run)")
    ap.add_argument("--html", action="store_true", help="print raw HTML instead of extracted text")
    ap.add_argument("--refresh", action="store_true", help="ignore any cached copy and refetch")
    ap.add_argument("--max-age", type=float, default=24.0, metavar="HOURS",
                    help="reuse cached copies younger than this (default: 24)")
    ap.add_argument("--cache-dir", type=Path,
                    default=Path(os.environ.get("CFP_CACHE_DIR", ".cache/parse-cfp")),
                    help="cache directory (default: .cache/parse-cfp, gitignored)")
    ap.add_argument("--timeout", type=int, default=30, help="request timeout in seconds (default: 30)")
    args = ap.parse_args()

    parts = urllib.parse.urlsplit(args.url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        fail(f"only absolute http(s) URLs are supported, got: {args.url!r}", code=2)

    base = cache_base(args.cache_dir, args.url)
    html_path = base.with_name(base.name + ".html")
    meta_path = base.with_name(base.name + ".meta.json")

    meta: dict | None = None
    if not args.refresh and meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = None
        if meta and time.time() - meta.get("fetched_epoch", 0) > args.max_age * 3600:
            meta = None  # stale
        if meta and not Path(meta.get("saved_to", "")).is_file():
            meta = None  # cached body was deleted; refetch

    if meta is None:
        email = contact_email()
        respect_rate_limit(args.cache_dir, parts.netloc)
        mark_request(args.cache_dir, parts.netloc)
        final_url, status, ctype, raw, charset = fetch(args.url, email, args.timeout)
        is_html = ctype in ("text/html", "application/xhtml+xml") or ctype.startswith("text/")
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        if is_html:
            html_path.write_text(raw.decode(charset, errors="replace"), encoding="utf-8")
            saved = html_path
        else:
            saved = base.with_name(base.name + ".bin")
            saved.write_bytes(raw)
        meta = {
            "requested_url": args.url,
            "final_url": final_url,
            "status": status,
            "content_type": ctype,
            "is_html": is_html,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fetched_epoch": time.time(),
            "bytes": len(raw),
            "saved_to": str(saved),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"[fetch] GET {args.url} -> {status} {ctype}, {len(raw)} bytes; cached at {saved}",
              file=sys.stderr)
    else:
        print(f"[cache] using copy fetched {meta['fetched_at']} ({meta['saved_to']}); "
              f"pass --refresh to refetch", file=sys.stderr)

    if not meta.get("is_html", True):
        fail(
            f"fetched non-HTML content ({meta['content_type']}), saved to {meta['saved_to']}. "
            "If this is a PDF call-for-papers, read that file directly instead of re-running.",
            code=3,
        )

    doc = Path(meta["saved_to"]).read_text(encoding="utf-8")
    out = doc if args.html else to_text(doc)
    if not args.html and len(out) < 500:
        print("[warn] very little text extracted — the page is likely JavaScript-rendered. "
              "Ask the user to paste the page content instead of guessing.", file=sys.stderr)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
