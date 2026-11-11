# CLAUDE.md

## Who you're working with

**Brie** is the main person working on this site. **She is not a programmer.** She uses Claude to make changes, save them, and get them live.

How to work with her:

- **Use plain language.** Skip jargon. If a technical word is unavoidable (like "branch" or "pull request"), explain it in one short sentence the first time it comes up in a conversation.
- **Do the technical work for her.** Run the git, GitHub, and build commands yourself. Don't hand her terminal commands to run unless there's no other way (for example, a login that needs her password). If she must run one, give her the exact line and tell her she can type `! ` before it in the prompt.
- **Go one step at a time.** Say what you're about to do, do it, then say what happened and what comes next.
- **Show, don't describe.** After a change, give her the Netlify preview link so she can see it in the browser.
- **Check before anything permanent.** Ask before merging to `main` (that makes it live), deleting files, or changing site settings. Say clearly what will happen.
- **Be honest about problems.** If a build fails or something looks wrong, tell her plainly what broke and what you're doing about it. Don't bury it.
- **Keep updates short.** She wants to know: what changed, where to see it, and whether it's ready.

## What this project is

A static website (plain HTML and CSS) for Polyworker. It is hosted on **Netlify**, which is connected to the GitHub repo `Bre12084/polyworkers-hc`.

- Every push to `main` deploys the live site.
- Every pull request gets its own **Deploy Preview** link from Netlify, so changes can be checked before they go live.

Build and deploy settings live in `netlify.toml`. (To be filled in once the site files are added.)

## How changes get made (the workflow)

Never commit straight to `main`. Always:

1. **Start a branch** from an up-to-date `main`, named for the change (e.g. `update-about-page`, `fix-header-color`).
2. **Make the changes** and check them locally if useful (open the HTML in a browser, or run a local preview).
3. **Commit** with a short, clear message describing the change.
4. **Push and open a pull request** to `main` with `gh pr create`. Write the PR description in plain language.
5. **Wait for Netlify's checks.** Use `gh pr checks <number> --watch` to see when the Netlify build and Deploy Preview finish. Share the preview link with Brie.
6. **Tell Brie when it's ready.** It's ready to merge when: the Netlify build passed, Brie has looked at the preview and is happy, and nothing else is pending.
7. **Merge when she says yes**: `gh pr merge <number> --squash --delete-branch`, then switch back to `main` and `git pull`.
8. Confirm the live site updated.

Explaining this to Brie: a *branch* is a separate draft copy of the site; a *pull request* is asking to add that draft into the real site; *merging* makes it live.

## Rules

- `main` = the live site. Treat it with care.
- Don't merge if the Netlify build check is failing. (Goal: add a GitHub rule that enforces this once the Netlify check exists.)
- Keep it simple: no frameworks, build tools, or npm packages unless there's a real need and Brie agrees.
- Don't commit secrets, passwords, or private files.
