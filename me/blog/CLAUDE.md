# CLAUDE.md — blog system (for agents)

This directory is a **client-side-rendered Markdown blog** bolted onto a hand-written
static site (`../index.html`, HTML5 UP "Strata"). It is served raw by **GitHub Pages**
(repo `pasquini-dario.github.io`, `master` branch) at `https://pasquini-dario.github.io/me/blog/`.

**There is no build step and there must not be one.** Posts are `.md` files fetched and
rendered in the reader's browser. "Publishing" = write/edit files + `git push`. Do not
introduce a bundler, framework, generator, or npm-installed dependency without the owner
explicitly asking — it would break the "just push files" contract this whole design exists to keep.

## Files

| File | Role |
|------|------|
| `reader.js` | **The renderer** (shared ES module). Takes the slug from `window.BLOG_POST_SLUG` (set by a per-post page) or the `?p=` query param, validates it against `posts.json`, fetches `posts/<slug>.md`, renders it. This is the core; both `post.html` and every `<slug>.html` load it. |
| `<slug>.html` | **One static page per post** (e.g. `lying-your-way-out-of-the-sandbox.html`). Carries the post's Open Graph / Twitter meta baked into `<head>` (for social link previews), sets `window.BLOG_POST_SLUG`, and loads `reader.js`. This is the **canonical, shareable URL** — the index and feed link here. |
| `POST-TEMPLATE.html` | Copy-me template for a new `<slug>.html`. Fill in the ALL-CAPS placeholders; boilerplate stays. Not served to anyone; it's an authoring aid. |
| `post.html` | Generic **fallback** reader — `post.html?p=<slug>` still renders any post via `reader.js`, but its `<head>` is generic, so a link to it gets only a generic preview. Kept for back-compat/deep-links; prefer `<slug>.html`. |
| `index.html` | Post listing. Fetches `posts.json`, sorts newest-first, links to `<slug>.html`. |
| `blog.css` | Standalone, themed stylesheet (CSS custom properties). **Do NOT replace with `../main.css`** (see Invariants). |
| `theme.js` | Shared dark/light toggle. Dark is the default; the reader's choice is persisted in `localStorage["blog-theme"]`. |
| `posts.json` | The metadata index: `[{slug, title, date (YYYY-MM-DD), description, author?}]`. Source of truth for what exists. `author` is optional (string or array of names). |
| `feed.xml` | Hand-maintained Atom feed. One `<entry>` per post; template comment is inside. Entry links point at `<slug>.html`. |
| `posts/*.md` | The post bodies. |
| `posts/images/` | Post images live here, referenced relatively (e.g. `images/foo.png`). Also holds per-post Open Graph share images (e.g. `og-<slug>.png`, 1200×630). |
| `check-blog.py` | **Consistency checker** — pure-stdlib Python that verifies `posts.json` / `posts/<slug>.md` / `<slug>.html` / `feed.xml` agree and referenced images exist. Errors = mandatory material missing/broken (blocks commit); warnings = optional/drift. Wired to a `pre-commit` hook. See "Consistency check". |

## Render pipeline (in `reader.js`)

The pipeline lives in `reader.js` (a shared ES module). Each host page — `post.html`
and every `<slug>.html` — includes the pinned library `<script>` tags (classic scripts,
so they execute during parse) and then `<script type="module" src="reader.js">` (deferred,
so it runs after the globals exist). Keep that ordering when you add a page.

Libraries load from jsDelivr, **versions pinned exactly** (never `@latest`):

- `katex@0.17.0` — math typesetting
- `marked@18.0.6` — Markdown → HTML (GFM tables on, raw HTML passed through)
- `marked-katex-extension@5.1.10` — captures `$...$` / `$$...$$` as marked tokens
- `@highlightjs/cdn-assets@11.11.1` — code highlighting. **Both** `github-dark.min.css`
  and `github.min.css` are loaded (with `id="hljs-dark"` / `id="hljs-light"`); `theme.js`
  enables one via the `disabled` attribute so code matches the active theme.
- `mermaid@11.16.0` — diagrams, lazy-imported as ESM only when a post contains one.
  Theme-aware: `dark` theme in dark mode, `neutral` in light mode; re-rendered on toggle.

Order of operations: `marked.parse(md)` → **resolve post-relative image paths**
(prefix bare-relative `<img src>` with `posts/`) → `hljs.highlightElement` over
`pre code` → wrap `<table>`s in `.table-wrap` (for mobile scroll) → render `.mermaid`
diagrams.

**Why the image-path rewrite exists:** posts reference images as `images/foo.png`
(files in `posts/images/`), but the rendered Markdown is injected into `post.html`,
which lives at `me/blog/post.html`. Relative `src`es therefore resolve against
`me/blog/`, not `posts/`, so without rewriting they 404. The renderer prefixes any
bare-relative image `src` with `posts/`; absolute URLs, protocol-relative (`//`),
root-relative (`/`), fragment (`#`), and `data:` URIs are left untouched. Keep this
step if you touch the pipeline — it's what makes the documented `images/foo.png`
authoring convention actually work.

## Social / link previews (Open Graph + Twitter Cards)

**The problem this solves.** When someone pastes a link into X, LinkedIn, Slack,
Facebook, WhatsApp, Discord, iMessage, etc., that platform's crawler fetches the URL
and reads `<meta property="og:…">` / `<meta name="twitter:…">` from the **raw HTML**
`<head>`. Crawlers **do not run JavaScript**. This blog renders in the browser, so:

- A link to `post.html?p=<slug>` gets only a **generic** preview — every `?p=` URL
  returns the identical `post.html`, and GitHub Pages can't vary the response by query
  string, so the head is the same for all posts. (Setting meta from JS doesn't help;
  the crawler already read the static head and left.)
- Therefore **each post has its own static page, `<slug>.html`**, whose `<head>`
  carries that post's meta. That file is the canonical, shareable URL — it's what the
  index (`index.html`) and the feed (`feed.xml`) link to.

**How a `<slug>.html` page works.** It is a thin wrapper: the same `<head>`/`<body>`
skeleton as `post.html`, plus a block of static per-post meta tags, plus
`<script>window.BLOG_POST_SLUG = "<slug>"</script>` before `reader.js`. `reader.js` then
renders the post exactly as `post.html?p=` would. The `<h1>` title is also baked in
(matches `posts.json`) so it shows before JS runs and for no-JS readers; `reader.js`
overwrites it with the same value.

**What you can customize in a preview** (all in the `<slug>.html` head — see the
`<!-- per-post identity -->` block, and `POST-TEMPLATE.html` for a blank one):

| Tag | Controls |
|-----|----------|
| `<title>` + `og:title` + `twitter:title` | the bold title line |
| `og:description` + `twitter:description` + `<meta name="description">` | the gray blurb |
| `og:image` + `twitter:image` | **the preview image** |
| `og:url` + `<link rel="canonical">` | the canonical link |
| `og:type` (`article`) / `og:site_name` | type + site label |
| `article:published_time` / `article:author` | date + author (shown by some platforms) |
| `twitter:card` | `summary_large_image` (big banner) or `summary` (small thumbnail) |

**Image rules (important):**
- `og:image` / `twitter:image` **must be absolute `https://…` URLs** — relative paths
  are ignored by most crawlers. Base is `https://pasquini-dario.github.io/me/blog/`.
- Ideal size is **1200×630** (1.91:1) for `summary_large_image`. `sips` can crop any
  screenshot to that: `sips --resampleWidth 1200 in.png --out t.png` then
  `sips --cropToHeightWidth 630 1200 t.png --out posts/images/og-<slug>.png`.
- **Per-post image:** put an `og-<slug>.png` in `posts/images/` and point the meta at it.
- **Default fallback:** if a post has no custom image, point `og:image` at the site
  default `https://pasquini-dario.github.io/me/me.png` (what `POST-TEMPLATE.html` and
  `post.html` use). Keep the meta in sync with `posts.json` by hand — the preview tags
  are static HTML, so `posts.json` (read only by JS) can't drive them.

## Invariants — do not break these

1. **Script load order is load-bearing.** In every host page (`post.html` and each
   `<slug>.html`), `katex.min.js` must load **before** `marked-katex-extension`, because
   that extension's UMD build binds the global `katex` at load time
   (`window.markedKatex = factory(window.katex)`). Reorder them and math silently stops
   working. The four library `<script>`s must also come **before**
   `<script type="module" src="reader.js">` — though the module is deferred so this is
   naturally satisfied, keep them in that order.

2. **Math is tokenized, not post-processed.** We use `marked-katex-extension` so `$...$`
   becomes a marked *token before emphasis parsing*. This is deliberate: the naive
   alternative (render Markdown, then run KaTeX auto-render over the DOM) lets the
   Markdown parser eat underscores/asterisks inside math — `x_i` turns into `x<em>i</em>`.
   If you ever swap the math approach, re-verify that `$x_i + y_j^k$` keeps its subscripts.

3. **`nonStandard: true`** is set on `markedKatex`. It allows inline math without
   surrounding whitespace (e.g. `($O(n)$)`). Tradeoff: a **literal dollar sign in prose
   must be escaped `\$`**, or the text between two `$` gets parsed as math.

4. **Mermaid fences are diverted by a custom `code` renderer** to `<pre class="mermaid">`,
   with the diagram source HTML-escaped so `-->` survives `innerHTML`. `hljs` runs on
   `pre code` and thus naturally skips mermaid blocks (they contain no `<code>`).
   The marked v18 renderer signature is `code(token)` (a token object, not positional
   args); returning `false` falls through to the default renderer.

5. **`blog.css` is standalone on purpose. Do not link `../main.css`.** Two reasons:
   `main.css` `@import`s a `fontawesome-all.min.css` that isn't in the repo (a permanent
   404), and it hard-codes the fixed-sidebar layout (`#header{position:fixed}`,
   `#main{margin-left:35%}`) which fights the centered reading column. `blog.css` is its
   own themeable stylesheet: all colors are CSS custom properties defined under
   `:root[data-theme="dark"]` (the default) and `:root[data-theme="light"]`. To change a
   color, edit the token, not the individual rules. Note the blog uses **Source Sans 3**
   (a superset of the homepage's Source Sans Pro) with a monospace system stack for code.

6. **Slug safety.** `reader.js` only fetches a post after matching the slug (from
   `window.BLOG_POST_SLUG` or the `?p=` value) against a `slug` in `posts.json`, and
   echoes an unknown slug to the page via `textContent` only — never as HTML, never
   interpolated raw into a fetch path. Keep it that way. Note `BLOG_POST_SLUG` is set by
   a hand-authored `<slug>.html`, not from user input.

7. **Failures must degrade, not blank the page.** KaTeX runs with `throwOnError:false`;
   `mermaid.run` with `suppressErrors:true`; every `fetch` is wrapped so a missing file
   shows a friendly "Post not found" with a link back to the index.

8. **One renderer, two entry points.** The render logic lives **only** in `reader.js`;
   `post.html` and every `<slug>.html` are thin wrappers that load it. Don't fork the
   pipeline back into a page's inline script. And every post in `posts.json` must have a
   matching `<slug>.html` (the index links to it) — a missing wrapper 404s. The wrapper's
   static preview meta must be kept in sync with `posts.json` by hand.

## Theming (dark by default)

`theme.js` owns the light/dark switch. Mechanics:

- The active theme is `document.documentElement.dataset.theme` (`"dark"` | `"light"`),
  persisted as `localStorage["blog-theme"]`. **Dark is the default** when nothing is stored.
- Each page has a tiny **inline `<head>` script** that sets `data-theme` (and, on
  `post.html`, the `disabled` state of the two hljs stylesheets) *before first paint*, so
  a returning light-theme reader doesn't see a dark flash. Keep that inline — moving it to
  an external file reintroduces the flash.
- `theme.js` (loaded `defer`) wires the `#theme-toggle` button, flips the tokens/stylesheet
  on click, and dispatches a `themechange` CustomEvent.
- `post.html` listens for `themechange` and **re-renders Mermaid** (it stores each diagram's
  source, restores it, clears `data-processed`, re-`initialize`s with the new theme, and
  re-`run`s). Mermaid can't restyle an already-rendered SVG, so re-rendering is required.
- KaTeX inherits `color`, so math needs no per-theme handling. highlight.js needs the
  stylesheet swap because its colors are baked into the CSS file, not variables.

If you add a page, copy the inline `<head>` snippet, the `defer` `theme.js` tag, and the
`#theme-toggle` button, or the toggle won't appear / the theme won't persist there.

## How to add a post

1. Create `posts/<slug>.md`. **Start body headings at `##`** — the H1 title comes from
   `posts.json`, so don't put a `# Title` in the file. Put images in `posts/images/`.
2. Add one object to `posts.json` (`slug`, `title`, `date` as `YYYY-MM-DD`, `description`,
   and optionally `author`). `author` may be a single name or an array of names; when
   omitted it defaults to **Dario Pasquini** (the `DEFAULT_AUTHOR` constant in both
   `reader.js` and `index.html`). The author(s) and date render together in the meta line,
   e.g. `Dario Pasquini · July 11, 2026`, or `A and B · …` / `A, B and C · …` for multiple.
3. **Create the per-post page** (this is the shareable URL and what makes link previews
   work): copy `POST-TEMPLATE.html` to `<slug>.html` and fill in the ALL-CAPS
   placeholders (`SLUG`, `TITLE`, `DESCRIPTION`, `YYYY-MM-DD`, `AUTHOR`, `OG_IMAGE`).
   Keep title/description/date/author in sync with `posts.json`. For the share image,
   either drop a 1200×630 `og-<slug>.png` in `posts/images/` and reference it, or leave
   the default `https://pasquini-dario.github.io/me/me.png`. See "Social / link previews".
4. Copy the `<!-- NEW POST TEMPLATE -->` `<entry>` in `feed.xml` (its link is `<slug>.html`),
   fill it in, and bump the feed-level `<updated>` to the new date.
5. **Run the consistency check** — `python3 me/blog/check-blog.py` (from the repo root).
   Fix any ✗ ERRORs and review the ⚠ WARNs. This catches the easy-to-forget mistakes:
   a missing `<slug>.html`, a title that drifted out of sync between `posts.json` and the
   page's `og:title`, a broken image reference, an unfilled template placeholder, a
   forgotten `feed.xml` entry. The `pre-commit` hook runs it for you (see "Consistency
   check"), but running it by hand first is faster than a rejected commit.
6. `git push`.

## Consistency check (`check-blog.py` + pre-commit hook)

Because there's **no build step**, the four hand-maintained sources for a post —
`posts.json`, `posts/<slug>.md`, `<slug>.html`, and the `feed.xml` `<entry>` — can silently
drift apart (a title changed in one place but not the others, a `<slug>.html` never created,
a template placeholder left unfilled, a broken image path). `check-blog.py` is the guard.
It's **pure Python stdlib** (no deps — respects the "just push files" contract), reads the
files, and reports; it never edits anything and nothing runs at serve time.

**Run it before pushing** (from the repo root, or from `me/blog/` — it locates itself):

```
python3 me/blog/check-blog.py          # ✗ errors + ⚠ warnings; exit 1 if any error
python3 me/blog/check-blog.py --strict # also exit 1 on warnings
```

**Severity split** (this is the contract the owner asked for):
- **✗ ERROR = mandatory material missing/broken** → exit 1 (blocks the commit). E.g. a post
  with no `title`/`date`/`description`, a bad date format, a missing `posts/<slug>.md` or
  `<slug>.html`, a `BLOG_POST_SLUG` that doesn't match, a leftover template placeholder, or
  an `og:image`/`twitter:image` that isn't an absolute `https://` URL (crawlers ignore
  relative ones).
- **⚠ WARN = optional material missing, or things drifted out of sync** → doesn't block. E.g.
  `og:title`/`description`/`article:published_time`/`og:url`/canonical that don't match
  `posts.json`, a missing `feed.xml` entry, a referenced image that doesn't exist, an
  H1 at the top of the `.md`, an orphan `<slug>.html`/draft `.md`, a stale feed `<updated>`.

**The pre-commit hook** lives at `.git/hooks/pre-commit`. It runs the checker **only when a
commit stages files under `me/blog/`** (so unrelated commits to the rest of the repo aren't
affected), and blocks the commit **on errors only** (warnings print but pass). Bypass in a
pinch with `git commit --no-verify`.

> **Hooks are not version-controlled.** `.git/hooks/` isn't part of the repo, so after a
> fresh clone the hook won't exist — the *checker* (`check-blog.py`) still does. To reinstall
> the hook, create `.git/hooks/pre-commit` (make it executable, `chmod +x`) with a shim that
> runs the checker when blog files are staged:
> ```sh
> #!/bin/sh
> root=$(git rev-parse --show-toplevel)
> git diff --cached --name-only | grep -q '^me/blog/' || exit 0
> python3 "$root/me/blog/check-blog.py"
> ```

## How to verify a change

**First, the cheap gate:** `python3 me/blog/check-blog.py` (see "Consistency check" above) —
it catches missing files, out-of-sync preview meta, and broken image paths without a browser.
Then verify rendering and previews:

`fetch()` fails on `file://`, so you need HTTP. Serve the **repo root** (so `../me.png`
etc. resolve like on Pages):

```
python3 -m http.server 8000 --directory /Users/dariopasquini/Desktop/CV
# open http://localhost:8000/me/blog/
```

Check: index lists posts and links to `<slug>.html`; a **`<slug>.html`** page renders
(math with intact subscripts, mermaid SVG, highlighted code, ruled table) — this is the
path that matters now, not just `post.html?p=`; `post.html?p=nope` shows the not-found
message; narrow viewport doesn't overflow (`pre`/`.katex-display` scroll).

For **link previews**, crawlers read static HTML, so just view-source the `<slug>.html`
and confirm the `og:*` / `twitter:*` tags and that `og:image`/`og:url` are absolute
`https://…` URLs that resolve. After pushing, validate the live URL with a card debugger
(e.g. LinkedIn Post Inspector, X Card Validator, or `https://opengraph.xyz`); these also
prime the platform's cache. A **headless render check** of the pipeline (no browser) is
in the section below.

**Headless render check** (no browser needed): the render pipeline can be exercised in
Node by loading the UMD builds in a `vm` context that acts like `window` (they take their
browser-global branch when `module`/`exports`/`define` are absent), then calling
`marked.parse` on a post and asserting the output contains `class="katex"`,
`<pre class="mermaid">`, `<table>`, etc. This catches library-API regressions (e.g. a
marked major bump changing the renderer signature) without a real DOM. Mermaid's actual
SVG output still needs a browser — the headless test only confirms the fence is diverted.

## Gotchas

- Dates are parsed as UTC (`iso + "T00:00:00Z"`, `timeZone:"UTC"`) to avoid off-by-one-day
  from the viewer's timezone. Keep that if you touch date formatting.
- The homepage (`../index.html`) has a `✏️ Blog` sidebar link and a `feed.xml` alternate
  `<link>`. If you rename/move the blog, update both.
- GitHub Pages caches served files ~10 min; a freshly pushed post may not appear instantly.
