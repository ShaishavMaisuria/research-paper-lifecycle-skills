---
name: work-with-overleaf
description: Bridges an Overleaf project to the local skills so a paper kept on Overleaf can be checked, polished, and reviewed, then synced back. Use when a researcher says "my paper is on Overleaf", "sync my Overleaf project", "pull my paper from Overleaf", "run preflight on my Overleaf paper", "edit my Overleaf project locally", or "push my changes back to Overleaf". Walks the three real paths — Overleaf Git integration (clone as a local repo), GitHub synchronization, or download-as-ZIP for free accounts — gets the .tex into a local working copy the other skills operate on, and guides syncing changes back. Treats the Overleaf access token as a secret, never auto-pushes without confirmation, and re-verifies the current Overleaf method live since premium availability and steps change. Trigger words - overleaf, my paper is on overleaf, sync overleaf, pull from overleaf, push to overleaf, edit overleaf locally.
---

# Work With Overleaf

Most academics keep their `.tex` in **Overleaf**, not on disk — so this skill gets an Overleaf project into a local working copy the rest of the toolkit can act on (`preflight-check`, `polish-prose`, `verify-citations`, `match-style`, …), then helps sync the changes back. It's the on-ramp; the other skills do the work.

## Pick the path that matches the account

Overleaf exposes three ways to move a project in and out. **Re-verify the current method and whether it's premium before relying on it** against Overleaf's live documentation, because account features and menu names can change. As of the last check:

| Path | Who | How |
|---|---|---|
| **Git integration** (recommended) | Premium / Server Pro 4.0+ | Project → Menu → *Git*; copy the `git clone https://git.overleaf.com/<id>` command. Authenticate with an **Overleaf token** (token-based auth). Work locally, then `git pull` / `git push`. Branch is `main` (older clones may be `master`). |
| **GitHub synchronization** | Premium | Link the project to a GitHub repo (Menu → *GitHub*); sync both ways. Run the skills on the GitHub clone you already have locally. |
| **Download ZIP** | Free (everyone) | Menu → *Download → Source*. Work locally; there is **no auto-merge** — re-upload changed files in the Overleaf editor, or paste edits back. Best for a one-shot check. |

If the user isn't sure which they have, ask; don't assume premium.

## Process

1. **Establish the local copy.** Determine the path above and get the project local (clone, use the existing GitHub clone, or unzip the download). Confirm the main `.tex` and `.bib` are present.
2. **Run the requested skills** on the local files exactly as normal — `preflight-check` for desk-reject risk, `polish-prose`/`match-style` for the writing, `verify-citations` for the `.bib`, `assess-paper` for the full read. Write outputs to `paper-workspace/`.
3. **Review changes before syncing.** Show the author a diff of what changed. **Never push automatically** — academic drafts are shared/co-authored and an unreviewed push can clobber a collaborator's edits.
4. **Sync back** by the same path: `git push` (Git integration), commit+push to the linked GitHub repo (sync), or tell the author exactly which files to re-upload (ZIP). For Git/GitHub, confirm first and surface any merge conflicts rather than forcing.
5. **Compile sanity.** Note that Overleaf compiles server-side; if the local edits use a package/option Overleaf's TeX Live version may differ on, flag it so the author recompiles on Overleaf before relying on the PDF.

## Guardrails

- **The Overleaf token is a secret.** Never print it, log it, write it to a file, or commit it. If a clone URL contains a token, redact it in any output.
- **Never auto-push or auto-upload without explicit confirmation** — and never rewrite the Overleaf project history. Co-authors may be editing concurrently.
- **Don't assume premium.** Git/GitHub paths are premium; if the user is on free Overleaf, use the ZIP path and say so.
- **Re-verify the live method** (premium status, menu steps, clone host, branch name) against Overleaf's current docs before instructing — do not rely on cached steps.
- Copilot, not pilot: propose the sync, show the diff, let the author run it.

## Memory

Uses the shared `.paper-memory/` convention ([paper-memory-convention.md](../paper-profile/references/paper-memory-convention.md)).
- **At start:** read `profile.yml`/`lessons.md` for the author's usual Overleaf path so you don't re-ask each time.
- **At end:** append `date · work-with-overleaf · path used · note` after deduping (e.g. "author uses Git integration, token in keychain").
- Create `.paper-memory/` on demand; local-only, never uploaded; never store the token there.
