#!/usr/bin/env python3
"""Shared plumbing for the find-papers scripts. Python 3 stdlib only.

Provides:
  - contact_email(): CONTACT_EMAIL env var; interactive prompt if unset;
    hard error when non-interactive (APIs need a real address for their
    polite pools).
  - http_get(): polite GET with a per-host rate limit persisted across
    invocations, exponential backoff on HTTP 429 (honors Retry-After),
    and response caching under .cache/find-papers/ (gitignored).
  - http_try(): same transport as http_get() but RAISES ProviderError on
    failure instead of exiting the process. This is the failover primitive:
    a single-provider script still hard-fails, but an orchestrator (e.g.
    resolve_papers.py) can catch one provider's outage and degrade to the
    other indexes rather than crashing or silently collapsing to whatever
    happens to still answer.
  - ProviderError: structured failure (provider, kind, message) so callers
    can tell "provider down -> retry/fallback" apart from "no result".
  - note_provider() / provider_report() / coverage_status(): a per-run
    ledger of which authoritative indexes answered, were degraded, or were
    unreachable, so a run can be honestly stamped COMPLETE vs PARTIAL.

This module is not a CLI. It is imported by dblp_search.py,
crossref_search.py, s2_search.py, arxiv_search.py and resolve_papers.py,
which live in the same directory.
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


class ProviderError(Exception):
    """A provider lookup failed for *provider* reasons, not relevance.

    `kind` is one of: 'http' (a non-2xx other than 429), 'rate_limit' (429s
    exhausted), 'network' (resets/timeouts), 'parse' (unexpected body). An
    orchestrator catches this to fail over to another index and to mark the
    provider degraded/unreachable in the coverage ledger — it must NOT be
    confused with a clean "0 results" answer, which is a real, complete
    response from a healthy provider.
    """

    def __init__(self, provider: str, kind: str, message: str):
        super().__init__(f"{provider}: {kind}: {message}")
        self.provider = provider
        self.kind = kind
        self.message = message


# --- per-run provider-coverage ledger ----------------------------------------
# Records, for one orchestrated run, whether each authoritative index answered
# cleanly, returned partial data, or was unreachable. Lets the run be stamped
# COMPLETE vs PARTIAL so a degraded run is visibly flagged instead of being
# reported as if it were exhaustive. In-process only (one run = one process).

_PROVIDER_LEDGER: dict[str, dict] = {}


def note_provider(provider: str, status: str, detail: str = "") -> None:
    """Record a provider's outcome for this run.

    status: 'ok' (answered cleanly), 'empty' (answered, no hits — still
    healthy coverage), 'degraded' (answered but incomplete, e.g. capped or
    a sub-query failed), or 'down' (unreachable / rate-limited out). The
    worst status seen for a provider wins, so one failed sub-query downgrades
    that provider for the whole run.
    """
    rank = {"ok": 0, "empty": 0, "degraded": 1, "down": 2}
    prev = _PROVIDER_LEDGER.get(provider)
    if prev is None or rank.get(status, 0) >= rank.get(prev["status"], 0):
        _PROVIDER_LEDGER[provider] = {"status": status, "detail": detail}


def coverage_status() -> str:
    """'COMPLETE' iff every consulted provider answered; else 'PARTIAL'.

    PARTIAL whenever any authoritative index was degraded or unreachable —
    the signal that real, relevant papers may be missing for provider
    reasons (rate limit / outage), not because they do not exist.
    """
    if not _PROVIDER_LEDGER:
        return "COMPLETE"
    worst = max((v["status"] for v in _PROVIDER_LEDGER.values()),
                key=lambda s: {"ok": 0, "empty": 0, "degraded": 1, "down": 2}.get(s, 0))
    return "COMPLETE" if worst in ("ok", "empty") else "PARTIAL"


def provider_report() -> dict:
    """Snapshot of the ledger plus the overall coverage verdict."""
    return {
        "coverage": coverage_status(),
        "providers": {k: dict(v) for k, v in _PROVIDER_LEDGER.items()},
    }


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


def _http_core(
    url: str,
    *,
    min_interval: float,
    headers: dict | None,
    ttl: int,
    use_cache: bool,
) -> str:
    """Polite GET shared by http_get() and http_try().

    Returns the body on success. On failure raises ProviderError so the
    caller decides whether to exit (single-provider script) or fail over to
    another index (orchestrator). Never calls sys.exit itself.

    - serves from .cache/find-papers/ when a fresh (< ttl) entry exists
    - rate-limits to one request per min_interval seconds per host
    - retries HTTP 429 / connection resets with exponential backoff
      (2s, 4s, 8s; honors Retry-After when larger)
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
            if e.code == 429:
                raise ProviderError(
                    host, "rate_limit",
                    f"persistent HTTP 429 after {MAX_RETRIES} attempts; url={url}",
                )
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            raise ProviderError(
                host, "http", f"HTTP {e.code}; url={url}; {detail}".rstrip()
            )
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
    raise ProviderError(
        host, "network",
        f"gave up after {MAX_RETRIES} attempts"
        + (f" (last error: {last_err})" if last_err else ""),
    )


def http_get(
    url: str,
    *,
    min_interval: float = 1.0,
    headers: dict | None = None,
    ttl: int = DEFAULT_TTL,
    use_cache: bool = True,
) -> str:
    """Polite GET for single-provider scripts. Exits nonzero on any failure.

    Identical transport to http_try(); the only difference is that a provider
    failure here is fatal to the process (the right behavior when a user runs
    one search script directly), whereas http_try() raises so an orchestrator
    can fall back to another index.
    """
    try:
        return _http_core(url, min_interval=min_interval, headers=headers,
                          ttl=ttl, use_cache=use_cache)
    except ProviderError as e:
        extra = ""
        if e.kind == "rate_limit" and "semanticscholar" in e.provider:
            extra = (" Request a free key and export S2_API_KEY for a "
                     "dedicated 1 req/s allowance.")
        fail(f"{e.provider}: {e.message}. Wait a minute and retry.{extra}")
    raise AssertionError("unreachable")


def http_try(
    url: str,
    *,
    provider: str,
    min_interval: float = 1.0,
    headers: dict | None = None,
    ttl: int = DEFAULT_TTL,
    use_cache: bool = True,
) -> str:
    """Polite GET for orchestrators. Raises ProviderError instead of exiting.

    `provider` is the human name recorded in the coverage ledger on failure
    (the caller should also note_provider('ok'/'empty') on success). Catch
    ProviderError to fail over to another index — do NOT let it abort the
    whole run, and do NOT treat it as "0 results".
    """
    try:
        return _http_core(url, min_interval=min_interval, headers=headers,
                          ttl=ttl, use_cache=use_cache)
    except ProviderError as e:
        # Re-label with the friendly provider name for the ledger/report.
        raise ProviderError(provider, e.kind, e.message) from None


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
