#!/usr/bin/env python3
"""Shared plumbing for the find-papers scripts. Python 3 stdlib only.

Provides:
  - contact_email(): CONTACT_EMAIL env var; interactive prompt if unset;
    hard error when non-interactive (APIs need a real address for their
    polite pools).
  - http_get(): polite GET with a per-host rate limit persisted across
    invocations, exponential backoff on HTTP 429 (honors Retry-After),
    and response caching under .cache/find-papers/ (gitignored).

This module is not a CLI. It is imported by dblp_search.py,
crossref_search.py, s2_search.py and arxiv_search.py, which live in the
same directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CACHE_DIR = os.path.join(os.getcwd(), ".cache", "find-papers")
RATELIMIT_FILE = os.path.join(CACHE_DIR, "_ratelimit.json")
DEFAULT_TTL = 24 * 60 * 60  # seconds; scholarly indexes change at most daily
MAX_RETRIES = 4             # attempts when a host answers HTTP 429
TIMEOUT = 30                # socket timeout, seconds


def fail(msg: str, code: int = 1):
    """Print a clear error to stderr and exit nonzero."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def contact_email() -> str:
    """Return a contact email for polite API access.

    Reads CONTACT_EMAIL; prompts interactively when unset and attached to a
    TTY; otherwise exits nonzero with instructions.
    """
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
            os.environ["CONTACT_EMAIL"] = email  # reuse within this process
            return email
    fail(
        "CONTACT_EMAIL is not set. Export a real contact email first, e.g.\n"
        "  export CONTACT_EMAIL=you@university.edu\n"
        "It is sent in the User-Agent (and Crossref mailto=) so providers can "
        "contact you instead of blocking you. Placeholder domains like "
        "example.com are rejected by some providers."
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
        pass  # caching is best-effort; never break a search over it


def _throttle(host: str, min_interval: float) -> None:
    """Sleep so this host sees at most one request per min_interval seconds.

    Timestamps persist in .cache/find-papers/_ratelimit.json so back-to-back
    script invocations are throttled too, not just calls within one process.
    """
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


def http_get(
    url: str,
    *,
    min_interval: float = 1.0,
    headers: dict | None = None,
    ttl: int = DEFAULT_TTL,
    use_cache: bool = True,
) -> str:
    """Polite GET. Returns the response body as text.

    - serves from .cache/find-papers/ when a fresh (< ttl) entry exists
    - rate-limits to one request per min_interval seconds per host
    - retries HTTP 429 with exponential backoff (2s, 4s, 8s; honors
      Retry-After when larger)
    - exits nonzero with a clear message on any other failure
    """
    cpath = _cache_path(url)
    if use_cache:
        entry = _load_json(cpath)
        if entry and time.time() - entry.get("fetched_at", 0) < ttl:
            return entry["body"]

    host = urllib.parse.urlsplit(url).netloc
    req_headers = {"User-Agent": user_agent(), "Accept": "*/*"}
    if headers:
        req_headers.update(headers)

    delay = 2.0
    last_err = ""
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle(host, min_interval)
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8", "replace")
            if use_cache:
                _save_json(
                    cpath, {"url": url, "fetched_at": time.time(), "body": body}
                )
            return body
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES:
                sleep_s = delay
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        sleep_s = max(float(retry_after), delay)
                    except ValueError:
                        pass
                print(
                    f"HTTP 429 from {host}; backing off {sleep_s:.0f}s "
                    f"(attempt {attempt}/{MAX_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(sleep_s)
                delay *= 2
                continue
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            fail(f"HTTP {e.code} from {host}\n  url: {url}\n  {detail}".rstrip())
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # Connection resets are how some hosts (e.g. dblp.org) shed
            # bursty clients — treat as transient and back off like a 429.
            reason = getattr(e, "reason", e)
            last_err = f"{type(e).__name__}: {reason}"
            if attempt < MAX_RETRIES:
                print(
                    f"transient network error from {host} ({last_err}); "
                    f"backing off {delay:.0f}s (attempt {attempt}/{MAX_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(delay)
                delay *= 2
                continue
    fail(
        f"gave up after {MAX_RETRIES} attempts talking to {host}"
        + (f" (last error: {last_err})" if last_err else " (persistent HTTP 429)")
        + ". Wait a minute and retry. If this was api.semanticscholar.org, request "
        "a free key and export S2_API_KEY for a dedicated 1 req/s allowance."
    )
    raise AssertionError("unreachable")


if __name__ == "__main__":
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        sys.exit(0)
    fail(
        "polite_http.py is a shared library, not a search command. Run one of:\n"
        "  python3 scripts/dblp_search.py --help\n"
        "  python3 scripts/crossref_search.py --help\n"
        "  python3 scripts/s2_search.py --help\n"
        "  python3 scripts/arxiv_search.py --help"
    )
