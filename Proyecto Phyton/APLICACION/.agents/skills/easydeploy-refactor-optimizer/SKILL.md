---
name: easydeploy-refactor-optimizer
description: Use for EASY DEPLOY Python/Tkinter safe refactoring, duplicate-code reduction, dead-code cleanup, startup/runtime responsiveness, and maintainability improvements. Preserve exact behavior, Spanish UI text, version/changelog rules, PyInstaller/UPX builds, resource checks, offline installers, and existing workflows. Keep token use low by reading only relevant files first.
---

# EASY DEPLOY refactor optimizer

## Mission

Improve EASY DEPLOY code quality, maintainability, size, and responsiveness while preserving existing behavior.

Use this skill for:
- reducing duplicated code,
- removing dead or unused code,
- simplifying oversized functions,
- centralizing repeated helpers,
- improving Tkinter responsiveness,
- improving startup time,
- reducing repeated file/resource checks,
- cleaning imports and small maintainability issues.

Always combine mentally with project guidance from `AGENTS.md` and, when available, `$easydeploy-maintainer`.

## Non-negotiable rules

- Preserve exact user-visible behavior unless the user explicitly approves a behavior change.
- Do not remove features.
- Do not change business logic unless required for a safe refactor and clearly explained first.
- Do not rewrite the whole app.
- Do not migrate away from Tkinter unless the user explicitly asks.
- Do not minify Python source code.
- Do not make code shorter by making it harder to read.
- Do not use `eval`, `exec`, dynamic import hacks, or obfuscation to reduce lines.
- Do not rename public functions/classes/files unless necessary and safe.
- Preserve Spanish UI text, including `ñ`, `Ñ`, accents, punctuation, commas, `¿` and `¡`.
- Do not change EASY DEPLOY version/changelog rules except when the user asks for build/release work.
- Preserve PyInstaller and `upx.exe` build behavior.
- Preserve resource-check behavior and green/red prerequisite states.
- Preserve offline installer behavior.
- Preserve Exchange, AD, DC, router, switch, Office, Skype, SharePoint, JChat and related workflows.
- Keep diffs focused; do not mix unrelated refactors.

## Token-saving workflow

To keep token use low:
1. Read `AGENTS.md`.
2. Read this skill.
3. Identify only the files relevant to the requested refactor.
4. Avoid scanning the whole repo unless the user requests a global audit.
5. If the request is broad, do an audit first and do not edit.
6. Prefer small phases over one large rewrite.
7. Summarize files not inspected.

## Safe workflow

Before editing:
1. State the behavior that must remain unchanged.
2. Identify affected files/functions/classes.
3. List duplicate/dead/oversized/risky code found.
4. Propose a short plan.
5. Ask for approval only if the change is broad, risky, or touches many workflows.

When editing:
1. Make one focused refactor at a time.
2. Preserve function signatures when possible.
3. Keep imports explicit.
4. Extract repeated constants/helpers only when it clearly reduces duplication.
5. Keep Tkinter UI code readable.
6. Avoid formatting-only changes that create noisy diffs.

After editing:
1. Run a syntax check when possible.
2. Run the app or relevant command when possible.
3. Report changed files.
4. Report expected unchanged behavior.
5. Report risks or anything not verified.

## Preferred improvements

### Duplicate code
Extract repeated:
- path handling,
- Tkinter widget creation helpers,
- messagebox/error display helpers,
- subprocess execution helpers,
- resource validation helpers,
- file copy/download/check helpers,
- build/version/changelog helpers.

### Oversized functions
- Split only when it improves clarity.
- Use small private helpers with clear names.
- Keep behavior identical.
- Avoid splitting just to create more files.

### Imports and dependencies
- Remove unused imports.
- Avoid heavy imports at startup when safe.
- Use local imports for optional/heavy features only if it improves startup safely.
- Do not add dependencies without approval.

### Tkinter responsiveness
- Avoid blocking the UI thread with long work.
- Use `after()` or safe threading patterns when appropriate.
- Do not update Tkinter widgets directly from background threads.
- Use queues or `root.after()` for thread-to-UI communication.
- Keep progress/status messages visible and clear.

### Startup performance
- Avoid expensive startup checks unless required.
- Delay scans until the user opens the relevant section.
- Cache safe repeated calculations.
- Do not cache volatile system state incorrectly.

### Resource checks
- Do not mark missing files as present.
- Keep green/red status accurate.
- Avoid repeated disk scans when the same safe result can be reused.
- Keep error messages actionable.

### Build and packaging
- Preserve PyInstaller command behavior.
- Preserve `upx.exe` usage.
- Keep `.spec` changes minimal and explained.
- Do not remove build resources or icons.

## Performance rule

Do not guess performance improvements. Prefer measurable or clearly safe improvements:
- less repeated work,
- fewer repeated disk scans,
- less blocking UI work,
- less startup work,
- simpler loops,
- fewer unnecessary subprocess calls.

## Definition of done

A refactor is done only when:
- intended behavior remains identical,
- syntax checks pass when possible,
- the app still starts when possible,
- changed files are listed,
- risky assumptions are stated,
- no unrelated rewrite was introduced.
