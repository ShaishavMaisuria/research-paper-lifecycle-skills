---
name: polish-prose
description: De-AI-ifies and tightens academic prose without changing any technical claim. Use when a researcher says "this sounds like ChatGPT / AI-written", "humanize my paper", "remove the AI words", "too many delves and leverages", "polish my writing", "tighten the prose", "fix my hedging", "too many Moreover/Furthermore", "make my contributions active", or "keep my terminology consistent". Runs deterministic stdlib linters — prose_lint.py (leftover chatbot artifacts, LLM-tell vocabulary, connective stacking, em-dash density, double hedges, overclaiming boosters, passive contribution statements) and terminology_check.py (dataset/data set/data-set variants, acronym discipline, -ise/-ize mixing, glossary enforcement) — then drives a section-by-section edit pass using rewrite catalogs and the venue family's register norms. Numbers, results, claims, and citations are never altered; the venue's AI-use disclosure policy is surfaced and respected, never dodged.
---

# Polish Prose

Turn an AI-flavored or overwrought draft into prose that reads like a
careful researcher wrote it — without moving a single number, claim, or
citation. Reviewers now pattern-match the LLM register (delve/leverage
vocabulary, Moreover-stacked paragraphs, em-dash chains, uniform hedging),
and a leftover "Certainly! Here is..." or "[insert citation]" is a
desk-reject-grade embarrassment. This skill finds all of it
deterministically, then guides a disciplined human-in-the-loop rewrite:
expression changes, content does not.

## When to use

- "My paper sounds like ChatGPT wrote it" / "humanize this" / "de-AI-ify"
- "Remove the AI words" / "it keeps saying delve and leverage"
- "Tighten / polish my writing" / "this is too wordy"
- "Fix my hedging" — overclaimed contributions or drowned-in-maybes results
- "Make my contribution statements active" ("a method is proposed..." →
  "We propose...")
- "Is my terminology consistent?" (dataset vs data set, acronym discipline,
  British vs American spelling)
- Called before `preflight-check` as part of the final submission pass, or
  after heavy drafting with any LLM assistant.

## Inputs

1. The draft: a `.tex` file (preamble/math/verbatim are masked
   automatically), a `.md`/`.txt` file, or pasted text via stdin.
2. Optional: the venue profile `venues/conferences/<venue>-<year>.yml`
   (schema in `venues/schema.yml`) — supplies the venue family for register
   norms and `review.llm_policy` for AI-use disclosure duties.
3. Optional: a project glossary (`canonical term = variant | variant` per
   line) if the team has already standardized terminology.

## Process

1. **Freeze the technical content first.** Build the no-touch inventory
   before editing anything: every number and unit, every `\cite` key, every
   stated result, dataset name, and system name. Snapshot it:

   ```
   grep -oE '[0-9][0-9.,]*\s*(%|\\%|ms|s|GB|MB|x|×)?' draft.tex | sort | uniq -c > /tmp/numbers-before.txt
   ```

   The same command must produce identical output after the edit pass
   (step 9). If polishing would require changing a claim, stop and tell
   the user — that is a content decision, not a style edit.

2. **Resolve the venue register and the LLM policy.** If a venue profile is
   given, read its `family` (register norms per
   [references/venue-register.md](references/venue-register.md)) and
   `review.llm_policy`. **Re-verify the LLM policy against the live
   `cfp_url` before relying on it** — these policies churn every cycle.
   Tell the user plainly: polishing AI-assisted text does not remove a
   disclosure obligation. If the venue requires an AI-use statement, help
   write an honest one; never frame this skill as a way to avoid it.

3. **Run the linters** (Python 3, stdlib only, no network):

   ```
   python3 scripts/prose_lint.py main.tex
   python3 scripts/terminology_check.py main.tex --allow GPS,SDK
   ```

   Both accept `.tex`, plain text, or `-` for stdin; `--json` for
   machine-readable output; `--strict` to exit 1 while findings remain.
   Exit codes: 0 ok, 1 strict-failure, 2 bad input. `--allow` skips the
   undefined-acronym check for acronyms your community treats as
   universally known; `--glossary FILE` enforces a terminology table.
   Findings are candidates with line numbers, never auto-replacements —
   domain terms can look like tells ("leverage scores", "robust
   statistics").

4. **Kill RISK findings immediately.** Chatbot artifacts ("As an AI
   model...", "Certainly! Here is...", "[insert X]") are deleted or filled
   in, full stop. Several venues treat undisclosed LLM output as a
   desk-reject trigger; an unfilled placeholder is also a missing citation
   — route real citation needs through `verify-citations`, never invent
   one.

5. **Edit pass A — lexical and structural tells.** Work section by section
   with [references/llm-tells.md](references/llm-tells.md) open. For each
   WARN: keep it if it is a domain term or genuinely the best word
   (occasional use is fine — density is the tell, not existence);
   otherwise apply the rewrite pattern. Break Moreover/Furthermore
   paragraph chains by deleting the connective — if the logic no longer
   flows, the paragraph order was wrong, which is worth knowing. Recast
   surplus em-dashes as separate sentences or commas. Propose edits as
   diffs (old → new, with line numbers) and apply only with the user's
   approval.

6. **Edit pass B — hedging and claims.** Calibrate per
   [references/hedging-and-claims.md](references/hedging-and-claims.md):
   contributions, definitions, and completed actions lose their hedges
   ("we propose", not "we attempt to propose"); interpretations,
   generalizations, and limitations keep exactly one honest hedge; double
   hedges collapse to one; boosters (clearly, undoubtedly) are cut — the
   evidence carries the claim or nothing does. Rewrite passive
   contribution statements as active, specific claims that say what is
   new. Never strengthen a claim beyond what the paper's own evidence
   supports, and never weaken a result the user measured.

7. **Edit pass C — terminology.** Turn every `compound-variant`,
   `spelling-mix`, and acronym finding into a one-line decision: present
   the variants with counts, let the user pick the canonical form (default:
   the majority form; spelling per the venue register), then apply it
   everywhere. Record decisions in a glossary file and re-run:

   ```
   python3 scripts/terminology_check.py main.tex --glossary glossary.txt
   ```

   Fix acronym discipline: define once at first use, expand consistently,
   drop definitions never used again.

8. **Edit pass D — venue register.** Apply the family norms from
   [references/venue-register.md](references/venue-register.md): person
   and voice conventions, tense discipline, spelling convention,
   contraction policy, and the register differences between ML, systems,
   HCI, and LNCS venues. When no profile is given, default to consistent
   American spelling and the conventions already dominant in the draft.

9. **Verify nothing technical moved.** Re-run both linters (clean, or each
   remaining finding consciously accepted by the user); re-run the step-1
   number snapshot and diff it — any difference is a bug in the edit pass
   and must be reverted; confirm the `\cite` count and keys are unchanged.
   Present a short before/after table for every sentence whose claim
   strength changed in pass B so the user signs off on each one.

10. **Optional gate for CI or pre-submission:** `prose_lint.py main.tex
    --strict` exits 1 while any RISK/WARN remains — useful as a final
    check alongside `preflight-check`.

## Output

- Two lint reports (Markdown or `--json`) with line-numbered findings.
- Proposed edits as diffs, applied only with approval, one pass at a time.
- A terminology decision table plus a reusable `glossary.txt`.
- A verification note: numbers/citations diff clean, claim-strength changes
  enumerated, remaining accepted findings listed.

## What this skill is not

- **Not an AI-detector evasion tool.** The goal is prose quality and an
  honest register, not beating a classifier. If the user's actual goal is
  to hide LLM use from a venue that requires disclosure, decline that goal,
  show the venue's `llm_policy`, and offer to draft the disclosure instead.
- **Not a content editor.** It does not restructure arguments, add
  citations, or change what the paper claims — `tailor-to-venue` handles
  repositioning, `write-abstract` handles the abstract, `verify-citations`
  handles references.

## Relationship to other skills

- `write-abstract` — abstract-specific structure and venue metadata norms.
- `preflight-check` — the desk-reject gate; run it after polishing.
- `anonymize-paper` — identity leaks; this skill does not touch them.
- `verify-citations` — any citation need surfaced here routes there.

## Adapt to your discipline

The tell lexicons are field-agnostic; the register is not. Fork and adjust
[references/venue-register.md](references/venue-register.md) for your
field's journals (many mandate British spelling or third-person voice),
extend the `--allow` acronym list for your community's alphabet soup, and
add discipline-specific tells to `prose_lint.py`'s `TELL_PATTERNS` table.

## Guardrails

- Never alter numbers, results, claims, citations, or technical statements;
  expression only. Verify with the step-9 diff, every time.
- Never auto-apply lexicon findings — every WARN is a judgment call and
  domain terms ("leverage scores") are innocent.
- Never fabricate text for "[insert X]" placeholders; ask the user for the
  real content or route citations through `verify-citations`.
- Never present the result as "undetectable" or "human-written"; never help
  evade an AI-use disclosure requirement — surface `review.llm_policy` and
  re-verify it against the live `cfp_url`.
- Never submit anything to any system on the user's behalf.
- Quote at most the flagged line in reports; never reproduce large portions
  of the paper in outputs.

## Memory

This skill uses the shared `.paper-memory/` convention in the user's paper
directory (full spec: [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `.paper-memory/lessons.md` and `profile.yml`. Use
  `writing_preferences` (style signature, spelling, voice) to set the target
  register, and lead with any `recurring` prose habits already recorded (e.g.
  "you habitually write passive contribution statements") so you watch for
  them first instead of re-explaining them.
- **At end:** append durable findings in the shared format `- [YYYY-MM-DD]
  (polish-prose | <scope>) pattern -> recommendation` (via
  `reflect-and-improve`'s `reflect_log.py append`, which dedupes and dates). A
  tell or habit seen across drafts is `recurring`; a one-off fix is
  `this-paper`. Do not log routine one-shot edits.
- Create `.paper-memory/` on demand if absent and offer to add it to the
  project `.gitignore`. It is local-only; never upload it or copy it into this
  repo.
