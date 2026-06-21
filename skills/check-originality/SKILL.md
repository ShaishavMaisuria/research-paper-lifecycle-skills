---
name: check-originality
description: Checks a draft for plagiarism, self-plagiarism, text recycling, and uncited near-quotes using several detection methods, and reports overlapping passages so the author can fix them before reviewers or an integrity check do. Use when a researcher says "check for plagiarism", "plagiarism check", "did I copy too much", "self-plagiarism", "text recycling", "am I reusing too much of my own paper", "check originality", "is this too close to the source", or "did I paraphrase closely enough". Compares the draft against sources the user provides (their own prior papers, co-author drafts, suspected sources, or papers fetched on demand), detects internal duplication, and surfaces distinctive phrases to search externally. Honest about scope - it is not iThenticate/Turnitin and has no private publisher corpus; it catches overlap against given sources and publicly findable phrases. Trigger words - plagiarism, self-plagiarism, text recycling, originality, copied, overlap, too close to source, duplicate text.
---

# Check Originality

Multi-method originality check that catches the overlap which actually gets papers desk-rejected or retracted — **before** an editor's integrity scan does.

**Read this honestly and tell the user:** this is **not** iThenticate or Turnitin. It has **no access to any private publisher corpus**, so it cannot guarantee a passage is original against all published literature. What it does reliably is detect overlap against sources you can name or fetch, internal text recycling, and distinctive phrases that are publicly searchable. For a journal's official originality report you still need the publisher's tool — this gets your draft clean *first*.

## When to use

- Before submission, to catch accidental copy-paste and close paraphrase.
- When reusing your own prior work (text recycling / self-plagiarism is a real violation at most venues even though it's "your" text).
- When a co-authored draft may contain a collaborator's verbatim text from elsewhere.
- After heavy AI drafting, to confirm nothing was reproduced verbatim from a source.

## The detection methods (run several — that's what "catch it properly" means)

See [references/detection-methods.md](references/detection-methods.md) for the full method and thresholds.

1. **Source overlap** — shingle (k-gram) comparison against sources the user provides or that `fetch-paper` pulls (open-access only). Reports matched passages + overlap %.
2. **Self-plagiarism / recycling** — near-duplicate passages against the author's own prior papers, and internal duplication within the draft.
3. **Quote & paraphrase integrity** — verbatim spans that lack quotation marks or a citation; paraphrases that stay too close to the source's wording.
4. **Distinctive-phrase external search** — pull the draft's most distinctive long phrases and search the web / Semantic Scholar for verbatim matches the local check can't see.
5. **Common-knowledge vs needs-citation** — flag factual claims presented without a citation that likely need one (hand off specifics to `verify-citations`).

## Process

1. **Gather comparison sources.** Ask the user for: their own prior papers (for self-plagiarism), any suspected sources, and the paper's own cited references (fetch the open-access ones with `fetch-paper`). More sources = a more meaningful check; say so.
2. **Run source + self overlap:**
   ```
   python3 scripts/overlap_check.py --draft paper.tex --against prior1.tex prior2.tex source.txt --self --distinctive 15
   ```
   It prints flagged sources (overlap %), the matched passages, internal near-duplicates, and distinctive phrases. Exit code 2 if anything is flagged.
3. **External pass.** Take the emitted distinctive phrases and search them (web + Semantic Scholar via `find-papers`) for verbatim hits the local pass couldn't see. Record any matches.
4. **Quote/paraphrase review.** For each flagged passage, decide: is it a legitimate quote (then it needs quotation marks + citation), an over-close paraphrase (rewrite in the author's own words), or copied (remove/rewrite + cite). Self-overlap with prior work → flag as recycling and advise disclosure or rewrite.
5. **Report** to `paper-workspace/review/originality-report.md` in the user's paper workspace: each finding with source, the overlapping text, severity, and the fix — plus the explicit scope caveat.

## Output

An originality report listing, per finding: the source, the overlapping passage, overlap %, type (external copy / self-recycle / unquoted / close-paraphrase), severity, and the recommended fix. Always includes the scope/limitations note and a reminder that the publisher's own tool is still authoritative.

## Guardrails

- **Never claim a clean result means the paper is plagiarism-free** — only that no overlap was found against the sources checked. State the limitation every time.
- Comparison sources are processed transiently; never bundle or commit third-party paper text (see `fetch-paper`). Only the user's own papers and open-access sources are fetched.
- Never rewrite a flagged passage to merely *evade* detection while keeping the copied idea uncited — the fix is proper quotation/citation or genuine rephrasing, and surfacing it to the author.
- Self-overlap with the author's own work is reported as an ethics/recycling issue, not silently passed.

## Memory

Uses the shared `.paper-memory/` convention (full spec: [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `lessons.md` for prior originality flags so repeat offenders (a section the author keeps recycling) are checked first.
- **At end:** append durable findings — `date · check-originality · <scope> · finding · fix` — after deduping. A passage recycled across multiple drafts is `recurring`.
- Create `.paper-memory/` on demand; it is local-only, never uploaded.
