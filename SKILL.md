---
name: offline-docs
description: "Render existing project Markdown into one searchable, self-contained offline docs/index.html (three-column docs UI, dark/light theme, search, Mermaid as SVG) using Python and Pandoc. Use when the user asks for a local/offline wiki, a Markdown-to-HTML docs build, or to refresh a generated docs site. Renders only: never writes or edits Markdown."
---

# Offline Docs

Run the deterministic builder. Never generate HTML or rewrite Markdown yourself. Never read source code for this task. Details and troubleshooting: `README.md`.

## Documentation handoff

For a separate task that creates or maintains project Markdown, direct the writing agent to the [documentation contract](README.md#documentation-contract-for-agents). It defines source layout, page content and change maintenance for any stack. Once the Markdown is ready, use the workflow below to render it. An HTML refresh does not require reorganizing existing documentation.

## Workflow

1. **Locate Markdown.** Default `docs/`. Ask only if no `docs/` exists or several candidates do.
2. **Check tools.** `pandoc --version` and Python 3.9+. If a tool is missing, say what is missing and ask before installing it (https://pandoc.org/installing.html). Never install silently. Never run unreviewed remote scripts.
3. **Run the builder** from this skill's directory (resolve its absolute path):

   ```bash
   python <skill-dir>/scripts/build.py --docs <abs-path>/docs --title "Project Documentation"
   ```

   On Windows, `py -3` also works.
4. **Handle errors.**
   - `mmdc` missing (only raised when Markdown has `mermaid` fences): ask to install `npm install -g @mermaid-js/mermaid-cli`, or rerun with `--mermaid-source` if the user agrees. Diagrams then stay code.
   - `already exists and was not created by this skill`: ask before rerunning with `--overwrite-existing`.
   - Any other error: report it verbatim. Never claim success.
5. **Report** the builder's last line: `No changes: ...` or `Built: ... (N pages, mermaid ..., bytes)`.

Do not open a browser to verify unless the user asks or this is the first build in the project.

## Behavior

- Output is only `docs/index.html`. Nothing else is written to the project.
- A SHA-256 fingerprint of the Markdown, local assets, theme and options is stored in the HTML. Unchanged input prints `No changes` and exits. `--force` rebuilds.
- Source code changes do not trigger a rebuild. Updating Markdown content is a separate task.
- Resources referenced from outside `docs/` are not fingerprinted. Use `--force` after changing them.
- To keep docs out of a game/app build, exclude `docs/` in the engine's export settings. This skill does not change them.
