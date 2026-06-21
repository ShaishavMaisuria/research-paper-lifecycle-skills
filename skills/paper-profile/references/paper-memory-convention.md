# The .paper-memory/ convention

`.paper-memory/` is a per-project directory in the **author's paper working
directory** (the user's paper repo — NOT this skills repo). It is created at
use time and holds everything the toolkit remembers about *this* paper so the
skills get smarter over the life of the project instead of starting cold every
time. It is **local and private**: never uploaded, never committed unless the
author deliberately chooses to.

`paper-profile` owns and writes `profile.yml`. The other two files are written
by other skills; they are documented here so authors understand the whole
directory and so skill authors implement the shared hygiene rules consistently.

## Files

```
<paper-dir>/.paper-memory/
  profile.yml     # author/paper positioning  (paper-profile writes this)
  lessons.md      # accumulated, deduplicated lessons  (skills append)
  decisions.md    # venue/track/positioning decisions with rationale
```

### profile.yml

Schema v1, validated by `scripts/profile_io.py`. See positioning-axes.md and
downstream-consumption.md. Required: `vertical`, `contribution_type`,
`venue_tier`, `risk_appetite`.

### lessons.md

A running, deduplicated log other skills (`preflight-check`, `polish-prose`,
`verify-citations`, `simulate-reviewers`, …) **append to** when they catch
something, and **read at start** so they don't repeat the same advice and can
personalize. Each entry:

```markdown
- 2026-06-21 | polish-prose | issue: overuses "leverage" (7x) |
  rec: replace with "use"/"exploit" | scope: recurring
```

Fields: `date`, `skill`, `issue/pattern`, `recommendation`,
`scope: this-paper | recurring`.

### decisions.md

Venue/track/positioning decisions with rationale, so a later skill (or a
co-author) understands *why* a choice was made:

```markdown
- 2026-06-21 | venue | chose SIGSPATIAL 2026 Research track over VLDB |
  why: spatial framing + 10pp fits scope; VLDB cycle too late for deadline
```

## Memory hygiene (the rules every appending skill follows)

1. **Dedupe on append.** Before adding a lesson, check for an equivalent
   existing entry (same skill + same issue). Update its date instead of adding
   a duplicate.
2. **Date every entry.** So stale advice can be pruned and recency reasoned
   about.
3. **Cap `lessons.md`.** Keep the last N entries (e.g. 50) **plus all
   `scope: recurring` entries regardless of age.** Recurring patterns are the
   valuable signal; one-off `this-paper` notes age out.
4. **Surface recurring patterns proactively.** If a `recurring` lesson applies
   to the current task, mention it up front rather than re-deriving it.
5. **Prune stale `this-paper` lessons** when they no longer apply (e.g. the
   flagged section was rewritten).

## Privacy and versioning

- `.paper-memory/` is **local**. Nothing in it is uploaded.
- Recommend adding `.paper-memory/` to the paper repo's `.gitignore` by
  default — it holds private positioning and working notes.
- Some teams *do* want to version it (shared positioning, audit trail of
  decisions across co-authors). That's a legitimate choice; make it the
  author's, not the tool's. If versioning, note that `lessons.md` will then be
  visible to co-authors — fine for most, worth flagging.

## Scope boundary for paper-profile

This skill:

- Creates `.paper-memory/` if absent.
- Writes and validates `profile.yml`.
- Explains `lessons.md` / `decisions.md` and the hygiene rules.

This skill does **not** write `lessons.md` or `decisions.md` — those are
appended by the skills that generate the lessons and make the decisions. If the
user asks to record a lesson or decision now, you may seed the file with a
correctly formatted first entry, but the ongoing maintenance belongs to the
skills that produce them.
