# Polyworkers for Healthcare Reform

Campaign website. Plain static HTML/CSS, no build step.

- `site/`: the published website
- `netlify.toml`: Netlify settings (publishes `site/`, headers, short links)

Deployed on Netlify from `main`; pull requests get a Deploy Preview. See `CLAUDE.md` for the workflow.

Local preview: `python3 -m http.server 8000 -d site`
