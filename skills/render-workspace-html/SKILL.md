---
name: render-workspace-html
description: Renders the paper-workspace (outputs + lifecycle progress) into a single self-contained HTML dashboard the author can open in a browser, and refreshes it on request. Use when a researcher says "show me an HTML view", "give me a dashboard", "can I see my progress in a browser", "visualize what's been done", "make an HTML report", or "update the dashboard". Offered as an option whenever a visual overview would help (it is opt-in, not generated unprompted), and re-run after each significant change so the page stays current. The output is one local dashboard.html with inline CSS — no network, no external assets, light/dark aware — listing every generated artifact by stage with clickable links and a recent-activity timeline. Trigger words - html, dashboard, browser view, visualize progress, html report, update the html.
---

# Render Workspace HTML

Turns the `paper-workspace/` directory into a **dashboard** the author can open in a browser — lifecycle progress, every generated artifact grouped by stage with clickable links, and a recent-activity timeline. It's the visual "where am I / what's been done" view on top of the files the other skills produce.

This is **opt-in**: offer it when a visual overview would genuinely help (after a batch of work, or when the author asks), not on every turn. When the author wants it kept live, **refresh it after each significant change** so it never goes stale.

## When to use

- The author asks for an HTML view / dashboard / browser-readable summary of progress.
- After several skills have run and the workspace has enough in it to be worth a glance.
- The author says "keep the HTML updated" — then regenerate it at the end of each request that changed the workspace.

## Process

1. **Offer, don't impose.** If the author hasn't asked, ask once: "Want an HTML dashboard of your progress? I can refresh it after each change." Generate only on yes.
2. **Generate (deterministic):**
   ```
   python3 scripts/build_dashboard.py --workspace paper-workspace
   ```
   It reads `paper-workspace/INDEX.md` and the stage folders (and `.paper-memory/profile.yml` for the title/venue if present) and writes `paper-workspace/dashboard.html` — one self-contained file, inline CSS, no network or external assets, light/dark aware. Exit 1 only if there is no workspace yet.
3. **Point the author to it** (`open paper-workspace/dashboard.html`). Summarize what it shows.
4. **Refresh on request.** If the author asked to keep it live, re-run step 2 at the end of any request that wrote new artifacts, and say you refreshed it. Otherwise regenerate only when asked again.

## Output

`paper-workspace/dashboard.html` — a stage-by-stage progress bar, artifact cards with links to each output, and a recent-activity timeline from `INDEX.md`. Opens offline in any browser.

## Guardrails

- **Local only.** The dashboard is a local file built from local artifacts; never upload it, host it, or copy it into this skills repo. No third-party paper content is rendered (only the author's own outputs).
- **Self-contained, no tracking.** Inline CSS only — no external scripts, fonts, images, or analytics.
- **Opt-in.** Don't generate the dashboard unprompted on every turn; offer it, then refresh per the author's preference.
- It only *displays* what other skills produced; it never edits artifacts, scores, or the paper.

## Memory

Uses the shared `.paper-memory/` convention ([paper-memory-convention.md](../paper-profile/references/paper-memory-convention.md)).
- **At start:** read `profile.yml` for the paper title/venue to label the dashboard; check whether the author opted into auto-refresh.
- **At end:** record the auto-refresh preference (`date · render-workspace-html · auto-refresh on/off`) so later runs honor it without re-asking.
- Create `.paper-memory/` on demand; local-only, never uploaded.
