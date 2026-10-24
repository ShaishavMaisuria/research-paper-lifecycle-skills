# The `.paper-memory/` convention

This reference contains the memory convention needed by `verify-citations`.
It is included with the skill so that a single-skill installation works
without `paper-profile` or `reflect-and-improve`.

## Location and privacy

`.paper-memory/` lives in the user's paper working directory, alongside the
manuscript and bibliography. It is not part of the installed skill. Create it
on demand when there is a durable lesson to record.

```text
my-paper/
  main.tex
  refs.bib
  .paper-memory/
    lessons.md
```

Memory is local and private by default. Offer to add `.paper-memory/` to the
paper project's `.gitignore`. Do not upload it, send it to an API, or copy it
into a skill repository. Version it only if the user deliberately chooses to.

## Lesson format

Write one Markdown bullet per lesson, on a single line:

```text
- [YYYY-MM-DD] (skill | scope) issue -> recommendation
```

- `date`: the current ISO date, used to identify stale advice.
- `skill`: `verify-citations` for lessons recorded by this skill.
- `scope`: `this-paper` for a draft-specific issue, or `recurring` for a habit
  worth checking across papers.
- `issue -> recommendation`: the observed pattern and the canonical fix.

```markdown
# Paper memory - lessons

- [2026-06-18] (verify-citations | recurring) cites preprints after publication -> prefer the published record when appropriate; confirm from the canonical source
- [2026-06-18] (verify-citations | this-paper) two bibliography years mismatched -> corrected from Crossref records
```

Only record findings supported by the current verification run. Never record
fabricated metadata or treat an old lesson as evidence that an entry is
verified now.

## Reading and appending

At the start, read existing lessons if present. Surface relevant recurring
patterns and avoid repeating advice about issues already resolved. The memory
does not replace a fresh citation check.

When `reflect-and-improve` is available, its helper can append lessons:

```bash
python3 <reflect-and-improve-skill-dir>/scripts/reflect_log.py append \
    --memory .paper-memory --skill verify-citations --scope recurring \
    --issue "arXiv-only entries for papers since published" \
    --rec "prefer the published record; confirm from the canonical source"
```

Replace `<reflect-and-improve-skill-dir>` with that companion skill's installed
directory. The helper is optional. Without it, edit `lessons.md` directly in
the exact one-line format above and apply the hygiene rules below. No other
skill or script is required for this fallback.

## Hygiene

- Before appending, check for the same skill and equivalent issue, ignoring
  case and extra whitespace. Refresh that entry's date instead of duplicating
  it, preserving its `recurring` scope if already set.
- Date every lesson. Keep the most recent 30 `this-paper` entries and all
  `recurring` entries; do not automatically prune recurring lessons.
- Surface applicable recurring patterns at the start of a run.
- Record the pattern and canonical recommendation, not private manuscript
  text or invented citation details.
