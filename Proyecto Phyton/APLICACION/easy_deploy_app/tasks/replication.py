# -*- coding: utf-8 -*-
"""Herramientas de replicación AD/DFSR para Easy Deploy.

Incluye:
- Repadmin: fuerza KCC, SyncAll y muestra resumen de replicación.
- D2/D4: asistente guiado por pasos para recuperación DFSR SYSVOL.

Las acciones D2/D4 están separadas por botones para que el operador pueda
coordinar el orden entre DCs sin ejecutar todo de golpe.
"""

import os
import re
import subprocess
import threading
import time

import customtkinter as ctk

from ..core.sysutils import SysUtils


DFSR_EVENT_LOG = "DFS Replication"


def show_repadmin_tool(app):
    """Confirma y lanza una sincronización AD/KCC con repadmin."""
    if not SysUtils.is_admin():
        app.ui_showerror(
            "Repadmin",
            "Repadmin necesita permisos de Administrador.\n\n"
            "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
        )
        return

    if not app.ui_askyesno(
        "Repadmin SyncAll",
        "Esta acción fuerza la topología KCC y la replicación de Active Directory.\n\n"
        "Se intentará detectar el PDC Emulator del dominio y ejecutar:\n\n"
        "- repadmin /kcc *\n"
        "- repadmin /syncall <PDC> /AdeP\n"
        "- repadmin /replsummary\n\n"
        "Es recomendable ejecutarlo desde un Controlador de Dominio.\n\n"
        "¿Quieres continuar?",
    ):
        return

    app.iniciar_tarea(task_repadmin_syncall, app)


def show_d2_d4_tool(app):
    """Abre el asistente moderno D2/D4 DFSR SYSVOL.

    La ventana es nativa/redimensionable y se registra como singleton para evitar
    abrir varias copias del asistente. No usa grab_set ni wait_window para no
    romper minimizar, maximizar ni resize de Windows.
    """
    if not SysUtils.is_admin():
        app.ui_showerror(
            "D2 / D4 DFSR",
            "El asistente D2/D4 necesita permisos de Administrador.\n\n"
            "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
        )
        return

    window_key = "d2_d4"
    if hasattr(app, "_focus_secondary_window") and app._focus_secondary_window(window_key):
        return

    colors = getattr(app, "colors", {})
    panel_fg = (colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22"))
    card_fg = (colors.get("card_light", "#F7F8FA"), colors.get("card_dark", "#26262A"))
    card_hover = (colors.get("card_hover_light", "#F1F5F4"), colors.get("card_hover_dark", "#2A2A2F"))
    border = (colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40"))
    accent = colors.get("accent", "#2F9E8F")
    warning = colors.get("warning", "#D97706")
    danger = colors.get("danger", "#B42318")
    secondary = colors.get("secondary", "#4B5563")
    secondary_hover = colors.get("secondary_hover", "#374151")
    accent_hover = colors.get("accent_hover", "#258176")

    try:
        width = min(1240, max(1040, app.winfo_screenwidth() - 100))
        height = min(860, max(720, app.winfo_screenheight() - 100))
    except Exception:
        width, height = 1120, 760

    dialog = ctk.CTkToplevel(app)
    dialog.title("D2 / D4 DFSR SYSVOL")
    dialog.resizable(True, True)
    dialog.minsize(960, 680)
    dialog.overrideredirect(False)
    dialog.configure(fg_color=panel_fg)
    app._center_window(dialog, width, height)
    if hasattr(app, "_register_secondary_window"):
        app._register_secondary_window(window_key, dialog)

    danger_warning = (
        "Este paso modifica DFSR/SYSVOL en Active Directory o toca el servicio DFSR.\n\n"
        "Hazlo solo si estás siguiendo el orden correcto y tienes claro qué DC tiene el SYSVOL bueno."
    )

    flows = [
        {
            "title": "1. Diagnóstico",
            "badge": "INFO",
            "accent": accent,
            "subtitle": "Mirar estado antes de tocar nada.",
            "detail": (
                "Usa este apartado primero. No cambia nada peligroso: solo consulta el contexto del DC, "
                "el estado del servicio DFSR y eventos recientes. Sirve para saber desde qué máquina estás trabajando."
            ),
            "steps": [
                ("Detectar dominio, PDC y SYSVOL", "detect_context", None, accent),
                ("Estado del servicio DFSR", "dfsr_service_status", None, secondary),
                ("Últimos eventos DFSR", "check_recent_events", None, secondary),
                ("Resumen Repadmin", "repadmin_summary", None, secondary),
            ],
        },
        {
            "title": "2. Repadmin",
            "badge": "REP",
            "accent": "#0F766E",
            "subtitle": "Forzar réplica normal de Active Directory.",
            "detail": (
                "Usa Repadmin cuando solo quieres empujar la replicación de AD entre DCs. "
                "No marca ningún DC como autoritativo ni no autoritativo para SYSVOL."
            ),
            "steps": [
                ("Forzar KCC + SyncAll", "repadmin_syncall", None, accent),
                ("Solo resumen replsummary", "repadmin_summary", None, secondary),
            ],
        },
        {
            "title": "3. D2 no autoritativo",
            "badge": "D2",
            "accent": warning,
            "subtitle": "Para un DC que debe recibir SYSVOL desde el DC bueno.",
            "detail": (
                "Ejecuta este flujo en cada DC que esté mal y deba reconstruir SYSVOL. "
                "No lo ejecutes en el DC que usarás como origen bueno.\n\n"
                "Orden típico: FALSE en este DC → Repadmin desde PDC/DC bueno → PollAD → 4114 → TRUE → PollAD → 4614/4604."
            ),
            "steps": [
                ("1. Poner msDFSR-Enabled = FALSE", "d2_disable_local", danger_warning, warning),
                ("2. Ejecutar DFSRDIAG POLLAD", "dfsr_pollad", None, accent),
                ("3. Buscar evento 4114", "check_4114", None, secondary),
                ("4. Poner msDFSR-Enabled = TRUE", "d2_enable_local", danger_warning, warning),
                ("5. Ejecutar DFSRDIAG POLLAD", "dfsr_pollad", None, accent),
                ("6. Buscar eventos 4614 / 4604", "check_4614_4604", None, secondary),
            ],
        },
        {
            "title": "4. D4 autoritativo / DC bueno",
            "badge": "D4",
            "accent": danger,
            "subtitle": "Solo en el DC que tiene el SYSVOL correcto.",
            "detail": (
                "Este flujo se ejecuta solo en el DC que contiene las GPO y scripts correctos. Normalmente será el PDC Emulator, "
                "pero lo importante es que sea el DC con SYSVOL bueno.\n\n"
                "Antes de seguir, detén DFSR en todos los DCs y prepara los demás DCs como no autoritativos."
            ),
            "steps": [
                ("1. DFSR manual + detener", "dfsr_manual_stop", danger_warning, danger),
                ("2. Marcar D4: FALSE + options=1", "d4_authoritative_disable", danger_warning, danger),
                ("3. Forzar Repadmin", "repadmin_syncall", None, accent),
                ("4. Iniciar DFSR", "dfsr_start", danger_warning, warning),
                ("5. Buscar evento 4114", "check_4114", None, secondary),
                ("6. Poner msDFSR-Enabled = TRUE", "d4_authoritative_enable", danger_warning, danger),
                ("7. Repadmin + PollAD", "repadmin_pollad", None, accent),
                ("8. Buscar evento 4602", "check_4602", None, secondary),
                ("9. Dejar DFSR automático", "dfsr_auto", danger_warning, secondary),
            ],
        },
        {
            "title": "5. D4 en DC secundario",
            "badge": "DC",
            "accent": "#7C3AED",
            "subtitle": "Para los DCs que recibirán SYSVOL del DC bueno.",
            "detail": (
                "Este flujo se ejecuta en cada DC que NO será el origen bueno durante un D4. "
                "Coordínalo con el flujo D4 del DC bueno/PDC.\n\n"
                "Orden local: detener DFSR → FALSE → esperar Repadmin del DC bueno → iniciar DFSR → 4114 → TRUE → PollAD → 4614/4604."
            ),
            "steps": [
                ("1. DFSR manual + detener", "dfsr_manual_stop", danger_warning, danger),
                ("2. Poner msDFSR-Enabled = FALSE", "d2_disable_local", danger_warning, warning),
                ("3. Revisar/esperar Repadmin del DC bueno", "repadmin_summary", None, secondary),
                ("4. Iniciar DFSR", "dfsr_start", danger_warning, warning),
                ("5. Buscar evento 4114", "check_4114", None, secondary),
                ("6. Poner msDFSR-Enabled = TRUE", "d2_enable_local", danger_warning, warning),
                ("7. Ejecutar DFSRDIAG POLLAD", "dfsr_pollad", None, accent),
                ("8. Buscar eventos 4614 / 4604", "check_4614_4604", None, secondary),
                ("9. Dejar DFSR automático", "dfsr_auto", danger_warning, secondary),
            ],
        },
    ]

    selected = {"index": 0}
    nav_buttons = {}

    def close_dialog(event=None):
        try:
            if hasattr(app, "_unregister_secondary_window"):
                app._unregister_secondary_window(window_key)
        except Exception:
            pass
        try:
            dialog.destroy()
        except Exception:
            pass

    def run_action(action_key, title, warning_text=None):
        if warning_text:
            proceed = app.ui_askyesno(title, warning_text + "\n\n¿Ejecutar este paso ahora?")
            if not proceed:
                try:
                    if hasattr(app, "_focus_secondary_window"):
                        app._focus_secondary_window(dialog)
                except Exception:
                    pass
                return
        close_dialog()
        app.iniciar_tarea(task_dfsr_action, app, action_key)

    root = ctk.CTkFrame(
        dialog,
        fg_color=panel_fg,
        border_width=1,
        border_color=border,
        corner_radius=8,
    )
    root.pack(fill="both", expand=True, padx=12, pady=12)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    accent_line = ctk.CTkFrame(root, height=4, fg_color=warning, corner_radius=3)
    accent_line.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
    body.grid_columnconfigure(0, weight=0, minsize=278)
    body.grid_columnconfigure(1, weight=1)
    body.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(
        body,
        fg_color=card_fg,
        border_width=1,
        border_color=border,
        corner_radius=8,
        width=278,
    )
    left.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
    left.grid_propagate(False)
    left.grid_columnconfigure(0, weight=1)
    left.grid_rowconfigure(8, weight=1)

    header = ctk.CTkFrame(left, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=14, pady=(16, 10))
    header.grid_columnconfigure(1, weight=1)

    badge = ctk.CTkFrame(header, width=38, height=38, fg_color=("#FEF3C7", "#342A14"), corner_radius=8)
    badge.grid(row=0, column=0, rowspan=2, padx=(0, 10), sticky="n")
    badge.grid_propagate(False)
    ctk.CTkLabel(
        badge,
        text="D2\nD4",
        font=("Segoe UI", 11, "bold"),
        text_color=warning,
    ).pack(fill="both", expand=True)

    ctk.CTkLabel(
        header,
        text="D2 / D4 DFSR SYSVOL",
        font=("Segoe UI", 18, "bold"),
        anchor="w",
    ).grid(row=0, column=1, sticky="ew")
    ctk.CTkLabel(
        header,
        text="Recuperación guiada de SYSVOL",
        font=("Segoe UI", 11, "bold"),
        text_color=warning,
        anchor="w",
    ).grid(row=1, column=1, sticky="ew", pady=(2, 0))

    ctk.CTkLabel(
        left,
        text="Primero usa Diagnóstico. Usa D4 solo si sabes con seguridad qué DC tiene el SYSVOL bueno.",
        font=("Segoe UI", 12),
        text_color=("gray35", "gray72"),
        wraplength=238,
        justify="left",
        anchor="w",
    ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

    def select_flow(index):
        selected["index"] = index
        for idx, button in nav_buttons.items():
            flow = flows[idx]
            if idx == index:
                button.configure(
                    fg_color=(colors.get("sidebar_active", "#E7F5F2") if isinstance(colors.get("sidebar_active"), str) else colors.get("sidebar_active", ("#E7F5F2", "#263432"))),
                    border_color=flow["accent"],
                    text_color=flow["accent"],
                )
            else:
                button.configure(
                    fg_color="transparent",
                    border_color=border,
                    text_color=("gray20", "gray86"),
                )
        render_flow(flows[index])

    for idx, flow in enumerate(flows, start=0):
        btn = ctk.CTkButton(
            left,
            text=f"{flow['badge']}  {flow['title']}",
            height=38,
            corner_radius=8,
            anchor="w",
            fg_color="transparent",
            hover_color=card_hover,
            border_width=1,
            border_color=border,
            text_color=("gray20", "gray86"),
            font=("Segoe UI", 12, "bold"),
            command=lambda i=idx: select_flow(i),
        )
        btn.grid(row=2 + idx, column=0, sticky="ew", padx=12, pady=4)
        nav_buttons[idx] = btn

    context_label = ctk.CTkLabel(
        left,
        text="Detectando contexto DFSR...",
        font=("Consolas", 10),
        text_color=("gray40", "gray65"),
        wraplength=238,
        justify="left",
        anchor="sw",
    )
    context_label.grid(row=9, column=0, sticky="sew", padx=14, pady=(8, 14))

    right = ctk.CTkFrame(
        body,
        fg_color=card_fg,
        border_width=1,
        border_color=border,
        corner_radius=8,
    )
    right.grid(row=0, column=1, sticky="nsew")
    right.grid_columnconfigure(0, weight=1)
    right.grid_rowconfigure(1, weight=1)

    right_header = ctk.CTkFrame(right, fg_color="transparent")
    right_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
    right_header.grid_columnconfigure(1, weight=1)

    flow_badge = ctk.CTkFrame(right_header, width=50, height=38, fg_color=("#E7F5F2", "#263432"), corner_radius=8)
    flow_badge.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="n")
    flow_badge.grid_propagate(False)
    flow_badge_label = ctk.CTkLabel(flow_badge, text="", font=("Segoe UI", 12, "bold"))
    flow_badge_label.pack(fill="both", expand=True)

    flow_title = ctk.CTkLabel(right_header, text="", font=("Segoe UI", 22, "bold"), anchor="w")
    flow_title.grid(row=0, column=1, sticky="ew")
    flow_subtitle = ctk.CTkLabel(
        right_header,
        text="",
        font=("Segoe UI", 12, "bold"),
        anchor="w",
    )
    flow_subtitle.grid(row=1, column=1, sticky="ew", pady=(2, 0))

    steps_area = ctk.CTkScrollableFrame(right, fg_color="transparent")
    steps_area.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
    steps_area.grid_columnconfigure(0, weight=1)

    footer = ctk.CTkFrame(right, fg_color="transparent")
    footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
    footer.grid_columnconfigure(0, weight=1)
    ctk.CTkButton(
        footer,
        text="Cerrar",
        width=130,
        height=38,
        fg_color=secondary,
        hover_color=secondary_hover,
        font=("Segoe UI", 12, "bold"),
        command=close_dialog,
    ).grid(row=0, column=1, sticky="e")

    def render_flow(flow):
        flow_badge_label.configure(text=flow["badge"], text_color=flow["accent"])
        flow_badge.configure(fg_color=("#E7F5F2", "#263432"))
        flow_title.configure(text=flow["title"])
        flow_subtitle.configure(text=flow["subtitle"], text_color=flow["accent"])

        for child in steps_area.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        ctk.CTkFrame(steps_area, height=3, fg_color=flow["accent"], corner_radius=3).grid(
            row=0, column=0, sticky="ew", padx=4, pady=(0, 12)
        )
        ctk.CTkLabel(
            steps_area,
            text=flow["detail"],
            font=("Segoe UI", 12),
            text_color=("gray25", "gray82"),
            wraplength=760,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 16))

        for row, (text, action_key, warn, color) in enumerate(flow["steps"], start=2):
            step = ctk.CTkFrame(
                steps_area,
                fg_color=(colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")),
                border_width=1,
                border_color=border,
                corner_radius=8,
            )
            step.grid(row=row, column=0, sticky="ew", padx=4, pady=5)
            step.grid_columnconfigure(1, weight=1)
            ctk.CTkFrame(step, width=4, fg_color=color or flow["accent"], corner_radius=3).grid(
                row=0, column=0, sticky="nsw", padx=(0, 10), pady=10
            )
            ctk.CTkLabel(
                step,
                text=text,
                font=("Segoe UI", 12, "bold"),
                anchor="w",
                justify="left",
                wraplength=560,
            ).grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=16)
            ctk.CTkButton(
                step,
                text="Ejecutar",
                width=104,
                height=32,
                fg_color=color or flow["accent"],
                hover_color=accent_hover,
                font=("Segoe UI", 11, "bold"),
                command=lambda k=action_key, t=text, w=warn: run_action(k, t, w),
            ).grid(row=0, column=2, sticky="e", padx=(0, 14), pady=12)

    def update_context_async():
        def worker():
            ok, data, _message = _detect_dfsr_context()
            if ok:
                role = "PDC" if data.get("is_pdc") else "no es PDC"
                text = (
                    f"Equipo: {data.get('computer', 'desconocido')}\n"
                    f"Dominio: {data.get('domain', 'desconocido')}\n"
                    f"PDC: {data.get('pdc', 'desconocido')}\n"
                    f"Este equipo: {role}\n"
                    f"DFSR: {data.get('dfsr_status', 'desconocido')} / {data.get('dfsr_starttype', 'desconocido')}"
                )
            else:
                text = "No se pudo detectar el contexto DFSR.\nUsa Diagnóstico para ver el error completo."
            try:
                app._call_ui_thread(context_label.configure, text=text)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    dialog.protocol("WM_DELETE_WINDOW", close_dialog)
    dialog.bind("<Escape>", close_dialog)
    select_flow(0)
    update_context_async()
    if hasattr(app, "_focus_secondary_window"):
        app._focus_secondary_window(dialog)
    else:
        try:
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass


def task_repadmin_syncall(app):
    """Tarea principal para botón Repadmin."""
    _run_repadmin_full()


def task_dfsr_action(app, action_key):
    """Ejecuta una acción guiada D2/D4."""
    action_key = str(action_key or "").strip()
    print(f">>> Acción D2/D4: {action_key}")

    actions = {
        "repadmin_syncall": _run_repadmin_full,
        "repadmin_summary": _run_repadmin_summary,
        "repadmin_pollad": _run_repadmin_and_pollad,
        "detect_context": _print_dfsr_context,
        "dfsr_service_status": _print_dfsr_service_status,
        "dfsr_manual_stop": _set_dfsr_manual_stop,
        "dfsr_start": _start_dfsr_service,
        "dfsr_auto": _set_dfsr_auto,
        "dfsr_pollad": _run_dfsr_pollad,
        "check_4114": lambda: _check_dfsr_events([4114], minutes=180),
        "check_4614_4604": lambda: _check_dfsr_events([4614, 4604], minutes=360),
        "check_4602": lambda: _check_dfsr_events([4602], minutes=360),
        "check_recent_events": lambda: _check_dfsr_events([4114, 4602, 4614, 4604, 2213, 4012], minutes=720),
        "d2_disable_local": lambda: _set_local_sysvol_subscription(enabled=False, authoritative=False),
        "d2_enable_local": lambda: _set_local_sysvol_subscription(enabled=True, authoritative=False),
        "d4_authoritative_disable": lambda: _set_local_sysvol_subscription(enabled=False, authoritative=True),
        "d4_authoritative_enable": lambda: _set_local_sysvol_subscription(enabled=True, authoritative=None),
    }

    action = actions.get(action_key)
    if not action:
        print(f"[ERROR] Acción no reconocida: {action_key}")
        return

    try:
        action()
        print("[OK] Acción finalizada.")
    except Exception as exc:
        print(f"[ERROR] Acción detenida: {exc}")


def _ps(script, timeout=60):
    ok, output = SysUtils.run_powershell(script, capture=True, timeout=timeout)
    return ok, (output or "").strip()


def _detect_dfsr_context():
    script = r'''
$ErrorActionPreference = 'Stop'
Import-Module ActiveDirectory -ErrorAction Stop
$domain = Get-ADDomain -ErrorAction Stop
$local = $env:COMPUTERNAME
$dc = Get-ADDomainController -Identity $local -ErrorAction Stop
$pdc = [string]$domain.PDCEmulator
$domainDn = [string]$domain.DistinguishedName
$base = "CN=DFSR-LocalSettings,CN=$($dc.Name),OU=Domain Controllers,$domainDn"
$sub = Get-ADObject -LDAPFilter '(cn=SYSVOL Subscription)' -SearchBase $base -SearchScope Subtree -Properties msDFSR-Enabled,msDFSR-Options -ErrorAction Stop | Select-Object -First 1
$svc = Get-Service -Name DFSR -ErrorAction SilentlyContinue
"COMPUTER=$local"
"DC_NAME=$($dc.Name)"
"DOMAIN=$($domain.DNSRoot)"
"DOMAIN_DN=$domainDn"
"PDC=$pdc"
"IS_PDC=$($pdc.Split('.')[0].Equals($local, [System.StringComparison]::OrdinalIgnoreCase))"
"SUBSCRIPTION_DN=$($sub.DistinguishedName)"
"MSDFSR_ENABLED=$($sub.'msDFSR-Enabled')"
"MSDFSR_OPTIONS=$($sub.'msDFSR-Options')"
if ($svc) {
    "DFSR_STATUS=$($svc.Status)"
    "DFSR_STARTTYPE=$($svc.StartType)"
} else {
    "DFSR_STATUS=No encontrado"
    "DFSR_STARTTYPE=No encontrado"
}
'''
    ok, output = _ps(script, timeout=45)
    data = {}
    for raw in output.splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip().lower()] = value.strip()
    if "is_pdc" in data:
        data["is_pdc"] = data["is_pdc"].lower() == "true"
    message = _format_context(data, output if not ok else "")
    return ok and bool(data.get("subscription_dn")), data, message


def _format_context(data, error_text=""):
    if not data:
        return "[ERROR] No se pudo detectar dominio/PDC/DFSR.\n" + (error_text or "")
    lines = [
        f"Equipo local: {data.get('computer', 'desconocido')}",
        f"Dominio: {data.get('domain', 'desconocido')}",
        f"PDC Emulator: {data.get('pdc', 'desconocido')}",
        f"Es PDC local: {'Sí' if data.get('is_pdc') else 'No'}",
        f"DFSR: {data.get('dfsr_status', 'desconocido')} | Inicio: {data.get('dfsr_starttype', 'desconocido')}",
        f"msDFSR-Enabled: {data.get('msdfsr_enabled', 'desconocido')}",
        f"msDFSR-Options: {data.get('msdfsr_options', 'desconocido')}",
        f"DN SYSVOL: {data.get('subscription_dn', 'no detectado')}",
    ]
    return "\n".join(lines)


def _print_dfsr_context():
    ok, data, message = _detect_dfsr_context()
    print(message)
    if not ok:
        print("[ERROR] Revisa que estás en un DC, con módulo ActiveDirectory disponible y permisos suficientes.")


def _domain_pdc():
    script = r'''
$ErrorActionPreference = 'Stop'
Import-Module ActiveDirectory -ErrorAction Stop
$domain = Get-ADDomain -ErrorAction Stop
"DOMAIN=$($domain.DNSRoot)"
"PDC=$($domain.PDCEmulator)"
'''
    ok, output = _ps(script, timeout=30)
    if not ok:
        raise RuntimeError(output or "No se pudo detectar PDC Emulator.")
    data = {}
    for raw in output.splitlines():
        if "=" in raw:
            k, v = raw.split("=", 1)
            data[k.strip().lower()] = v.strip()
    pdc = data.get("pdc")
    if not pdc:
        raise RuntimeError("No se pudo obtener PDC Emulator del dominio.")
    return data.get("domain", ""), pdc


def _run_command_clean(cmd, timeout=120, show_output_on_success=False):
    code, output = SysUtils.run_native_command(cmd, timeout=timeout)
    command_text = " ".join(cmd)
    if code == 0:
        print(f"[OK] {command_text}")
        if show_output_on_success and output:
            for line in _compact_repadmin_output(output):
                print(line)
        return True, output
    print(f"[ERROR] {command_text} devolvió código {code}")
    if output:
        for line in output.splitlines():
            print(line)
    return False, output


def _compact_repadmin_output(output):
    keep_tokens = (
        "SyncAll terminated with no errors",
        "SyncAll Finished",
        "error",
        "failed",
        "fails",
        "fails",
        "largest delta",
        "source dsa",
        "destination dsa",
        "total",
        "delta",
        "percent",
    )
    lines = []
    for raw in (output or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if any(token.lower() in lower for token in keep_tokens):
            lines.append(line)
    return lines[:80]


def _run_repadmin_full():
    print("Preparando Repadmin SyncAll...")
    domain, pdc = _domain_pdc()
    print(f"[INFO] Dominio: {domain}")
    print(f"[INFO] PDC Emulator: {pdc}")

    print(">>> Forzando KCC en todos los DC...")
    _run_command_clean(["repadmin.exe", "/kcc", "*"], timeout=90, show_output_on_success=False)

    print(">>> Forzando replicación AD con SyncAll...")
    ok, output = _run_command_clean(["repadmin.exe", "/syncall", pdc, "/AdeP"], timeout=180, show_output_on_success=False)
    if ok:
        print("[OK] SyncAll terminó sin errores según repadmin.")
    else:
        print("[AVISO] SyncAll devolvió errores. Revisa la salida anterior.")

    print(">>> Resumen de replicación...")
    _run_command_clean(["repadmin.exe", "/replsummary"], timeout=120, show_output_on_success=True)


def _run_repadmin_summary():
    print("Consultando resumen de replicación con repadmin /replsummary...")
    _run_command_clean(["repadmin.exe", "/replsummary"], timeout=120, show_output_on_success=True)


def _run_repadmin_and_pollad():
    _run_repadmin_full()
    _run_dfsr_pollad()


def _set_local_sysvol_subscription(enabled, authoritative=None):
    enabled_literal = "$true" if enabled else "$false"
    authoritative_block = ""
    if authoritative is True:
        authoritative_block = "\n$replace['msDFSR-Options'] = 1"

    script = f'''
$ErrorActionPreference = 'Stop'
Import-Module ActiveDirectory -ErrorAction Stop
$domain = Get-ADDomain -ErrorAction Stop
$dc = Get-ADDomainController -Identity $env:COMPUTERNAME -ErrorAction Stop
$base = "CN=DFSR-LocalSettings,CN=$($dc.Name),OU=Domain Controllers,$($domain.DistinguishedName)"
$sub = Get-ADObject -LDAPFilter '(cn=SYSVOL Subscription)' -SearchBase $base -SearchScope Subtree -Properties msDFSR-Enabled,msDFSR-Options -ErrorAction Stop | Select-Object -First 1
if (-not $sub) {{ throw "No se encontró SYSVOL Subscription para $env:COMPUTERNAME" }}
$replace = @{{ 'msDFSR-Enabled' = {enabled_literal} }}{authoritative_block}
Set-ADObject -Identity $sub.DistinguishedName -Replace $replace -Server $domain.PDCEmulator -ErrorAction Stop
$after = Get-ADObject -Identity $sub.DistinguishedName -Properties msDFSR-Enabled,msDFSR-Options -ErrorAction Stop
"DN=$($after.DistinguishedName)"
"msDFSR-Enabled=$($after.'msDFSR-Enabled')"
"msDFSR-Options=$($after.'msDFSR-Options')"
'''
    label = "TRUE" if enabled else "FALSE"
    if authoritative is True:
        print(f">>> Marcando este DC como autoritativo D4: msDFSR-Enabled={label}, msDFSR-Options=1")
    else:
        print(f">>> Cambiando SYSVOL Subscription local: msDFSR-Enabled={label}")
    ok, output = _ps(script, timeout=60)
    if not ok:
        raise RuntimeError(output or "No se pudo modificar SYSVOL Subscription.")
    for line in output.splitlines():
        if line.strip():
            print(line.strip())
    print("[OK] Atributos DFSR actualizados en Active Directory.")


def _set_dfsr_manual_stop():
    print(">>> Configurando DFSR en Manual y deteniendo servicio local...")
    script = r'''
$ErrorActionPreference = 'Continue'
$svc = Get-Service -Name DFSR -ErrorAction Stop
Set-Service -Name DFSR -StartupType Manual
if ($svc.Status -ne 'Stopped') {
    Stop-Service -Name DFSR -Force -ErrorAction Stop
}
$svc = Get-Service -Name DFSR
"DFSR_STATUS=$($svc.Status)"
"DFSR_STARTTYPE=$($svc.StartType)"
'''
    ok, output = _ps(script, timeout=90)
    if not ok:
        raise RuntimeError(output or "No se pudo detener DFSR.")
    print(output)
    print("[OK] DFSR detenido y en inicio Manual.")


def _start_dfsr_service():
    print(">>> Iniciando servicio DFSR local...")
    script = r'''
$ErrorActionPreference = 'Stop'
Start-Service -Name DFSR -ErrorAction Stop
Start-Sleep -Seconds 2
$svc = Get-Service -Name DFSR
"DFSR_STATUS=$($svc.Status)"
"DFSR_STARTTYPE=$($svc.StartType)"
'''
    ok, output = _ps(script, timeout=60)
    if not ok:
        raise RuntimeError(output or "No se pudo iniciar DFSR.")
    print(output)
    print("[OK] DFSR iniciado.")


def _set_dfsr_auto():
    print(">>> Configurando DFSR en Automático...")
    script = r'''
$ErrorActionPreference = 'Stop'
Set-Service -Name DFSR -StartupType Automatic
$svc = Get-Service -Name DFSR
"DFSR_STATUS=$($svc.Status)"
"DFSR_STARTTYPE=$($svc.StartType)"
'''
    ok, output = _ps(script, timeout=45)
    if not ok:
        raise RuntimeError(output or "No se pudo configurar DFSR en Automático.")
    print(output)
    print("[OK] DFSR configurado en Automático.")


def _print_dfsr_service_status():
    script = r'''
$svc = Get-Service -Name DFSR -ErrorAction SilentlyContinue
if ($svc) {
    "DFSR_STATUS=$($svc.Status)"
    "DFSR_STARTTYPE=$($svc.StartType)"
} else {
    "DFSR no encontrado"
}
'''
    ok, output = _ps(script, timeout=30)
    if not ok:
        raise RuntimeError(output or "No se pudo consultar DFSR.")
    print(output)


def _run_dfsr_pollad():
    print(">>> Ejecutando DFSRDIAG POLLAD...")
    script = r'''
$ErrorActionPreference = 'Continue'
$cmd = Get-Command dfsrdiag.exe -ErrorAction SilentlyContinue
if (-not $cmd) {
    Write-Output '[AVISO] DFSRDIAG no encontrado. Intentando instalar RSAT-DFS-MGMT-CON...'
    try { Install-WindowsFeature 'RSAT-DFS-MGMT-CON' -IncludeManagementTools | Out-String | Write-Output } catch { Write-Output "[AVISO] No se pudo instalar RSAT-DFS-MGMT-CON: $($_.Exception.Message)" }
}
$cmd = Get-Command dfsrdiag.exe -ErrorAction SilentlyContinue
if (-not $cmd) { throw 'DFSRDIAG no está disponible en este equipo.' }
& dfsrdiag.exe pollad
exit $LASTEXITCODE
'''
    ok, output = _ps(script, timeout=120)
    if output:
        print(output)
    if not ok:
        raise RuntimeError(output or "DFSRDIAG POLLAD falló.")
    print("[OK] DFSRDIAG POLLAD ejecutado.")


def _check_dfsr_events(event_ids, minutes=240):
    ids = ",".join(str(int(i)) for i in event_ids)
    print(f">>> Buscando eventos DFSR {ids} en los últimos {minutes} minutos...")
    script = f'''
$ids = @({ids})
$start = (Get-Date).AddMinutes(-{int(minutes)})
$events = @(Get-WinEvent -FilterHashtable @{{ LogName = '{DFSR_EVENT_LOG}'; Id = $ids; StartTime = $start }} -ErrorAction SilentlyContinue | Sort-Object TimeCreated -Descending | Select-Object -First 12)
if ($events.Count -eq 0) {{
    Write-Output "NO_EVENTS"
    exit 0
}}
foreach ($event in $events) {{
    $msg = ([string]$event.Message).Replace("`r", ' ').Replace("`n", ' ')
    if ($msg.Length -gt 220) {{ $msg = $msg.Substring(0, 220) + '...' }}
    "EVENT|$($event.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'))|$($event.Id)|$msg"
}}
'''
    ok, output = _ps(script, timeout=45)
    if not ok:
        raise RuntimeError(output or "No se pudieron consultar eventos DFSR.")
    if "NO_EVENTS" in output:
        print("[AVISO] No se han encontrado esos eventos en el intervalo indicado. Puede que todavía no hayan aparecido o que estés mirando el DC incorrecto.")
        return
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("EVENT|"):
            _prefix, when, event_id, message = line.split("|", 3)
            print(f"[OK] Evento {event_id} encontrado ({when})")
            print(f"      {message}")
        else:
            print(line)
