# EASY DEPLOY Codex instructions

These are persistent project rules for EASY DEPLOY.

EASY DEPLOY is a Windows desktop application built with Python + Tkinter and packaged as a Windows `.exe`.

## Core rule

Preserve existing behavior unless the user explicitly asks for a behavior change.

Do not remove features, break workflows, change business logic, or rewrite the project broadly unless the user clearly requests it.

## Mandatory start-of-task protocol

Before doing any EASY DEPLOY task, read this `AGENTS.md` first.

At the start of every response, before editing files, explicitly confirm the applicable mode/risk and that `AGENTS.md` has been read. If the user asks for code changes, do not edit immediately until you have identified:

1. The exact function(s) involved.
2. The exact file(s) to touch.
3. The minimal change for each issue.
4. What will NOT be touched.
5. The risk level for each change.

If the task involves windows, focus, dialogs, Ping, AD/EXC forms, license, resources, Skype, Exchange, build, or security, treat it as high-risk and inspect the relevant existing helpers before changing behavior.

Do not proceed from an old memory of the project. Work only from the current repository files.

## Critical anti-regression rules: focus, windows, and typing

The main EASY DEPLOY window must never stay above its own child/tool windows in a way that hides them or prevents clicks/typing.

These invariants are mandatory:

- Any secondary window launched from `Sistemas`, `Redes`, `Programas`, `Guías`, `Seguridad`, `Consola`, `Herramientas`, Ping, AD/EXC, Skype, Exchange, D2/D4, Recursos, Versiones, or Créditos must open in front of EASY DEPLOY.
- Clicking an already-open tool button must restore/focus the existing singleton window instead of creating a duplicate.
- The main window must not be left as permanent `-topmost` over secondary windows.
- Secondary windows may use temporary topmost only to appear in front, and it must be released after a short delay.
- Do not use permanent `topmost` to “fix” focus problems.
- Do not use repeated `focus_force()`, repeated `lift()`, repeated `grab_set()`, or aggressive `after(...)` loops while the user is typing.
- Text entries must remain writable after repeated open/close cycles.
- If a text entry shows a cursor but does not accept text, treat it as a focus/modal/grab regression.
- If a window is visible but cannot be brought forward by clicking it, treat it as a global focus regression and stop before making unrelated UI changes.
- Large windows must not use `grab_set()` unless a truly modal workflow requires it, and any grab must be reliably released.
- `wait_window()` must not be used in a way that blocks or freezes follow-up dialogs such as Ping/Favoritos.
- Do not keep references to destroyed Entry widgets, destroyed dialogs, or stale singleton windows.
- Always clean window registries/chips when a window is closed, destroyed, restored, or invalid.

Regression checklist after touching focus/window code:

1. Open every Sistemas card and confirm its window/subwindow appears in front.
2. Open Ping monitor and press `+ Añadir ping` at least 5 times; the IP Entry must accept typing every time.
3. Open Ping Favoritos from the Ping dialog and return; the IP Entry must still accept typing.
4. Open AD/EXC forms; all entries must accept typing.
5. Open Versiones and Créditos/Acerca de; they must appear in front and not stay permanently topmost.
6. Minimize and restore multiple tool windows; no duplicate restore chips or stale registry entries.

## Current fragile areas that must not regress

The following areas have broken before and must be protected:

- License/access window:
  - Keep `LayoutMixin.input_dialog(..., initial_error=None)` compatible with `app.py`.
  - Preserve inline error display through `initial_error`.
  - Preserve logo/escudo, version text, active-license text, `Ver`, `Cancelar`, and `Entrar`.
  - Do not change license validation, hashes, or secret handling unless the task is specifically license/security.
  - Do not reintroduce a visible black square around the rounded license card.
  - Do not add focus loops; typing in the license field must remain stable.

- Ping:
  - Monitor must open in front and be singleton.
  - `+ Añadir ping` must allow typing every time, even after 5 repeated pings.
  - Favoritos must open in front, have scroll when needed, and not block/freeze the Ping input.
  - Adding favorites from the monitor should not create modal deadlocks.
  - Do not fix Ping by adding permanent topmost or unsafe grabs.

- Sistemas and child windows:
  - Nothing opened from the Sistemas tab may remain behind the main window.
  - This includes Controlador de dominio, KMS, SQL, JCHAT, Exchange, SharePoint, Skype, Net Framework, AD/EXC, D2/D4, and nested dialogs.
  - If this breaks globally, inspect window focus helpers first before changing individual modules.

- AD/EXC forms:
  - Do not change PowerShell, CSV/PS1 generation, validation rules, or user-creation logic during visual fixes.
  - The top information box must be compact and must not push the form down excessively.
  - Status/error messages must remain visible in a fixed lower status area above the bottom action buttons.
  - Buttons must remain fixed and visible.
  - `Reutilizar datos para el siguiente usuario` starts unchecked and must only ask when checked.

- Acerca de / Créditos:
  - Must open at a useful initial size.
  - Must be singleton and open in front.
  - Scrollbar should appear only when needed.
  - Do not add duplicate close buttons when native window controls already exist.

- Minimized-window selector:
  - Keep one selector/panel, not many floating chips.
  - It must support restoring individual minimized windows.
  - If a `Cerrar todas` action exists, it must close only listed/minimized windows and clean registry/chip entries.
  - Click outside the selector should close the selector panel, not destroy active windows.


## Skill selection

Prefer these skills when the task matches:

- `$easydeploy-maintainer`: general EASY DEPLOY work, UI rules, versioning, resources, Spanish text, PyInstaller/UPX builds, installers, Exchange/SharePoint/JChat/DC/router/switch workflows, cleanup.
- `$easydeploy-refactor-optimizer`: reduce duplicated code, simplify Python/Tkinter code, remove dead code, improve maintainability, preserve exact behavior.
- `$easydeploy-security-auditor`: defensive security audit, secrets, unsafe execution, subprocess, paths, packaging risk, dependency risk, local data handling.
- `$easydeploy-build-release-manager`: version/changelog, build, PyInstaller, UPX, `.spec`, resource checks, `.exe` release preparation.
- `$easydeploy-regression-qa`: review changes, detect regressions, run syntax/startup checks, validate that behavior was preserved.
- `$easydeploy-tkinter-performance`: frozen UI, slow startup, long-running tasks, progress/status responsiveness, repeated scans, Tkinter thread safety.
- `$interface-design`: UI/design improvements only, especially Tkinter layout, visual consistency, spacing, hierarchy, clipped text, crushed buttons, and resizable windows.

For important tasks, combine `$easydeploy-maintainer` with the specialist skill.

Examples:

- Build/release: `$easydeploy-maintainer` + `$easydeploy-build-release-manager`
- Refactor: `$easydeploy-maintainer` + `$easydeploy-refactor-optimizer`
- Security: `$easydeploy-maintainer` + `$easydeploy-security-auditor`
- Regression review: `$easydeploy-maintainer` + `$easydeploy-regression-qa`
- Performance: `$easydeploy-maintainer` + `$easydeploy-tkinter-performance`
- Visual UI: `$easydeploy-maintainer` + `$interface-design`

## Token economy

Use the minimum context needed.

- Read only files relevant to the current task first.
- Prefer targeted search before whole-project review.
- Do not read old JSONL histories, binaries, installers, PDFs, ISOs, `dist`, `build`, `.venv`, `venv`, `__pycache__`, or large generated folders unless the user explicitly asks.
- If the task is broad, audit first and propose phases before editing.
- Keep diffs small and focused.
- Avoid broad formatting-only changes.

## Spanish text and encoding

Preserve Spanish text correctly.

- Keep `ñ`, `Ñ`, accents, `¿`, `¡`, commas, punctuation, and spacing correct.
- Do not replace Spanish with English unless requested.
- Do not simplify messages by removing useful user guidance.
- Do not introduce mojibake or encoding regressions.
- When fixing UI clipping, keep the meaning of the original text.

## Tkinter UI rules

For all UI changes:

- Do not allow clipped text.
- Do not create crushed or tiny buttons.
- Respect margins and padding when the user resizes windows.
- Keep windows readable at normal sizes.
- Group related controls in frames.
- Use consistent spacing, labels, and button sizes.
- Avoid mixing `pack`, `grid`, and `place` in the same container unless there is a clear reason.
- Prefer reusable style/layout helpers when this reduces duplication safely.
- Do not change logic while making visual improvements unless necessary and explained.
- If the design task is significant, use `$interface-design`.

## Secondary windows and dialogs

For every new secondary window, form, confirmation, assistant, or dialog:

- Use the common EASY DEPLOY dialog/window shell when it exists.
- Do not create `Toplevel` windows with huge fixed heights unless the content really needs them.
- Confirmation dialogs must size to their content with reasonable margins.
- Medium and large windows should be resizable when it makes sense for their content.
- Assistants such as D2/D4 must keep coherent `Volver`, `Cerrar`, or `Cancelar` controls.
- Avoid permanent `topmost` unless the dialog is genuinely critical.
- Do not block resize with heavy reflows or repeated rebuilds.
- Do not mix legacy visual styles when a common helper is available.
- Preserve Dark/Light mode in all secondary windows.
- Do not leave giant blank gaps between the message/content and the button row.

## Secondary window lifecycle rules

These rules are mandatory for every secondary window, large dialog, form, assistant, result window, and minimizable notice.

### Opening behavior

- Secondary windows must open in front of EASY DEPLOY when the user presses their button.
- They must not remain permanently above every other Windows application.
- To bring a window forward, prefer a common helper that:
  - restores/deiconifies the window if minimized,
  - calls `lift()`,
  - gives focus with `focus_force()` or `focus_set()` when safe,
  - applies `attributes("-topmost", True)` only temporarily,
  - removes topmost automatically after 300-500 ms.
- Do not use permanent `topmost` for ordinary tools such as Info Sistema, Top Procesos, Roles, D2/D4, AD/EXC forms, Recursos, Versiones, Créditos, or Ping.
- Use permanent modal behavior only for short critical confirmations or inputs where blocking is intentional.

### Singleton behavior

- Large/informative/assistant windows must be singleton by key.
- If a window is already open and the user presses the same button again:
  - do not create a duplicate window,
  - restore it if minimized,
  - bring it to the front,
  - give it focus,
  - do not create another internal restore chip.
- Use a central registry on the app instance when possible, for example:
  - `_secondary_windows: dict[str, window]`
  - `_register_secondary_window(key, window)`
  - `_unregister_secondary_window(key)`
  - `_focus_secondary_window(key)`
  - `_show_or_focus_secondary_window(key, factory)`
- Do not use loose module-level globals for active windows.
- Clean the registry when a window closes, is destroyed, restored, or becomes invalid.
- Before creating any new large window, check the registry first.

Windows that should be singleton unless there is a specific reason not to:
- D2/D4 DFSR SYSVOL,
- Crear usuarios AD,
- Crear usuarios EXC,
- Info Sistema / Comprobar entorno,
- Top Procesos,
- Ver roles instalados,
- Estado de Almacenamiento,
- Versiones,
- Créditos,
- resource/status/result windows,
- any other medium/large `CTkToplevel` or native `Toplevel` used as a tool window.

### Minimize / restore chip behavior

- Internal minimized buttons/chips must also be singleton by key.
- One window key may have at most one restore chip/button.
- If a restore chip already exists, do not create another.
- If the user minimizes the same tool repeatedly, update/focus the existing chip instead of adding duplicates.
- When the window is restored, remove or hide its restore chip.
- When the window is closed, remove its restore chip and clear the window registry.
- If the original button is pressed while the window is minimized, restore/focus the existing window rather than creating a new one.
- Apply this to all minimizable internal notices and tools, including Ping/favorites/common target dialogs, Credits, Versions, AD/EXC forms, D2/D4, Repadmin/status windows, Privilegios, Teclado ESP, DC1/DC2 tools, Unir equipo a dominio, Políticas de grupo, and similar tool windows.

### Native vs frameless windows

- For medium/large windows that need normal Windows behavior, prefer native windows:
  - `overrideredirect(False)`,
  - `resizable(True, True)`,
  - sensible `minsize(...)`.
- Use frameless windows only when the custom shell provides all expected controls: close, cancel/back where needed, minimize/restore, focus handling, and no duplicate restore chips.
- If a frameless window cannot be minimized, restored, or resized correctly, convert it to native Windows chrome unless there is a strong visual reason not to.
- Do not use `grab_set()` on large informational windows unless blocking is required. If `grab_set()` is necessary for a true modal form, ensure minimizing/restoring and closing still work.

### Dialog sizing

- Small confirmations should be compact and content-sized.
- Do not calculate a large fixed height before content is built and then anchor buttons at the bottom.
- The button row should be close to the content with normal margin.
- For long text, use a maximum height with scroll instead of leaving large blank gaps.
- Avoid `pack(expand=True)` or weighted empty frames that push buttons to the bottom unless the layout genuinely needs it.
- Test common confirmations such as Crear usuarios AD, Crear usuarios EXC, Permisos Skype, and Puntero DNS Skype for giant blank gaps.

## EASY DEPLOY frontend design system rules

When doing visual/frontend work, follow the current EASY DEPLOY design direction.

- Use `.interface-design/system.md` as the visual source of truth when present.
- Use `easy_deploy_app/ui/design_tokens.py` for palette/skin values when safe.
- Keep the visual style professional, minimal, technical, and macOS-inspired without copying macOS literally.
- Prefer neutral graphite/zinc/marfil surfaces, soft borders, subtle hovers, and desaturated state colors.
- Avoid saturated, flashy, or inconsistent colors unless they represent danger/warning/success.
- Keep Light mode comfortable, not pure white; use the marfil/soft-neutral direction.
- Keep Dark mode sober and readable.
- Preserve `Segoe UI` as the default UI font. Do not introduce external fonts.
- Use consistent button families: primary, secondary, danger, warning, ghost, success, info.
- Use consistent cards, badges, chips, form fields, dialog shells, and section headers.
- Do not mix old legacy visual styles with the new design system when a common helper exists.
- Do not make large visual changes and logic changes in the same pass.
- Do not touch `_build_adaptive_page()` or `show_frame()` during visual polish unless the task is specifically about those functions.
- Do not reintroduce expensive reflows, repeated rebuilds, or `update_idletasks()` during resize.
- Do not claim a palette/skin change is complete unless it visibly affects at least the sidebar, main background, cards, topbar, buttons, borders, and active/hover states.
- If a palette selector exists, changing palette should either apply visibly in-session or clearly state which areas require reopening/rebuilding.
- Palette persistence must store only UI settings such as `skin` and `appearance_mode`, preferably in `LOCALAPPDATA\EasyDeploy\ui_settings.json`; never store secrets.



## Current frontend handoff state

As of the latest frontend pass, treat the current UI baseline as the active work state unless the user provides newer files.

Current recorded release state:
- `APP_VERSION` should be at least `2.2.5.4` if the latest QA regression-fix pass has been applied. Always verify the real current value in `easy_deploy_app/constants.py` before editing.
- The latest user-facing visual changes include: softer Light/Dark skins, palette support, a single `Apariencia` button, `Versiones` and `Créditos` moved into `Herramientas`, removal of `Reiniciar UI` and `Salir` from `Herramientas`, a subtle vertical separator between sidebar and content, singleton secondary windows, a unified minimized-window selector, and fixed text-entry focus behavior.
- Recent fragile fixes include Net Framework 3.5 from `OTROS\NetFramework3.5.iso`, safe ISO dismount after successful use, Ping/focus stabilization attempts, compact AD/EXC status areas, Acerca de sizing, minimized-window selector improvements, and removal of the visible black exterior square around the license card. Treat these as protected regressions and verify them manually if touched.

Important handoff rules:
- Always work from the latest files the user provides. Do not reuse older generated ZIP contents if the user has made further changes.
- If a change affects UI structure, request or inspect the latest `easy_deploy_app/ui/layout.py` first.
- If a change affects tool windows, minimized windows, focus, or popups, inspect `layout.py` and the relevant task/action file before editing.
- If a change affects version/changelog, update `constants.py` and `changelog.py` together.
- When continuing frontend work, first preserve the latest fixes for focus, window singleton behavior, minimized-window selector, topbar/tools placement, and sidebar separator.

## Input focus and typing stability rules

Text-entry dialogs and forms must be stable while the user types.

- Do not create repeated focus loops for inputs.
- Do not schedule cascades of `focus_force()`, `grab_set()`, `_focus_secondary_window()`, or repeated `after(...)` calls while the user is typing.
- For entry widgets, prefer one initial `focus_set()` plus `icursor("end")` after the window is visible.
- Use topmost only temporarily to bring the dialog forward, then release it.
- Do not call the generic secondary-window focus helper repeatedly on active text-entry dialogs.
- Do not use validation handlers that constantly rewrite the text or steal focus while the user types.
- If auto-formatting is needed, prefer formatting after submit rather than while typing, unless the feature has already been tested thoroughly.
- Test focus-sensitive fields after UI changes: license/password prompt, KMS/product-key input, Ping destination/name, AD user fields, EXC user fields, Skype FQDN/IP fields, and any `ui_input_dialog()` usage.
- If a cursor flickers rapidly or input loses focus, treat it as a regression and inspect focus/topmost/grab/after logic before changing visuals.

## Minimized-window selector rules

EASY DEPLOY uses a unified minimized-window selector instead of stacking many restore buttons across the top of the app.

- Do not create one visible restore button per minimized window across the topbar/content area.
- Keep a single restore control such as `Ventanas minimizadas (N)` when multiple windows are minimized.
- The selector should open a compact dropdown/panel listing minimized windows so the user can restore exactly one.
- The selector must not overlap `Apariencia`, topbar buttons, page title, or sidebar content.
- Place the selector below the topbar/content header area with safe margins.
- Restoring one item must close/hide the selector and leave other minimized windows minimized.
- Closing/restoring a window must clean its registry entry and its minimized selector item.
- If a window is already minimized and its original launch button is pressed again, restore/focus the existing window rather than creating a new window or selector entry.

## Topbar, tools menu, and appearance rules

The current desired topbar is intentionally clean.

- Keep `Apariencia` as the single compact topbar control for visual settings.
- `Apariencia` should contain both palette/skin selection and Light/Dark mode selection.
- Do not re-add separate topbar buttons for `Versiones`, `Créditos`, `Paleta`, or standalone `Light/Dark` unless the user explicitly asks.
- `Versiones` and `Créditos` should be available from the `Herramientas` menu near the bottom in a clear EASY DEPLOY section.
- Do not re-add `Reiniciar UI` or `Salir` to `Herramientas`; the native window close button already covers normal exit and the user requested those actions removed.
- The sidebar/content separator should remain subtle, vertical, not full height, and palette-aware. It should not reach the very top or bottom of the app.
- Palette changes should remain visibly meaningful. A palette change is not complete if only hidden variables change and the user cannot see a clear difference in sidebar, content background, cards, topbar, buttons, borders, and active/hover states.

## Native-window close-control rules

When a secondary window uses native Windows chrome, avoid duplicate close controls.

- If a window has the native Windows titlebar with minimize/maximize/close, do not add an extra custom `x` button inside the content header.
- Internal `Cerrar`, `Cancelar`, `Volver`, or action buttons are allowed when they are part of the workflow.
- D2/D4, Crear usuarios AD, and Crear usuarios EXC should not show a redundant internal `x` when they already have native close controls.
- For frameless windows, provide all expected controls explicitly: close, minimize/restore where applicable, focus behavior, drag behavior, and no duplicate restore chips.

## Refactor and optimization rules

When reducing or improving code:

- Preserve exact behavior.
- Do not change business logic.
- Do not remove workflows.
- Do not rename public functions/classes/files unless necessary and safe.
- Do not minify Python code or make it unreadable just to reduce line count.
- Do not use `eval`, `exec`, or dynamic hacks to reduce code.
- Remove duplicated code only when the shared helper is clear and safe.
- Split large functions only when it improves clarity and maintainability.
- Run syntax checks when possible.

## Performance rules

When improving fluency/responsiveness:

- Avoid blocking the Tkinter main thread with long tasks.
- Do not update Tkinter widgets directly from background threads.
- Use `root.after()` or a queue-based pattern for background-to-UI updates.
- Avoid heavy startup checks unless required.
- Delay expensive resource scans until needed when safe.
- Avoid repeated disk scans for the same resource set in a single action.
- Do not guess performance improvements; explain assumptions.

## Security rules

Security work must be defensive.

- Look for hardcoded secrets, tokens, passwords, private URLs, certificates, and keys.
- Review risky uses of `eval`, `exec`, `pickle`, `marshal`, unsafe YAML loading, `os.system`, and `subprocess(..., shell=True)`.
- Validate file paths, temp files, resource writes, and deletion logic.
- Do not implement stealth, antivirus bypass, persistence, credential theft, offensive injection, or evasion.
- Do not claim the `.exe` is impossible to reverse engineer.
- Do not store secrets inside the packaged client.


## Source exposure and temporary file protection

EASY DEPLOY must not expose Python source files to users or write extracted `.py` modules into temporary/system folders during normal use, compilation, packaging, startup, or feature execution.

Rules:

- Do not generate, copy, unpack, or leave `.py` source files in `%TEMP%`, `%TMP%`, `C:\Windows\Temp`, user profile temp folders, desktop folders, logs folders, resource folders, or any other external/system location.
- Do not implement workflows that require extracting internal Python modules to disk so the app can execute them.
- Keep internal modules packaged inside the application/project structure and call them through normal imports or bundled package mechanisms.
- If a feature needs helper code, keep it as an internal module in `easy_deploy_app/` or another approved project package, not as a generated temp script.
- Build scripts, `.spec` files, packaging helpers, and runtime code must be reviewed to ensure they do not emit `.py` files outside the project source tree.
- When compiling with PyInstaller, verify that runtime extraction does not leave readable project `.py` files behind in accessible temp/log folders.
- Do not add `--add-data` or copy steps that expose raw `.py` files unless explicitly required for development-only tooling and clearly excluded from release builds.
- Avoid `tempfile`, manual extraction, `shutil.copy`, `Path.write_text`, or similar runtime code that writes Python source to disk for later execution.
- If a temporary file is unavoidable for non-source data, use a safe temporary location, avoid secrets/source code, clean it up reliably, and document why it is needed.
- During security/build reviews, search for generated `.py` artifacts and cleanup risks in packaging scripts, `.spec` files, logs, temp handling, and helper launchers.
- Before release/build, check that no readable copies of sensitive `.py` files such as router/switch helpers, internal task modules, or security-sensitive logic are being produced outside the packaged app.
- If any code path is found writing `.py` files to temp or external folders, treat it as a security regression and fix it before release.

Expected checks when relevant:

- Search the repo for `.py` writes/copies/extractions involving `%TEMP%`, `%TMP%`, `tempfile`, `shutil.copy`, `copytree`, `write_text`, `open(..., "w")`, PyInstaller `.spec` `datas`, build scripts, and helper launchers.
- After compiling, inspect `%TEMP%`, `%TMP%`, `C:\Windows\Temp`, project `logs`, `dist`, and other generated locations for unexpected readable `.py` files.
- Report clearly whether any `.py` exposure was found and what was changed to prevent it.

## Version, changelog, and release rules

When compiling, preparing release changes, or when the user asks to update versions/changelog:

- Update version/changelog only when the task is about a release/build or the user asks.
- Use a four-number version scheme when changes are being recorded: `major.minor.daily.change`, for example `2.2.2.1`.
- The third number is the daily version counter. Each new calendar day with changes increments the third number by 1. Example: `16/05/2026 = 2.2.2.x`, `17/05/2026 = 2.2.3.x`, `18/05/2026 = 2.2.4.x`.
- The fourth number is the same-day change counter. It increases every time changes are applied on that same day, including small fixes when they affect the release/changelog. Example: first change of the day `2.2.2.1`, tenth significant change of the same day `2.2.2.10`.
- When a new day starts, increment the third number and reset the fourth number to `.1` for the first recorded change of that day.
- Do not create multiple changelog entries with the same date. Keep one entry for the day and update its version to the latest fourth-number counter for that day.
- Add new same-day changes at the top of that day's existing changelog list, keeping entries short and user-readable.
- Do not duplicate solved fixes across later dates. If a fix was already recorded on an earlier date, do not repeat it unless the later change is a genuinely new regression fix with a different user-visible result.
- Do not expose internal implementation details in the user-facing changelog.
- Preserve the real current version source of truth and derive the next number from it before editing.
- Before compiling, show the exact build command or `.spec` method.
- Always use `upx.exe` for PyInstaller compression if available and applicable.
- Keep paths quoted because the project path contains spaces.

## Resources and offline installers

When touching resources:

- Preserve resource-check behavior.
- Do not mark missing resources as present.
- Keep green/red prerequisite indicators accurate.
- Preserve offline installer behavior.
- Do not break PDF guide buttons, icons, installer paths, `upx.exe`, or bundled scripts.
- Do not relaunch the app or ask for a password when pressing resource-related buttons unless the existing behavior requires it.

## Error handling

Errors shown to the user should be clear and actionable.

- Do not hide failures silently.
- Do not expose secrets in error messages.
- Keep Spanish messages understandable.
- Preserve useful context such as missing file name, failed command, or section affected.

## QA expectations

After edits:

- List changed files.
- State what behavior should remain unchanged.
- Run syntax checks when possible.
- Start the app if possible and relevant.
- If a build was requested, report command, output path, UPX handling, and any warnings.
- If something was not verified, say so clearly.
