# Offline Docs — single-file Markdown documentation skill

A portable agent skill for **Codex, Claude Code, Gemini CLI, or other agents supporting skills**. Converts existing Markdown into **one offline `docs/index.html`** using Python and Pandoc. Inspired by the visual layout in modern docs interfaces, including Zensical, but uses **original CSS/JS** and **does not require Zensical**.

### Features

- Dark/light theme, responsive layout, left navigation and right-side section index.
- Instant search of documentation text (`Ctrl+K` / `Cmd+K`), no server or cloud service.
- Syntax-highlighted code, tables, internal Markdown links, embedded local images, and Mermaid diagrams rendered to self-contained SVGs.
- Only one output file, `docs/index.html`. No project-side config or install files.
- Source fingerprint inside the output skips unchanged builds; `--force` overrides.
- Reads Markdown; does **not** generate or change Markdown content.

### Prerequisites

- **Python 3.9+**
- **Pandoc**, installed on PATH (`pandoc --version`), https://pandoc.org/installing.html
- **Mermaid CLI** only for diagrams (`mmdc --version`): https://github.com/mermaid-js/mermaid-cli

For Mermaid, install Node/npm as needed and then (after confirming trust/permissions):

```bash
npm install -g @mermaid-js/mermaid-cli
```

Mermaid CLI may require a browser/Chromium on the machine. Some restricted environments need configuration; see the official mermaid-cli troubleshooting instructions.

### Install skill globally

Copy the complete `offline-docs` folder into a global skills directory recognized by your agent (for example, `~/.claude/skills/offline-docs/` or `~/.agents/skills/offline-docs/`). Retain the subfolders `scripts/` and `assets/`. Agent paths vary by host.

### Build manually

```bash
python /path/to/offline-docs/scripts/build.py --docs /path/to/project/docs --title "My Project"
```

Windows example:

```powershell
py -3 C:\path\to\offline-docs\scripts\build.py --docs C:\path\to\my-project\docs --title "My Project"
```

Double-click `docs/index.html` to open the offline site. No webserver needed.

### Optional flags

| Flag | Use |
| --- | --- |
| `--docs PATH` | Source Markdown directory; default `./docs` |
| `--output PATH` | Output HTML within that directory; default `docs/index.html` |
| `--title TITLE` | Site title |
| `--force` | Force rebuild if hash unchanged |
| `--overwrite-existing` | Explicitly overwrite a pre-existing HTML file not created by this skill |
| `--mermaid-source` | Leave Mermaid fences as code when rendering unavailable (no diagrams) |

### Example projects

The layout is the same for any stack: Markdown in `docs/`, one generated `docs/index.html`.

Game (Unity/Godot/Unreal):

```text
my-game/
├── Assets/                # Engine files
└── docs/
    ├── index.md
    ├── architecture.md
    ├── gameplay.md
    └── index.html          # THE ONLY generated project file
```

Website (JS/Node.js/React):

```text
my-web-app/
├── package.json
├── src/
│   ├── components/
│   └── server/
└── docs/
    ├── README.md           # Becomes the first page
    ├── api/
    │   └── endpoints.md
    ├── frontend/
    │   ├── components.md
    │   └── state.md
    └── index.html          # Generated
```

Add an npm script so anyone on the team can rebuild:

```json
{
  "scripts": {
    "docs": "python /path/to/offline-docs/scripts/build.py --docs docs --title \"My Web App\""
  }
}
```

Java prototype (Maven/Gradle):

```text
my-java-prototype/
├── pom.xml                 # or build.gradle
├── src/main/java/
└── docs/
    ├── index.md
    ├── domain-model.md     # Mermaid class diagrams render to SVG
    ├── modules.md
    └── index.html          # Generated
```

```bash
python /path/to/offline-docs/scripts/build.py --docs my-java-prototype/docs --title "Java Prototype"
```

Exclude `docs/` from what you ship: `.npmignore` or the `files` field in `package.json` for Node packages; for Java, keep it out of `src/main/resources` so it never lands in the JAR.

Generated site resources and search index are embedded directly inside `index.html`. Markdown links targeting other included Markdown pages are rewritten as local navigation within the generated HTML. Rebuild when documentation changes.

### Important limitations

- `index.html` is an **output artifact**. Don't hand-edit it: edit Markdown and rebuild.
- The initial dependency installation and Mermaid diagram compilation may need internet access. Opening the generated site does not.
- Very large document sets or huge embedded images can make `index.html` large, slow to open, or slow to search. For large projects use a multi-page static site instead.
- Mermaid diagrams are compiled to static SVG (clear and offline), not edited interactively in the browser.
- The builder does not maintain factual accuracy of Markdown against evolving source code; that's a separate documentation-writing task.
- Markdown containing intentionally embedded HTML is treated as trusted project content; do not compile untrusted HTML into an artifact you'll distribute.
- Local image changes within `docs/` are detected as inputs. Resources referenced from **outside** `docs/` may require `--force` after a change.
- Excluding docs from game binaries depends on each engine's build/export settings, not this skill.

### Verification

Run `python -m unittest discover -s tests -v` from the skill folder. Tests require Pandoc; browser checks require Playwright but are not required to build documentation.
