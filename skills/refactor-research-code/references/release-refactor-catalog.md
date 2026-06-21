# Release-refactor catalog

The per-category playbook for `refactor-research-code`. For each finding class
the static audit (`scripts/release_audit.py`) reports, this gives: what it is,
**why it matters for a release**, the **risk class** (SAFE / ASK-FIRST /
IDENTITY), and the concrete, behavior-preserving recipe.

The governing rule, repeated because it is the whole job: **clean the repo
without changing the numbers the paper reports.** When a recipe says ASK-FIRST,
the model presents the change and the result-risk and *waits for the author* —
it does not apply it. When unsure, default to ASK-FIRST.

How "behavior preserved" is actually checked: by **re-running** the pipeline (or
the smoke test) and diffing the output against a pre-refactor baseline — never by
the model reading its own diff and judging it fine. That re-run/diff is
`test-research-code` / `verify-results` territory; this skill flags and
coordinates it.

---

## SAFE — mechanical, behavior-preserving (apply on the author's nod)

These cannot change what the code computes.

### layout — README / LICENSE / .gitignore / directory structure
- **README** (the ML Code Completeness item): state what the artifact is, the
  **one command to run the pipeline end to end**, the **exact command that
  reproduces each result** (ideally a results table → command), the
  dependencies, the data instructions, and a short directory map. Adding docs
  changes nothing the code does.
- **LICENSE**: a release without one leaves reuse rights undefined; most
  artifact tracks expect it. Pick with the author (MIT/BSD/Apache-2.0 for code;
  CC-BY/CC0 for data) — never invent a license they didn't choose.
- **.gitignore**: exclude caches, outputs, large blobs, and secrets from the
  release so they don't get shipped.
- **Repo layout**: a flat dump of 10+ scripts at the root → a `src/`/package
  layout with subdirs (`src/`, `configs/`, `scripts/`, `data/`, `results/`).
  *Moving files is mechanical, but it changes import paths* — fix the imports
  and **re-run** to confirm the same output. (The move is safe; a broken import
  is caught immediately by the re-run, not silently.)

### entrypoint (documentation side) — name the one command
- If a runnable entrypoint already exists, **document** it in the README. Pure
  documentation is safe. *Wiring a new entrypoint* (adding a `__main__`, a
  `Makefile` target, a `run.sh`) is structural — verify it invokes the same code
  with the same args and produces the same output before trusting it.

### hygiene — remove junk from the release copy
- Delete `__pycache__/`, `*.pyc`/`*.pyo`, `.DS_Store`, editor swap files
  (`*.swp`), `.ipynb_checkpoints/`, stray `*.log`. These are build/editor
  artifacts; removing them from the release copy changes nothing.
- (Large in-tree data/model blobs are **ASK-FIRST**, below — they may be needed
  at runtime.)

---

## ASK-FIRST — could move the numbers (never apply without explicit OK)

For each: present the finding, the proposed edit, and *the specific way it could
change results*. Apply only on a per-item yes, then re-run + diff.

### dead-code — commented-out blocks, `if False:`/`if 0:`, backup files
- **Why it's risky, not free:** a commented-out block may be a *toggled
  experiment path* the author re-enables; a `*_v2.py`/`*.bak` file may **shadow**
  the live module (Python imports the wrong one depending on `sys.path`), so
  deleting it can change which code actually runs. An `if False:` branch is
  usually dead — *usually*.
- **Recipe:** confirm with the author (and a quick grep for imports/references)
  that nothing reaches it in **any** config, then delete. Version control keeps
  the history — you don't need the commented copy. Re-run after deleting.

### config — hardcoded hyperparameters and absolute/home paths in source
- **Why it's risky:** the point of extraction is to move a value, not change it.
  A single transcription error (`0.003` → `0.03`, `lr` read from the wrong key)
  silently changes results, and config-file precedence/merge order can override
  a value you thought you set.
- **Recipe:** create a `config.yaml` (or argparse flags) and move each literal in
  **unchanged**, with the same default. Keep the *exact* value and type. Re-run
  and diff against the baseline — the numbers must be identical. Absolute/home
  paths (`/home/<you>/data`) become a config/CLI arg with the author's path as a
  documented default, so the repo runs on another machine.

### determinism — seeding, RNG, threads/workers, dtype/precision, order
- **The highest-risk class. Adding determinism *changes* a previously
  nondeterministic run by definition.** Setting a seed on a run that had none
  produces a *different* number than the unseeded run that's in the paper. So:
  - **Never silently add a seed.** Surface that the run is unseeded and ask how
    the author wants to handle it — re-run with a fixed seed and report that
    number, or document the seed used to produce the paper's number, or report a
    mean±std over seeds. This is the author's scientific call.
  - **Time-based seeds** (`seed = int(time.time())`) make the run
    irreproducible; replace with a fixed, recorded seed — but that re-defines the
    run, so coordinate.
  - **Thread/worker count and evaluation order** (`num_workers>0`, `set()`
    iteration used as data, parallel reductions, non-associative float sums) can
    change results run-to-run. Pin them or sort the order — and re-confirm.
  - **dtype/precision** (fp16 ↔ fp32, a different BLAS/CUDA version): never change
    silently; it moves numbers.
  - The mechanics of seeding all RNGs (`random`, `numpy`, framework,
    `PYTHONHASHSEED`, `torch.use_deterministic_algorithms(True)`) and capturing
    the environment belong to **`test-research-code`** — flag here, hand off
    there. Document residual nondeterminism honestly (GPU atomics) rather than
    pretending it's gone.

### hygiene (the risky member) — large in-tree data/model blobs
- A committed checkpoint/dataset bloats the release and the right home is an
  archival host (Zenodo/Software Heritage via `prepare-artifacts`) or a download
  script — **but confirm it isn't needed at runtime** (a fixture the tests load,
  a baseline the eval compares against) before removing it from the tree.

---

## IDENTITY — double-blind leaks (scrub before any blind-review upload)

Surface-level only here; the **deep** sweep (commit history, notebook output
metadata, self-citation phrasing, anonymized mirror) is `anonymize-paper`.

- **Emails / author names / institutions** in source, comments, configs, or
  filenames → scrub or replace with neutral placeholders.
- **Home paths** (`/home/<username>`, `/Users/<username>`) → reveal a username;
  replace with a config arg or a neutral path.
- **`.git` history** → commit author/email identify you even after you edit the
  files. Ship an **anonymized export without `.git`**, or proxy through
  **anonymous.4open.science** (it scrubs owner/org/name + listed terms across
  filenames and contents and refreshes on push).
- Pass the author's identifying terms to the audit with `--names "Jane
  Doe,Example University,ProjectCodename"` so name hits are caught in content and
  filenames.

This is needed only for **blind** review — don't anonymize a non-blind or
single-blind release (it mangles a fine repo). Confirm the blind level first.

---

## What this skill does NOT do (route elsewhere)

| Job | Owner |
|---|---|
| Add smoke/sanity tests, pin seeds, capture env (lockfile/Dockerfile) | `test-research-code` |
| Archival deposit, DOI (version vs concept), SWHID, badge taxonomy, appendix | `prepare-artifacts` |
| Deep paper+repo anonymization, reversible de-anon at camera-ready | `anonymize-paper` |
| Confirm produced numbers match the paper's tables (within tolerance) | `verify-results` |

A clean audit here is *necessary, not sufficient*: it means the repo is tidy and
documented, **not** that it reproduces or earns a badge — those are a re-run and
a committee's call against the live Call for Artifacts.
