---
name: token-efficient-workflow
description: Use for repository search, code reading, debugging, tests, and summaries when Codex should limit unnecessary context and terminal output without reducing correctness.
---

# Token-Efficient Workflow

Reduce unnecessary context while preserving correctness and safety.

## Classify the task

- For a small task, inspect only the relevant files and run the smallest useful validation.
- For multi-file, debugging, publishing, credential, automation, or production-data work, make a short plan, inspect before acting, and validate each important result.

## Work from narrow evidence

1. Follow the repository `AGENTS.md`.
2. Check `PROJECT_EXCLUSIONS.md` before broad searches or reading large files.
3. Search for symbols and filenames first; open only relevant excerpts.
4. Prefer the project helpers in `tools/codex-helpers/` for symbol search, usages, changed-file listing, and short text summaries.
5. Verify helper output; use direct commands when a helper is unsuitable.
6. If PowerShell execution policy blocks a helper, do not change or bypass that policy; use the equivalent direct `rg` or Git command.

## Avoid routine context noise

Do not search or read generated/dependency folders, local databases, logs, exports, backups, or environment files unless the task specifically requires them. Never expose credentials, tokens, or sensitive database contents in output.

## Keep changes and output focused

- Make the smallest change that meets the request.
- Do not bundle unrelated formatting or refactoring.
- Capture only relevant error lines from long command output.
- Report actual validation results, including skipped tests and limitations.

## Important limits

`PROJECT_EXCLUSIONS.md` and helper scripts are workflow aids, not security boundaries. They do not prevent Codex or another process from reading files. `.codexignore` behavior is not assumed. Use operating-system permissions and keep secrets outside the repository for actual protection.

## Provenance

Adapted from Creativebrook's `codex-token-optimizer-kit` under the MIT License. The adapted helpers and license notice are in `tools/codex-helpers/`.
