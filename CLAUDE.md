# CLAUDE.md — Airforce API SDKs

Entry point for Claude Code and similar agent tooling working in this repo.
Everything below is also useful to a human contributor.

## What lives here

One SDK per language, each self-contained in its own directory:

`csharp/` · `dart/` · `go/` · `java/` · `php/` · `python/` · `rust/` ·
`typescript/`

`docs/API_SURFACE.md` is the shared contract. **Treat it as the source of truth:**
when the surface changes, every SDK follows, and a change that lands in one
language only is a bug — users compare them side by side.

## Branch model: `dev` → `test` → `main`

- **`dev` accepts merged pull requests only** (2026-08-25). The path is:
  issue -> branch `<kind>/<nr>-<slug>` -> PR saying `Fixes #<nr>` -> bot review
  on the PR -> merge. A direct push is rejected with `GH013`.
- **The escape hatch stays open**: `dev` carries **no** required checks. You can
  open a PR and merge it immediately - red, unreviewed, whatever. That costs the
  same thirty seconds a push did and still leaves a trail. The strictness lives
  at the gate into `test`, not on the way into `dev`.
- `test` and `main` are protected by rulesets. `test` and `main` are protected by rulesets — no force
  push, no deletion, no state without green required checks, `bypass_actors = 0`.
  `main` accepts **merged pull requests only**.
- `promote-to-test.yml` advances `test` once all eight required checks are green —
  **TypeScript, Java, Go, Python, C#, PHP, Dart, Rust** — every commit has been
  reviewed, and no finding of severity `hoch` is left unanswered. When the gate
  holds, the run does **not** turn red: the reason is filed as a self-closing
  issue instead.
- A `hoch` finding is closed by a comment **on that commit**: `#erledigt` (fixed)
  or `#fehlalarm` (false positive, with a reason). A false positive is a valid
  answer — silently ignoring one is not. Answer promptly: an open finding blocks
  delivery for everyone, not just your own commit.
- **`dev` must be releasable at all times.** Unfinished work belongs on its own
  branch. Half-finished commits on `dev` block everyone else's delivery.
- **No cherry-picking between `dev` and `main`.** A release is a merge of the
  whole state. Cherry-picking puts the same work in the tree twice under two
  different SHAs; the next merge can then resolve to the older copy and silently
  revert finished work.

**Three traps, all three observed in practice:**

1. **A direct push to `dev` is never reviewed in this repo.** Unlike the other
   repositories, this one has no `review-push.yml` — `review.yml` fires on
   `pull_request` only. Since the gate requires a review for *every* commit, a
   direct push stalls it indefinitely, and the run stays green while nothing
   moves. **Work through a pull request here.** If a review is missing on an
   existing PR, trigger it by hand:
   `gh workflow run review.yml --ref dev -f pr=<NUMBER>`
2. **A push made by a bot triggers nothing at all** — by GitHub's design, a push
   authenticated with `GITHUB_TOKEN` starts no workflows. If the newest `dev`
   commit came from the sync bot, the chain stalls until a human pushes.
3. **The default branch is `main` — for `schedule` and `workflow_run`.** Those
   two always read the workflow file from the default branch, never from the
   branch concerned. A change to a scheduled or downstream workflow that only
   exists on `dev` therefore takes effect only after a release.
   **`workflow_dispatch` behaves differently**, and that is the useful exception:
   it runs the version from the ref you name. Measured on 2026-08-25 —
   `gh workflow run … --ref dev` produced a run on the head of `dev`, not on
   `main`. A workflow only has to **exist** on the default branch to be
   dispatchable at all; one that is new and missing there is invisible.

## House rules

- **No AI attribution** in commits, pull requests, code or docs (no
  `Co-Authored-By` trailers).
- **Never `git add -A` / `git add .`.** Run `git status --short` first and stage
  explicit paths.
- **Never commit credentials** — no API keys, no tokens, not even as a plausible
  looking example value. Examples use obvious placeholders.
- **Keep the SDKs in step.** A new endpoint, a renamed field or a changed default
  is not done until every language has it and `docs/API_SURFACE.md` reflects it.
- Code, identifiers, comments and documentation are **English**.
- Dependabot targets **`dev`**, not the default branch. Without `target-branch` a
  bump would land on `main` without ever having been on `dev` — never through the
  gate, never accepted. Precisely the kind of change nobody reads by hand.
