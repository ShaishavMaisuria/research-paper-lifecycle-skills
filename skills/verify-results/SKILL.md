---
name: verify-results
description: Check whether reported paper metrics are consistent with outputs from the local code artifact. Use for result reproduction checks, artifact evaluation, reproducibility checklists, code-versus-paper audits, table or claim metric comparisons, and badge-readiness review.
---

# Verify Results

Close the loop between what the paper *claims* and what the artifact *produces*.
This skill helps the author confirm their reported numbers reproduce: it locates
the experiment code, helps stand up a clean/sandboxed run, runs the artifact's
own tests, and does a **consistency audit** — comparing the metrics the run
produces against the paper's tables and claims, within a tolerance that does not
change the paper's conclusions. It reports mismatches (paper says X, code
produces Y) and missing reproduction steps, and audits the artifact against
current reproducibility-badge expectations.

It is a **copilot**: it sets up and guides, and the author runs anything heavy
(training, long evals) in their own environment. It never fabricates a number,
never executes destructive commands, and never claims a result was
independently reproduced — a clean audit means *consistent*, not *reproduced*.

## When to use

- "Do my results reproduce?" / "Does my code match the paper's tables?"
- "Check my reproducibility" / "verify my experiments" / "reproduce my numbers".
- Prepping an artifact for an evaluation track (ACM AE, USENIX, OSDI, SOSP,
  SIGMOD ARI, ETAPS, NeurIPS/ICML/ACL reproducibility).
- Filling a reproducibility checklist (NeurIPS Paper Checklist, ACL Responsible
  NLP, ML Code Completeness) and wanting an honest read on each item.
- After a results table changes and you need to confirm the code still produces it.

## Inputs

1. The **artifact / experiment code** (a directory; a repo URL the author has
   cloned locally — this skill reads local files, it does not clone for you).
2. The **paper** `.tex` whose tables/claims are being checked (or the specific
   `\input` file that holds the results table).
3. The **target venue's artifact track**, if any — its current Call for
   Artifacts decides which badges exist and what hosting they require.
4. Optionally, a **metrics file** from a prior run (JSON/CSV) to compare without
   re-running.

## Process

This skill follows plan → set up → run (author) → audit, with the verification
step grounded in **external, measurable signals** (test pass/fail, a numeric
diff against a file the run produced) — never the model's own judgment that the
numbers "look right".

1. **Locate the experiment code and the claims.** Confirm where the code lives
   and which paper tables/claims it is supposed to produce. Extract the paper's
   reported numbers into a reviewable **claims ledger**:

   ```
   python3 scripts/extract_claims.py paper.tex --ledger claims.json
   ```

   The ledger is a *starting point, not ground truth* — walk it with the author:
   drop spurious numbers (years, citation counts, the `top-1=1` from a `\\` row),
   fix metric labels, mark each kept claim `confirmed`. The author is the author.

2. **Audit the artifact for completeness and badge-readiness.**

   ```
   python3 scripts/audit_repo.py path/to/artifact --blind <single|double|none>
   ```

   This inventories the repo against the **ML Code Completeness Checklist**
   (dependencies, training code, evaluation code, pretrained models, a README
   with a results table + exact reproduce command), checks for the artifact's
   **own tests**, flags **missing reproduction steps**, and warns when the only
   hosting is a GitHub/personal URL (badge tracks want an **archival DOI** —
   Zenodo/FigShare/Dryad/Software Heritage). It **runs nothing**. Under
   `--blind double` it also scans the README for de-anonymizing emails/URLs.

   This is a **fast pre-comparison gate**, not the deep version. Don't re-do work
   the sibling skills own: making the code run-ready/deterministic and the
   repro-essentials audit belong to [`test-research-code`](../test-research-code/SKILL.md);
   packaging, the badge taxonomy, and the archival DOI belong to
   [`prepare-artifacts`](../prepare-artifacts/SKILL.md); the deep double-blind
   sweep belongs to [`anonymize-paper`](../anonymize-paper/SKILL.md) /
   [`refactor-research-code`](../refactor-research-code/SKILL.md). The unique job
   of *this* skill is the **consistency audit** (step 5) — does the run's output
   match the paper's tables. Use `audit_repo.py` only to confirm there is enough
   to run before comparing, then hand deep gaps to the owner skill.

3. **Re-verify the badge rules against the live Call for Artifacts — mandatory.**
   Badge offerings change **per venue, per year** (e.g. one cycle a venue offers
   all three badges; another, only *Artifacts Available*). The terms *Reproduced*
   vs *Replicated* were **swapped by ACM after 2020-05-14** — pre-2020 papers use
   the inverse meanings. Do not state any badge requirement, hosting rule, or
   deadline from memory: fetch the venue's current CFA and confirm it with a
   source URL and access date.
   Reproducibility standards and the badge taxonomy are in
   [references/repro-standards.md](references/repro-standards.md) — treat it as a
   map of what to verify, not as current truth.

4. **Set up a clean, sandboxed run — then hand the author the commands.** A
   reproduction must run from a pinned, isolated environment, not the author's
   polluted shell. Help build the recipe (fresh venv/conda/container from the
   dependency spec; seeds fixed; the exact command from the README), but **the
   author runs anything heavy**. See
   [references/sandbox-and-run.md](references/sandbox-and-run.md). First have the
   author run the **artifact's own tests** (`pytest`, `make test`, the repo's
   harness) — a concrete pass/fail gate before any metric comparison. Never run
   destructive commands; never auto-install into the author's base environment.

5. **Consistency audit: compare produced metrics to the paper.** Point the run's
   output (a metrics JSON/CSV the author generated) at the confirmed ledger:

   ```
   python3 scripts/compare_metrics.py --ledger claims.json --metrics run.json \
       --rel-tol 0.01 --abs-tol 0.005 [--map test_acc=c1 ...]
   ```

   It reports **MATCH / MISMATCH / MISSING** per claim with a tolerance that
   *does not change the paper's claim* — **never bit-exact** (ACM, SIGMOD ARI,
   and ETAPS all require only agreement within tolerance / "similar behavior").
   Tune `--rel-tol`/`--abs-tol` to the metric's scale and use `--map` when names
   differ. A `metric/no-produced-value` is a **missing repro step** (the paper
   reports it; the run didn't emit it).

6. **Decide the verification outcome with explicit stop conditions.** Map each
   compared claim to: **match** (consistent within tolerance), **mismatch**
   (paper says X, code produces Y — reconcile: stale table? wrong seed? different
   split? selective reporting?), or **unverified** (could not run / metric not
   emitted — say so, never paper over it). Do **not** loop indefinitely: stop
   when all confirmed claims are match-or-explained, or escalate to the author
   when a mismatch needs a judgment call (which number is right). Escalation is a
   feature, not a failure (working-principle #4).

7. **Write the reproduction report** to
   `paper-workspace/review/reproduction-report.md` and append a line to
   `paper-workspace/INDEX.md`. Lead
   with the verdict (N of M claims consistent), then the mismatch table (claim,
   paper value, produced value, |diff|, likely cause), the artifact-completeness
   checklist with each item's status, missing repro steps, and badge-readiness
   per the live CFA. State plainly what was and was not actually run.

## Output

A `reproduction-report.md`: verdict (consistent claims / total) → mismatch
table (paper vs produced, with diffs and suspected cause) → artifact
completeness checklist (5 items + tests + hosting) → missing reproduction steps
→ badge-readiness against the live CFA (with source links and dates). Plus the
machine-readable `claims.json` ledger and the `--json` outputs if requested.

## Adapt to your discipline

The metric heuristics target ML/systems papers (accuracy, F1, BLEU, latency,
speedup...). For other fields, the ledger is just `{metric, value}` records —
hand-author it for any quantitative claim (effect sizes, p-values, runtimes) and
`compare_metrics.py` still does the tolerance-aware audit. Non-code artifacts
(datasets, proofs) use steps 2–3 only.

## Related skills (don't duplicate them)

This skill's one unique job is the **consistency audit**: does the run's output
match the paper's reported numbers. Everything adjacent has an owner — hand it off
rather than re-doing it.

| Need | Owner skill |
|---|---|
| Make the code run-ready/deterministic; repro-essentials audit | [`test-research-code`](../test-research-code/SKILL.md) |
| Packaging, badge taxonomy, archival DOI, artifact appendix | [`prepare-artifacts`](../prepare-artifacts/SKILL.md) |
| Release cleanup of a research repo | [`refactor-research-code`](../refactor-research-code/SKILL.md) |
| Deep, reversible double-blind sweep | [`anonymize-paper`](../anonymize-paper/SKILL.md) |
| Each *written claim* traces to evidence (not just numbers) | [`verify-claims`](../verify-claims/SKILL.md) |

`audit_repo.py` here is a lightweight pre-comparison gate, not a replacement for
`test-research-code`'s `repro_check.py` or `prepare-artifacts`' badge work.

## Guardrails

- **Consistency is not reproduction.** A clean audit says the produced numbers
  *match the paper within tolerance* — it does **not** mean the result was
  independently reproduced or replicated. Never claim a badge is earned; that is
  a committee's call against the live CFA.
- **Never fabricate a number, a metric, or a "passing" run.** If a run did not
  happen or a metric was not emitted, report it as unverified — do not infer it.
- **Don't trust the model's own read of correctness.** The verification signal
  is external: a test exit code, a numeric diff against a file the author
  produced. Self-reflection validates hallucinations — do not use it as the gate.
- **Run nothing heavy or destructive.** The author runs training/long evals in
  their own sandbox; this skill sets up and guides. No installs into the base
  env, no `rm`, no network side effects.
- **Anonymization-aware.** Under double-blind, flag identifying content in the
  artifact and prefer an anonymized mirror; never expose the author's identity.
- **Never submit** the paper or the artifact to any system on the author's behalf.

## Memory

Uses the shared `.paper-memory/` convention (full spec:
[`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `.paper-memory/lessons.md` (and `profile.yml` for the
  contribution type — a `dataset`/`system` paper is judged on the artifact more
  heavily). Lead with any `recurring` repro habits (e.g. "tables drift from the
  code between drafts", "unpinned dependencies").
- **At end:** append each finding worth remembering as one dated entry in the
  shared format `- [YYYY-MM-DD] (verify-results | <scope>) issue ->
  recommendation` (use `reflect-and-improve`'s `reflect_log.py append`, which
  dedupes and dates). Tag a cross-paper habit `recurring`, a one-off `this-paper`.
- Create `.paper-memory/` on demand and offer to add it to `.gitignore`. It is
  local-only; never upload it or copy it into this repo.
