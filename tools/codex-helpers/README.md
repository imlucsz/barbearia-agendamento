# Codex helpers

PowerShell helpers adapted from [Creativebrook/codex-token-optimizer-kit](https://github.com/Creativebrook/codex-token-optimizer-kit). They require `rg` (ripgrep) and/or Git on `PATH`.

Run from the repository root:

```powershell
.\tools\codex-helpers\search_symbol.ps1 "Appointment"
.\tools\codex-helpers\find_usages.ps1 "create_appointment"
.\tools\codex-helpers\list_changed_files.ps1
.\tools\codex-helpers\summarize_file.ps1 .\README.md
```

Search helpers skip common generated folders, local virtual environments, local database files, logs, and credential-like files. `summarize_file.ps1` refuses common sensitive filenames and binary data extensions. These are convenience safeguards, not a security boundary; review the target before reading it.

PowerShell's execution policy may block these scripts. Do not weaken or bypass that policy just to run a helper; use the equivalent direct Git or ripgrep command instead.

The upstream kit does not automatically force Codex to call the helpers. This project references the workflow in `AGENTS.md` and provides the local skill at `.agents/skills/token-efficient-workflow/SKILL.md`.
