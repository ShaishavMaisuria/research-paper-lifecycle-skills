<h1 align="center">Research Paper Lifecycle Skills</h1>

<p align="center">
  Agent skills for getting a research paper from CFP to camera-ready.
  Search, cite, tailor, submit, rebut, publish, and present with less
  deadline panic.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue.svg"></a>
  <img alt="Skills: 24" src="https://img.shields.io/badge/skills-24-2f6feb.svg">
  <img alt="Package: Agent Skills" src="https://img.shields.io/badge/package-Agent%20Skills-111827.svg">
  <img alt="No bundled papers" src="https://img.shields.io/badge/paper%20content-not%20bundled-green.svg">
</p>

---

## Why This Exists

Drafting is only one part of publishing a paper. The surrounding mechanics are
where researchers lose time: CFP requirements, page limits, anonymization,
rebuttals, camera-ready forms, talk slots, poster dimensions, and citation
cleanup.

`research-paper-lifecycle-skills` gives your agent a structured playbook for
that full lifecycle.

## At A Glance

| Stage | What the skills help with |
|---|---|
| Discover | Find papers, fetch legal open-access copies, study exemplars. |
| Write | Draft abstracts, literature reviews, related work, and polished prose. |
| Verify | Check BibTeX entries, duplicates, metadata mismatches, and likely fabrications. |
| Submit | Parse CFPs, select venues, tailor the paper, anonymize, and run preflight checks. |
| Respond | Triage reviews and draft rebuttals for common response formats. |
| Publish | Prepare camera-ready checklists and final-file linting. |
| Present | Build talks, scripts, Q&A drills, and posters. |

---

## Quick Start

### Agent Skills CLI

For Codex, Cursor, Gemini CLI, and compatible agents:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills
```

See what is included:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --list
```

Install a single skill:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --skill preflight-check
```

Install globally:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills -g
```

### Claude Code Plugin

```text
/plugin marketplace add ShaishavMaisuria/research-paper-lifecycle-skills
/plugin install paper-submission@research-paper-lifecycle-skills
```

Available plugin bundles:

```text
paper-search
paper-writing
paper-submission
paper-presenting
```

## Usage Examples

Once installed, ask your agent for the workflow you need:

```text
Run a preflight check on my LaTeX paper for this CFP.
```

```text
Verify this refs.bib file and flag fabricated or mismatched citations.
```

```text
Turn these reviews into a rebuttal plan with severity and effort.
```

```text
Make a 12-minute talk script from this deck and give me a cut list.
```

For venue-aware skills, provide a local venue profile or ask the agent to
create one from the live CFP with `parse-cfp` or `add-venue-profile`.

---

## Available Skills

### Paper Search

| Skill | Use it when you need to... |
|---|---|
| `find-papers` | Search scholarly metadata across key-free providers. |
| `fetch-paper` | Resolve a DOI or arXiv ID to a legal open-access copy. |
| `verify-citations` | Check BibTeX entries for fabrication, mismatch, duplicates, and retractions. |
| `study-exemplars` | Study strong venue papers from legal open copies fetched on demand. |

### Paper Writing

| Skill | Use it when you need to... |
|---|---|
| `write-abstract` | Draft, rewrite, lint, or register a venue-aware abstract. |
| `literature-review` | Build a structured, citation-grounded review. |
| `draft-related-work` | Position related work against verified references. |
| `polish-prose` | Tighten academic prose without changing technical claims. |
| `polish-tables-figures` | Improve LaTeX tables, figures, captions, crossrefs, and palettes. |

### Paper Submission

| Skill | Use it when you need to... |
|---|---|
| `parse-cfp` | Turn a CFP URL into a local requirements profile. |
| `select-venue` | Rank possible venues and tracks for a paper. |
| `tailor-to-venue` | Plan retargeting, page cuts, template changes, and anonymization. |
| `preflight-check` | Run deterministic desk-reject checks before submission. |
| `anonymize-paper` | Sweep double-blind leaks and support camera-ready reversal. |
| `triage-reviews` | Turn raw reviews into a priority matrix. |
| `write-rebuttal` | Draft responses for OpenReview, one-page PDFs, and R&R cycles. |
| `simulate-reviewers` | Run a venue-calibrated mock review. |
| `prepare-camera-ready` | Walk accepted papers through final-file requirements. |
| `plan-submission` | Build a backwards timeline from submission deadlines. |
| `add-venue-profile` | Create a local venue profile from a live CFP. |

### Paper Presenting

| Skill | Use it when you need to... |
|---|---|
| `make-slides` | Build or lint a talk deck sized to the actual slot. |
| `write-talk-script` | Write timed speaker notes and a cut list. |
| `rehearse-qa` | Practice hostile and curious audience questions. |
| `make-poster` | Plan and lint posters plus 2-minute and 5-minute pitches. |

---

## Common Workflows

### Before Submission

```text
parse-cfp -> tailor-to-venue -> anonymize-paper -> preflight-check
```

Use this path when you are aiming at a specific CFP and want to catch
formatting, page-limit, template, anonymization, and policy issues before the
paper leaves your machine.

### When Reviews Arrive

```text
triage-reviews -> write-rebuttal -> preflight-check
```

Use this path to split reviews into concerns, prioritize the response, draft a
budget-aware rebuttal, and lint the revised paper.

### After Acceptance

```text
prepare-camera-ready -> make-slides -> write-talk-script -> rehearse-qa
```

Use this path for final-file requirements, presentation prep, timing, and Q&A.

---

## How Skills Are Structured

Each skill is self-contained:

| Path | Contents |
|---|---|
| `SKILL.md` | Trigger description, workflow instructions, output expectations, guardrails. |
| `references/` | Supporting checklists, rubrics, conventions, and examples. |
| `scripts/` | Deterministic helper scripts for linting, checking, parsing, timing, or validation. |

The helper scripts are designed to do the mechanical work; the agent uses the
skill instructions to decide when and how to run them.

---

## Project Principles

| Principle | What it means |
|---|---|
| Human-led | Skills draft, check, and explain. They do not submit anything. |
| Citation-aware | Writing workflows route new references through verification. |
| Copyright-conscious | Paper content is fetched only from legal open sources, on demand. |
| Venue-skeptical | Profiles and CFP facts can go stale; final rules must be checked live. |
| Lightweight | The repository ships skills and scripts, not paper PDFs or cached metadata. |

---

## Repository Layout

```text
skills/                         24 agent skills
  <skill>/SKILL.md               instructions and guardrails
  <skill>/references/            supporting guidance
  <skill>/scripts/               deterministic helper scripts
.claude-plugin/marketplace.json  plugin bundle manifest
LICENSE                          Apache-2.0 license
NOTICE                           attribution notice
CITATION.cff                     citation metadata
```

---

## Attribution And License

Copyright 2026 Shaishav Maisuria.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

If you redistribute this package or include substantial portions of these
skills in another repository, keep the copyright/license notices and the
[NOTICE](NOTICE) attribution file so the original work is credited.
