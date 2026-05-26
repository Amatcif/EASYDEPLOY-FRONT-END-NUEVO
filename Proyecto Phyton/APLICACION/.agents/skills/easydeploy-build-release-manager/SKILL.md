---
name: easydeploy-build-release-manager
description: Use for EASY DEPLOY release preparation, versioning, changelog handling, PyInstaller builds, UPX usage, .spec review, resource checks, build cleanup, and .exe packaging. Preserve project rules: same-day changes stay in one version, do not expose internal implementation details in the user-facing changelog, and always use upx.exe when building if available.
---

# EASY DEPLOY build release manager

## Mission

Prepare safe, repeatable EASY DEPLOY Windows `.exe` releases.

Use this skill for:
- version changes,
- changelog updates,
- PyInstaller command review,
- `.spec` maintenance,
- UPX build rules,
- resource verification,
- `dist`/`build` cleanup,
- release checklist and final build validation.

## Non-negotiable rules

- Preserve existing application behavior.
- Do not change business logic unless the release task requires it.
- Group all changes made on the same day into the same version entry.
- Do not create a new version for every tiny same-day fix unless the user explicitly asks.
- Keep user-facing changelog clean: describe visible improvements/fixes, not internal implementation noise.
- Keep Spanish text correct: ñ, Ñ, accents, punctuation, commas.
- Preserve the app name and expected Windows `.exe` output conventions.
- Always use the existing `upx.exe` for PyInstaller compression when building, if present.
- Do not remove `upx.exe` assumptions unless the user explicitly requests a no-UPX build.
- Do not include secrets, old histories, installers, ISOs, PDFs, `.venv`, `build`, or stale `dist` artifacts in source changes.

## Token-saving workflow

1. Read `AGENTS.md` first.
2. Inspect only release-relevant files first: main entry file, version/changelog locations, `.spec`, build scripts, `requirements.txt`, resource checker, and `upx.exe` path.
3. Do not scan the whole repo unless the build fails or the user asks.
4. Before compiling, show the exact command or `.spec` flow that will be used.

## Version and changelog rules

When changing version/release notes:
- Find the current version source of truth before editing.
- If today's version already exists, add the change to that same entry.
- If no current-day entry exists and the task is a release/build task, create one according to existing project style.
- Keep notes short and user-readable.
- Avoid mentioning implementation details such as helper names, internal variable names, or file rewrites unless important for maintainers.

## Build rules

Before building:
- Confirm the entry point.
- Confirm whether build uses `.spec` or direct PyInstaller command.
- Confirm `upx.exe` exists in the expected project location.
- Confirm required resources exist.
- Avoid stale output confusion by cleaning only safe build artifacts when appropriate.

When building:
- Prefer the existing known-good build method.
- If using PyInstaller directly, include UPX with an explicit `--upx-dir` when applicable.
- Do not change icons/resources silently.
- Keep paths quoted because the project path contains spaces.

After building:
- Report the output `.exe` path.
- Report the exact command used.
- Report resource or warning issues.
- Do not claim the build is verified unless it was actually executed.

## Definition of done

A release/build task is complete only when:
- version/changelog handling is correct,
- UPX rule is respected or a reason is given,
- resources are checked or limitations are stated,
- changed files are listed,
- command used or intended is shown,
- remaining risks are reported.
