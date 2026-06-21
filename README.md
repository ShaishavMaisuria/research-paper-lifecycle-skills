<p align="center">
  <img src="assets/hero.svg" alt="research-paper-lifecycle-skills - from idea to camera-ready" width="100%">
</p>

<h1 align="center">research-paper-lifecycle-skills</h1>

<p align="center">
  <b>Agent skills that take a research paper from idea to camera-ready: search,
  write, verify, submit, rebut, publish, and present with less deadline panic.</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache-2.0"></a>
  <a href="#find-the-skill-you-need"><img src="https://img.shields.io/badge/skills-41-blue.svg" alt="41 skills"></a>
  <img src="https://img.shields.io/badge/package-Agent%20Skills-111827.svg" alt="Agent Skills package">
  <img src="https://img.shields.io/badge/paper_content-not_bundled-success.svg" alt="no bundled paper content">
  <a href="https://agentskills.io"><img src="https://img.shields.io/badge/standard-agentskills.io-black.svg" alt="agentskills.io"></a>
</p>

---

## Why this exists

Drafting is only one part of publishing a paper. The surrounding mechanics are
where researchers lose time: CFP requirements, page limits, anonymization,
rebuttals, camera-ready forms, artifact packaging, talk slots, poster
dimensions, and citation cleanup.

`research-paper-lifecycle-skills` gives compatible agents a structured playbook
for that full lifecycle. It works for any discipline with public CFPs or author
instructions, while the deepest current examples and testing are still in
Computer Science conference and journal workflows.

**Copilot, not pilot:** skills draft, check, and explain. You decide, you stay
the author, and nothing is submitted anywhere on your behalf.

## Quick start

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills
```

See what is included:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --list
```

Install one skill:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --skill preflight-check
```

Install into a specific supported agent target:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent codex
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent cursor
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent gemini
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent claude-code
```

Claude Code plugin marketplace:

```text
/plugin marketplace add ShaishavMaisuria/research-paper-lifecycle-skills
/plugin install paper-submission@research-paper-lifecycle-skills
```

Public plugin bundles currently exposed in `.claude-plugin/marketplace.json`:
`paper-search`, `paper-writing`, `paper-submission`, and `paper-presenting`.
Use the Agent Skills CLI above to install the complete 41-skill package.

## At a glance

| Stage | What the skills do for you |
|---|---|
| **Profile** | Capture your paper's positioning and local lessons so later passes stay calibrated. |
| **Discover** | Find papers, fetch legal open-access copies, and study strong exemplars. |
| **Write** | Draft abstracts, literature reviews, related work, polished prose, and Overleaf round-trips. |
| **Verify** | Check citations, originality, claims-vs-evidence, and desk-reject risks. |
| **Submit** | Parse CFPs, pick venues and tracks, tailor, anonymize, and plan the deadline. |
| **Artifacts** | Test, verify, refactor, and package research code for reproducibility review. |
| **Respond** | Triage reviews and write rebuttals in common venue formats. |
| **Publish** | Prepare camera-ready files, slides, scripts, Q&A drills, and posters. |

## What it solves

| The moment | What goes wrong | Skill |
|---|---|---|
| The night before the deadline | One page over, a blind-review leak, a missing checklist, or a stale CFP assumption can desk-reject the paper. | [`preflight-check`](skills/preflight-check) |
| Building the bibliography | LLMs and manual BibTeX edits produce plausible but wrong references. | [`verify-citations`](skills/verify-citations) |
| "Is this good enough?" | You need strengths, risks, and fixes before reviewers decide for you. | [`assess-paper`](skills/assess-paper), [`simulate-reviewers`](skills/simulate-reviewers) |
| The prose reads AI-ish | The writing needs to sound like the author without moving claims or citations. | [`polish-prose`](skills/polish-prose), [`match-style`](skills/match-style) |
| The paper is too long or too thin | You need a section-by-section length map and a resize plan that protects claims, results, and citations. | [`fit-page-limit`](skills/fit-page-limit) |
| Your paper lives on Overleaf | The `.tex` is not local, so other skills need a safe bridge in and back out. | [`work-with-overleaf`](skills/work-with-overleaf) |
| Reviews came back | Raw reviews need triage before a rebuttal draft. | [`triage-reviews`](skills/triage-reviews), [`write-rebuttal`](skills/write-rebuttal) |
| Accepted, now what? | Camera-ready, artifact, slides, scripts, and Q&A all become separate deadlines. | [`prepare-camera-ready`](skills/prepare-camera-ready), [`prepare-artifacts`](skills/prepare-artifacts), [`make-slides`](skills/make-slides) |

## Usage examples

Ask in plain language. The right skill triggers itself.

| You ask | You get |
|---|---|
| "Will this get desk-rejected at an IEEE conference? Check my `main.tex` against this CFP." | A preflight report with IEEE template, page-limit, anonymization, checklist, and policy risks tied to live requirements. |
| "Verify `refs.bib` and flag fabricated or mismatched citations." | Canonical-record checks across scholarly metadata sources, with duplicates and suspicious entries surfaced. |
| "How good is my paper? One honest report." | A paper-health report with strengths first, ranked fixes, integrity gates, and no acceptance prediction. |
| "Humanize this section but do not change any claims." | Cleaner academic prose with AI-tell phrasing removed, while numbers, results, and citations stay fixed. |
| "I'm one page over the limit; what should I cut?" | A section-budget map plus a ranked compression plan that preserves the paper's core evidence. |
| "My paper is on Overleaf; pull it local, run checks, help me sync back." | A safe Git/GitHub/ZIP path, a local working copy, reviewed diffs, and confirm-first sync. |
| "Show me an HTML dashboard of progress." | A local `paper-workspace/dashboard.html` with stage progress, artifact links, and recent activity. |
| "Take my idea and experiments toward a submission for venue X." | `orchestrate-paper` plans the pipeline, invokes specialist skills, checkpoints with you, and records what is done, next, and blocked. |

### Worked example

```text
I have a method and results for streaming-trajectory indexing.
Get it submission-ready for SIGSPATIAL.
```

1. `paper-profile` records contribution type, target audience, constraints, and
   risk appetite.
2. `find-papers`, `literature-review`, and `verify-citations` build a verified
   reference base.
3. `write-abstract`, `draft-related-work`, `polish-prose`, and `match-style`
   shape the draft without changing claims.
4. `parse-cfp`, `tailor-to-venue`, `anonymize-paper`, and `preflight-check`
   verify live requirements and desk-reject risks.
5. `simulate-reviewers`, `benchmark-paper`, and `assess-paper` produce the
   review-readiness pass.
6. `render-workspace-html` gives a local dashboard of the resulting
   `paper-workspace/` outputs.

## How it works

<p align="center">
  <img src="assets/lifecycle.svg" alt="The research-paper lifecycle and the skills at each stage" width="100%">
</p>

1. **Skills**: one folder per task. `SKILL.md` tells the agent when to use the
   skill; `references/` and `scripts/` hold supporting guidance and
   deterministic checks.
2. **Live verification**: venue facts, artifact rules, and citation claims can
   go stale. Venue-aware skills build or re-check rules from the live CFP or
   author instructions, double-check desk-reject-class facts when possible, and
   treat unsourced rules as unverified.
3. **Local paper workspace**: generated reports go into `paper-workspace/`;
   preferences and lessons live in `.paper-memory/`. Both stay with the user's
   paper, not in this package.

## Find the skill you need

Search by what you want to do, then open the linked `SKILL.md` for the exact
trigger rules, process, guardrails, references, and scripts.

| Stage | Skill | Use it for |
|---|---|---|
| Coordinate | [`orchestrate-paper`](skills/orchestrate-paper/SKILL.md) | Run the whole lifecycle with checkpoints. |
| Coordinate | [`assess-paper`](skills/assess-paper/SKILL.md) | Get one overall paper-health report. |
| Coordinate | [`paper-profile`](skills/paper-profile/SKILL.md) | Capture paper positioning and preferences. |
| Coordinate | [`reflect-paper`](skills/reflect-paper/SKILL.md) | Run separate Researcher and Writer reflection passes. |
| Coordinate | [`reflect-and-improve`](skills/reflect-and-improve/SKILL.md) | Check whether a generated change actually improved. |
| Coordinate | [`render-workspace-html`](skills/render-workspace-html/SKILL.md) | Render a browser dashboard of outputs. |
| Discover | [`find-papers`](skills/find-papers/SKILL.md) | Search scholarly metadata and proceedings. |
| Discover | [`fetch-paper`](skills/fetch-paper/SKILL.md) | Fetch legal open-access copies. |
| Discover | [`study-exemplars`](skills/study-exemplars/SKILL.md) | Study strong papers from a target venue. |
| Discover | [`literature-review`](skills/literature-review/SKILL.md) | Build a structured, citation-grounded review. |
| Write | [`write-abstract`](skills/write-abstract/SKILL.md) | Draft, revise, or lint a venue-aware abstract. |
| Write | [`draft-related-work`](skills/draft-related-work/SKILL.md) | Position related work against verified references. |
| Write | [`polish-prose`](skills/polish-prose/SKILL.md) | Tighten academic prose without changing claims. |
| Write | [`match-style`](skills/match-style/SKILL.md) | Align a draft to the author's voice or venue style. |
| Write | [`polish-tables-figures`](skills/polish-tables-figures/SKILL.md) | Clean up figures, tables, captions, and crossrefs. |
| Write | [`refactor-structure`](skills/refactor-structure/SKILL.md) | Repair argument structure and narrative flow. |
| Write | [`fit-page-limit`](skills/fit-page-limit/SKILL.md) | Compress or expand a paper to fit a target length. |
| Write | [`work-with-overleaf`](skills/work-with-overleaf/SKILL.md) | Bring Overleaf projects into a local workflow. |
| Verify | [`verify-citations`](skills/verify-citations/SKILL.md) | Check BibTeX entries for fabricated or mismatched records. |
| Verify | [`check-originality`](skills/check-originality/SKILL.md) | Check plagiarism, self-plagiarism, and text recycling. |
| Verify | [`verify-claims`](skills/verify-claims/SKILL.md) | Audit claims against evidence, results, and citations. |
| Submit | [`parse-cfp`](skills/parse-cfp/SKILL.md) | Turn a live CFP into a requirements card. |
| Submit | [`add-venue-profile`](skills/add-venue-profile/SKILL.md) | Create or refresh a venue profile from live sources. |
| Submit | [`select-venue`](skills/select-venue/SKILL.md) | Build a ranked venue and track shortlist. |
| Submit | [`tailor-to-venue`](skills/tailor-to-venue/SKILL.md) | Adapt a draft to a venue, track, template, or limit. |
| Submit | [`preflight-check`](skills/preflight-check/SKILL.md) | Catch desk-reject risks before submission. |
| Submit | [`anonymize-paper`](skills/anonymize-paper/SKILL.md) | Sweep for double-blind identity leaks. |
| Submit | [`plan-submission`](skills/plan-submission/SKILL.md) | Build a deadline-aware submission timeline. |
| Submit | [`simulate-reviewers`](skills/simulate-reviewers/SKILL.md) | Run a venue-calibrated mock review. |
| Submit | [`benchmark-paper`](skills/benchmark-paper/SKILL.md) | Compare draft shape to strong venue exemplars. |
| Respond | [`triage-reviews`](skills/triage-reviews/SKILL.md) | Convert raw reviews into a response plan. |
| Respond | [`write-rebuttal`](skills/write-rebuttal/SKILL.md) | Draft rebuttals and author responses. |
| Publish | [`prepare-camera-ready`](skills/prepare-camera-ready/SKILL.md) | Walk through final-file and publication rails. |
| Artifacts | [`test-research-code`](skills/test-research-code/SKILL.md) | Make research code runnable and repeatable. |
| Artifacts | [`verify-results`](skills/verify-results/SKILL.md) | Compare reported metrics with local outputs. |
| Artifacts | [`refactor-research-code`](skills/refactor-research-code/SKILL.md) | Clean research code for release without changing behavior. |
| Artifacts | [`prepare-artifacts`](skills/prepare-artifacts/SKILL.md) | Package code/data for reproducibility review. |
| Present | [`make-slides`](skills/make-slides/SKILL.md) | Turn a paper into a conference talk deck. |
| Present | [`write-talk-script`](skills/write-talk-script/SKILL.md) | Write a timed speaker script. |
| Present | [`rehearse-qa`](skills/rehearse-qa/SKILL.md) | Practice hostile and curious Q&A. |
| Present | [`make-poster`](skills/make-poster/SKILL.md) | Create and check a research poster. |

## Common workflows

```text
New paper:       paper-profile -> literature-review -> write-abstract -> draft-related-work -> polish-prose
Before submit:   parse-cfp -> tailor-to-venue -> anonymize-paper -> preflight-check
Quality pass:    verify-citations -> check-originality -> benchmark-paper -> simulate-reviewers -> assess-paper
Length pass:     fit-page-limit -> polish-prose / refactor-structure / polish-tables-figures
Overleaf:        work-with-overleaf -> preflight-check / verify-citations / polish-prose -> work-with-overleaf
Artifacts:       test-research-code -> verify-results -> refactor-research-code -> prepare-artifacts
Reviews are in:  triage-reviews -> write-rebuttal
Accepted:        prepare-camera-ready -> make-slides -> write-talk-script -> rehearse-qa -> make-poster
End to end:      orchestrate-paper
```

## Integrations

This is an Agent Skills package, not a Claude-only prompt bundle. The
repository ships portable `SKILL.md` folders plus optional scripts and
references, so any agent that understands the Agent Skills format can use it.

| Environment | Install |
|---|---|
| Codex | `npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent codex` |
| Cursor | `npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent cursor` |
| Gemini CLI | `npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent gemini` |
| Claude Code | `npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --agent claude-code` or `/plugin install ...` |
| Any compatible agent | `npx skills add ShaishavMaisuria/research-paper-lifecycle-skills` |
| One-off use | `npx skills use ShaishavMaisuria/research-paper-lifecycle-skills --skill reflect-paper` |

Manual install for tools with their own skills directory:

```bash
mkdir -p "$YOUR_AGENT_SKILLS_DIR"
SKILL_NAME=preflight-check
cp -R "skills/$SKILL_NAME" "$YOUR_AGENT_SKILLS_DIR/"
```

## Memory and dashboards

Most tools forget you when the chat ends. This package uses a local
`.paper-memory/` convention, described in
[`paper-memory-convention.md`](skills/paper-profile/references/paper-memory-convention.md),
so skills can reuse paper positioning, writing preferences, decisions, and
lessons without uploading them.

`render-workspace-html` turns `paper-workspace/` into a local browser dashboard
with progress, artifact cards, and recent activity. The dashboard is
self-contained HTML, refreshable on request, and never uploaded by the skill.

## Principles

1. **Human-led.** Skills draft, check, and explain; they do not submit anything.
2. **Citation-aware.** Writing workflows route new references through
   verification instead of trusting plausible text.
3. **Copyright-conscious.** Paper content is fetched only from legal open
   sources, on demand, and is not bundled in this repository.
4. **Venue-skeptical.** Profiles and CFP facts can go stale; final rules must
   be checked live, with source links, before relying on them.
5. **Lightweight.** The repository ships skills, scripts, README visuals, and
   package metadata; not paper PDFs or cached research corpora.

## Repository layout

```text
assets/                         README visuals
skills/                         41 agent skills
  <skill>/SKILL.md               instructions and guardrails
  <skill>/references/            supporting guidance
  <skill>/scripts/               deterministic helper scripts
.claude-plugin/marketplace.json  optional Claude Code plugin bundle metadata
LICENSE                          Apache-2.0 license
NOTICE                           attribution notice
CITATION.cff                     citation metadata
```

## Attribution and license

Copyright 2026 Shaishav Maisuria.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

If you redistribute this package or include substantial portions of these
skills in another repository, keep the copyright/license notices and the
[NOTICE](NOTICE) attribution file so the original work is credited.

*Disclaimer: venue rules change every year. Always confirm against the live CFP
or author instructions before submission.*
