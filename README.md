# Portfolio Website with MkDocs Material

This repository provides a template for creating a professional freelance portfolio website using MkDocs Material. Originally designed for technical documentation, MkDocs Material has evolved into a [powerful framework](https://squidfunk.github.io/mkdocs-material/blog/2024/08/19/how-were-transforming-material-for-mkdocs/) that's perfect for portfolios, blogs, and personal websites - all manageable through simple Markdown and YAML files.

## Why MkDocs Material?

- **Quick Setup**: Get your site running in minutes
- **Markdown-Based**: Write content in simple Markdown
- **Code-Friendly**: Built-in syntax highlighting and code blocks
- **Responsive Design**: Looks great on all devices
- **No Frontend Skills Needed**: Professional design out of the box
- **SEO Optimized**: Built-in SEO features
- **Search Functionality**: Full-text search included
- **Social Cards**: Auto-generated preview cards for social media sharing
- **Dark Mode**: Automatic dark/light theme switching

As you go through this setup, please find all the most up to date information in the [official documentation here](https://squidfunk.github.io/mkdocs-material/getting-started/).

## Quick Start


### Option 1: Local Installation (Recommended for Mac Users)

1. **Clone this repository**
   ```bash
   git clone https://github.com/datalumina/mkdocs-website-template.git
   cd mkdocs-website-template
   ```

2. **Install MkDocs Material**
   ```bash
   # Installs the Python from .python-version and the exact versions in
   # uv.lock — never a fresh resolve, so the build stays reproducible.
   uv sync --locked

   # For MacOS, install required dependencies
   brew install cairo freetype libffi libjpeg libpng zlib pngquant
   ```

3. **Point Python at Homebrew's libcairo (Apple Silicon, one time)**

   The `social` plugin rasterizes its cards through `cairosvg`, which loads
   `libcairo` at runtime. A standalone interpreter — uv's CPython, for
   instance — does not search `/opt/homebrew/lib`, so the build fails with
   *"no library called cairo-2 was found"*. Link the library into a directory
   macOS already searches by default:
   ```bash
   mkdir -p ~/lib && ln -s /opt/homebrew/lib/libcairo.2.dylib ~/lib/
   ```
   `export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` fixes it too, but has
   to be repeated per shell, and macOS strips `DYLD_*` variables whenever a
   command runs through a `/bin/sh` wrapper — which newer uv-generated entry
   point scripts do.

4. **Preview your site**
   ```bash
   uv run mkdocs serve
   ```
   Visit `http://localhost:8000` to see your site.

   Material 9.7 prints a banner about the upcoming MkDocs 2.0 rewrite on every
   build. It concerns upstream MkDocs, not this site — Material 9.x requires
   `mkdocs<2`, so nothing here can be pulled into that rewrite. Silence it with
   `export NO_MKDOCS_2_WARNING=1` (CI already sets it).

> **Note on Operating Systems**: 
> - This setup has been thoroughly tested on MacOS (Intel and Apple Silicon)
> - Windows setup instructions are still being updated
> - If you encounter any issues on Windows:
>   1. First, check the [official MkDocs Material documentation](https://squidfunk.github.io/mkdocs-material/getting-started/)
>   2. Try to resolve the issue using their troubleshooting guides
>   3. If the problem persists, please message Dave on Circle for assistance
>   4. Your feedback will help improve the documentation for other Windows users!


### Option 2: Using Docker (Recommended for Windows, Mac and Linux)

Docker provides a consistent environment across all operating systems, making it an excellent choice for development. This method works reliably on Windows, MacOS, and Linux.

-> Special thanks to our community member, Nisar, for contributing the Docker implementation! 🐳

1. **Download & Install Docker Desktop**
https://docs.docker.com/get-started/get-docker/

2. **Clone this repository**
   ```bash
   git clone https://github.com/data-freelancer-mastermind/mkdocs-website-template.git
   cd mkdocs-website-template
   ```

3. **Start the server**
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```
   Visit `http://localhost:8000` to see your site.

## Customizing Your Portfolio

### 1. Basic Configuration

Edit `mkdocs.yml` to customize your site:

- Site name and metadata
- Navigation structure
- Color scheme and fonts
- Custom CSS settings in `stylesheets/extra.css`
- Social links
- Extensions and plugins

### 2. Content Structure

```bash
docs/
├── index.md          # Homepage / about
├── articles/         # Blog
│   ├── index.md      # Article overview page
│   ├── .authors.yml  # Author profiles
│   └── posts/
│       └── 2026-09-30_some-article/  # One folder per post
│           ├── index.md              # The post itself
│           └── diagram.png           # Images used by this post only
├── portfolio/        # Case studies
├── assets/           # Site-wide images: logo, favicon, author photo
└── stylesheets/      # Custom CSS
```

Each post is a folder containing an `index.md` plus the images that post uses.
Co-locating them means an image is referenced by its bare filename —
`![Diagram](diagram.png)` — with no `../../assets/` path to get right, and
deleting a post takes its images with it, so orphaned files cannot pile up.
Folder names are date-prefixed to keep posts in chronological order, while the
published URL comes from the `slug` in the post's front matter.

Only genuinely shared images belong in `docs/assets/`.

YouTube videos use the same image-like syntax, with a `youtube:` target and the
11-character video id — the part after `v=` in the watch URL:

```markdown
![A demo of the thing](youtube:dQw4w9WgXcQ)
```

`hooks/youtube.py` expands that into a lazy-loaded, responsive embed on
youtube-nocookie.com, and fails the build on an id it does not recognise. The
caption becomes the iframe's `title`, which is what screen readers announce.

### 3. Drawings

Drawings are made in [tldraw](https://tldraw.com) and exported as SVG. Drop the
export straight into the post folder and reference it with a `drawing:` target:

```markdown
![Histogram buckets](drawing:histogram-buckets.svg)
```

There is no conversion step. A tldraw export bakes in the colors of whichever
mode the canvas was in, so `hooks/drawings.py` re-themes it during the build,
swapping each baked color for a CSS variable naming the tldraw palette entry it
came from. The same hook inlines the SVG into the page, which is what lets
those variables resolve at all: an `<img>` is a separate document and cannot
see the page's stylesheet.

Because the drawing is inlined, the SVG file itself is never fetched, so
`exclude_docs` in `mkdocs.yml` keeps post drawings out of the built site — they
would otherwise be duplicated into the `gh-pages` branch for nothing. An SVG
meant to be served normally belongs in `docs/assets/`.

Cross-posts are the one exception, since dev.to and Hashnode need a URL rather
than markup. `hooks/drawings.py` writes a standalone copy of each drawing an
article actually referenced straight into the built site, carrying both
palettes so it follows the reader's system theme on somebody else's page.

Put `<!-- more -->` above the first drawing. Everything before it is the
excerpt the blog index, the archive and each category page render, and a
drawing above the separator is inlined into all of them at once.

The 12 drawing colors are defined per scheme in `stylesheets/extra.css`, taken
from tldraw's own light and dark themes so a drawing looks here the way it did
on the canvas. Edit them there to restyle every drawing on the site at once:

```bash
tools/tldraw_theme.py css docs/articles/posts/*/*.svg   # regenerate the block
tools/tldraw_theme.py convert <file>                    # theme a file on disk
```

`convert` is not needed for the site, which themes at build time; it is there
for exporting a drawing somewhere else. `tools/tldraw-palette.json` is a copy
of tldraw's `defaultThemes.ts` — if tldraw changes its palette, the build fails
naming the color it did not recognise, rather than quietly leaving a drawing
unthemed.

### 4. Redirects

Short URLs that forward somewhere else — `vanderoost.com/ai-tools` to a Google
Doc, say — live in `redirects.yml` at the repo root, one `slug: url` line each.
GitHub Pages serves static files only and cannot issue a real 301, so
`hooks/redirects.py` writes a self-forwarding HTML page per entry at build
time. It fails the build on a malformed entry, a duplicate slug, or a slug that
collides with a page the site already publishes.

### 5. Cross-posting

Articles are republished to dev.to and Hashnode with a canonical URL pointing
back here, so search engines keep treating vanderoost.com as the original.
`.github/workflows/syndicate.yml` runs after every successful deploy — after,
not during, because both platforms fetch the images at publish time and cache
a 404 as readily as a picture.

Set `DEVTO_API_KEY` as a repository secret (dev.to → Settings → Extensions),
and optionally `DEVTO_ORGANIZATION_ID`. A platform with no token is skipped
with a one-line notice rather than failing the run, so one is enough to start.

Hashnode is implemented but not enabled here, because its API stopped being
free on 2026-05-13: every call, reads included, now needs a Pro plan on the
publication. Publications that had a custom domain, webhooks or GitHub backup
before Pro launched are grandfathered. To turn it on, upgrade under Billing in
the blog dashboard and set `HASHNODE_TOKEN` (Settings → Developer → Personal
Access Token) and `HASHNODE_PUBLICATION_ID` — the 24-character id in your
dashboard URL, `hashnode.com/dashboards/<id>/general`, not the blog's
subdomain.

Locally, with the same variables in your environment:

```bash
# What a platform would receive, no network at all
uv run python -m tools.syndication render histogram-plotting-in-the-terminal
uv run python -m tools.syndication render <post> --json

# What would change, read-only
uv run python -m tools.syndication sync --dry-run
uv run python -m tools.syndication status

# Try one article privately first: dev.to gives a draft a real URL
uv run python -m tools.syndication sync --platform devto --remote-draft <post>
```

`syndication.json` at the repo root records which remote post belongs to which
article. It is a cache, not the source of truth — every adapter can re-find its
own post by canonical URL — so losing it costs one extra API read rather than a
duplicate article. `reconcile` rebuilds it from the platforms.

Posts are cross-posted as Markdown, so `tools/syndication/portable.py`
translates what Material adds on top: content tabs, admonitions, attribute
lists, and the `youtube:` and `drawing:` pseudo images. Anything it does not
recognise stops the run instead of shipping as literal punctuation. If you add
a new Markdown extension to `mkdocs.yml`, expect to teach that file about it.

## Deployment

I recommend publishing your site with GitHub Pages. If you want to keep your repo private, you need a GitHub Pro subscription. Public repos can be deployed with a free GitHub account.

1. Push your repository to GitHub
2. Follow the instructions here: [Publishing your site](https://squidfunk.github.io/mkdocs-material/publishing-your-site/)
3. Set up the GitHub actions for your project
4. Test the deployment by pushing changes

### Custom Domain



1. Add a `CNAME` file in your `docs` folder with your domain
2. Go to `repository/settings/pages` and check the domain settings
3. Follow the [instructions here](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site) to configure your domain and DNS settings
4. GitHub recently changed the DNS linking process: Let me know if we need to update these docs!
5. Also enable HTTPS on this page

## Useful Resources

- [Official MkDocs Material Documentation](https://squidfunk.github.io/mkdocs-material/getting-started/)
- [Icons and Emojis Reference](https://squidfunk.github.io/mkdocs-material/reference/icons-emojis/)
- [Blog Setup Guide](https://squidfunk.github.io/mkdocs-material/blog/)
- [Social Cards Configuration](https://squidfunk.github.io/mkdocs-material/plugins/requirements/image-processing/)
