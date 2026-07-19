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
| `post.html` | The renderer. Reads `?p=<slug>`, validates it against `posts.json`, fetches `posts/<slug>.md`, renders it. This is the core. |
| `index.html` | Post listing. Fetches `posts.json`, sorts newest-first, links to `post.html?p=<slug>`. |
| `blog.css` | Standalone, themed stylesheet (CSS custom properties). **Do NOT replace with `../main.css`** (see Invariants). |
| `theme.js` | Shared dark/light toggle. Dark is the default; the reader's choice is persisted in `localStorage["blog-theme"]`. |
| `posts.json` | The metadata index: `[{slug, title, date (YYYY-MM-DD), description, author?}]`. Source of truth for what exists. `author` is optional (string or array of names). |
| `feed.xml` | Hand-maintained Atom feed. One `<entry>` per post; template comment is inside. |
| `posts/*.md` | The post bodies. |
| `posts/images/` | Post images live here, referenced relatively (e.g. `images/foo.png`). |

## Render pipeline (in `post.html`)

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

## Invariants — do not break these

1. **Script load order is load-bearing.** In `post.html`, `katex.min.js` must load
   **before** `marked-katex-extension`, because that extension's UMD build binds the
   global `katex` at load time (`window.markedKatex = factory(window.katex)`). Reorder
   them and math silently stops working.

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

6. **Slug safety.** `post.html` only fetches a post after matching the `?p=` value against
   a `slug` in `posts.json`, and echoes an unknown slug to the page via `textContent`
   only — never as HTML, never interpolated raw into a fetch path. Keep it that way.

7. **Failures must degrade, not blank the page.** KaTeX runs with `throwOnError:false`;
   `mermaid.run` with `suppressErrors:true`; every `fetch` is wrapped so a missing file
   shows a friendly "Post not found" with a link back to the index.

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
   `post.html` and `index.html`). The author(s) and date render together in the meta line,
   e.g. `Dario Pasquini · July 11, 2026`, or `A and B · …` / `A, B and C · …` for multiple.
3. Copy the `<!-- NEW POST TEMPLATE -->` `<entry>` in `feed.xml`, fill it in, and bump the
   feed-level `<updated>` to the new date.
4. `git push`.

## How to verify a change

`fetch()` fails on `file://`, so you need HTTP. Serve the **repo root** (so `../me.png`
etc. resolve like on Pages):

```
python3 -m http.server 8000 --directory /Users/dariopasquini/Desktop/CV
# open http://localhost:8000/me/blog/
```

Check: index lists posts; a post renders (math with intact subscripts, mermaid SVG,
highlighted code, ruled table); `post.html?p=nope` shows the not-found message;
narrow viewport doesn't overflow (`pre`/`.katex-display` scroll).

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
