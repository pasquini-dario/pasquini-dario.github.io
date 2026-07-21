#!/usr/bin/env python3
"""
check-blog.py — pre-push consistency check for the client-side Markdown blog.

Run it before committing/pushing a new or edited post:

    python3 me/blog/check-blog.py          # from the repo root
    python3 check-blog.py                   # from me/blog/

It verifies that the four hand-maintained sources agree with each other:
posts.json  <->  posts/<slug>.md  <->  <slug>.html  <->  feed.xml
plus that referenced images exist. It is an *authoring aid*, not a build step:
it reads files and reports; it never modifies anything and nothing runs at
serve time. See CLAUDE.md ("Consistency check").

Severity:
  ERROR (✗)  mandatory material is missing/broken -> exit code 1 (blocks commit)
  WARN  (⚠)  optional material missing, or things drifted out of sync -> exit 0
Pass --strict to also fail on warnings.

Pure Python 3 standard library — no dependencies (keeps the "no npm deps" rule).
"""

import html
import json
import re
import sys
from pathlib import Path

BLOG = Path(__file__).resolve().parent          # me/blog/
REPO_ROOT = BLOG.parent.parent                  # the pasquini-dario.github.io checkout
SITE = "https://pasquini-dario.github.io/"      # Pages origin; maps 1:1 to REPO_ROOT
BASE = SITE + "me/blog/"                         # canonical base for post URLs
DEFAULT_OG_IMAGE = SITE + "me/me.png"           # site-default share image

KNOWN_KEYS = {"slug", "title", "date", "description", "author"}
SLUG_STRICT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")   # preferred shape
SLUG_SAFE = re.compile(r"^[A-Za-z0-9._-]+$")              # still filename/URL safe
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Signatures that mean a copied POST-TEMPLATE.html was never filled in.
PLACEHOLDERS = ['"TITLE"', '"DESCRIPTION"', "OG_IMAGE", "YYYY-MM-DD",
                '"AUTHOR"', "/SLUG.html", '"SLUG"', ">TITLE<"]

# Pages that are NOT per-post pages, so they're exempt from post checks.
NON_POST_HTML = {"index.html", "post.html", "POST-TEMPLATE.html"}

# ----- reporting -------------------------------------------------------------
_use_color = sys.stdout.isatty()
def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _use_color else s

errors = 0
warnings = 0
def err(msg):
    global errors; errors += 1
    print(f"  {_c('1;31', '✗ ERROR')}  {msg}")
def warn(msg):
    global warnings; warnings += 1
    print(f"  {_c('1;33', '⚠ WARN ')}  {msg}")

def read_text(p):
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None

# ----- tiny HTML extractors (regex is fine for our own controlled templates) -
def parse_meta(doc):
    """Map each <meta> tag's property/name (lowercased) -> unescaped content."""
    metas = {}
    for tag in re.findall(r"<meta\b[^>]*>", doc, re.I):
        k = re.search(r'\b(?:property|name)\s*=\s*"([^"]*)"', tag, re.I)
        c = re.search(r'\bcontent\s*=\s*"([^"]*)"', tag, re.I)
        if k:
            metas[k.group(1).strip().lower()] = html.unescape(c.group(1)).strip() if c else None
    return metas

def get_title(doc):
    m = re.search(r"<title>(.*?)</title>", doc, re.I | re.S)
    return html.unescape(m.group(1)).strip() if m else None

def get_canonical(doc):
    tag = re.search(r'<link\b[^>]*rel\s*=\s*"canonical"[^>]*>', doc, re.I)
    if not tag:
        return None
    href = re.search(r'\bhref\s*=\s*"([^"]*)"', tag.group(0), re.I)
    return href.group(1).strip() if href else None

def get_blog_slug(doc):
    m = re.search(r'window\.BLOG_POST_SLUG\s*=\s*["\']([^"\']*)["\']', doc)
    return m.group(1) if m else None

def local_path_for(url):
    """Map a Pages URL back to a file in the checkout, or None if off-site."""
    if url and url.startswith(SITE):
        return REPO_ROOT / url[len(SITE):]
    return None

def eq(label, actual, expected):
    if actual is None:
        warn(f"{label}: missing (expected {expected!r})")
    elif actual.strip() != expected.strip():
        warn(f"{label}: {actual!r} != posts.json {expected!r}")

# ----- load posts.json -------------------------------------------------------
raw = read_text(BLOG / "posts.json")
if raw is None:
    print(_c("1;31", "✗ posts.json not found — nothing to check.")); sys.exit(1)
try:
    posts = json.loads(raw)
except json.JSONDecodeError as e:
    print(_c("1;31", f"✗ posts.json is not valid JSON: {e}")); sys.exit(1)
if not isinstance(posts, list):
    print(_c("1;31", "✗ posts.json must be a JSON array.")); sys.exit(1)

feed = read_text(BLOG / "feed.xml") or ""
feed_entries = re.findall(r"<entry>(.*?)</entry>", feed, re.S)

slugs = []
seen = set()

# ----- per-post checks -------------------------------------------------------
for i, post in enumerate(posts):
    if not isinstance(post, dict):
        print(f"\n{_c('1', f'entry #{i}')}"); err("not a JSON object"); continue

    slug = post.get("slug")
    label = slug if isinstance(slug, str) and slug else f"entry #{i}"
    print(f"\n{_c('1', label)}")

    # --- slug ---
    if not isinstance(slug, str) or not slug.strip():
        err("slug: missing or empty (mandatory)"); slug = None
    else:
        slug = slug.strip()
        if slug in seen:
            err(f"slug: duplicate '{slug}' (each slug must be unique)")
        seen.add(slug)
        slugs.append(slug)
        if not SLUG_SAFE.match(slug):
            err(f"slug: '{slug}' has characters unsafe for a filename/URL")
        elif not SLUG_STRICT.match(slug):
            warn(f"slug: '{slug}' — prefer lowercase-with-hyphens")

    # --- title / date / description ---
    title = post.get("title")
    if not isinstance(title, str) or not title.strip():
        err("title: missing or empty (mandatory)"); title = None
    date = post.get("date")
    if not isinstance(date, str) or not DATE_RE.match(date or ""):
        err(f"date: {date!r} — must be a YYYY-MM-DD string (mandatory)"); date = None
    desc = post.get("description")
    if not isinstance(desc, str) or not desc.strip():
        err("description: missing or empty (mandatory — drives the preview blurb)")
        desc = None

    # --- author (optional; validate shape only) ---
    author = post.get("author")
    if author is not None:
        ok_author = isinstance(author, str) or (
            isinstance(author, list) and all(isinstance(a, str) for a in author))
        if not ok_author:
            err("author: must be a string or an array of strings")

    # --- unknown keys (typo catcher) ---
    for k in post:
        if k not in KNOWN_KEYS:
            warn(f"unknown key {k!r} in posts.json (typo? known: {sorted(KNOWN_KEYS)})")

    if slug is None:
        continue  # can't check files without a slug

    # --- posts/<slug>.md ---
    md_path = BLOG / "posts" / f"{slug}.md"
    md = read_text(md_path)
    if md is None:
        err(f"posts/{slug}.md: file not found (mandatory — the post body)")
    else:
        if not md.strip():
            warn(f"posts/{slug}.md: file is empty")
        first = next((ln for ln in md.splitlines() if ln.strip()), "")
        if re.match(r"^#\s", first):
            warn(f"posts/{slug}.md: starts with an H1 (# …); the title comes from "
                 "posts.json, so begin body headings at ##")
        # referenced images must exist
        refs = re.findall(r"!\[[^\]]*\]\(\s*([^)\s]+)", md)
        refs += re.findall(r'<img[^>]*\bsrc\s*=\s*"([^"]+)"', md)
        for src in refs:
            if src.startswith("images/"):
                if not (BLOG / "posts" / src).exists():
                    warn(f"posts/{slug}.md: references missing image posts/{src}")

    # --- <slug>.html (the shareable page) ---
    html_path = BLOG / f"{slug}.html"
    doc = read_text(html_path)
    if doc is None:
        err(f"{slug}.html: file not found (mandatory — index/feed link here; "
            "copy POST-TEMPLATE.html)")
    else:
        hit = [p for p in PLACEHOLDERS if p in doc]
        if hit:
            err(f"{slug}.html: unfilled template placeholder(s): {', '.join(hit)}")

        page_slug = get_blog_slug(doc)
        if page_slug is None:
            err(f"{slug}.html: no window.BLOG_POST_SLUG set (reader.js won't know "
                "which post to render)")
        elif page_slug != slug:
            err(f"{slug}.html: BLOG_POST_SLUG is {page_slug!r}, expected {slug!r}")

        meta = parse_meta(doc)
        if title:
            t = get_title(doc)
            if t is None:
                warn(f"{slug}.html: <title> missing")
            elif title not in t:
                warn(f"{slug}.html: <title> {t!r} doesn't contain posts.json title {title!r}")
            eq(f"{slug}.html og:title", meta.get("og:title"), title)
            eq(f"{slug}.html twitter:title", meta.get("twitter:title"), title)
        if desc:
            eq(f"{slug}.html og:description", meta.get("og:description"), desc)
            eq(f"{slug}.html twitter:description", meta.get("twitter:description"), desc)
            eq(f"{slug}.html meta description", meta.get("description"), desc)
        if date:
            eq(f"{slug}.html article:published_time", meta.get("article:published_time"), date)

        want_url = f"{BASE}{slug}.html"
        eq(f"{slug}.html og:url", meta.get("og:url"), want_url)
        eq(f"{slug}.html canonical", get_canonical(doc), want_url)

        for key in ("og:image", "twitter:image"):
            img = meta.get(key)
            if not img:
                warn(f"{slug}.html: {key} missing (no preview image)")
            elif not img.startswith("https://"):
                err(f"{slug}.html: {key} must be an absolute https URL "
                    f"(crawlers ignore relative paths): {img!r}")
            else:
                lp = local_path_for(img)
                if lp is not None and not lp.exists():
                    warn(f"{slug}.html: {key} points to {img} but "
                         f"{lp.relative_to(REPO_ROOT)} doesn't exist")

    # --- feed.xml entry ---
    entry = None
    for e in feed_entries:
        href = re.search(r'<link\b[^>]*href\s*=\s*"([^"]*)"', e, re.I)
        if href and href.group(1).rstrip("/").endswith(f"/{slug}.html"):
            entry = e; break
    if entry is None:
        warn(f"feed.xml: no <entry> linking to {slug}.html (RSS won't list this post)")
    elif title:
        ft = re.search(r"<title>(.*?)</title>", entry, re.S)
        if ft and html.unescape(ft.group(1)).strip() != title.strip():
            warn(f"feed.xml: entry title {html.unescape(ft.group(1)).strip()!r} "
                 f"!= posts.json {title!r}")

# ----- repo-wide checks ------------------------------------------------------
print(f"\n{_c('1', 'repo-wide')}")
slugset = set(slugs)

# feed-level <updated> should be >= newest post date
dates = [p.get("date") for p in posts if isinstance(p.get("date"), str) and DATE_RE.match(p.get("date", ""))]
if dates and feed:
    fu = re.search(r"<updated>(\d{4}-\d{2}-\d{2})", feed)
    newest = max(dates)
    if fu and fu.group(1) < newest:
        warn(f"feed.xml: feed <updated> {fu.group(1)} is older than newest post {newest} "
             "(bump it)")

# orphan per-post pages: a <slug>.html with no posts.json entry
for hp in sorted(BLOG.glob("*.html")):
    if hp.name in NON_POST_HTML:
        continue
    ps = get_blog_slug(read_text(hp) or "")
    if ps and ps not in slugset:
        warn(f"{hp.name}: sets BLOG_POST_SLUG={ps!r} but no such slug in posts.json "
             "(orphan page)")

# orphan drafts: a posts/*.md with no posts.json entry
for mp in sorted((BLOG / "posts").glob("*.md")):
    if mp.stem not in slugset:
        warn(f"posts/{mp.name}: no matching posts.json entry (unpublished draft?)")

# ----- summary ---------------------------------------------------------------
print()
if errors == 0 and warnings == 0:
    print(_c("1;32", "✓ all good — everything is aligned."))
    sys.exit(0)

parts = []
if errors:
    parts.append(_c("1;31", f"{errors} error(s)"))
if warnings:
    parts.append(_c("1;33", f"{warnings} warning(s)"))
print(", ".join(parts) + ".")

strict = "--strict" in sys.argv
if errors or (strict and warnings):
    if strict and warnings and not errors:
        print(_c("1;33", "failing on warnings (--strict)."))
    sys.exit(1)
if warnings:
    print("warnings don't block the commit (run with --strict to make them fail).")
sys.exit(0)
