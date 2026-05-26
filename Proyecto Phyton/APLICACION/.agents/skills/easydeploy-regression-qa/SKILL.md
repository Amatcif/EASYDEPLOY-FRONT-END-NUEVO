---
name: easydeploy-regression-qa
description: Use after changes to EASY DEPLOY to detect regressions, review diffs, run syntax/startup checks, verify Tkinter/UI behavior, resource paths, Spanish text, version/build rules, and unintended logic changes. Focus on preventing breakage after edits.
---

# EASY DEPLOY regression QA

## Mission

Catch regressions after Codex changes EASY DEPLOY.

Use this skill for:
- final review after edits,
- before/after diff inspection,
- syntax checks,
- startup checks,
- Tkinter layout regression review,
- resource path checks,
- build/release preflight,
- ensuring no unrelated logic changed.

## Non-negotiable rules

- Do not add new features during QA.
- Do not refactor during QA unless fixing a regression caused by the current change.
- Do not hide risky changes in broad formatting diffs.
- Preserve Spanish text and punctuation.
- Preserve version/changelog/UPX rules from `AGENTS.md`.
- Prefer targeted checks over scanning unrelated directories.

## Token-saving workflow

1. Read `AGENTS.md`.
2. Review only files changed in the current task first.
3. Inspect directly affected imports, callers, and UI screens.
4. Avoid `dist`, `build`, `__pycache__`, `.venv`, installers, PDFs, ISOs, and old JSONL histories.
5. If broader checking is needed, explain why.

## QA checklist

### Python correctness
- Syntax check changed Python files.
- Look for missing imports, unused variables introduced by the patch, unreachable code, and broken function signatures.
- Check that moved helpers are imported correctly.

### Behavior preservation
- Compare intent before/after.
- Confirm no business logic was changed unless requested.
- Confirm no existing workflow was removed.
- Confirm no user-facing text changed unintentionally.

### Tkinter/UI checks
- Check text clipping risk.
- Check buttons are not crushed or too small.
- Check resizable windows keep margins/padding.
- Check layout managers are not mixed unsafely in the same container.
- Check long tasks are not newly blocking the UI.

### Resource and path checks
- Check icons, PDFs, offline installers, scripts, `upx.exe`, and bundled resources still resolve.
- Check paths with spaces are quoted safely.
- Check resource-check green/red logic is preserved.

### Build/release checks
- If the task touched release/build files, verify version/changelog rules.
- If compiling, verify UPX usage and command accuracy.

## Output format

Report:
1. Checks performed.
2. Issues found.
3. Fixes applied, if any.
4. Files changed.
5. Checks not performed and why.
6. Remaining risks.

## Definition of done

QA is complete only when changed files were reviewed, syntax/startup checks were attempted when possible, and any unverified areas are clearly stated.
