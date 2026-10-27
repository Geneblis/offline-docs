#!/usr/bin/env python3
"""Build one searchable, offline HTML wiki from Markdown via Pandoc.

No project-side configuration, dependencies, cache, or build directories.
Only writes docs/index.html (unless --output is specified).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

SKILL_DIR = Path(__file__).resolve().parent.parent
CSS = SKILL_DIR / "assets" / "theme.css"
JS = SKILL_DIR / "assets" / "app.js"
VERSION = "1.1.0"
MERMAID_FENCE = re.compile(r"(?m)^(?P<fence>`{3,}|~{3,})\s*mermaid\s*\n(?P<code>.*?)(?:\n)^(?P=fence)[ \t]*(?=\n|$)", re.S)
BODY_RE = re.compile(r"<body[^>]*>(.*?)</body>", re.S | re.I)
ID_RE = re.compile(r'\bid="([^"]+)"')
HREF_RE = re.compile(r'(<a\b[^>]*?\bhref=")([^"]+)(")', re.I)
TAG_ID_RE = re.compile(r'(<[a-zA-Z][^<>]*?\bid=")([^"]+)(")')
TITLE_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
TAGS_RE = re.compile(r"<[^>]*>")


def error(message: str) -> None:
    raise SystemExit(f"[offline-docs] ERROR: {message}")


def find_docs(docs: Path) -> list[Path]:
    excluded = {".git", ".venv", "venv", "node_modules", "_site", "site", "dist", "build", "_build", ".cache"}
    files = [p for p in docs.rglob("*.md") if p.is_file() and not any(part.lower() in excluded or part.startswith(".") for part in p.relative_to(docs).parts)]
    files.sort(key=lambda p: (p.name.lower() not in ("index.md", "readme.md"), len(p.relative_to(docs).parts), str(p.relative_to(docs)).lower()))
    return files


def page_id(path: Path, docs: Path) -> str:
    rel = path.relative_to(docs).as_posix()
    slug = re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-")
    return "doc-" + slug + "-" + hashlib.sha1(rel.encode()).hexdigest()[:6]


def svg_icon(name: str, size: int = 21) -> str:
    icons = {
        "book": '<path d="M12 7.5c-2.4-2.4-5.8-2.7-9-1.5v13c3.2-1.2 6.6-.9 9 1.5m0-13c2.4-2.4 5.8-2.7 9-1.5v13c-3.2-1.2-6.6-.9-9 1.5m0-13v13"/>',
        "search": '<circle cx="10.8" cy="10.8" r="6.7"/><path d="m16 16 5 5"/>',
        "moon": '<path d="M20 15.6A8.4 8.4 0 0 1 8.4 4 8.5 8.5 0 1 0 20 15.6Z"/>',
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
        "file": '<path d="M7 3h7l5 5v13H7zM14 3v6h5M10 13h6M10 17h6"/>',
        "rocket": '<path d="M13 4c4-1 6-1 8-1 0 2 0 4-1 8l-6 6-5-5zM8 13l-3 3H2v-3l4-4M13 18l-3 3H7v-3l3-3M8 16l-1 3-3 1 1-3z"/>',
    }
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{icons[name]}</svg>'


def pandoc_version(pandoc: str) -> str:
    # Version, not path: the hash must match across machines or the committed HTML churns.
    return subprocess.run([pandoc, "--version"], text=True, capture_output=True).stdout.split("\n", 1)[0]


def make_signature(docs: Path, title: str, pandoc: str, mmdc: str | None, mermaid_source: bool, output: Path) -> str:
    digest = hashlib.sha256()
    digest.update((VERSION + "|" + title + "|" + pandoc + "|" + str(bool(mmdc)) + "|" + str(mermaid_source)).encode())
    for asset in (CSS, JS):
        digest.update(asset.read_bytes())
    # Markdown + local documentation assets (images, styles, etc.).
    for f in sorted(docs.rglob("*")):
        if not f.is_file() or f.resolve() == output or any(part.startswith(".") or part in {"_site", "site", "build", "dist", "node_modules"} for part in f.relative_to(docs).parts):
            continue
        digest.update(f.relative_to(docs).as_posix().encode())
        digest.update(f.read_bytes())
    return digest.hexdigest()


def render_diagram(source: str, mmdc: str, index: int, page: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="offline-docs-mermaid-") as d:
        folder = Path(d)
        source_path = folder / "diagram.mmd"
        svg_path = folder / "diagram.svg"
        source_path.write_text(source.strip() + "\n", encoding="utf-8")
        cmd = [mmdc, "-i", str(source_path), "-o", str(svg_path), "-t", "dark", "-b", "transparent"]
        res = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
        if res.returncode != 0 or not svg_path.exists():
            msg = (res.stderr or res.stdout or "render failed").strip()[-1000:]
            error(f"Mermaid CLI failed on diagram {index} ({page.name}): {msg}")
        svg = svg_path.read_bytes()
        data = base64.b64encode(svg).decode("ascii")
        return f'\n<figure class="diagram"><img src="data:image/svg+xml;base64,{data}" alt="Mermaid diagram {index}" loading="lazy"/><figcaption>Diagram · {html.escape(page.stem)}</figcaption></figure>\n'


def pre_render_mermaid(markdown: str, page: Path, mmdc: str | None, source_only: bool) -> str:
    count = 0
    def replace(match: re.Match) -> str:
        nonlocal count
        count += 1
        if source_only:
            return match.group(0)
        if mmdc is None:
            error("Mermaid diagrams found, but 'mmdc' is not installed. "
                  "Install it with 'npm install -g @mermaid-js/mermaid-cli' (with authorization) "
                  "or run with --mermaid-source to keep the blocks as code.")
        return render_diagram(match.group("code"), mmdc, count, page)
    return MERMAID_FENCE.sub(replace, markdown)


def pandoc_html(page: Path, mmdc: str | None, source_only: bool) -> str:
    md = pre_render_mermaid(page.read_text(encoding="utf-8-sig"), page, mmdc, source_only)
    cmd = ["pandoc", "-f", "markdown+raw_html+pipe_tables+fenced_code_attributes+task_lists", "-t", "html5", "--standalone", "--embed-resources", "--metadata", f"pagetitle={page.stem}", "--highlight-style", "pygments"]
    result = subprocess.run(cmd, input=md, text=True, capture_output=True, cwd=page.parent, encoding="utf-8")
    if result.returncode != 0:
        error(f"Pandoc failed on {page}: {result.stderr.strip()[-1500:]}")
    match = BODY_RE.search(result.stdout)
    if not match:
        error(f"Pandoc produced no <body> for {page}")
    return match.group(1).strip()


def rewrite_links(fragment: str, page: Path, docs: Path, ids: dict[Path, str], prefix: str) -> str:
    def replace_link(m: re.Match) -> str:
        original = html.unescape(m.group(2))
        parts = urlsplit(original)
        if parts.scheme or parts.netloc or original.startswith("//"):
            return m.group(0)
        if not parts.path:
            if parts.fragment:
                return m.group(1) + "#" + html.escape(prefix + "--" + unquote(parts.fragment), quote=True) + m.group(3)
            return m.group(0)
        ext = Path(unquote(parts.path)).suffix.lower()
        if ext not in (".md", ".markdown"):
            return m.group(0)
        target = (page.parent / unquote(parts.path)).resolve()
        if target not in ids:
            return m.group(0)
        loc = ids[target]
        if parts.fragment:
            loc += "--" + unquote(parts.fragment)
        return m.group(1) + "#" + html.escape(loc, quote=True) + m.group(3)
    fragment = HREF_RE.sub(replace_link, fragment)
    # Rewrite IDs in headings, code spans, figures and nested sections alike.
    fragment = TAG_ID_RE.sub(lambda m: m.group(1) + html.escape(prefix + "--" + html.unescape(m.group(2)), quote=True) + m.group(3), fragment)
    return fragment


def infer_title(fragment: str, path: Path) -> str:
    match = TITLE_RE.search(fragment)
    return html.unescape(TAGS_RE.sub("", match.group(1))).strip() if match else path.stem.replace("_", " ").replace("-", " ").title()


def make_html(site_title: str, pages: list[dict], signature: str) -> str:
    nav = "\n".join(f'<a class="nav-item" href="#{html.escape(p["id"], quote=True)}" data-page="{p["id"]}">{svg_icon("rocket" if i == 0 else "file", 17)}<span>{html.escape(p["title"])}</span></a>' for i, p in enumerate(pages))
    content = "\n".join(f'<article id="{p["id"]}" class="doc-page" data-title="{html.escape(p["title"], quote=True)}" {"" if i==0 else "hidden"}>{p["html"]}</article>' for i, p in enumerate(pages))
    safe_title = html.escape(site_title)
    return f'''<!doctype html>
<html lang="en" data-theme="dark" data-site-title="{html.escape(site_title, quote=True)}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="offline-docs-version" content="{VERSION}"><meta name="offline-docs-signature" content="{signature}">
<meta name="color-scheme" content="dark light"><title>{safe_title}</title>
<style>{CSS.read_text(encoding="utf-8")}</style>
</head>
<body>
<header class="topbar"><div class="topinner">
<a class="brand" href="#{pages[0]['id']}">{svg_icon('book',24)}<span>{safe_title}</span></a>
<div class="head-actions">
<button class="iconbutton menu-button" id="menu-toggle" aria-label="Show navigation">{svg_icon('menu')}</button>
<button class="iconbutton" id="theme-toggle" aria-label="Toggle theme">{svg_icon('moon')}</button>
<button class="search-trigger" id="open-search" aria-label="Search documentation">{svg_icon('search',19)}<span class="search-label">Search</span><kbd>⌘ K</kbd></button>
</div></div></header>
<div class="layout"><aside class="sidebar" aria-label="Documentation pages"><div class="nav-heading">Documentation</div><nav class="page-nav">{nav}</nav></aside>
<main class="main-content" id="main-content">{content}</main>
<aside class="toc" aria-label="On this page"><div class="toc-title">On this page</div><ul class="toc-list" id="toc-items"></ul></aside></div>
<div class="search-overlay" id="search-overlay" role="dialog" aria-label="Search documentation" aria-modal="true" hidden><div class="search-panel"><div class="search-row">{svg_icon('search')}<input id="search-input" type="search" placeholder="Search documentation..." autocomplete="off" aria-label="Search"><button class="search-close" id="search-close" aria-label="Close search">Esc</button></div><div class="results" id="search-results" role="listbox"></div><div class="search-help"><kbd>↑</kbd> <kbd>↓</kbd> navigate &nbsp; <kbd>Enter</kbd> open &nbsp; <kbd>Esc</kbd> close</div></div></div>
<script>{JS.read_text(encoding="utf-8").replace('</script>', '<\\/script>')}</script>
</body></html>
'''


def build(args: argparse.Namespace) -> int:
    docs = args.docs.expanduser().resolve()
    if not docs.is_dir():
        error(f"Documentation directory not found: {docs}")
    output = (args.output or (docs / "index.html")).expanduser().resolve()
    if not output.is_relative_to(docs):
        error("For safety, the output must stay inside the docs directory.")
    pandoc = shutil.which("pandoc")
    if not pandoc:
        error("Pandoc not found. Install the official release (https://pandoc.org/installing.html), "
              "check `pandoc --version` and try again.")
    files = find_docs(docs)
    if not files:
        error(f"No Markdown found in: {docs}")
    has_mermaid = any(MERMAID_FENCE.search(f.read_text(encoding="utf-8-sig")) for f in files)
    mmdc = shutil.which("mmdc") if has_mermaid else None
    title = args.title or docs.parent.name.replace("-", " ").replace("_", " ").title() or "Documentation"
    signature = make_signature(docs, title, pandoc_version(pandoc), mmdc, args.mermaid_source, output)
    if output.is_file() and not args.force:
        # Read just the header; do not scan huge embedded image/SVG content.
        with output.open("r", encoding="utf-8") as existing:
            head = existing.read(1600)
        if 'name="offline-docs-version"' not in head and not args.overwrite_existing:
            error(f"{output} already exists and was not created by this skill. "
                  "To replace it, get authorization and use --overwrite-existing.")
        if f'content="{signature}"' in head:
            print(f"[offline-docs] No changes: {output}")
            return 0
    if output.is_file() and args.force and not args.overwrite_existing:
        with output.open("r", encoding="utf-8") as existing:
            if 'name="offline-docs-version"' not in existing.read(1600):
                error("Existing HTML file was not generated by this skill. "
                      "Use --overwrite-existing only with authorization.")
    ids = {p.resolve(): page_id(p, docs) for p in files}
    pages = []
    for page in files:
        frag = pandoc_html(page, mmdc, args.mermaid_source)
        title_page = infer_title(frag, page)
        frag = rewrite_links(frag, page, docs, ids, ids[page.resolve()])
        pages.append({"id": ids[page.resolve()], "title": title_page, "html": frag})
    result = make_html(title, pages, signature)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Atomic file replacement (no temp file inside project).
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, prefix=".offline-docs-", suffix=".tmp", delete=False) as temp:
        temp.write(result)
        temp_path = Path(temp.name)
    os.replace(temp_path, output)
    print(f"[offline-docs] Built: {output} ({len(pages)} pages, mermaid {'rendered' if mmdc and not args.mermaid_source else 'none/source'}, {len(result.encode('utf-8')):,} bytes)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an offline single-file HTML wiki with Pandoc.")
    parser.add_argument("--docs", type=Path, default=Path("docs"), help="Directory with Markdown files (default: docs)")
    parser.add_argument("--output", type=Path, help="Output HTML (default: docs/index.html)")
    parser.add_argument("--title", help="Documentation title")
    parser.add_argument("--force", action="store_true", help="Rebuild even without changes")
    parser.add_argument("--overwrite-existing", action="store_true", help="Allow replacing an index.html not generated by this skill")
    parser.add_argument("--mermaid-source", action="store_true", help="Keep Mermaid diagrams as code when mmdc is missing (not recommended)")
    return build(parser.parse_args())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired as exc:
        error(f"Timed out running {exc.cmd}")
    except (OSError, UnicodeError) as exc:
        error(str(exc))
