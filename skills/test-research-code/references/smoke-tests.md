# Smoke / sanity tests for research artifacts

A smoke test for a research artifact is **not** a unit test suite. Its one job is
to answer the artifact-evaluation question — **"does this run end to end and
produce something sane?"** — fast and cheaply, on a tiny input, so an evaluator
(or CI) gets a green/red signal in seconds instead of a multi-hour GPU run.

This is what *Functional* badging actually checks: documented, consistent,
complete, **exercisable**. A focused smoke test that drives the real pipeline is
worth more than 100 mocked unit tests that never touch it.

## Principles

- **Exercise the real pipeline, not a mock.** The point is to catch "it doesn't
  even import" and "the entrypoint crashes," which mocks hide.
- **Tiny, deterministic input.** A synthetic array, 10 rows of the real data, or
  1 training step on 1 batch. Seed it (see
  [`repro-essentials.md`](repro-essentials.md)).
- **Assert shape/sanity, not exact paper numbers.** The smoke test confirms the
  machinery turns; reproducing the *numbers within tolerance* is a separate,
  heavier run the README documents.
- **Fast.** Target seconds. If it needs a GPU, gate it (`@pytest.mark.gpu`) and
  provide a CPU-only path that still exercises the code.
- **No network in the test** where avoidable; if data must be fetched, point at a
  committed tiny sample.

## Template — pytest, end-to-end on synthetic input

```python
# tests/test_smoke.py  — runs the real pipeline on a tiny synthetic input.
import numpy as np
import pytest

SEED = 0


def _tiny_dataset():
    rng = np.random.default_rng(SEED)
    X = rng.standard_normal((16, 4)).astype("float32")
    y = (X[:, 0] > 0).astype("int64")
    return X, y


def test_imports():
    """The package imports without side effects."""
    import yourpkg  # noqa: F401


def test_train_one_step_runs():
    """One training step on a tiny batch completes and returns finite loss."""
    from yourpkg.train import train_step, build_model
    X, y = _tiny_dataset()
    model = build_model(in_dim=X.shape[1], seed=SEED)
    loss = train_step(model, X, y)
    assert np.isfinite(loss), "loss should be finite"


def test_eval_produces_sane_metric():
    """The eval path runs and yields a metric in a valid range."""
    from yourpkg.eval import evaluate, build_model
    X, y = _tiny_dataset()
    model = build_model(in_dim=X.shape[1], seed=SEED)
    metric = evaluate(model, X, y)
    assert 0.0 <= metric <= 1.0, f"metric out of range: {metric}"


def test_determinism():
    """Two seeded runs on the same input agree (within float tolerance)."""
    from yourpkg.eval import evaluate, build_model
    X, y = _tiny_dataset()
    m1 = evaluate(build_model(in_dim=X.shape[1], seed=SEED), X, y)
    m2 = evaluate(build_model(in_dim=X.shape[1], seed=SEED), X, y)
    assert abs(m1 - m2) < 1e-6, "seeded runs should match"


@pytest.mark.gpu
def test_gpu_path():
    """Optional: exercise the CUDA path if a GPU is present."""
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("no GPU")
    # ... run one step on cuda:0 ...
```

## Template — no test framework, plain stdlib script

For repos that don't use pytest, a runnable script is fine and is itself an
entrypoint signal:

```python
# tests/smoke.py — exit 0 on success, nonzero on failure.
import sys


def main() -> int:
    try:
        import yourpkg
        out = yourpkg.run(steps=1, n=16, seed=0)   # tiny end-to-end run
    except Exception as e:                          # noqa: BLE001
        print(f"SMOKE FAIL: {e}", file=sys.stderr)
        return 1
    ok = out is not None and getattr(out, "shape", (1,))[0] > 0
    print("SMOKE PASS" if ok else "SMOKE FAIL: empty output")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

Wire it into the entrypoint: `make smoke` → `python tests/smoke.py`, and put it
in CI so a green badge tracks "the artifact still runs."

## What a smoke test is NOT

- It is **not** proof the paper's numbers reproduce — that's the README's
  documented full run, validated by the committee within tolerance.
- It is **not** comprehensive coverage. Don't gold-plate it into a unit suite;
  the marginal value past "the pipeline turns end to end" is low for AE.
- It should **not** silently pass on a no-op. Assert that real work happened
  (finite loss, non-empty output, metric in range).
