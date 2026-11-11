---
name: check-links
description: Check every link, image, and file reference on the website for breakage (missing files, bad #anchors, external pages that 404 or no longer exist). Use when Brie asks to check links, find broken links, or check the site before merging, and after edits that add or change links.
---

# Check links

Runs a link checker over every page in `site/` and explains the results to Brie in plain language.

## What it checks

- **Internal links and images**: the file exists in `site/` (pages, images, icons, the manifest).
- **Jump links** (`#petition`, `demystified.html#debate`): the section they point to exists on that page.
- **Short links** from `netlify.toml` (like `/petition`): followed to where they really go.
- **External links** (news articles, KFF, Congress, Change.org, etc.): the page still loads and isn't a 404 or a dead website. This includes URLs inside the page's scripts.

## How to run it

From the project root:

```bash
python3 .claude/skills/check-links/check_links.py
```

- It takes about 10–30 seconds because it visits every external site.
- To check only the site's own files (fast, no internet), add `--internal-only`.
- It uses only built-in Python, so there's nothing to install.
- Exit code `1` means something is broken; `0` means nothing broken.

## Reading the results

- **BROKEN (✗)**: definitely needs fixing. A missing file, a jump link to a section that doesn't exist, a page that returns "404 not found", or a website that no longer exists.
- **NEEDS A HUMAN LOOK (?)**: might be fine. Usually:
  - **403 / "blocked the automated check"**: some sites (congress.gov, epi.org, americanprogress.org and others) block robots but work fine in a browser. Open the link with `open <url>` or ask Brie to click it to confirm.
  - **Server error / connection problem**: may be temporary. Run the check again later.
  - **Link preview image should be a full https:// address**: the `og:image`/`twitter:image` tags use a relative path. This is a known to-do until the final site address is set (see CLAUDE.md). Mention it briefly; don't treat it as new.

## Telling Brie

Keep it short and plain:

1. Start with the headline: "All links work" or "I found N broken links."
2. For each broken link, say **which page**, **what the link text or purpose is** (look at the HTML around that line), and **what's wrong**, in everyday words. Example: "On the white paper page, the link to the KFF enrollment article now goes to a 'page not found'."
3. Suggest a fix (a replacement URL if you can find the moved page, or removing the link). Ask before changing anything.
4. Only mention the "needs a look" items if they matter. Don't overwhelm her with the robot-blocked sites if you've confirmed they work.

If you fix links, follow the normal workflow in CLAUDE.md (branch → PR → Netlify preview → merge when Brie says yes), and run this check again before saying it's ready.
