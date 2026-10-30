---
name: offline-docs
description: "Build or refresh a searchable, self-contained offline docs/index.html from existing Markdown using Python/Pandoc. Use for offline wikis or Markdown-to-HTML builds; content authoring is separate."
---

# Offline Docs

## Document before acting

Record intent, scope and check once (chat suffices for render-only work); close with actual outcome and limits. Reuse context; avoid duplicate plans and per-command logs.

For authoring, read the [documentation contract](README.md#documentation-contract-for-agents): use numbered source notes and relevant production images. Record proposed changes in the affected Markdown; reconcile with implementation and checks before rendering. Otherwise read README only for relevant errors. Render-only work never edits Markdown or audits source code.

## Render

1. Use the supplied source root or `docs/`; ask if absent or ambiguous. Require Python 3.9+ and Pandoc; reuse known tool availability.
2. Resolve this skill's path and run once (`py -3` also works on Windows):

   ```bash
   python <skill-dir>/scripts/build.py --docs <absolute-docs-path> --title "Project Documentation"
   ```

3. On failure, inspect only the reported cause. Allow one corrective retry per request, after a concrete correction; otherwise report the error and stop. No polling or autonomous retry loops. Obtain authorization if not already given before installing tools, using `--overwrite-existing` on foreign HTML, or using `--mermaid-source` to leave diagrams as code when `mmdc` is missing. Never run unreviewed remote scripts.
4. Close the task note with the builder's final `Built: ...` or `No changes: ...` line; on failure report the error and blocker, never success.

A successful build verifies rendering, not Markdown accuracy. Unless explicitly requested, never open the output, inspect generated HTML, take screenshots, or run browser/Playwright tests, including on the first build. This does not prohibit Mermaid CLI's internal diagram rendering. Do not load source, assets or builder code during normal builds; execute the deterministic builder, never generate HTML yourself.

## Invariants

- Only generated project output: `docs/index.html` by default; `--output` must stay inside the source root.
- SHA-256 skips unchanged inputs. Code changes alone do not refresh docs. Use `--force` for changed resources outside the source root.
- No watchers, servers or export-setting changes. Excluding docs from app/game builds belongs to the project.
