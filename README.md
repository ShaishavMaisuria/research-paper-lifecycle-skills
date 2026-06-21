<h1 align="center">Research Paper Lifecycle Skills</h1>

<p align="center">
  Agent skills for getting a research paper from CFP to camera-ready:
  search, citations, abstracts, venue tailoring, preflight checks,
  rebuttals, final files, talks, Q&A, and posters.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue.svg"></a>
  <img alt="Skills: 24" src="https://img.shields.io/badge/skills-24-2f6feb.svg">
  <img alt="Package: Agent Skills" src="https://img.shields.io/badge/package-Agent%20Skills-111827.svg">
  <img alt="No bundled papers" src="https://img.shields.io/badge/paper%20content-not%20bundled-green.svg">
</p>

---

## What This Gives You

Most paper-assistant tools focus on drafting. This package covers the
submission and publication mechanics around the draft:

| Stage | What the skills help with |
|---|---|
| Discover | Find papers, fetch legal open-access copies, study exemplars. |
| Write | Draft abstracts, literature reviews, related work, and polished prose. |
| Verify | Check BibTeX entries, duplicates, metadata mismatches, and likely fabrications. |
| Submit | Parse CFPs, select venues, tailor the paper, anonymize, and run preflight checks. |
| Respond | Triage reviews and draft rebuttals for common response formats. |
| Publish | Prepare camera-ready checklists and final-file linting. |
| Present | Build talks, scripts, Q&A drills, and posters. |

This is a clean release package. It ships the skills and supporting scripts
only. It does not ship venue databases, eval fixtures, examples, internal
research notes, launch plans, cached metadata, PDFs, paper text, abstracts, or
generated artifacts.

When a skill needs a venue profile, create one locally with `parse-cfp` or
`add-venue-profile`, or point the skill at your own local profile.

---

## Install

### Agent Skills CLI

For Codex, Cursor, Gemini CLI, and compatible agents:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills
```

List the skills before installing:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --list
```

Install a single skill:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --skill preflight-check
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

---

## Skill Map

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

## Example Workflows

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

## Design Principles

| Principle | What it means |
|---|---|
| Human-led | Skills draft, check, and explain. They do not submit anything. |
| Citation-aware | Writing workflows route new references through verification. |
| Copyright-conscious | Paper content is fetched only from legal open sources, on demand. |
| Venue-skeptical | Profiles and CFP facts can go stale; final rules must be checked live. |
| Release-safe | This package intentionally avoids internal notes, fixture PDFs, venue databases, and cached metadata. |

---

## Repository Layout

```text
skills/                         24 Agent Skills
  <skill>/SKILL.md               skill instructions
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
