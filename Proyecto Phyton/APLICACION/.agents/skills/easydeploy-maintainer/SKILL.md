---
name: easydeploy-maintainer
description: Use for EASY DEPLOY / EasyDeploy, a Windows Python Tkinter app packaged as .exe. Trigger on UI/layout/design, Spanish text/Ñ/accents, version/changelog, PyInstaller/UPX builds, resource checks, offline installers, guides/PDFs, Exchange/SharePoint/JChat/DC/router/switch workflows, error messages, or project cleanup. Keep token use low by reading only relevant files first.
---

# EASY DEPLOY maintainer skill

## Mission

Maintain and improve EASY DEPLOY, a Windows desktop application built with Python + Tkinter and packaged as an `.exe`, while preserving existing behavior and reducing repeated mistakes.

Optimize for:
- stable app behavior,
- clear Spanish UI,
- no clipped text or crushed buttons,
- coherent design,
- safe Windows/offline installer workflows,
- correct version/changelog updates,
- reproducible PyInstaller + UPX builds,
- minimum necessary token/context usage.

## Token discipline

Before reading many files:
1. Identify the task type: UI, build/version, resources/installers, security, bugfix, or cleanup.
2. Read only the likely entry point, affected modules, build scripts, resource manifest/checker, and changelog/version code.
3. Do not read old transcripts, exported JSONL conversations, large logs, binaries, installers, PDFs, ISOs, images, or `dist/build/.venv/__pycache__` unless explicitly needed.
4. Prefer targeted search over whole-repo reading.
5. Summarize findings briefly before broad changes.
6. Do not load extra skills unless the task needs them.

## Skill composition

If the task changes UI, layout, visual hierarchy, windows, dialogs, buttons, spacing, colors, or overall design, also apply `$interface-design` if it is installed.

Use `$interface-design` only for UI/design work. Do not load it for simple version bumps, build command edits, resource-list updates, or non-UI bug fixes.

## Project identity

The project is EASY DEPLOY / EASY-DEPLOY.

Known characteristics:
- Python + Tkinter desktop app.
- Windows-focused.
- Packaged as an `.exe`.
- Uses local/offline resources and installers.
- Must work without internet when installing bundled programs or server components.
- Repository may be under paths similar to:
  - `C:\Users\amatc\Desktop\PROYECTOS\EASYDEPLOY\Proyecto Phyton\APLICACION`
  - resource root similar to `C:\Users\amatc\Desktop\PROYECTOS\EASYDEPLOY\EASY DEPLOY`
- Do not hardcode obsolete absolute paths if a relative/project-root/resource-root solution is possible.

## Non-negotiable rules

- Preserve existing business logic unless the user explicitly asks for behavior changes.
- Do not remove features silently.
- Do not introduce internet downloads for workflows that must run offline.
- Do not add dependencies without explaining why.
- Keep Windows compatibility.
- Avoid destructive cleanup unless files are clearly unused and the user requested cleanup.
- Never put secrets, passwords, license keys, API keys, or certificates in code, changelog, build scripts, or the `.exe`.
- Use Spanish UI text with correct accents, commas, `ñ`, and `Ñ`.
- Do not expose private names or implementation details in user-facing version notes.

## Version and changelog policy

When compiling, preparing a release, or making user-visible changes:
1. Check the current app version and changelog/version screen first.
2. If today already has a changelog entry, add all new user-facing changes to the same date/version entry and keep only the highest/current version for that day.
3. Do not create multiple version entries with the same date.
4. If it is a new day, increment the patch version by default unless the user requests another scheme.
5. Use Spanish dates consistently, preferably `dd/mm/yyyy`.
6. Keep newest changes at the top and oldest changes at the bottom.
7. Changelog entries must describe what changed for the user, not how it was implemented.
8. Do not add entries such as “copiado/movido internamente para no romper el programa”; phrase it as user-facing maintenance, for example “Se han reorganizado recursos para mejorar la eficiencia del programa.”
9. Do not mention private names, internal conversation details, “meses sin trabajo”, or implementation discussions.
10. Preserve historical version entries unless the user asks to rewrite them.
11. If the user says not to add a specific change to the changelog, obey that instruction.

Historical convention already used by the project:
- Initial historical line starts around version `1.0.0`.
- Old versions were distributed up to roughly `1.9.0`.
- Newer work continues from `2.0.0` onward.
- Always derive the real current version from the code, not from this skill.

## Build / `.exe` policy

When asked to compile, build, or update the `.exe`:
1. Use the existing build command or build script as the source of truth.
2. The build must use PyInstaller and UPX unless the user explicitly changes this.
3. Preserve `--clean`, `--noconfirm`, `--onefile`, `--windowed`, app name `"EASY DEPLOY"`, icon resources, and `--upx-dir` when present.
4. Verify `upx.exe` exists in the configured UPX directory before building.
5. If build paths changed, update the project’s `Crear .EXE` / `Crear exe.txt` command file with the exact command used.
6. Do not leave the user without a reproducible build command.
7. Do not compile from an obsolete folder if the current project path has changed.
8. Do not include unnecessary files in the bundle.
9. Keep icons/images/resources referenced correctly after folder reorganizations.
10. After changing build logic, state the exact command or script to run.

Known previous PyInstaller pattern to preserve/adapt:
```powershell
py -3 -m PyInstaller --clean --noconfirm --onefile --windowed --name "EASY DEPLOY" --icon "<PROJECT>\logotipo.ico" --add-data "<PROJECT>\logotipo.ico;." --add-data "<PROJECT>\EscudoRT.png;." --upx-dir "<UPX_DIR>" "<PROJECT>\EASY DEPLOY.py"
```

Adapt `<PROJECT>` and `<UPX_DIR>` to the current repository layout.

## UI / Tkinter design policy

For every UI change:
1. Prevent clipped text in all current and future dialogs.
2. Prevent crushed, narrow, or unreadable buttons.
3. Use dynamic sizing, `wraplength`, `minsize`, column/row weights, padding, and resizable-safe layouts.
4. Respect margins on top, bottom, left, and right, including when users resize windows.
5. Avoid fixed dimensions unless there is a clear reason and fallback.
6. Avoid mixing `pack`, `grid`, and `place` in the same parent container unless necessary and documented.
7. Use reusable helpers for dialogs, notices, confirmations, scrollable text, and button rows.
8. Make Yes/No, Accept/Cancel, Delete, View Password, and installer buttons wide enough for Spanish text.
9. Keep primary/secondary actions visually consistent.
10. Split two-column layouts with enough spacing so right-side text and buttons are readable.
11. Do not let new buttons inherit inconsistent sizes, colors, or fonts.
12. Use `$interface-design` for visual polish when the task touches design.

For message/confirmation windows:
- Text must grow or wrap dynamically.
- Buttons must not be compressed.
- Long messages must use scrollable or wrapped content.
- Important installer notices may need `topmost`, `transient`, and `grab_set` so the installer does not hide them.
- Blocking dialogs should not freeze the main app.

For the password/license/start window:
- Do not allow it to disappear forever when minimized.
- Avoid or remove minimize behavior if it causes unrecoverable hidden windows.
- Ensure textbox focus works even if another program/notification interrupts app startup.
- Accept/Cancel controls must be present where needed.

For dark/light mode:
- Theme switching must not close the app, leave it running in background, or freeze it.
- Avoid theme changes while a modal dialog or long task is blocking the UI.
- Use safe scheduling (`after`) and state guards where appropriate.

## Spanish text / encoding policy

All user-facing Spanish text must preserve:
- accents,
- commas,
- `ñ`,
- `Ñ`,
- inverted punctuation if used,
- readable line breaks.

When touching console output, subprocess output, logs, or text files:
- Prefer UTF-8 explicitly.
- Use `encoding="utf-8"` and `errors="replace"` where appropriate.
- Avoid mojibake in logs/consoles.
- Review common words such as `Contraseña`, `España`, `Añadir`, `Guía`, `Dirección`, `Instalación`, `Configuración`.

## Resources, installers, and guides

The app relies on local resources. When adding/removing programs, guides, installers, PDFs, icons, or resource folders:
1. Update the resource checker/manifest immediately.
2. The “Recursos” button/status must accurately show OK, incomplete, or missing.
3. If resources are incomplete, show only the missing items clearly, grouped by folder when useful.
4. If resources are missing, allow the user to select the correct resource folder again.
5. Do not relaunch the app or show the password window when the user clicks resources.
6. If resources are OK, clicking resources should open the resources folder, not restart the program.
7. Keep resource paths relative to the selected resource root where possible.

Known resource areas:
- `OTROS` for installers such as Firefox, WinRAR, Adobe Reader.
- `GUIAS` for guide PDFs.
- `OFFICE\officeoffline` for Office offline installation assets.
- Other bundled app folders may exist for SQL, Exchange, SharePoint, JChat, DC, WDS, WSUS, etc.

For PDF guide buttons:
- Buttons should open the correct PDF.
- If default PDF viewers fail, use a robust Windows open method; Edge/Explorer fallback is acceptable.
- Guide labels must use `Guía` with accent.

For offline installers:
- Do not download from the internet.
- Launch existing local installers/scripts.
- If a `.bat` only works when double-clicked/admin, launch it in the closest equivalent way.
- If a `.vbs` hidden installer exists and is the chosen solution, use it directly.
- Make user-facing messages simple: “La instalación ha comenzado” rather than raw exit-code wording unless troubleshooting requires it.

## Status widgets and prerequisites

For any checker/prerequisite workflow, including Exchange, SharePoint, JChat, DC1, DC2, firewall, routers, switches, Office, Skype, or similar:
1. Show clear status to the user.
2. Use green check/OK for installed or detected items.
3. Use red X/error for missing or failed items.
4. Apply this pattern consistently across all prerequisite checkers.
5. Do not show ambiguous orange/partial statuses for unrelated checks.
6. If a command fails, explain the likely user action, not only the raw code.

Firewall widget:
- Show green only when all Domain, Private, and Public profiles are enabled.
- Show red if any profile is disabled.
- Activation/deactivation buttons must check and report final state.

Switch/router serial workflows:
- If functions finish with code `1` or indicate no serial device, show a clear message that the console cable/port may not be connected or detected.
- Keep logs useful but give the user a clear next step.

## Error handling

Prefer actionable Spanish dialogs:
- what failed,
- likely cause,
- what the user should do next,
- whether admin rights, domain membership, resources, or reboot are required.

Avoid:
- raw stack traces as the only feedback,
- vague “error código 1” messages,
- hidden background failures,
- app freezes while long tasks run.

When long commands/installers run:
- Do not block the Tkinter UI thread.
- Use background thread/process plus safe UI updates.
- Disable relevant buttons during execution and re-enable them afterward.
- Keep progress/status visible.

## Project cleanup

When asked to reorganize:
- Move visual assets to a clear folder such as `iconos` or `assets` only after updating all references.
- Keep router/switch modules inside the app folder if they belong to the app.
- Remove old/unused files only after confirming references by search.
- Do not delete build outputs/resources/installers that are still needed for offline operation.

## Security posture

Allowed defensive improvements:
- remove hardcoded secrets,
- improve local config safety,
- validate paths,
- avoid unsafe `eval`, `exec`, `pickle`, unsafe YAML loading,
- reduce shell injection risk,
- check subprocess calls,
- keep build reproducible,
- use UPX as configured,
- recommend stronger options such as Nuitka/Cython/PyArmor only with tradeoffs.

Do not implement:
- antivirus bypass,
- stealth/persistence,
- malicious injection,
- credential theft,
- hidden behavior intended to evade security tools.

## Workflow for any task

1. Restate the concrete task in one sentence.
2. Identify the minimal files needed.
3. Inspect only those files first.
4. If UI is involved, apply `$interface-design` if available.
5. Make small, targeted changes.
6. Update version/changelog only when appropriate.
7. Update resource manifest/checker if resources changed.
8. Run a syntax check or app/build command when practical.
9. Report:
   - files changed,
   - user-visible behavior changed,
   - whether version/changelog was updated,
   - whether build command/UPX was affected,
   - remaining risks.

## Done criteria

A change is not finished until:
- the app still starts or the modified files pass basic syntax checks,
- Spanish text is readable,
- windows/dialogs do not clip text or buttons,
- resize behavior is reasonable,
- relevant resources/checkers are updated,
- changelog/version policy has been applied when needed,
- build command remains reproducible if packaging was touched.
