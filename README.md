# research-paper-lifecycle-skills

Public release package for research-paper lifecycle skills.

This package includes agent skills for paper search, citation checking,
abstracts, related work, CFP parsing, venue tailoring, preflight checks,
anonymization, rebuttals, camera-ready preparation, slides, talk scripts,
Q&A rehearsal, and posters.

This public package intentionally ships only:

- `skills/`
- `.claude-plugin/marketplace.json`
- `README.md`
- `LICENSE`

It does not ship venue databases, eval fixtures, examples, internal research
notes, launch plans, cached metadata, PDFs, or generated artifacts. When a
skill asks for a venue profile, create one locally with `parse-cfp` or
`add-venue-profile`, or point the skill at your own local profile.

## Install

```bash
# Agent Skills CLI for Codex, Cursor, Gemini CLI, and compatible agents
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --full-depth
```

```bash
# Claude Code plugin flow
/plugin marketplace add ShaishavMaisuria/research-paper-lifecycle-skills
/plugin install paper-submission@research-paper-lifecycle-skills
```

To list available skills before installing:

```bash
npx skills add ShaishavMaisuria/research-paper-lifecycle-skills --list --full-depth
```

## Bundles

### paper-search

| Skill | Purpose |
|---|---|
| `find-papers` | Search scholarly metadata across key-free providers. |
| `fetch-paper` | Resolve a DOI or arXiv ID to a legal open-access copy. |
| `verify-citations` | Check BibTeX entries for fabrication, mismatch, duplicates, and retractions. |
| `study-exemplars` | Study venue exemplar papers by fetching legal open copies on demand. |

### paper-writing

| Skill | Purpose |
|---|---|
| `write-abstract` | Draft, rewrite, and lint venue-aware abstracts. |
| `literature-review` | Build a structured, citation-grounded literature review. |
| `draft-related-work` | Draft or rewrite related work from verified references. |
| `polish-prose` | Tighten academic prose without changing technical claims. |
| `polish-tables-figures` | Improve LaTeX tables, figures, captions, and palettes. |

### paper-submission

| Skill | Purpose |
|---|---|
| `parse-cfp` | Turn a CFP URL into a local requirements profile. |
| `select-venue` | Rank possible venues and tracks for a paper. |
| `tailor-to-venue` | Plan retargeting, page cuts, template changes, and anonymization. |
| `preflight-check` | Run deterministic desk-reject checks before submission. |
| `anonymize-paper` | Sweep double-blind leaks and support camera-ready reversal. |
| `triage-reviews` | Turn raw reviews into a priority matrix. |
| `write-rebuttal` | Draft response packages for OpenReview, one-page PDFs, and R&R cycles. |
| `simulate-reviewers` | Run a venue-calibrated mock review. |
| `prepare-camera-ready` | Walk accepted papers through camera-ready requirements. |
| `plan-submission` | Build a backwards timeline from submission deadlines. |
| `add-venue-profile` | Create a local venue profile from a live CFP. |

### paper-presenting

| Skill | Purpose |
|---|---|
| `make-slides` | Build or lint a talk deck sized to the actual slot. |
| `write-talk-script` | Write timed speaker notes and a cut list. |
| `rehearse-qa` | Practice hostile and curious audience questions. |
| `make-poster` | Plan and lint posters plus 2-minute and 5-minute pitches. |

## Safety Notes

- The package does not submit anything on your behalf.
- It does not bundle paper PDFs, abstracts, venue CFP text dumps, or third-party
  templates.
- Scripts use polite single-item requests and require contact-email environment
  variables when calling scholarly APIs.
- Venue rules change. Always verify final deadlines, page limits, and policies
  against the live CFP or submission site.

## License

MIT. See [LICENSE](LICENSE).
