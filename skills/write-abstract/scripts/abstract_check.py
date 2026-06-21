#!/usr/bin/env python3
"""Deterministic abstract linter for the write-abstract skill.

Checks an abstract (from a .tex file, a plain-text/.md file, or stdin)
against a venue profile's norms:

  - word count vs format.abstract_words (or the 150-250 convention when the
    venue mandates nothing — clearly labeled as a convention, not a rule)
  - presence/shape of the venue's keywords block: ACM CCS Concepts
    (CCSXML + \\ccsdesc + \\keywords), IEEE Index Terms (IEEEkeywords env),
    LNCS \\keywords{a \\and b}, or none (NeurIPS-style)
  - self-containedness: \\cite / \\ref / math / URLs / placeholders in the
    abstract (abstracts ship as standalone metadata)
  - the quantified-result-slot invariant: an abstract is DRAFT-not-
    submittable while it still carries any unresolved slot. Every
    results-pending draft must carry exactly ONE designated quantified-
    result slot, written as a typed contract — [RESULT: metric, units,
    sign/direction, comparison-target] — not free-text prose, so the
    result->impact arc is structurally complete and the slot is trivially
    fillable. Bare/free-text slots and >1 result slot are flagged; any
    unresolved slot HARD-FAILS the run (non-zero exit) regardless of
    --strict, and the open-slot count is printed.
  - acmart gotcha: abstract must appear BEFORE \\maketitle
  - lexical gap/approach/results/impact move signals (INFO only; the
    motivation move has no reliable lexical signal — judge it by reading)

Severities: RISK (likely desk-reject / metadata breakage), WARN (norm
violation), INFO (signal for human/LLM judgment).

Usage:
    python3 abstract_check.py <main.tex|abstract.txt|-> [--venue PROFILE.yml]
                              [--strict] [--no-family]

--venue accepts a conference profile (venues/conferences/*.yml, family
merged automatically) or a family profile (venues/families/*.yml).

Exit codes: 0 ok, 1 RISK findings present with --strict OR any unresolved
slot left (the invariant hard-fails independent of --strict), 2 bad input.
The slot gate is intentionally non-overridable: a draft with an open slot is
not submittable, so the script refuses to report success for it.
"""

import argparse
import os
import re
import sys

import venueyaml

GENERIC_RANGE = (150, 250)  # convention only — never presented as a mandate


# ---------------------------------------------------------------------------
# LaTeX handling
# ---------------------------------------------------------------------------

_COMMENT_RE = re.compile(r"(?<!\\)%.*")
_INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")


def strip_comments(text):
    return _COMMENT_RE.sub("", text)


def resolve_inputs(text, basedir, depth=0):
    """Inline \\input/\\include one file deep (twice), best effort."""
    if depth >= 2:
        return text

    def repl(m):
        name = m.group(1).strip()
        if not name.endswith(".tex"):
            name += ".tex"
        path = os.path.join(basedir, name)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    return resolve_inputs(strip_comments(fh.read()),
                                          os.path.dirname(path), depth + 1)
            except OSError:
                return ""
        return ""

    return _INPUT_RE.sub(repl, text)


_ABSTRACT_RE = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S)
_REFCMD_RE = re.compile(r"\\(?:cite[a-zA-Z]*|ref|autoref|eqref|cref|Cref|pageref)"
                        r"\s*(?:\[[^\]]*\])?\{[^}]*\}")
_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?")
_MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)", re.S)


def latex_words(text):
    """Approximate word list of LaTeX prose (citations/math become tokens)."""
    text = strip_comments(text)
    text = _REFCMD_RE.sub(" [ref] ", text)
    text = _MATH_RE.sub(" [math] ", text)
    for esc, lit in (("\\%", "%"), ("\\&", "&"), ("\\_", "_"), ("\\$", "$"),
                     ("~", " "), ("\\\\", " ")):
        text = text.replace(esc, lit)
    text = _CMD_RE.sub(" ", text)
    text = text.replace("{", " ").replace("}", " ")
    return [w for w in text.split() if any(c.isalnum() for c in w)]


def split_sentences(text):
    plain = " ".join(latex_words(text))
    parts = re.split(r"(?<=[.!?])\s+", plain)
    return [p for p in parts if len(p.split()) >= 2]


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX+|PLACEHOLDER)\b|lorem ipsum",
                             re.I)
_URL_RE = re.compile(r"https?://\S+|\\url\{")

# Unresolved fill-in slots of the form [LABEL: ...]. LABEL is an all-caps
# token; RESULT is the designated quantified-result slot, CONFIRM marks a
# fact the user must verify; any other all-caps slot is a generic open slot.
# Matches across the abstract; the body is captured so the RESULT slot can be
# checked against the typed contract.
_SLOT_RE = re.compile(r"\[\s*([A-Z][A-Z0-9_-]*)\s*:\s*(.*?)\]", re.S)

# A bound RESULT slot is a typed contract carrying, at minimum: a numeric
# magnitude (the metric value) AND a comparison target ("vs"/"over"/"than"/
# "relative to"/"compared to"/"baseline"). The metric name + units live in the
# same token (e.g. "+12% Recall@20 vs best hashing baseline under matched
# budget"). These signals are what distinguish a fillable typed slot from a
# bare "[RESULT: ...]" or free-text prose placeholder.
_RESULT_MAGNITUDE_RE = re.compile(r"[-+]?\d+(?:\.\d+)?\s*"
                                  r"(?:%|×|x\b|pp\b|ms\b|s\b|fps\b|gb\b|"
                                  r"qps\b|points?\b|percentage points?\b)?",
                                  re.I)
_RESULT_COMPARE_RE = re.compile(r"\b(vs\.?|versus|over|than|relative to|"
                                r"compared to|against|baseline|prior|"
                                r"state[- ]of[- ]the[- ]art|sota)\b", re.I)
# The slot is still an unfilled template if its body is empty or is a row of
# ellipsis / fill-me tokens rather than a concrete contract or value.
_SLOT_UNFILLED_BODY_RE = re.compile(r"^\s*(?:\.{2,}|…|x+|n/?a|metric|value|"
                                    r"number|fill|here|placeholder)?\s*$", re.I)

_MOVE_SIGNALS = [
    ("gap", re.compile(r"\b(however|yet\b|existing|prior (work|approaches)|"
                       r"lack|fail to|remains? (an )?open|no prior|"
                       r"little attention|limited to)\b", re.I)),
    ("approach", re.compile(r"\b(we (propose|present|introduce|develop|design|"
                            r"describe|formalize)|this paper (proposes|presents|"
                            r"introduces))\b", re.I)),
    ("results", re.compile(r"\d+(\.\d+)?\s*(%|×|x\b|pp\b)|"
                           r"\b(outperform|improv\w*|achiev\w*|reduc\w*|"
                           r"speedup|accuracy|recall|precision|f1|auc)\b", re.I)),
    ("impact", re.compile(r"\b(open[- ]?sourc\w*|publicly available|"
                          r"code (and data )?(is|are) available|enabl\w+|"
                          r"implications|first (step|system|study))\b", re.I)),
]


class Report:
    def __init__(self):
        self.findings = []  # (severity, tag, message)
        self.open_slots = 0  # unresolved fill-in slots — gates submittability

    def add(self, sev, tag, msg):
        self.findings.append((sev, tag, msg))

    def count(self, sev):
        return sum(1 for s, _, _ in self.findings if s == sev)


def check_length(rep, n_words, limits):
    if limits and isinstance(limits, (list, tuple)) and len(limits) == 2:
        lo, hi = limits
        if n_words < lo:
            rep.add("RISK", "length", "abstract is %d words — below the venue-"
                    "mandated minimum of %d (limit %d-%d)" % (n_words, lo, lo, hi))
        elif n_words > hi:
            rep.add("RISK", "length", "abstract is %d words — above the venue-"
                    "mandated maximum of %d (limit %d-%d)" % (n_words, hi, lo, hi))
        else:
            rep.add("INFO", "length", "abstract is %d words — within the venue-"
                    "mandated %d-%d range" % (n_words, lo, hi))
    else:
        lo, hi = GENERIC_RANGE
        if lo <= n_words <= hi:
            rep.add("INFO", "length", "abstract is %d words — no venue-mandated "
                    "limit; within the %d-%d convention" % (n_words, lo, hi))
        else:
            rep.add("WARN", "length", "abstract is %d words — no venue-mandated "
                    "limit, but outside the %d-%d convention; verify the live CFP"
                    % (n_words, lo, hi))


def check_self_contained(rep, abstract_tex):
    if re.search(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\])?\{", abstract_tex):
        rep.add("WARN", "cite-in-abstract", "\\cite inside the abstract — "
                "abstracts ship as standalone metadata where citations render "
                "as raw text/numbers; name the prior work in prose instead")
    if re.search(r"\\(?:ref|autoref|cref|Cref|eqref)\s*\{", abstract_tex):
        rep.add("WARN", "ref-in-abstract", "\\ref-style cross-reference inside "
                "the abstract — dangling once the abstract is shown alone")
    if _MATH_RE.search(abstract_tex):
        rep.add("WARN", "math-in-abstract", "math inside the abstract — often "
                "breaks in HTML/metadata renderings (TAPS, IEEE Xplore, "
                "OpenReview); prefer prose")
    if _URL_RE.search(abstract_tex):
        rep.add("INFO", "url-in-abstract", "URL inside the abstract — fine at "
                "some venues, leaks identity at double-blind ones; check the "
                "blind level")
    m = _PLACEHOLDER_RE.search(abstract_tex)
    if m:
        rep.add("RISK", "placeholder", "placeholder text %r in the abstract — "
                "several venues (e.g. KDD, AAAI) delete or desk-reject "
                "placeholder abstracts at the registration deadline"
                % m.group(0))


def _result_slot_is_typed(body):
    """True if a RESULT slot body is a bound typed contract.

    Requires both a numeric magnitude (metric value) and a comparison target,
    so '[RESULT: +12% Recall@20 vs best hashing baseline]' passes but
    '[RESULT: ...]' or '[RESULT: outperforms prior work]' does not.
    """
    if _SLOT_UNFILLED_BODY_RE.match(body):
        return False
    has_magnitude = bool([t for t in _RESULT_MAGNITUDE_RE.findall(body) or [body]
                          if re.search(r"\d", t)]) \
        and bool(re.search(r"\d", body))
    has_compare = bool(_RESULT_COMPARE_RE.search(body))
    return has_magnitude and has_compare


def check_result_slot(rep, abstract_tex):
    """Enforce the typed quantified-result-slot invariant.

    The quantified result is the single most-predictive surface of an abstract
    and the one most likely to be deferred while results are pending. This
    check makes the result->impact arc structurally complete and the open
    state machine-detectable:

      - every unresolved slot [LABEL: ...] is counted as an open slot; any
        open slot leaves the abstract DRAFT-not-submittable (hard gate);
      - results-pending drafts must carry exactly ONE designated quantified-
        result slot, and it must be a typed contract (metric value + units +
        sign/direction + comparison target), never bare or free-text prose;
      - >1 RESULT slot or a CONFIRM/other open slot is flagged so the user
        binds or removes it before registering/submitting.
    """
    slots = list(_SLOT_RE.finditer(abstract_tex))
    result_slots = [m for m in slots if m.group(1).upper() == "RESULT"]
    other_slots = [m for m in slots if m.group(1).upper() != "RESULT"]

    rep.open_slots = len(slots)

    if not slots:
        # No open slot: either results are filled in, or this is not a
        # results-pending draft. Nothing to enforce here — the moves check
        # still reports whether a quantified result is present at all.
        return

    if len(result_slots) > 1:
        rep.add("RISK", "result-slot", "%d RESULT slots present — an abstract "
                "carries exactly ONE designated quantified-result slot; merge "
                "the headline result into one typed slot and move secondary "
                "numbers to the body" % len(result_slots))

    for m in result_slots:
        body = m.group(2).strip()
        if not _result_slot_is_typed(body):
            rep.add("RISK", "result-slot", "RESULT slot %r is not a bound typed "
                    "contract — emit it as [RESULT: <value+units>, "
                    "<sign/direction>, vs <comparison target>] (e.g. "
                    "'[RESULT: +XX%% Recall@20 vs best hashing baseline under "
                    "matched budget]'), not bare or free-text prose, so the "
                    "result->impact arc can score" % ("[RESULT: %s]" % body))
        else:
            rep.add("INFO", "result-slot", "RESULT slot is a typed contract but "
                    "still UNBOUND — fill it with the verified number from the "
                    "evaluation before registering/submitting; never invent it")

    for m in other_slots:
        label, body = m.group(1).upper(), m.group(2).strip()
        rep.add("RISK", "open-slot", "unresolved %s slot %r — bind it with a "
                "verified value (or delete it) before this abstract is "
                "submittable" % (label, "[%s: %s]" % (label, body[:60])))


def check_sentences(rep, abstract_tex):
    sents = split_sentences(abstract_tex)
    if not sents:
        return
    longest = max(len(s.split()) for s in sents)
    rep.add("INFO", "sentences", "%d sentences; longest is %d words%s"
            % (len(sents), longest,
               " — consider splitting sentences over 40 words" if longest > 40 else ""))


def check_moves(rep, abstract_tex):
    plain = " ".join(latex_words(abstract_tex))
    hit = [name for name, rx in _MOVE_SIGNALS if rx.search(plain)]
    missing = [name for name, _ in _MOVE_SIGNALS if name not in hit]
    msg = "lexical move signals (heuristic — judge the actual prose): "
    msg += "detected %s" % (", ".join(hit) if hit else "none")
    if missing:
        msg += "; no signal for %s" % ", ".join(missing)
    msg += " (motivation is not lexically detectable — check it by reading)"
    rep.add("INFO", "moves", msg)


def check_keywords(rep, body, style):
    """body = full resolved tex; style = profile format.keywords value."""
    has_ccsxml = "\\begin{CCSXML}" in body
    has_ccsdesc = "\\ccsdesc" in body
    has_kw = re.search(r"\\keywords\s*\{", body)
    has_ieee = "\\begin{IEEEkeywords}" in body

    if style == "ccs-concepts":
        if not has_ccsxml:
            rep.add("RISK", "ccs-concepts", "no \\begin{CCSXML} block — ACM "
                    "venues require CCS Concepts; generate them with the "
                    "official tool at https://dl.acm.org/ccs (never hand-write "
                    "concept ids)")
        if not has_ccsdesc:
            rep.add("RISK", "ccs-concepts", "no \\ccsdesc lines — paste the "
                    "lines generated by https://dl.acm.org/ccs")
        if not has_kw:
            rep.add("RISK", "keywords", "no \\keywords{...} — ACM templates "
                    "require free-text author keywords after the CCS block")
        if has_ccsxml:
            ccs = body.split("\\begin{CCSXML}", 1)[1].split("\\end{CCSXML}")[0]
            if re.search(r"PASTE|REPLACE|TODO|FIXME|<concept_id>\s*0+\s*<",
                         ccs, re.I):
                rep.add("RISK", "ccs-concepts", "CCSXML block still contains "
                        "placeholder content — fill it from https://dl.acm.org/ccs")
    elif style == "ieee-index-terms":
        if not has_ieee:
            rep.add("RISK", "index-terms", "no \\begin{IEEEkeywords} block — "
                    "IEEE templates expect Index Terms right after the abstract")
        else:
            terms_src = body.split("\\begin{IEEEkeywords}", 1)[1]
            terms_src = terms_src.split("\\end{IEEEkeywords}")[0]
            terms = [t.strip() for t in terms_src.replace("\n", " ").split(",")
                     if t.strip()]
            rep.add("INFO", "index-terms", "%d Index Terms found%s"
                    % (len(terms),
                       "" if terms == sorted(terms, key=str.lower)
                       else " — IEEE convention orders them alphabetically"))
    elif style == "lncs-keywords":
        if not has_kw:
            rep.add("RISK", "keywords", "no \\keywords{...} block — LNCS "
                    "papers carry keywords directly after the abstract "
                    "(\\keywords{First \\and Second \\and Third})")
        else:
            kw_src = body.split("\\keywords", 1)[1]
            depth, buf = 0, ""
            for ch in kw_src:
                if ch == "{":
                    depth += 1
                    if depth == 1:
                        continue
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
                if depth >= 1:
                    buf += ch
            kws = [k.strip() for k in buf.split("\\and") if k.strip()]
            if not 3 <= len(kws) <= 6:
                rep.add("WARN", "keywords", "%d keyword(s) found — Springer "
                        "guidance and most LNCS CFPs ask for 3-6" % len(kws))
            else:
                rep.add("INFO", "keywords", "%d keywords found (3-6 expected)"
                        % len(kws))
    elif style == "none":
        if has_ccsxml or has_ieee or has_kw:
            rep.add("INFO", "keywords", "a keywords/CCS block is present but "
                    "this venue family has no in-paper keywords section "
                    "(topics are picked in the submission form) — consider "
                    "removing it")
    else:
        rep.add("INFO", "keywords", "venue profile does not specify a keywords "
                "style — verify the live CFP before adding/removing blocks")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint an abstract against a venue profile's norms "
        "(length, keywords block, self-containedness). Prints Markdown.")
    parser.add_argument("source", help="main .tex file, plain-text abstract "
                        "(.txt/.md), or - for stdin")
    parser.add_argument("--venue", default=None,
                        help="venue profile .yml (conference or family)")
    parser.add_argument("--no-family", action="store_true",
                        help="do not merge the family profile")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any RISK finding")
    args = parser.parse_args(argv)

    # --- load source ---
    if args.source == "-":
        raw = sys.stdin.read()
        is_tex = "\\begin{abstract}" in raw
        basedir = os.getcwd()
        label = "<stdin>"
    else:
        if not os.path.isfile(args.source):
            sys.stderr.write("error: file not found: %s\n" % args.source)
            return 2
        with open(args.source, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        is_tex = args.source.endswith(".tex")
        basedir = os.path.dirname(os.path.abspath(args.source))
        label = args.source
    if not raw.strip():
        sys.stderr.write("error: %s is empty\n" % label)
        return 2

    # --- load venue ---
    profile, vname, limits, style = None, None, None, None
    if args.venue:
        try:
            if args.no_family:
                profile = venueyaml.load(args.venue)
            else:
                profile = venueyaml.load_with_family(args.venue)
        except venueyaml.VenueYamlError as exc:
            sys.stderr.write("error: %s\n" % exc)
            return 2
        vname = profile.get("name") or profile.get("id") or args.venue
        fmt = profile.get("format") or {}
        limits = fmt.get("abstract_words")
        style = fmt.get("keywords")

    # --- extract abstract ---
    if is_tex:
        body = resolve_inputs(strip_comments(raw), basedir)
        m = _ABSTRACT_RE.search(body)
        abstract = m.group(1) if m else None
    else:
        body = None
        abstract = raw

    rep = Report()
    if abstract is None:
        rep.add("RISK", "missing-abstract",
                "no \\begin{abstract}...\\end{abstract} found (after resolving "
                "\\input/\\include one level)")
        n_words = 0
    else:
        n_words = len(latex_words(abstract))
        check_length(rep, n_words, limits)
        check_self_contained(rep, abstract)
        check_result_slot(rep, abstract)
        check_sentences(rep, abstract)
        check_moves(rep, abstract)

    if body is not None:
        if "acmart" in body[:2000]:  # documentclass region
            mk, ab = body.find("\\maketitle"), body.find("\\begin{abstract}")
            if mk != -1 and ab != -1 and ab > mk:
                rep.add("RISK", "acmart-order", "abstract appears AFTER "
                        "\\maketitle — acmart requires the abstract before "
                        "\\maketitle or it is dropped/mis-typeset")
        check_keywords(rep, body, style)
    elif style:
        rep.add("INFO", "keywords", "plain-text input — keywords-block checks "
                "skipped; run against the .tex to check the %s block" % style)

    # --- print report ---
    print("# Abstract check — %s\n" % label)
    print("- Venue: %s" % (vname or "none given (generic conventions only)"))
    if profile:
        ver = profile.get("verified") or {}
        print("- Profile verified: %s (%s) — re-verify against the live CFP: %s"
              % (ver.get("date", "unknown"), ver.get("confidence", "unknown"),
                 profile.get("cfp_url", "n/a")))
        print("- Keyword style: %s" % (style or "unspecified"))
    if abstract is not None:
        print("- Abstract length: %d words" % n_words)
    print("\n## Findings\n")
    if not rep.findings:
        print("- nothing to report")
    for sev, tag, msg in sorted(rep.findings,
                                key=lambda f: ("RISK", "WARN", "INFO").index(f[0])):
        print("- %s [%s] %s" % (sev, tag, msg))
    print("\n## Summary\n")
    print("RISK: %d, WARN: %d, INFO: %d"
          % (rep.count("RISK"), rep.count("WARN"), rep.count("INFO")))
    print("Open slots: %d" % rep.open_slots)
    if rep.open_slots:
        print("\n**DRAFT — not submittable**: %d unresolved slot(s) remain. "
              "Bind every slot with a verified value (the RESULT slot is the "
              "abstract's most-predictive surface) before registering or "
              "submitting. This gate hard-fails regardless of --strict."
              % rep.open_slots)
    else:
        print("\nAll slots bound — no open-slot gate blocking submission.")

    # The slot invariant is non-overridable: an abstract with an open slot is
    # not submittable, so we refuse to exit 0 even without --strict.
    if rep.open_slots:
        return 1
    if args.strict and rep.count("RISK"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
