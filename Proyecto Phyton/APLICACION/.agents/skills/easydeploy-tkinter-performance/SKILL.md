---
name: easydeploy-tkinter-performance
description: Use to improve EASY DEPLOY Tkinter responsiveness, startup time, long-running task handling, progress reporting, resource scan efficiency, and UI non-blocking behavior. Preserve exact behavior and Spanish UI text. Do not use for visual redesign; combine with interface-design only when the task is also visual.
---

# EASY DEPLOY Tkinter performance

## Mission

Make EASY DEPLOY feel faster and more responsive without changing what it does.

Use this skill for:
- frozen UI issues,
- slow startup,
- long-running button actions,
- progress/status responsiveness,
- repeated filesystem scans,
- subprocess calls that block the UI,
- slow resource checks,
- heavy imports at startup.

## Non-negotiable rules

- Preserve exact behavior and workflows.
- Do not change business logic.
- Do not change Spanish UI text unless fixing encoding, accents, punctuation, or clipping.
- Do not update Tkinter widgets directly from background threads.
- Do not add dependencies unless the user explicitly approves.
- Do not create unsafe concurrency.
- Respect EASY DEPLOY versioning/build/resource rules from `AGENTS.md`.

## Token-saving workflow

1. Read `AGENTS.md` first.
2. Inspect only the slow/frozen screen or function first.
3. Trace only directly related callbacks, subprocess calls, resource checks, and imports.
4. Do not scan the entire project unless necessary.

## Tkinter responsiveness rules

- Keep long work out of the main UI thread when safe.
- Use `threading` only for background work that does not directly touch widgets.
- Use `queue.Queue` or `root.after()` to send updates back to Tkinter safely.
- Keep progress messages clear and frequent enough for users.
- Disable/re-enable buttons safely during long operations if needed.
- Avoid recursive `after()` loops without cancellation/stop conditions.

## Startup performance rules

- Avoid heavy scans during startup unless required.
- Delay expensive checks until the relevant section is opened.
- Cache stable results only when safe.
- Do not cache volatile system state incorrectly.
- Prefer local imports for heavy optional modules when it improves startup safely.

## Resource scan rules

- Avoid repeated disk scans for the same resource set in a single action.
- Keep missing-resource detection accurate.
- Preserve green/red status behavior.
- Preserve clear error messages.

## Subprocess rules

- Avoid blocking the UI during long subprocess operations.
- Capture output safely when needed.
- Show progress/status instead of leaving the user with a frozen window.
- Keep command arguments safe and quoted.

## Definition of done

A performance change is complete only when:
- behavior is intended to remain identical,
- UI-thread safety is considered,
- changed files are listed,
- checks are run when possible,
- any unverified responsiveness improvement is clearly stated.
