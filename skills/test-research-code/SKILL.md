---
name: test-research-code
description: Make research code runnable and repeatable for artifact review by auditing README, dependencies, seeds, entrypoints, data instructions, result commands, and smoke tests with repro_check.py. Use for smoke tests, seed pinning, environment capture, reproducibility checks, or works-on-my-machine cleanup.
---

# Test Research Code

Brings a research **code artifact** to the state an artifact-evaluation committee (ACM AE, USENIX/OSDI/SOSP, SIGMOD ARI, ETAPS, NeurIPS code release) expects: it **runs**, it is **deterministic** enough to reproduce within tolerance, its **environment is captured**, and a stranger can follow the README to the paper's main result. This is the code-side counterpart to `preflight-check` for the PDF.

It is **not** generic software TDD. The goal is one reliable **end-to-end "does it run and roughly reproduce" path**, not exhaustive unit coverage. A focused smoke test that exercises the real pipeline on a tiny input is worth more than 100 mocked unit tests.

## When to use

- The code is **"works on my machine"** and needs to become runnable by a stranger — no pinned env, no seeds, no obvious entrypoint, no sanity test.
- The author asks to **add a smoke/sanity test**, **pin seeds / make it deterministic**, or **capture/pin the environment** before they package or hand it off.
- An artifact-evaluation deadline is approaching and the code is not yet in testable shape — do this engineering first, then route to the siblings below.

**Boundary (avoid overlap).** This skill is the *engineering* step — tests, seeds, env capture. It does **not** own:
- **Packaging, badge taxonomy, archival DOI, anonymization** → [`prepare-artifacts`](../prepare-artifacts/SKILL.md).
- **Whether the produced numbers actually match the paper's tables** → [`verify-results`](../verify-results/SKILL.md).
- **General code cleanup/refactor** → `refactor-research-code`.
When the request is "get my code ready for the artifact track," start here for the run-ability gaps, then hand off; don't re-do their work.

## Inputs

- A path to the **research-code directory** (the repo or a subfolder with training/eval scripts, etc.).
- Optionally, whether review is **double-blind** (so a captured env / added test does not leak author identity).
- Optionally `.paper-memory/profile.yml` for positioning (a `system`/`dataset` contribution leans harder on a reusable, well-tested artifact; an `empirical` one on deterministic re-runs).

## Process

1. **Read memory first.** Read `.paper-memory/lessons.md` (and `profile.yml` if present) so you don't re-flag what the author already fixed and you lead with their `recurring` habits. See [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md).

2. **Confirm scope.** Ask whether review is double-blind (if not stated) so nothing added — a captured env, a test fixture, a notebook — leaks identity. If the author is targeting a specific artifact track, note that **badge offerings and the separate artifact deadline must be re-verified live against the venue's current Call for Artifacts** because they change per venue per year — but that resolution lives in [`prepare-artifacts`](../prepare-artifacts/SKILL.md). Here, just make the code testable; don't restate the badge taxonomy. Background context (badge families, the post-2020 Reproduced/Replicated swap) is in [`references/artifact-standards.md`](references/artifact-standards.md) for awareness, not for asserting a current rule.

3. **Audit the repo (deterministic).** Run the bundled script — do not hand-grep:
   ```
   python3 scripts/repro_check.py <code-dir>          # text report
   python3 scripts/repro_check.py <code-dir> --json   # machine-readable
   ```
   It reports six essentials — **README, ENV (deps, pinned?), SEED, ENTRYPOINT, DATA, RESULTS_CMD** — as OK / WARN / MISSING, plus whether any tests exist. This is the **external, measurable signal** the rest of the work is grounded in; do not substitute your own judgment of "looks reproducible". Exit code: 0 clean, 1 missing essential, 2 usage error.

4. **Close the gaps, in this order** (each maps to a script finding and to [`references/repro-essentials.md`](references/repro-essentials.md)):
   - **ENV** — write/repair the dependency manifest and **pin exact versions**. `pip freeze > requirements.txt`, an `environment.yml`, or a `Dockerfile` that pins a base image. Unpinned deps are the single most common reason an evaluator cannot rebuild. Capture the OS/CUDA/hardware the results were produced on.
   - **SEED** — set and **record** seeds for every RNG in play (`random`, `numpy`, framework — `torch.manual_seed` + `torch.use_deterministic_algorithms(True)`, `PYTHONHASHSEED`). Document residual nondeterminism (GPU atomics, data-loader workers) honestly rather than hiding it.
   - **ENTRYPOINT** — provide one obvious command (`make reproduce`, `run.sh`, `python -m pkg`, a `__main__` guard) that runs the pipeline end to end.
   - **SMOKE/SANITY TEST** — add a minimal test that runs the real pipeline on a tiny/synthetic input and asserts it completes and produces a sane shape/value. See the template in [`references/smoke-tests.md`](references/smoke-tests.md). One end-to-end smoke test beats broad unit coverage here.
   - **DATA** — give exact instructions to obtain inputs (download script, or "no external data"), with the source and a checksum where possible.
   - **RESULTS_CMD** — put in the README a short **table of reported results and, per result, the exact command that produces it** (the ML Code Completeness item). Note expected runtime and that numbers should match *within tolerance*, not bit-for-bit.

5. **Re-run `repro_check.py`** until essentials are OK (or consciously WARN). Set an explicit **stop condition** — all essentials non-MISSING, or a hard cap of ~3 fix passes — rather than polishing open-endedly.

6. **Hosting & anonymization (advise, never act).**
   - **Archival hosting (Zenodo/SWHID, version-vs-concept DOI, the USENIX no-bare-GitHub rule)** is owned by [`prepare-artifacts`](../prepare-artifacts/SKILL.md). Do **not** resolve it here — once the code is testable, flag "next step: package + deposit via prepare-artifacts" and stop.
   - **Double-blind**: if the repo is reviewed blind, anything you add (env file, fixture, notebook) must not reintroduce identity. Anonymization itself routes to `anonymize-paper` / `prepare-artifacts`; flag it, don't do a half job inline.

7. **Write the report and checklist** to `paper-workspace/submission/artifact-repro-checklist.md` and append to `paper-workspace/INDEX.md`. Lead with what's done, then the ranked gap list, each tied to a `repro_check.py` finding and a concrete fix.

## Output

A reviewable `paper-workspace/submission/artifact-repro-checklist.md`: the audit table (six essentials, OK/WARN/MISSING), the smoke-test you added or recommended, the env-capture command run, the seeds pinned, and the data/reproduce instructions — plus any actual files written into the author's repo (a `tests/test_smoke.py`, a pinned `requirements.txt`, a `Makefile`/`run.sh`). Every gap cites the script finding it came from. The checklist ends with a one-line handoff to `prepare-artifacts` (packaging/badge/DOI) and `verify-results` (do the numbers match) — it does not duplicate their work.

## Adapt to your discipline

This targets CS artifact tracks (ACM/USENIX/SIGMOD/ML). For other fields: swap the env-capture for your stack's lockfile (`renv.lock` for R, `Manifest.toml` for Julia, `conda` for bioinformatics), and swap the seed/test idioms for your framework's. Badge/venue mapping is `prepare-artifacts`'s job, not this skill's — here, "testable + deterministic + env captured" is field-agnostic.

## Guardrails

- **Never run anything destructive, and never run untrusted experiment code to "prove" it works without the author's say-so.** `repro_check.py` is static and read-only by design (no execution, no network). Running the artifact end-to-end is the author's call and may need a sandbox/GPU.
- **A passing checklist is necessary, not sufficient.** Do not tell the author the artifact "will earn the badge" or "is reproducible" — those are the *committee's* findings against the live CFA, and "reproduce" everywhere means *within a tolerance that doesn't change the paper's claims*, never bit-exact. Use necessary-not-sufficient language.
- **Don't fabricate results or commands.** The reproduce command must be one that actually exists in the repo; if it doesn't run, say so.
- **Anonymization-aware**: for double-blind review, never expose author identity through the repo, commit history, or notebook metadata.
- It checks, scaffolds, and explains; it **does not submit** the artifact or mint a DOI on the author's behalf.
- `references/` files stay one level deep; keep this file under 500 lines.

## Memory

Uses the shared `.paper-memory/` convention (full spec: [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `lessons.md` to skip already-fixed gaps and lead with `recurring` habits (e.g. "you tend to ship unpinned deps — checking that first"); read `profile.yml` for contribution type so the badge target is right.
- **At end:** append one dated entry per recurring gap, in the canonical format, via `reflect-and-improve`'s `reflect_log.py`:
  ```
  python3 ../reflect-and-improve/scripts/reflect_log.py append \
      --memory .paper-memory --skill test-research-code --scope recurring \
      --issue "experiment scripts ship without seed setting" \
      --rec "set random/numpy/framework seeds + PYTHONHASHSEED every artifact"
  ```
- Create `.paper-memory/` on demand; offer to add it to `.gitignore`; local-only, never uploaded.
