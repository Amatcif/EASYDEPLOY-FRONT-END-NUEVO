---
name: easydeploy-security-auditor
description: Use for defensive security audits and hardening of EASY DEPLOY, a Windows Python/Tkinter app packaged as an .exe. Focus on secrets, unsafe execution, subprocess, file paths, packaging risks, dependency risk, resource integrity, local data handling, and safe mitigations. Do not use for malware, stealth, antivirus bypass, offensive exploitation, persistence, credential theft, or evasion.
---

# EASY DEPLOY security auditor

## Mission

Review and harden EASY DEPLOY defensively without changing legitimate behavior.

Use this skill for:
- secret and credential audits,
- unsafe Python pattern review,
- subprocess and command execution review,
- file/path/resource safety,
- packaging risk review for Windows `.exe` builds,
- local data and configuration handling,
- dependency and supply-chain hygiene,
- update/download/integrity review,
- defensive hardening plans.

## Non-negotiable rules

- Preserve existing behavior unless the user explicitly approves a behavior change.
- Do not remove features.
- Do not implement malware-like stealth, evasion, anti-analysis, persistence, credential theft, or offensive injection techniques.
- Do not claim that a Python-built `.exe` is impossible to reverse engineer.
- Do not store secrets in source code, `.spec`, config files, logs, build scripts, or bundled resources.
- Do not add obfuscation that makes maintenance unsafe.
- Do not introduce new dependencies without explaining why.
- Keep Spanish UI text correct: ñ, Ñ, accents, punctuation, and commas.
- Respect EASY DEPLOY versioning, UPX, resource, and release rules from `AGENTS.md`.

## Token-saving workflow

1. Read `AGENTS.md` first.
2. Inspect only security-relevant files first: entry points, build scripts, `.spec`, config handling, subprocess helpers, resource checks, updater/download code, and modules named auth/security/license/build/tools.
3. Avoid scanning `dist`, `build`, `__pycache__`, `.venv`, installers, ISOs, PDFs, and old JSONL histories unless the user explicitly asks.
4. Start with an audit report before editing.

## What to look for

### Secrets and sensitive data
- API keys, passwords, tokens, license secrets, private URLs, credentials, private certificates, hardcoded keys.
- Secrets in logs, changelogs, README, `.spec`, `.bat`, `.ps1`, JSON, YAML, or bundled files.

### Dangerous Python patterns
- `eval`, `exec`, dynamic imports, unsafe `pickle`, `marshal`, unsafe `yaml.load`, deserializing untrusted data.
- `os.system`, `subprocess(..., shell=True)`, unquoted paths, concatenated commands, user-controlled command arguments.

### File and path risks
- path traversal,
- unsafe temporary files,
- writes outside intended app directories,
- trusting current working directory incorrectly,
- deleting broad paths,
- overwriting resources without verification.

### Packaging and release risks
- accidental inclusion of secrets in the `.exe`, `dist`, build cache, or resources,
- missing `upx.exe` handling,
- fragile paths in `.spec`,
- unsigned executable risk,
- unclear integrity checks for downloaded/offline installers.

### Desktop-app hardening
- prefer server-side storage for real secrets,
- avoid treating local obfuscation as strong security,
- validate inputs before privileged actions,
- make errors clear but not secret-revealing.

## Safe remediation style

- Prefer small, reviewable patches.
- Replace risky subprocess calls with argument lists where possible.
- Quote and validate paths.
- Add explicit checks and clear messages.
- Move secrets out of the app or require external configuration.
- If a change is risky, report it and ask before editing.

## Definition of done

A security pass is complete only when:
- findings are prioritized high/medium/low,
- changed files are listed,
- behavior-preservation assumptions are stated,
- syntax checks are run when possible,
- remaining risks are documented.
