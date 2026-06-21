# Contributing

Thanks for helping improve `research-paper-lifecycle-skills`. The most useful
contributions are clear skill improvements, deterministic helper scripts,
documentation fixes, and small workflow checks that make the released package
easier to trust.

## What belongs here

Good public contributions include:

- New or improved `skills/<skill-name>/SKILL.md` files.
- Small helper scripts under `skills/<skill-name>/scripts/`.
- Supporting public references under `skills/<skill-name>/references/`.
- README, install, integration, and attribution improvements.
- Self-contained GitHub workflows that validate this public package.

Please do not contribute:

- Paper PDFs, copied abstracts, publisher text, or copyrighted corpora.
- Private reviews, unpublished manuscripts, private evals, benchmark fixtures,
  findings, generated caches, venue/profile dumps, or local workspace output.
- Tooling that depends on unreleased private directories.
- Secrets, tokens, account names, private Overleaf links, or credentials.

## Skill guidelines

Each skill should be a normal Agent Skills folder:

```text
skills/<skill-name>/
  SKILL.md
  references/        optional public guidance
  scripts/           optional deterministic helpers
```

`SKILL.md` should:

- Start with valid YAML frontmatter.
- Use a lowercase-hyphen `name` that matches the directory.
- Include a clear third-person `description` explaining what the skill does
  and when an agent should use it.
- State guardrails, especially around citation integrity, copyright, venue
  rules, and human approval.
- Link only to files that are included in the public package.

Scripts should:

- Prefer Python standard library unless there is a strong reason otherwise.
- Be deterministic where possible and exit nonzero on failed checks.
- Avoid bulk-downloading paper content.
- Rate-limit network calls, back off on HTTP 429, and identify the caller when
  contacting public scholarly APIs.

## Before opening a pull request

Run the lightweight checks locally:

```bash
python3 -m py_compile $(find skills -path '*/scripts/*.py')
npx skills add . --list
```

If you changed `README.md`, make sure every relative link points to a file that
exists in this repository.

## Pull request expectations

- Keep changes focused.
- Explain what changed and why.
- Note any skill behavior that changed.
- Include validation output or explain why a check was not run.
- Preserve `LICENSE`, `NOTICE`, and attribution when adapting or redistributing
  substantial parts of this package.

By contributing, you agree that your contribution is submitted under the
project's Apache-2.0 license.
