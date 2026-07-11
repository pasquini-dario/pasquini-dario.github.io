# Blog

A tiny Markdown blog for the site, with **no build step**. You write a post in Markdown,
add a couple of lines, and `git push` — GitHub Pages serves it and the browser renders it.

Posts support **Markdown**, **LaTeX math** (`$inline$` and `$$display$$`),
**Mermaid diagrams**, **syntax-highlighted code**, and there's an **RSS/Atom feed**.

Live at <https://pasquini-dario.github.io/me/blog/>.

## Writing a new post

1. **Create the post file** at `posts/<slug>.md`, where `<slug>` is a short
   URL-friendly name (lowercase, hyphens), e.g. `posts/my-new-idea.md`.
   - Don't put a `# Title` at the top — the title comes from `posts.json` (next step).
     Start your headings at `##`.
   - Put any images in `posts/images/` and reference them relatively, e.g.
     `![caption](images/diagram.png)`.

2. **List it** by adding one entry to `posts.json`:
   ```json
   {
     "slug": "my-new-idea",
     "title": "My New Idea",
     "date": "2026-07-15",
     "description": "One sentence shown on the index and in the feed."
   }
   ```
   (`date` is `YYYY-MM-DD`. The index sorts newest-first automatically.)

3. **Add it to the feed** in `feed.xml`: copy the commented `NEW POST TEMPLATE` block,
   fill in the slug/title/date/summary, and bump the `<updated>` near the top of the file
   to the new post's date. (Optional but nice for subscribers.)

4. **Publish**: `git push`. It's live in a few minutes.

## What you can write in a post

- Standard Markdown: headings, **bold**, *italic*, lists, links, images, `> quotes`,
  tables, and `inline code`.
- Fenced code with a language for highlighting:
  ~~~
  ```python
  print("hello")
  ```
  ~~~
- Math with LaTeX syntax: `$E = mc^2$` inline, or `$$ ... $$` on its own lines for a
  centered display equation.
  - ⚠️ Because math uses `$`, a **literal dollar amount must be escaped** as `\$5`.
- A [Mermaid](https://mermaid.js.org/) diagram:
  ~~~
  ```mermaid
  flowchart LR
    A --> B --> C
  ```
  ~~~

See `posts/rendering-test.md` for a live example that uses every feature (you can delete
that post once you're comfortable — remove its file, its `posts.json` entry, and its
`feed.xml` entry).

## Previewing locally

The blog fetches files over HTTP, so opening the `.html` directly (`file://`) won't work.
Run a local server from the repo root and open the blog:

```bash
python3 -m http.server 8123 --directory /Users/dariopasquini/Desktop/CV
# then visit http://localhost:8123/me/blog/
```

## How it fits together (short version)

- `index.html` — the post list.
- `post.html` — renders a single post (`post.html?p=<slug>`).
- `blog.css` — styling, matched to the main site.
- `posts.json` — the list of posts.
- `feed.xml` — the RSS/Atom feed.
- `posts/` — your Markdown files (and `posts/images/`).

Rendering happens in the browser using well-known libraries (marked, KaTeX, highlight.js,
Mermaid) loaded from a CDN. There's nothing to install or compile.

> For agents/LLMs working on the *machinery* (not just writing posts), see `CLAUDE.md` in
> this folder — it documents the render pipeline and the invariants that keep it working.
