#!/usr/bin/env python3
"""Check every link and file reference in the site for breakage.

Usage:  python3 .claude/skills/check-links/check_links.py [--internal-only] [site_dir]

Checks:
  - Internal links/images/icons point to files that exist in site/
  - #anchors point to an id that exists on the target page
  - Short links defined as redirects in netlify.toml (e.g. /petition)
  - External links (http/https) actually load (not 404, not dead)

Exit code: 0 = nothing broken, 1 = broken links found.
Uses only the Python standard library (no installs needed).
"""
import concurrent.futures
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlparse

REPO = Path(__file__).resolve().parents[3]
SKIP_SCHEMES = ("mailto:", "tel:", "sms:", "javascript:", "data:", "blob:")
URL_ATTRS = {"href", "src", "poster", "action"}
META_URL_PROPS = {"og:image", "twitter:image", "og:url", "og:image:secure_url"}
# Hosts that only exist to be "preconnected" to; their bare root returns 404 by design.
PRECONNECT_ONLY = {"fonts.googleapis.com", "fonts.gstatic.com"}
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 15


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []          # (line, url, kind)
        self.ids = set()
        self._in_script = False
        self.script_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        for key in ("id", "name"):
            if a.get(key) and (key == "id" or tag == "a"):
                self.ids.add(a[key])
        if tag == "link" and "preconnect" in (a.get("rel") or "") or \
           tag == "link" and "dns-prefetch" in (a.get("rel") or ""):
            return
        for attr in URL_ATTRS:
            if a.get(attr):
                self.refs.append((line, a[attr].strip(), f"<{tag} {attr}>"))
        if a.get("srcset"):
            for part in a["srcset"].split(","):
                if part.strip():
                    self.refs.append((line, part.strip().split()[0], f"<{tag} srcset>"))
        if tag == "meta":
            prop = a.get("property") or a.get("name") or ""
            if prop in META_URL_PROPS and a.get("content"):
                self.refs.append((line, a["content"].strip(), f"<meta {prop}>"))
        if tag == "script":
            self._in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.script_text.append((self.getpos()[0], data))


def netlify_redirects(repo):
    """Return {from_path: to} for redirects in netlify.toml."""
    toml = repo / "netlify.toml"
    out = {}
    if not toml.exists():
        return out
    text = toml.read_text()
    for block in re.split(r"\[\[redirects\]\]", text)[1:]:
        f = re.search(r'from\s*=\s*"([^"]+)"', block)
        t = re.search(r'to\s*=\s*"([^"]+)"', block)
        if f and t:
            out[f.group(1).rstrip("/") or "/"] = t.group(1)
    return out


def parse_pages(site):
    pages = {}
    for p in sorted(site.rglob("*.html")):
        parser = PageParser()
        parser.feed(p.read_text(encoding="utf-8", errors="replace"))
        for line, text in parser.script_text:
            for m in re.finditer(r"https?://[^\s\"'`<>()\\]+", text):
                url = m.group(0).rstrip(".,;")
                if "${" in url or "{{" in url:
                    continue
                parser.refs.append((line + text[:m.start()].count("\n"), url, "<script>"))
        pages[p] = parser
    return pages


def resolve_internal(site, page, url, redirects):
    """Return (target_file or None, fragment, note)."""
    path_part, frag = urldefrag(url)
    path_part = unquote(urlparse(path_part).path)
    if path_part == "":
        return page, frag, None
    if path_part.startswith("/"):
        key = path_part.rstrip("/") or "/"
        if key in redirects:
            dest = redirects[key]
            if dest.startswith("http"):
                return None, frag, f"redirect->{dest}"
            path_part = dest
        target = site / path_part.lstrip("/")
    else:
        target = (page.parent / path_part)
    target = target.resolve()
    if target.is_dir():
        target = target / "index.html"
    if not target.exists() and target.suffix == "" and target.with_suffix(".html").exists():
        target = target.with_suffix(".html")   # Netlify "pretty URLs"
    return target, frag, None


def check_external(url):
    """Return (status, detail). status in OK / BROKEN / WARN."""
    ctx = ssl.create_default_context()
    last = None
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={
            "User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
                final = r.geturl()
                return "OK", f"{r.status}" + (f" -> {final}" if final != url else "")
        except urllib.error.HTTPError as e:
            last = e.code
            if method == "HEAD" and e.code in (400, 403, 404, 405, 429, 500, 501, 503):
                continue  # many servers reject HEAD; retry with GET
            break
        except (urllib.error.URLError, socket.timeout, ConnectionError, ssl.SSLError) as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.gaierror):
                return "BROKEN", "site does not exist (DNS lookup failed)"
            last = f"connection problem: {reason}"
            if method == "HEAD":
                continue
            break
    if last in (404, 410):
        return "BROKEN", f"{last} not found"
    if isinstance(last, int) and last >= 500:
        return "WARN", f"{last} server error (may be temporary)"
    if last in (401, 403, 429, 999):
        return "WARN", f"{last} site blocked the automated check; open it by hand to confirm"
    if isinstance(last, int):
        return "BROKEN", f"HTTP {last}"
    return "WARN", str(last)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    internal_only = "--internal-only" in sys.argv
    site = Path(args[0]).resolve() if args else REPO / "site"
    redirects = netlify_redirects(REPO)
    pages = parse_pages(site)
    ids = {p.resolve(): parser.ids for p, parser in pages.items()}

    broken, warns, external = [], [], {}
    internal_count = 0
    for page, parser in pages.items():
        rel = page.relative_to(site)
        for line, url, kind in parser.refs:
            if not url or url.lower().startswith(SKIP_SCHEMES):
                continue
            where = f"{rel}:{line}"
            if url.startswith("//"):
                url = "https:" + url
            if re.match(r"https?://", url, re.I):
                host = urlparse(url).hostname or ""
                if host in PRECONNECT_ONLY and urlparse(url).path in ("", "/"):
                    continue
                external.setdefault(urldefrag(url)[0], []).append(where)
                continue
            internal_count += 1
            target, frag, note = resolve_internal(site, page, url, redirects)
            if note and note.startswith("redirect->"):
                external.setdefault(note[len("redirect->"):], []).append(f"{where} (via {url})")
                continue
            if kind.startswith("<meta"):
                warns.append((where, url, "link preview image should be a full https:// address "
                                          "(LinkedIn/Facebook ignore relative paths)"))
            if not target.exists():
                broken.append((where, url, "file not found in site/"))
            elif frag and target.suffix == ".html" and frag not in ids.get(target, set()) and frag != "top":
                broken.append((where, url, f'no element with id="{frag}" on {target.name}'))

    results = {}
    if not internal_only and external:
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(check_external, u): u for u in external}
            for f in concurrent.futures.as_completed(futs):
                results[futs[f]] = f.result()
        for url, (status, detail) in sorted(results.items()):
            first = external[url][0] + (f" (+{len(external[url]) - 1} more)" if len(external[url]) > 1 else "")
            if status == "BROKEN":
                broken.append((first, url, detail))
            elif status == "WARN":
                warns.append((first, url, detail))

    print(f"Checked {len(pages)} pages: {internal_count} internal links, "
          f"{len(external)} unique external links"
          + (" (external skipped)" if internal_only else ""))
    print()
    if broken:
        print(f"BROKEN ({len(broken)}):")
        for where, url, why in broken:
            print(f"  ✗ {where}  {url}\n      {why}")
        print()
    if warns:
        print(f"NEEDS A HUMAN LOOK ({len(warns)}):")
        for where, url, why in warns:
            print(f"  ? {where}  {url}\n      {why}")
        print()
    ok = sum(1 for s, _ in results.values() if s == "OK")
    print(f"Summary: {len(broken)} broken, {len(warns)} to look at, {ok} external OK")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
