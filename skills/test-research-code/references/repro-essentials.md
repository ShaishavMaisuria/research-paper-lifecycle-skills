# The six reproducibility essentials (and how to close each gap)

These are the items `repro_check.py` audits, mapped to what artifact committees
and code-release checklists actually require. The script reports each as **OK /
WARN / MISSING**; this file is the fix playbook. The ordering is the order to fix
in — ENV and SEED unblock everything else.

The north star is the **ML Code Completeness Checklist** (paperswithcode, used by
NeurIPS), which is exactly five items:
1. **Specification of dependencies** (`requirements.txt` / `environment.yml` /
   `setup.py`).
2. **Training code.**
3. **Evaluation code.**
4. **Pre-trained models** (where applicable).
5. **README with a table of results AND the precise command to reproduce each.**

Empirically, repos hitting all five had far higher community adoption. Our six
essentials cover these plus **seeds** (determinism) and **data instructions**.

---

## 1. ENV — capture the environment, pinned

**Why:** unpinned dependencies are the **#1 reason an evaluator cannot rebuild**
the runtime. "It worked last month" fails when a transitive dep ships a new
major version.

**Fix:**
- Python: `pip freeze > requirements.txt` (pins `==`), or a Poetry/uv lockfile,
  or `conda env export > environment.yml`. For a hard guarantee, a **Dockerfile**
  pinning the base image + a frozen requirements file.
- R: `renv::snapshot()` → `renv.lock`. Julia: commit `Manifest.toml`.
- **Record the host**: OS, Python/CUDA version, GPU model, RAM. Put it in the
  README. Reviewers need to know what hardware produced the numbers.
- **WARN vs OK**: a `requirements.txt` with bare package names (no `==`) is WARN
  — it's present but won't reliably rebuild. Pin it.

## 2. SEED — make it deterministic enough

**Why:** without fixed seeds, every run differs and "results don't match" is the
evaluator's first complaint. You don't need bit-exactness (the badge tolerance
allows drift), but you need *controlled* randomness.

**Fix — seed every RNG in play and record the value:**
```python
import os, random, numpy as np
SEED = 0
os.environ["PYTHONHASHSEED"] = str(SEED)
random.seed(SEED)
np.random.seed(SEED)
# PyTorch:
import torch
torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
torch.use_deterministic_algorithms(True)   # surfaces nondeterministic ops
# TensorFlow:
# import tensorflow as tf; tf.keras.utils.set_random_seed(SEED)
```
- **Be honest about residual nondeterminism**: GPU atomics, multi-worker data
  loaders, and some cuDNN kernels are not fully deterministic. Document it ("CPU
  results are deterministic; GPU results vary by <0.3% due to atomic
  accumulation") rather than hiding it. Honest disclosure beats a false
  bit-exact promise.

## 3. ENTRYPOINT — one command that runs the pipeline

**Why:** the evaluator should not have to reverse-engineer call order. Give them
a single front door.

**Fix:** a `Makefile` (`make reproduce`), a `run.sh`, a `python -m yourpkg`
console-script entrypoint, or at minimum a `__main__` guard on the top-level
script. Document it as the first command in the README.

## 4. SMOKE / SANITY TEST — prove it runs end to end

This is the heart of the skill — see [`smoke-tests.md`](smoke-tests.md) for
templates. A research smoke test runs the **real** pipeline on a **tiny**
input (synthetic or a 10-row sample) and asserts it completes and produces a
sane shape/value. It is the cheap, fast proxy for "the artifact functions"
without a full multi-GPU run. **One end-to-end smoke test > broad unit
coverage** for artifact evaluation.

## 5. DATA — say exactly how to get the inputs

**Why:** an artifact that needs data the evaluator can't obtain is not
exercisable.

**Fix:**
- A `download_data.sh` / `scripts/get_data.py`, or clear README instructions with
  the **source URL and a checksum** (so the evaluator can confirm they got the
  right bytes).
- If data is large, host it on Zenodo/Hugging Face and link it; don't commit GBs
  to git.
- If there is **no external data** (fully synthetic), say so explicitly — that's
  a valid, passing state.
- Sensitive/PII data: provide a generator or a small public sample plus an access
  procedure, never raw restricted data in a public repo.

## 6. RESULTS_CMD — the table + the command per result

**Why:** this is the single highest-leverage README item (item 5 of the ML Code
Completeness Checklist) and what an evaluator follows to reproduce.

**Fix:** in the README, a short **table of the paper's reported results**, and
**for each, the exact command** that produces it, plus expected runtime:

```markdown
| Result        | Paper | Command                                  | ~Runtime |
|---------------|-------|------------------------------------------|----------|
| Table 2, F1   | 0.873 | `python eval.py --ckpt ckpts/base.pt`    | 5 min    |
| Fig 3 curve   |  —    | `python plot.py --logs runs/ && make fig`| 1 min    |
```
State that numbers should match **within tolerance**, not bit-for-bit.

---

## What the script does NOT check (do these by hand)

- Whether the code **actually runs** (the script is static/read-only — running it
  is the author's call, possibly in a sandbox).
- Whether reported numbers **actually reproduce** (that's the committee's job,
  within tolerance).
- **License** presence/compatibility (artifacts need a license for reuse — add an
  OSI license; check dataset/model licenses are compatible). Add a `LICENSE`.
- **Archival hosting** and **anonymization** — see
  [`artifact-standards.md`](artifact-standards.md); route the scrub to
  `anonymize-paper`.
