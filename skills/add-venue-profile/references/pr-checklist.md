# PR checklist — getting a venue profile merged

The contribution flow once the YAML is filled in. Goal: a single-file PR
that a maintainer can merge on provenance alone.

## 1. Validation gates (run all, in order)

From the repo root:

```bash
# Gate 1 — offline schema validation, warnings treated as errors
python3 skills/add-venue-profile/scripts/validate_profile.py \
    venues/conferences/<venue>-<year>.yml --strict

# Gate 2 — the repo-wide validator CI runs (needs PyYAML; skip locally if
# unavailable — gate 1 covers the same contract)
python3 tools/validate_venues.py
```

- Every ERROR must be fixed. No exceptions.
- Every remaining WARN must either be fixed or carry a one-line
  justification in the PR body (e.g. "submission_system `ourown-portal` is
  genuinely new — link in source_urls").
- If the file was hand-edited after validation, validate again.

## 2. Self-review before the diff

- [ ] One profile file in the diff, nothing else (family files are their own
      PR; never touch other venues' files in passing).
- [ ] `verified.date` is today; `confidence` matches how the facts were
      actually obtained; every `source_urls` entry annotated.
- [ ] Verbatim quotes present for: page-limit sentence (per track),
      `llm_policy`, `dual_submission`.
- [ ] No fetched CFP text, HTML dumps, or `.cache/` content staged.
- [ ] Copy-forward case: diff against last year's file reviewed line by
      line; every surviving value re-verified, not just the dates.
- [ ] No fabricated aliases — unverified alias fields are `null` with a
      "searched, not found" comment.

## 3. Branch and commit

```bash
git checkout -b venue/<venue>-<year>
git add venues/conferences/<venue>-<year>.yml
git commit -m "venues: add <venue>-<year> profile (verified <date>)"
```

One commit is ideal; if iterating, squash before the PR. Refresh PRs use
`venues: refresh <venue>-<year> (<what changed>)`.

## 4. PR body template

```markdown
## Venue profile: <NAME> <YEAR>

- **CFP:** <cfp_url>
- **Verified:** <date>, confidence `<confidence>`
- **Pages checked:** <bulleted source_urls with what each supplied>

### Highlights a reviewer should spot-check
- <page limit + incl/excl wording>
- <deadline timezone (call out if NOT AoE)>
- <blind level + submission system>
- <anything unusual: rebuttal format, required sections, rail deviation>

### Validation
- `validate_profile.py --strict`: <clean | N warnings, justified below>
- <justification per remaining warning, one line each>

### Not verified / left null
- <field>: <why — e.g. "no LLM policy anywhere on the site as of <date>">
```

## 5. Sending it

Show the user the final diff and the exact command:

```bash
gh pr create --title "venues: add <venue>-<year> profile" --body-file <body.md>
```

**Run it only when the user explicitly says to.** Preparing the PR is the
skill's job; pushing branches and opening PRs on someone's GitHub account is
the user's decision. The same applies to `git push`.

## 6. What CI checks (so the PR predicts green)

- `.github/workflows/validate.yml` runs the repo validators: schema shape,
  required fields, family existence, `verified:` completeness.
- Freshness tooling flags profiles whose `verified.date` is older than the
  current CFP cycle — a fresh date with honest confidence is what keeps the
  profile out of that report.

## 7. After the merge

- A profile is a snapshot, not a promise. If the venue amends its CFP
  mid-cycle (deadline slips are common), a follow-up refresh PR with an
  updated `verified:` block is the fix — never an untracked local edit.
- Encourage the user to watch the venue's announcements channel through the
  submission deadline; downstream skills always re-verify against `cfp_url`,
  but a current profile saves everyone that round trip.
