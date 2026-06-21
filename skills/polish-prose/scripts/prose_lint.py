#!/usr/bin/env python3
"""Deterministic LLM-tell and hedging linter for the polish-prose skill.

Scans academic prose (a .tex file, a plain-text/.md file, or stdin) for:

  RISK  leftover chatbot artifacts ("As an AI language model", "Certainly!
        Here is...", "[insert X]") — these read as pasted assistant output
        and several venues treat undisclosed LLM text as a desk-reject.
  WARN  LLM-tell vocabulary and filler phrases (delve, leverage, "it is
        worth noting that", "plays a crucial role"...), double hedges
        ("may potentially"), overclaiming boosters ("clearly",
        "undoubtedly"), passive-voice contribution statements ("a novel
        method is proposed in this paper"), connective stacking
        (Moreover/Furthermore-initial paragraphs in a row), high
        connective or em-dash density, repeated "not only...but also".
  INFO  density statistics (hedges, passives, vague openers, "significant"
        without statistics, sentence/paragraph rhythm) for human judgment.

Findings are CANDIDATES for a human/agent edit pass, never auto-replace
targets: domain terms can look like tells ("leverage scores", "robust
statistics"). Math, verbatim/listing environments, BibTeX keys, labels,
and URLs are masked before matching.

Usage:
    python3 prose_lint.py <main.tex|draft.txt|-> [--strict] [--json]

Exit codes: 0 ok; 1 with --strict when any RISK or WARN finding remains;
2 bad input.
"""

import argparse
import json
import re
import sys

import texprose

# ---------------------------------------------------------------------------
# lexicons
# ---------------------------------------------------------------------------

CHATBOT_ARTIFACTS = [
    r"\bas an ai(?: language)? model\b",
    r"\bas of my (?:last )?knowledge cutoff\b",
    r"\bknowledge cutoff\b",
    r"\bi hope this helps\b",
    r"\bcertainly[!,]? here (?:is|are)\b",
    r"\bhere(?:'s| is) (?:a|an|the) (?:revised|updated|polished|improved|rewritten) (?:version|draft|text)\b",
    r"\bregenerate response\b",
    r"\[insert [^\]\n]{1,60}\]",
    r"\bi (?:cannot|can't) (?:provide|assist|help with)\b",
    r"\blet me know if you\b",
]

# (regex, display-name) — single words and stock phrases that read as LLM
# output when they pile up. Each hit is one WARN with the line number.
TELL_PATTERNS = [
    (r"\bdelv(?:e|es|ed|ing)\b", "delve"),
    (r"\bdelve deeper\b", "delve deeper"),
    (r"\bleverag(?:e|es|ed|ing)\b", "leverage (verb)"),
    (r"\bharness(?:es|ed|ing)? the\b", "harness the ..."),
    (r"\bshowcas(?:e|es|ed|ing)\b", "showcase"),
    (r"\bunderscor(?:e|es|ed|ing)\b", "underscore"),
    (r"\bboast(?:s|ed|ing)?\b", "boast"),
    (r"\bunveil(?:s|ed|ing)?\b", "unveil"),
    (r"\bembark(?:s|ed|ing)?\b", "embark"),
    (r"\bpivotal\b", "pivotal"),
    (r"\bmultifaceted\b", "multifaceted"),
    (r"\bholistic(?:ally)?\b", "holistic"),
    (r"\bseamless(?:ly)?\b", "seamless"),
    (r"\bgroundbreaking\b", "groundbreaking"),
    (r"\bcutting[- ]edge\b", "cutting-edge"),
    (r"\bgame[- ]chang(?:er|ing)\b", "game-changing"),
    (r"\bever[- ]evolving\b", "ever-evolving"),
    (r"\brich tapestry\b|\btapestry of\b", "tapestry"),
    (r"\bin the realm of\b|\brealm of\b", "realm of"),
    (r"\bin the landscape of\b|\blandscape of\b", "landscape of"),
    (r"\bin today'?s\b", "in today's ..."),
    (r"\bit is worth noting that\b", "it is worth noting that"),
    (r"\bit is important to note that\b", "it is important to note that"),
    (r"\bit should be noted that\b", "it should be noted that"),
    (r"\bplays? a (?:crucial|vital|key|pivotal|critical) role\b",
     "plays a crucial role"),
    (r"\ba wide range of\b", "a wide range of"),
    (r"\ba myriad of\b", "a myriad of"),
    (r"\bstands? as a testament\b|\btestament to\b", "testament to"),
    (r"\bpav(?:e|es|ed|ing) the way\b", "paving the way"),
    (r"\bshed(?:s|ding)? (?:new )?light on\b", "shed light on"),
    (r"\bat the forefront of\b", "at the forefront of"),
    (r"\bgarner(?:s|ed|ing)? (?:significant|considerable|increasing|much) attention\b",
     "garnered significant attention"),
    (r"\bin recent years,? there has been\b", "in recent years, there has been"),
    (r"\bwith that being said\b", "with that being said"),
    (r"\bat the end of the day\b", "at the end of the day"),
    (r"\bneedless to say\b", "needless to say"),
    (r"\bcrucial(?:ly)?\b", "crucial"),
]

CONNECTIVES = ("Moreover", "Furthermore", "Additionally", "Consequently",
               "Notably", "Importantly", "Hence", "Thus")

DOUBLE_HEDGES = [
    r"\b(?:may|might|could|can)\s+(?:potentially|possibly|perhaps|conceivably)\b",
    r"\b(?:potentially|possibly|perhaps)\s+(?:may|might|could)\b",
    r"\b(?:seems?|appears?)\s+to\s+(?:suggest|indicate|imply)\b",
    r"\bit is possible that\b[^.!?]*\b(?:may|might|could)\b",
    r"\bmay\s+be\s+able\s+to\s+potentially\b",
]

BOOSTERS = [
    r"\bclearly\b", r"\bobviously\b", r"\bundoubtedly\b", r"\bcertainly\b",
    r"\bdefinitely\b", r"\bdramatically\b", r"\bdrastically\b",
    r"\bremarkably\b", r"\bincredibly\b", r"\bimmensely\b",
    r"\bof course\b", r"\bit is well[- ]known that\b",
]

HEDGE_WORDS = (r"\b(?:may|might|could|likely|possibly|potentially|arguably|"
               r"somewhat|relatively|suggests?|indicates?|appears?|seems?|"
               r"to some extent)\b")

PASSIVE_CONTRIB = (r"\b(?:is|are|was|were|has been|have been)\s+"
                   r"(?:proposed|presented|introduced|described|developed|"
                   r"designed|evaluated|investigated|conducted|demonstrated)\b")
THIS_PAPER = r"\bthis (?:paper|work|article|study)\b|\bherein\b"
PASSIVE_GENERIC = (r"\b(?:is|are|was|were|been|being)\s+"
                   r"[a-z]+(?:ed|own|ken|aged)\b")

NOT_ONLY = r"\bnot only\b[^.!?]{0,140}?\bbut also\b"
VAGUE_OPENER = (r"(?:(?<=[.!?])\s+|\A)\s*(?:There (?:is|are|was|were)|"
                r"It is)\b")

# density thresholds (per 1000 words) — documented, deterministic
CONNECTIVE_WARN_RATE = 8.0
CONNECTIVE_WARN_MIN = 5
EMDASH_WARN_RATE = 5.0
EMDASH_WARN_MIN = 4


class Report:
    def __init__(self):
        self.findings = []  # dicts: severity, tag, line, message

    def add(self, sev, tag, line, msg):
        self.findings.append(
            {"severity": sev, "tag": tag, "line": line, "message": msg})

    def count(self, sev):
        return sum(1 for f in self.findings if f["severity"] == sev)


def scan_lines(rep, plines):
    artifact_res = [re.compile(p, re.I) for p in CHATBOT_ARTIFACTS]
    tell_res = [(re.compile(p, re.I), name) for p, name in TELL_PATTERNS]
    dh_res = [re.compile(p, re.I) for p in DOUBLE_HEDGES]
    booster_res = [re.compile(p, re.I) for p in BOOSTERS]
    pc_re = re.compile(PASSIVE_CONTRIB, re.I)
    tp_re = re.compile(THIS_PAPER, re.I)
    no_re = re.compile(NOT_ONLY, re.I)

    not_only_hits, booster_count = [], 0
    seen_tells = {}
    for ln, text in plines:
        if not text.strip():
            continue
        low = text
        for rx in artifact_res:
            m = rx.search(low)
            if m:
                rep.add("RISK", "chatbot-artifact", ln,
                        "leftover assistant text %r — delete; undisclosed "
                        "LLM output is a desk-reject trigger at several "
                        "venues" % m.group(0).strip())
        for rx, name in tell_res:
            for m in rx.finditer(low):
                seen_tells.setdefault(name, []).append(ln)
        for rx in dh_res:
            m = rx.search(low)
            if m:
                rep.add("WARN", "double-hedge", ln,
                        "double hedge %r — keep one hedge, drop the other"
                        % m.group(0).strip())
        for rx in booster_res:
            m = rx.search(low)
            if m:
                booster_count += 1
                rep.add("WARN", "booster", ln,
                        "overclaiming booster %r — evidence, not adverbs, "
                        "carries the claim; cut it or cite the evidence"
                        % m.group(0).strip())
        if pc_re.search(low) and tp_re.search(low):
            rep.add("WARN", "passive-contribution", ln,
                    "passive-voice contribution statement — rewrite as an "
                    "active claim ('We propose ...') and say what is new")
        for m in no_re.finditer(low):
            not_only_hits.append(ln)

    # tells: one finding per distinct tell, with all line numbers
    for name in sorted(seen_tells):
        lns = seen_tells[name]
        rep.add("WARN", "llm-tell", lns[0],
                "LLM-tell %r (x%d, line%s %s) — see references/llm-tells.md "
                "for rewrite patterns; keep it only if it is a domain term"
                % (name, len(lns), "s" if len(lns) > 1 else "",
                   ", ".join(str(x) for x in lns)))

    sev = "WARN" if len(not_only_hits) >= 2 else "INFO"
    for ln in not_only_hits:
        rep.add(sev, "not-only-but-also", ln,
                "'not only ... but also' — fine once; repeated use is a "
                "tell. State the two facts plainly")
    return booster_count


def scan_densities(rep, plines, n_words):
    text = texprose.joined_prose(plines)
    per_k = (lambda n: (n * 1000.0 / n_words) if n_words else 0.0)

    # sentence-initial connectives
    conn_re = re.compile(r"(?:(?<=[.!?])\s+|\A)(%s)\b[, ]"
                         % "|".join(CONNECTIVES))
    conn_n = len(conn_re.findall(text))
    if conn_n >= CONNECTIVE_WARN_MIN and per_k(conn_n) > CONNECTIVE_WARN_RATE:
        rep.add("WARN", "connective-density", None,
                "%d sentence-initial connectives (%.1f/1000 words; threshold "
                "%.0f) — Moreover/Furthermore/Additionally stacking is the "
                "classic structural tell; delete most, the logic survives"
                % (conn_n, per_k(conn_n), CONNECTIVE_WARN_RATE))
    elif conn_n:
        rep.add("INFO", "connective-density", None,
                "%d sentence-initial connectives (%.1f/1000 words)"
                % (conn_n, per_k(conn_n)))

    # consecutive connective-opening paragraphs
    paras = texprose.paragraphs(plines)
    open_re = re.compile(r"^\s*(%s)\b" % "|".join(CONNECTIVES))
    run = []
    for start_ln, ptext in paras:
        if open_re.match(ptext.strip()):
            run.append(start_ln)
        else:
            if len(run) >= 2:
                rep.add("WARN", "connective-stacking", run[0],
                        "%d consecutive paragraphs open with a connective "
                        "(lines %s) — vary or drop the openers"
                        % (len(run), ", ".join(str(x) for x in run)))
            run = []
    if len(run) >= 2:
        rep.add("WARN", "connective-stacking", run[0],
                "%d consecutive paragraphs open with a connective (lines %s) "
                "— vary or drop the openers"
                % (len(run), ", ".join(str(x) for x in run)))

    # em-dashes
    em_n = text.count("—") + len(re.findall(r"(?<!-)---(?!-)", text))
    if em_n >= EMDASH_WARN_MIN and per_k(em_n) > EMDASH_WARN_RATE:
        rep.add("WARN", "emdash-density", None,
                "%d em-dashes (%.1f/1000 words; threshold %.0f) — heavy "
                "em-dash interruption reads as generated text; keep a few, "
                "recast the rest as separate sentences or commas"
                % (em_n, per_k(em_n), EMDASH_WARN_RATE))
    elif em_n:
        rep.add("INFO", "emdash-density", None,
                "%d em-dashes (%.1f/1000 words)" % (em_n, per_k(em_n)))

    # hedge inventory
    hedge_n = len(re.findall(HEDGE_WORDS, text, re.I))
    rep.add("INFO", "hedge-inventory", None,
            "%d hedge terms (%.1f/1000 words) — calibrate per "
            "references/hedging-and-claims.md: results and limitations keep "
            "their hedges, contributions and definitions lose them"
            % (hedge_n, per_k(hedge_n)))

    # significant without statistics
    sig_n = len(re.findall(r"\bsignificant(?:ly)?\b", text, re.I))
    stat_n = len(re.findall(r"\bstatistical(?:ly)?\b|p\s*[<=]|p-value",
                            text, re.I))
    if sig_n and not stat_n:
        rep.add("INFO", "significant", None,
                "'significant' used %d time(s) with no statistical-test "
                "language anywhere — many reviewers reserve the word for "
                "statistical significance; prefer 'substantial'/'large' or "
                "report the test" % sig_n)

    # passive density (heuristic)
    pas_n = len(re.findall(PASSIVE_GENERIC, text, re.I))
    sents = texprose.split_sentences(text)
    if sents:
        rep.add("INFO", "passive-density", None,
                "~%d passive constructions over %d sentences (heuristic) — "
                "passives are fine for methods, weak for contributions"
                % (pas_n, len(sents)))

    # vague openers
    vag_n = len(re.findall(VAGUE_OPENER, text))
    if vag_n >= 3:
        rep.add("INFO", "vague-opener", None,
                "%d sentences open with 'There is/are' or 'It is' — give "
                "those sentences a real subject" % vag_n)

    # sentence + paragraph rhythm
    if sents:
        lens = [len(s.split()) for s in sents]
        longest = max(lens)
        avg = sum(lens) / float(len(lens))
        msg = ("%d sentences; mean %.1f words, longest %d"
               % (len(sents), avg, longest))
        if longest > 60:
            rep.add("WARN", "sentence-length", None,
                    msg + " — split sentences over 60 words")
        else:
            rep.add("INFO", "sentence-length", None, msg)
    para_sents = [len(texprose.split_sentences(p)) for _, p in paras]
    para_sents = [n for n in para_sents if n >= 2]
    if len(para_sents) >= 6:
        mean = sum(para_sents) / float(len(para_sents))
        var = sum((n - mean) ** 2 for n in para_sents) / len(para_sents)
        if mean and (var ** 0.5) / mean < 0.25:
            rep.add("INFO", "uniform-paragraphs", None,
                    "%d paragraphs all have ~%.0f sentences — uniform "
                    "paragraph rhythm is a structural tell; merge or split "
                    "where the content allows" % (len(para_sents), mean))

    return {"words": n_words, "sentences": len(sents),
            "connectives": conn_n, "em_dashes": em_n, "hedges": hedge_n}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint academic prose for LLM tells, chatbot artifacts, "
        "hedging problems, and passive contribution statements. Prints a "
        "Markdown report with line numbers. Findings are candidates for a "
        "human edit pass, never auto-replace targets.")
    parser.add_argument("source",
                        help="main .tex file, plain text (.txt/.md), or - "
                        "for stdin")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any RISK or WARN finding")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    args = parser.parse_args(argv)

    try:
        raw, label = texprose.read_source(args.source)
    except texprose.SourceError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    tex = texprose.is_tex(args.source, raw)
    plines = texprose.prose_lines(raw, tex=tex)
    n_words = texprose.word_count(plines)
    if not n_words:
        sys.stderr.write("error: no prose found in %s (is the file all "
                         "preamble/comments?)\n" % label)
        return 2

    rep = Report()
    scan_lines(rep, plines)
    stats = scan_densities(rep, plines, n_words)

    order = {"RISK": 0, "WARN": 1, "INFO": 2}
    rep.findings.sort(key=lambda f: (order[f["severity"]],
                                     f["line"] if f["line"] else 0))
    if args.json:
        print(json.dumps({"source": label, "stats": stats,
                          "findings": rep.findings,
                          "summary": {s: rep.count(s)
                                      for s in ("RISK", "WARN", "INFO")}},
                         indent=2))
    else:
        print("# Prose lint — %s\n" % label)
        print("- %d words of prose scanned (math/verbatim/preamble masked)"
              % n_words)
        print("\n## Findings\n")
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
