# Setting up a clean run — and the copilot boundary

A reproduction only means something if it runs from a **pinned, isolated
environment**, not the author's day-to-day shell where stray packages, cached
checkpoints, and environment variables quietly make things "work". This skill
helps build that recipe and hands it to the author. **The author runs anything
heavy** (training, long evals, anything that needs their GPUs/data/credentials).
The skill never installs into a base environment, never runs destructive
commands, and never touches the network on the author's behalf.

## Why a clean room

Reproduction failures cluster in environment drift: an unpinned dependency that
silently upgraded, a checkpoint left in `~/.cache`, a `CUDA_VISIBLE_DEVICES` or
`PYTHONPATH` set in the author's profile, a seed that was never fixed, a data
file present locally but absent from the artifact. A clean environment surfaces
exactly these — which is the point.

## Pick the strongest isolation the artifact supports

In rough order of fidelity:

1. **Container** (`Dockerfile` / `Containerfile` / `Singularity`/`Apptainer`).
   Best fidelity — pins the OS layer too. If the artifact ships one, prefer it.
2. **Conda/mamba env** from `environment.yml` — pins Python + many native libs.
3. **venv + `pip install -r requirements.txt`** (ideally hash-pinned). The
   common ML case; combine with a fresh `PYTHONPATH`.
4. **Lockfile installs** (`poetry install`, `pip-sync`, `uv pip sync`) when a
   lockfile exists — the most reproducible pip path.

The dependency spec `audit_repo.py` found dictates which of these is available.
If none exists, that is itself a finding (an unpinnable environment).

## A recipe to hand the author (they run it)

Present commands for the author to run; do not run them yourself. Sketch:

```sh
# 1. fresh, isolated env (example: venv) — NEVER the base/system env
python3 -m venv .repro-env && . .repro-env/bin/activate
pip install --require-hashes -r requirements.txt   # or the lockfile/conda/container path

# 2. fix nondeterminism the artifact exposes
export PYTHONHASHSEED=0
# set the artifact's documented seed flags, deterministic cudnn, etc.

# 3. run the artifact's OWN tests first — a concrete pass/fail gate
pytest -q            # or: make test / the repo's documented harness

# 4. run the documented reproduce command, capturing metrics to a file
python3 eval.py --config configs/main.yaml --out run.json   # exact cmd from the README
```

Then point `compare_metrics.py` at `run.json` and the confirmed claims ledger.

## Run the artifact's own tests before any metric comparison

The artifact's test suite is an **external, measurable gate** (exit code 0/1) —
exactly the kind of signal verification should hinge on, not the model's sense
that the numbers look plausible. If tests fail, stop and report; comparing
metrics from a broken build is meaningless.

## Nondeterminism: agreement within tolerance, not bit-equality

GPU nondeterminism, data-loader shuffling, and library-version drift make
bit-exact outputs the exception, not the rule — and every badge program asks
only for agreement **within a tolerance that does not change the paper's
claims**. So:

- Fix every seed the artifact exposes and document the ones it does not.
- Set `--rel-tol`/`--abs-tol` in `compare_metrics.py` to the metric's natural
  scale (a 0.1-point accuracy swing is usually fine; a 3-point BLEU gap is not).
- A small, explained gap is a **match**; a gap that would change a ranking, a
  significance claim, or a headline number is a **mismatch** to reconcile.

## The copilot boundary

- **The author runs heavy/credentialed/long work.** Training, multi-hour evals,
  anything needing their data, GPUs, or secrets — guide, do not execute.
- **No installs into the base environment.** Only ever a fresh, named, disposable
  env, and only when the author asks you to.
- **Nothing destructive, nothing networked silently.** No `rm`, no overwriting
  the author's checkpoints, no downloads they did not ask for, no pushes.
- **Never claim a run happened that did not.** If you only set things up, say so;
  report unrun steps as *unverified*, not as passing.

## When a mismatch appears — reconcile, don't smooth over

A `metric/mismatch` ("paper says X, code produces Y") has a small set of usual
causes. Surface them to the author rather than picking one silently
when more than one explanation fits:

- **Stale table** — the paper number predates a code change. Update the table or
  re-run; note which is canonical.
- **Different split/seed/config** — the run used eval where the paper used test,
  or a different seed/hyperparameter. Align the config.
- **Selective reporting** — the paper's number is the best of several runs.
  Report mean ± std (ACL/NeurIPS checklists ask for this anyway).
- **A real bug** in the artifact or the metric code. The most important case to
  catch before reviewers do.

Decide *with* the author which number is correct; never overwrite a paper claim
or invent a reconciliation.
