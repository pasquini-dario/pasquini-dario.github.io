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
| `blog.css` | Standalone stylesheet. **Do NOT replace with `../main.css`** (see Invariants). |
| `posts.json` | The metadata index: `[{slug, title, date (YYYY-MM-DD), description}]`. Source of truth for what exists. |
| `feed.xml` | Hand-maintained Atom feed. One `<entry>` per post; template comment is inside. |
| `posts/*.md` | The post bodies. |
| `posts/images/` | Post images live here, referenced relatively (e.g. `images/foo.png`). |

## Render pipeline (in `post.html`)

Libraries load from jsDelivr, **versions pinned exactly** (never `@latest`):

- `katex@0.17.0` — math typesetting
- `marked@18.0.6` — Markdown → HTML (GFM tables on, raw HTML passed through)
- `marked-katex-extension@5.1.10` — captures `$...$` / `$$...$$` as marked tokens
- `@highlightjs/cdn-assets@11.11.1` — code highlighting (github light theme)
- `mermaid@11.16.0` — diagrams, lazy-imported as ESM only when a post contains one

Order of operations: `marked.parse(md)` → `hljs.highlightElement` over `pre code` →
`mermaid.run()` over `.mermaid`.

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
   `#main{margin-left:35%}`) which fights the centered reading column. `blog.css` instead
   copies the ~15 relevant style values (fonts, colors, code/table rules). If you change
   the site palette in `main.css`, mirror it here manually.

6. **Slug safety.** `post.html` only fetches a post after matching the `?p=` value against
   a `slug` in `posts.json`, and echoes an unknown slug to the page via `textContent`
   only — never as HTML, never interpolated raw into a fetch path. Keep it that way.

7. **Failures must degrade, not blank the page.** KaTeX runs with `throwOnError:false`;
   `mermaid.run` with `suppressErrors:true`; every `fetch` is wrapped so a missing file
   shows a friendly "Post not found" with a link back to the index.

## How to add a post

1. Create `posts/<slug>.md`. **Start body headings at `##`** — the H1 title comes from
   `posts.json`, so don't put a `# Title` in the file. Put images in `posts/images/`.
2. Add one object to `posts.json` (`slug`, `title`, `date` as `YYYY-MM-DD`, `description`).
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
