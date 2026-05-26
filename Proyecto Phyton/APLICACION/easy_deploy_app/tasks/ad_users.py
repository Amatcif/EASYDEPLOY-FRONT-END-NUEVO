# -*- coding: utf-8 -*-
"""Alta guiada de usuarios en Active Directory para Easy Deploy.

Este módulo se mantiene como punto de entrada funcional desde LayoutMixin:
show_ad_users_placeholder(app). El nombre se conserva por compatibilidad con el
import existente, aunque ya no es un placeholder.
"""

import csv
import locale
import os
import re
import subprocess
import time
import unicodedata

import customtkinter as ctk

from ..core.sysutils import SysUtils
from ..ui.dialog_utils import askyesno_child_dialog


AD_NAME_RE = re.compile(r"^[^\\/\[\]:;|=,+*?<>@\"\r\n]{1,128}$")


def show_ad_users_placeholder(app):
    """Compatibilidad con el LayoutMixin actual."""
    show_ad_users_tool(app)


def show_ad_users_tool(app):
    """Abre el asistente de alta de usuarios AD y lanza la tarea.

    La comprobación de AD es informativa. No bloquea la apertura del formulario,
    porque en algunos DC la detección previa puede fallar aunque la tarea real
    pueda ejecutarse correctamente. La validación fuerte se hace dentro del
    script PowerShell cuando el usuario pulsa Terminar y ejecutar.
    """
    if not SysUtils.is_admin():
        app.ui_showerror(
            "Permisos de administrador",
            "Crear usuarios AD necesita permisos de Administrador.\n\n"
            "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
        )
        return

    if not app.ui_askyesno(
        "Crear usuarios AD",
        "Requisitos antes de continuar:\n\n"
        "1. Recomendado: ejecuta esta función desde un Controlador de Dominio del dominio donde quieres crear usuarios.\n\n"
        "2. Usa una cuenta con permisos para crear usuarios en Active Directory.\n\n"
        "3. El módulo ActiveDirectory debe estar disponible. En un DC normalmente ya lo está.\n\n"
        "4. No hace falta que el usuario conozca la OU. Si dejas el destino vacío, Easy Deploy creará el usuario en el contenedor Users del dominio, igual que el asistente por defecto de Active Directory.\n\n"
        "Esta función crea usuarios SOLO en Active Directory. No crea buzón ni toca Exchange.\n\n"
        "La comprobación real de Active Directory se hará al pulsar Terminar y ejecutar.\n\n"
        "¿Quieres abrir el creador de usuarios AD?",
    ):
        return

    # Detección previa suave: se usa solo para mostrar el dominio si se puede obtener.
    # No debe bloquear ni mostrar avisos, porque la validación real se hace en el script
    # PowerShell al pulsar "Terminar y ejecutar". En algunos DC la comprobación previa
    # puede dar falsos negativos aunque New-ADUser funcione correctamente.
    try:
        _env_ok, _env_message, env_data = _ad_environment_report()
        if _env_message:
            print(_env_message)
    except Exception:
        env_data = {}

    detected_domain = env_data.get("domain", "") if env_data else ""

    users = _ad_users_dialog(app, detected_domain, "")
    if not users:
        return

    preview = "\n".join(
        f"- {user['Name']} ({user['SamAccountName']})"
        for user in users[:12]
    )
    if len(users) > 12:
        preview += f"\n- ... y {len(users) - 12} usuario(s) más"

    if app.ui_askyesno(
        "Confirmar usuarios AD",
        f"Se van a crear {len(users)} usuario(s) en Active Directory.\n\n"
        f"{preview}\n\n"
        "No se creará ningún buzón de Exchange.\n\n"
        "¿Continuar con la ejecución?",
    ):
        app.iniciar_tarea(task_ad_create_users, app, users)


def _ad_environment_report():
    script = r'''
$ErrorActionPreference = 'Continue'
try {
    $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    "COMPUTER=$env:COMPUTERNAME"
    "PART_OF_DOMAIN=$($cs.PartOfDomain)"
    "DOMAIN_ROLE=$($cs.DomainRole)"
    "IS_DC=$([int]$cs.DomainRole -ge 4)"
    try {
        Import-Module ActiveDirectory -ErrorAction Stop
        $domain = Get-ADDomain -ErrorAction Stop
        "DOMAIN=$($domain.DNSRoot)"
        "DOMAIN_DN=$($domain.DistinguishedName)"
        "PDC=$($domain.PDCEmulator)"
        "AD_MODULE=True"
    } catch {
        "AD_MODULE=False"
        "AD_ERROR=$($_.Exception.Message)"
    }
    exit 0
} catch {
    "ERROR=$($_.Exception.Message)"
    exit 1
}
'''
    ok, output = SysUtils.run_powershell(script, capture=True, timeout=30)
    data = {}
    for raw_line in (output or "").splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if key == "COMPUTER":
            data["computer"] = value
        elif key == "DOMAIN":
            data["domain"] = value
        elif key == "DOMAIN_DN":
            data["domain_dn"] = value
        elif key == "PDC":
            data["pdc"] = value
        elif key == "PART_OF_DOMAIN":
            data["part_of_domain"] = value.lower() == "true"
        elif key == "DOMAIN_ROLE":
            try:
                data["domain_role"] = int(value)
            except Exception:
                data["domain_role"] = -1
        elif key == "IS_DC":
            data["is_dc"] = value.lower() == "true"
        elif key == "AD_MODULE":
            data["ad_module"] = value.lower() == "true"
        elif key == "AD_ERROR":
            data["ad_error"] = value
        elif key == "ERROR":
            data["error"] = value

    messages = []
    if data.get("computer"):
        messages.append(f"Equipo: {data['computer']}")
    if data.get("domain"):
        messages.append(f"Dominio AD: {data['domain']}")
    if data.get("pdc"):
        messages.append(f"PDC Emulator: {data['pdc']}")
    if "is_dc" in data:
        messages.append("Es DC: " + ("Sí" if data.get("is_dc") else "No"))
    if data.get("ad_error"):
        messages.append("Error módulo AD: " + data["ad_error"])
    if data.get("error"):
        messages.append("Error: " + data["error"])

    env_ok = bool(ok and data.get("part_of_domain") and data.get("ad_module") and data.get("domain"))
    if not data.get("part_of_domain", False):
        env_ok = False
        messages.append("El equipo no parece estar unido a un dominio.")
    if not data.get("ad_module", False):
        env_ok = False
        messages.append("No se pudo cargar el módulo ActiveDirectory.")

    return env_ok, "\n".join(messages), data


def _ad_users_dialog(app, detected_domain="", env_warning=""):
    window_key = "crear_usuarios_ad"
    if app._focus_secondary_window(window_key):
        return None

    result = {"users": None}
    users = []
    common = {
        "ou": "",
        "password": "",
        "must_change": False,
        "cannot_change": True,
        "never_expires": True,
        "disabled": False,
    }
    colors = getattr(app, "colors", {})
    try:
        width = min(1180, max(1100, app.winfo_screenwidth() - 80))
    except Exception:
        width = 1180
    form_width = 480
    list_min_width = 480
    field_wrap = form_width - 72
    field_padx = (16, 24)
    try:
        height = max(720, min(900, app.winfo_screenheight() - 45))
    except Exception:
        height = 860

    dialog = ctk.CTkToplevel(app)
    dialog.title("Crear usuarios AD")
    dialog.resizable(True, True)
    dialog.minsize(1040, 680)
    dialog.overrideredirect(False)
    dialog.configure(fg_color=(colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")))
    app._center_window(dialog, width, height)
    app._register_secondary_window(window_key, dialog)

    panel = ctk.CTkFrame(
        dialog,
        fg_color=(colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")),
        border_width=0,
        corner_radius=0,
    )
    panel.pack(fill="both", expand=True)
    accent_line = ctk.CTkFrame(panel, height=3, fg_color=colors.get("accent", "#2F9E8F"), corner_radius=3)
    accent_line.pack(fill="x", padx=22, pady=(16, 0))

    header = ctk.CTkFrame(panel, fg_color="transparent")
    header.pack(fill="x", padx=24, pady=(16, 8))
    header.grid_columnconfigure(1, weight=1)

    badge = ctk.CTkFrame(
        header,
        width=48,
        height=48,
        fg_color=colors.get("sidebar_active", ("#E7F5F2", "#263432")),
        border_width=1,
        border_color=(colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40")),
        corner_radius=10,
    )
    badge.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="n")
    badge.grid_propagate(False)
    ctk.CTkLabel(badge, text="AD", font=("Segoe UI", 16, "bold"), text_color=colors.get("accent", "#2F9E8F")).pack(fill="both", expand=True)

    title_label = ctk.CTkLabel(header, text="Crear usuarios Active Directory", font=("Segoe UI", 20, "bold"), anchor="w")
    title_label.grid(row=0, column=1, sticky="ew")
    subtitle_label = ctk.CTkLabel(
        header,
        text="Alta rápida o masiva de usuarios en Active Directory",
        font=("Segoe UI", 12, "bold"),
        text_color=colors.get("accent", "#2F9E8F"),
        anchor="w",
    )
    subtitle_label.grid(row=1, column=1, sticky="ew")

    def close_dialog():
        result["users"] = None
        try:
            dialog.grab_release()
        except Exception:
            pass
        dialog.destroy()

        # Ventana nativa: se usa la barra de Windows para cerrar/minimizar/maximizar.
        # No se añade botón X custom ni arrastre frameless para evitar controles duplicados.

    body = ctk.CTkFrame(panel, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=24, pady=(4, 18))
    body.grid_columnconfigure(0, weight=1, minsize=form_width)
    body.grid_columnconfigure(1, weight=2, minsize=list_min_width)
    body.grid_rowconfigure(0, weight=1)
    body.grid_rowconfigure(1, weight=0)
    body.grid_rowconfigure(2, weight=0)

    form = ctk.CTkFrame(
        body,
        width=form_width,
        fg_color=(colors.get("card_light", "#F7F8FA"), colors.get("card_dark", "#26262A")),
        border_width=1,
        border_color=(colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40")),
        corner_radius=10,
    )
    form.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
    form.grid_propagate(False)
    form.grid_columnconfigure(0, weight=1)
    form.grid_rowconfigure(0, weight=1)

    form_fields = ctk.CTkScrollableFrame(form, width=form_width - 44, fg_color="transparent")
    form_fields.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 0))
    form_fields.grid_columnconfigure(0, weight=1)

    list_frame = ctk.CTkFrame(
        body,
        fg_color=(colors.get("card_light", "#F7F8FA"), colors.get("card_dark", "#26262A")),
        border_width=1,
        border_color=(colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40")),
        corner_radius=10,
    )
    list_frame.grid(row=0, column=1, sticky="nsew")
    list_frame.grid_columnconfigure(0, weight=1)
    list_frame.grid_rowconfigure(1, weight=1)

    buttons = ctk.CTkFrame(body, fg_color="transparent")
    buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    buttons.grid_columnconfigure((0, 1, 2, 3), weight=1)

    name_var = ctk.StringVar()
    ou_var = ctk.StringVar()
    password_var = ctk.StringVar()
    reuse_var = ctk.BooleanVar(value=False)
    reuse_confirmed = {"value": False}
    must_change_var = ctk.BooleanVar(value=common["must_change"])
    cannot_change_var = ctk.BooleanVar(value=common["cannot_change"])
    never_expires_var = ctk.BooleanVar(value=common["never_expires"])
    disabled_var = ctk.BooleanVar(value=common["disabled"])
    show_password = {"value": False}
    panel_fg = (colors.get("panel_light", "#FAF8F3"), colors.get("panel_dark", "#1B1B1F"))
    border_color = (colors.get("border_light", "#DDD8CE"), colors.get("border_dark", "#35353A"))
    input_fg = (colors.get("panel_light", "#FAF8F3"), colors.get("panel_dark", "#1B1B1F"))
    text_primary = ("#1F2933", "#F5F5F7")
    text_secondary = ("#5F6670", "#D4D4D8")
    secondary_color = "#5B6472"
    secondary_hover = "#47515F"
    info_color = colors.get("info", "#3B6EA8")
    info_hover = "#315C8D"

    status_frame = ctk.CTkFrame(
        body,
        fg_color=panel_fg,
        border_width=1,
        border_color=border_color,
        corner_radius=8,
    )
    status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    status_frame.grid_columnconfigure(0, weight=1)

    def add_label(parent, text, pady=(10, 4)):
        ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            text_color=("gray25", "gray82"),
        ).pack(fill="x", padx=field_padx, pady=pady)

    def add_section_label(parent, text, pady=(14, 4)):
        ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            text_color=(colors.get("text_muted_light", "#6B7280"), colors.get("text_muted_dark", "#A1A1AA")),
        ).pack(fill="x", padx=field_padx, pady=pady)

    def form_entry(parent, variable, placeholder_text="", show=None):
        return ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=40,
            placeholder_text=placeholder_text,
            show=show,
            font=("Segoe UI", 13),
            fg_color=input_fg,
            border_width=1,
            border_color=border_color,
            corner_radius=8,
        )

    info_text = (
        "Destino en AD vacío usa Users. La comprobación real se hará al ejecutar."
    )
    ctk.CTkLabel(
        form_fields,
        text=info_text,
        font=("Segoe UI", 10),
        justify="left",
        wraplength=field_wrap,
        text_color=text_secondary,
        anchor="w",
    ).pack(fill="x", padx=field_padx, pady=(4, 2))

    add_section_label(form_fields, "Datos del usuario", pady=(6, 4))
    add_label(form_fields, "Nombre de usuario / nombre visible", pady=(8, 4))
    name_entry = form_entry(
        form_fields,
        placeholder_text="Ej: PC.COLAG.JEFE o usuario01",
        variable=name_var,
    )
    name_entry.pack(fill="x", padx=field_padx, pady=(0, 4))

    add_section_label(form_fields, "Destino y contraseña")
    add_label(form_fields, "Destino en AD (opcional / avanzado)")
    ou_entry = form_entry(
        form_fields,
        placeholder_text="Déjalo vacío para crear en Users. Ej avanzado: OU=Usuarios,DC=et,DC=ms,DC=esp",
        variable=ou_var,
    )
    ou_entry.pack(fill="x", padx=field_padx, pady=(0, 4))
    ctk.CTkLabel(
        form_fields,
        text="Si no escribes nada aquí, Easy Deploy usará Users automáticamente.",
        font=("Segoe UI", 11, "bold"),
        text_color=colors.get("warning", "#D97706"),
        anchor="w",
        justify="left",
        wraplength=field_wrap,
    ).pack(fill="x", padx=field_padx, pady=(0, 4))

    add_label(form_fields, "Contraseña")
    password_row = ctk.CTkFrame(form_fields, fg_color="transparent")
    password_row.pack(fill="x", padx=field_padx, pady=(0, 4))
    password_entry = form_entry(
        password_row,
        variable=password_var,
        show="*",
    )
    password_entry.pack(side="left", fill="x", expand=True)

    def toggle_password():
        show_password["value"] = not show_password["value"]
        password_entry.configure(show="" if show_password["value"] else "*")
        password_toggle.configure(text="Ocultar" if show_password["value"] else "Ver")

    password_toggle = ctk.CTkButton(
        password_row,
        text="Ver",
        width=96,
        height=40,
        corner_radius=8,
        fg_color=secondary_color,
        hover_color=secondary_hover,
        font=("Segoe UI", 12, "bold"),
        command=toggle_password,
    )
    password_toggle.pack(side="left", padx=(8, 0))

    reuse_check = ctk.CTkCheckBox(
        form_fields,
        text="Reutilizar datos para el siguiente usuario",
        variable=reuse_var,
        fg_color=colors.get("accent", "#2F9E8F"),
        hover_color=colors.get("accent_hover", "#258176"),
        border_color=border_color,
        text_color=text_primary,
        font=("Segoe UI", 12, "bold"),
    )
    reuse_check.pack(fill="x", padx=field_padx, pady=(12, 4))

    add_section_label(form_fields, "Opciones de contraseña y cuenta", pady=(18, 2))

    def keep_options_consistent(source=""):
        if source == "must_change" and must_change_var.get():
            cannot_change_var.set(False)
            never_expires_var.set(False)
        elif source in {"cannot_change", "never_expires"} and (cannot_change_var.get() or never_expires_var.get()):
            must_change_var.set(False)

    must_change_check = ctk.CTkCheckBox(
        form_fields,
        text="Cambiar contraseña al iniciar sesión",
        variable=must_change_var,
        command=lambda: keep_options_consistent("must_change"),
        fg_color=colors.get("accent", "#2F9E8F"),
        hover_color=colors.get("accent_hover", "#258176"),
        border_color=border_color,
        text_color=text_primary,
        font=("Segoe UI", 12),
    )
    must_change_check.pack(fill="x", padx=field_padx, pady=(12, 4))

    cannot_change_check = ctk.CTkCheckBox(
        form_fields,
        text="No puede cambiar contraseña",
        variable=cannot_change_var,
        command=lambda: keep_options_consistent("cannot_change"),
        fg_color=colors.get("accent", "#2F9E8F"),
        hover_color=colors.get("accent_hover", "#258176"),
        border_color=border_color,
        text_color=text_primary,
        font=("Segoe UI", 12),
    )
    cannot_change_check.pack(fill="x", padx=field_padx, pady=(6, 4))

    never_expires_check = ctk.CTkCheckBox(
        form_fields,
        text="Contraseña nunca expira",
        variable=never_expires_var,
        command=lambda: keep_options_consistent("never_expires"),
        fg_color=colors.get("accent", "#2F9E8F"),
        hover_color=colors.get("accent_hover", "#258176"),
        border_color=border_color,
        text_color=text_primary,
        font=("Segoe UI", 12),
    )
    never_expires_check.pack(fill="x", padx=field_padx, pady=(6, 4))

    disabled_check = ctk.CTkCheckBox(
        form_fields,
        text="Cuenta deshabilitada",
        variable=disabled_var,
        fg_color=colors.get("accent", "#2F9E8F"),
        hover_color=colors.get("accent_hover", "#258176"),
        border_color=border_color,
        text_color=text_primary,
        font=("Segoe UI", 12),
    )
    disabled_check.pack(fill="x", padx=field_padx, pady=(6, 10))

    domain_status_text = f"Dominio AD detectado: {detected_domain}" if detected_domain else "Dominio AD: se comprobará al ejecutar"
    domain_label = ctk.CTkLabel(
        form_fields,
        text=domain_status_text,
        font=("Segoe UI", 11, "bold"),
        text_color=colors.get("success", "#16803C") if detected_domain else colors.get("warning", "#D97706"),
        anchor="w",
        justify="left",
        wraplength=field_wrap,
    )
    domain_label.pack(fill="x", padx=field_padx, pady=(2, 0))

    status_label = ctk.CTkLabel(
        status_frame,
        text="",
        font=("Segoe UI", 11, "bold"),
        text_color=colors.get("danger", "#B42318"),
        anchor="w",
        justify="left",
        wraplength=field_wrap,
    )
    status_label.grid(row=0, column=0, sticky="ew", padx=14, pady=7)

    def update_status_wrap(event=None):
        try:
            status_label.configure(wraplength=max(320, status_frame.winfo_width() - 28))
        except Exception:
            pass

    status_frame.bind("<Configure>", update_status_wrap, add="+")

    list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
    list_header.grid(row=0, column=0, padx=16, pady=(14, 10), sticky="ew")
    list_header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        list_header,
        text="Usuarios preparados",
        font=("Segoe UI", 16, "bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew")
    count_label = ctk.CTkLabel(
        list_header,
        text="0 usuarios",
        font=("Segoe UI", 11, "bold"),
        fg_color=colors.get("sidebar_active", ("#EEF2F7", "#26262A")),
        corner_radius=8,
        text_color=colors.get("accent", "#2F9E8F"),
        anchor="center",
        width=86,
        height=26,
    )
    count_label.grid(row=0, column=1, padx=(12, 0), sticky="e")
    users_box = ctk.CTkTextbox(
        list_frame,
        font=("Consolas", 12),
        wrap="none",
        border_width=1,
        border_color=border_color,
        fg_color=panel_fg,
        corner_radius=8,
    )
    users_box.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="nsew")
    users_box.configure(state="disabled")

    option_widgets = [must_change_check, cannot_change_check, never_expires_check, disabled_check]

    def set_status(text, error=True):
        status_label.configure(
            text=text,
            text_color=colors.get("danger", "#B42318") if error else colors.get("success", "#16803C"),
        )

    def flags_for_user(user):
        flags = []
        if user.get("MustChangePassword"):
            flags.append("cambia-login")
        if user.get("CannotChangePassword"):
            flags.append("no-cambia")
        if user.get("PasswordNeverExpires"):
            flags.append("no-expira")
        if user.get("AccountDisabled"):
            flags.append("deshabilitada")
        return ",".join(flags) if flags else "normal"

    def refresh_list():
        users_box.configure(state="normal")
        users_box.delete("1.0", "end")
        if users:
            for idx, user in enumerate(users, start=1):
                users_box.insert(
                    "end",
                    f"{idx:02d}. {user['Name']:<30} | {user['SamAccountName']:<20} | {flags_for_user(user):<28} | {user['OrganizationalUnit']}\n",
                )
        else:
            users_box.insert("end", "Todavía no hay usuarios preparados.\n")
        users_box.configure(state="disabled")
        count_label.configure(text=f"{len(users)} usuario(s)")

    def apply_reuse_lock():
        if not reuse_var.get():
            reuse_confirmed["value"] = False
        locked = bool(users and reuse_var.get() and reuse_confirmed["value"])
        state = "disabled" if locked else "normal"
        for widget in (ou_entry, password_entry, password_toggle, *option_widgets):
            try:
                widget.configure(state=state)
            except Exception:
                pass
        if locked:
            set_status("Modo rápido activo: cambia solo el nombre y pulsa Añadir usuario.", error=False)
        else:
            set_status("", error=False)

    reuse_check.configure(command=apply_reuse_lock)

    def normalize_user_input():
        keep_options_consistent()
        name = name_var.get().strip()
        raw_ou = ou_var.get().strip() or common.get("ou", "")
        ou = raw_ou.strip() if raw_ou else "Users"
        password = password_var.get().strip() or common.get("password", "")
        sam = _ad_sam_from_name(name)

        if not name or not AD_NAME_RE.match(name):
            return None, "Introduce un nombre/login válido. Evita caracteres especiales de AD como / \\ [ ] : ; | = , + * ? < > @ comillas."
        if not sam:
            return None, "No se puede generar SamAccountName desde ese nombre. Escribe otro nombre/login."
        if not SysUtils.is_plain_value(ou, max_len=256):
            return None, "El destino indicado no es válido. Puedes dejarlo vacío para usar Users."
        if not SysUtils.is_plain_value(password, max_len=128):
            return None, "Introduce una contraseña válida."

        must_change = bool(must_change_var.get())
        cannot_change = bool(cannot_change_var.get())
        never_expires = bool(never_expires_var.get())
        disabled = bool(disabled_var.get())
        if must_change and (cannot_change or never_expires):
            return None, "Opciones incompatibles: si debe cambiar contraseña al iniciar, no puede estar marcado no cambiar contraseña ni contraseña nunca expira."

        sam_key = sam.lower()
        name_key = name.lower()
        if any(user["SamAccountName"].lower() == sam_key for user in users):
            return None, "Ese SamAccountName ya está en la lista. Cambia el nombre/login."
        if any(user["Name"].lower() == name_key for user in users):
            return None, "Ya existe un usuario en la lista con ese nombre."

        return {
            "Name": name,
            "SamAccountName": sam,
            "OrganizationalUnit": ou,
            "Password": password,
            "MustChangePassword": must_change,
            "CannotChangePassword": cannot_change,
            "PasswordNeverExpires": never_expires,
            "AccountDisabled": disabled,
        }, ""

    def save_common_from_user(user):
        common["ou"] = user["OrganizationalUnit"]
        common["password"] = user["Password"]
        common["must_change"] = user["MustChangePassword"]
        common["cannot_change"] = user["CannotChangePassword"]
        common["never_expires"] = user["PasswordNeverExpires"]
        common["disabled"] = user["AccountDisabled"]

    def restore_common_to_form():
        ou_var.set(common["ou"])
        password_var.set(common["password"])
        must_change_var.set(common["must_change"])
        cannot_change_var.set(common["cannot_change"])
        never_expires_var.set(common["never_expires"])
        disabled_var.set(common["disabled"])

    def add_user():
        user, error = normalize_user_input()
        if error:
            set_status(error, error=True)
            return

        reuse_requested = bool(reuse_var.get())
        users.append(user)
        save_common_from_user(user)
        refresh_list()

        if reuse_requested and not reuse_confirmed["value"]:
            try:
                dialog.grab_release()
            except Exception:
                pass
            reuse = askyesno_child_dialog(
                app,
                dialog,
                "Reutilizar datos",
                "¿Quieres reutilizar el destino, contraseña y opciones para los siguientes usuarios?\n\n"
                "Si aceptas, el formulario bloqueará esos campos y solo tendrás que introducir el nombre del siguiente usuario.",
                "Sí",
                "No",
                key="ad_reutilizar_datos",
            )
            reuse_confirmed["value"] = bool(reuse)
            reuse_var.set(bool(reuse))
            try:
                app._focus_secondary_window(dialog)
            except Exception:
                pass
        elif not reuse_requested:
            reuse_confirmed["value"] = False

        if reuse_var.get() and reuse_confirmed["value"]:
            name_var.set("")
            restore_common_to_form()
            name_entry.focus_set()
        else:
            name_var.set("")
            ou_var.set("")
            password_var.set("")
            must_change_var.set(False)
            cannot_change_var.set(True)
            never_expires_var.set(True)
            disabled_var.set(False)
            name_entry.focus_set()
        apply_reuse_lock()
        set_status(f"Usuario preparado: {user['Name']} ({user['SamAccountName']}) | Destino: {user['OrganizationalUnit']}", error=False)

    def remove_last():
        if not users:
            set_status("No hay usuarios para eliminar.", error=True)
            return
        removed = users.pop()
        refresh_list()
        apply_reuse_lock()
        set_status(f"Eliminado de la lista: {removed['Name']}", error=False)

    def finish():
        if not users:
            set_status("Añade al menos un usuario antes de terminar.", error=True)
            return
        result["users"] = list(users)
        try:
            dialog.grab_release()
        except Exception:
            pass
        dialog.destroy()

    ctk.CTkButton(
        buttons,
        text="Añadir usuario",
        height=42,
        corner_radius=8,
        fg_color=colors.get("accent", "#2F9E8F"),
        hover_color=colors.get("accent_hover", "#258176"),
        command=add_user,
        font=("Segoe UI", 13, "bold"),
    ).grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 0))
    ctk.CTkButton(
        buttons,
        text="Eliminar último",
        height=42,
        corner_radius=8,
        fg_color=secondary_color,
        hover_color=secondary_hover,
        command=remove_last,
        font=("Segoe UI", 13, "bold"),
    ).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(0, 0))
    ctk.CTkButton(
        buttons,
        text="Terminar y ejecutar",
        height=42,
        corner_radius=8,
        fg_color=info_color,
        hover_color=info_hover,
        command=finish,
        font=("Segoe UI", 13, "bold"),
    ).grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=(0, 0))
    ctk.CTkButton(
        buttons,
        text="Cancelar",
        height=42,
        corner_radius=8,
        fg_color=colors.get("danger", "#B42318"),
        hover_color="#991B1B",
        command=close_dialog,
        font=("Segoe UI", 13, "bold"),
    ).grid(row=0, column=3, sticky="ew", padx=(0, 0), pady=(0, 0))

    dialog.bind("<Return>", lambda _event=None: add_user())
    dialog.bind("<Escape>", lambda _event=None: close_dialog())
    dialog.protocol("WM_DELETE_WINDOW", close_dialog)
    refresh_list()
    apply_reuse_lock()
    app._focus_secondary_window(dialog)
    name_entry.focus_set()
    app.wait_window(dialog)
    return result["users"]


def _ad_sam_from_name(name):
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    text = text.strip().lower()
    text = re.sub(r"\s+", ".", text)
    text = re.sub(r"[^a-z0-9._-]", "", text)
    text = re.sub(r"\.+", ".", text).strip("._-")
    if not text:
        return ""
    return text[:20]


def _ad_users_script_dir(app):
    return SysUtils.get_easydeploy_temp_scripts_dir()


def _write_ad_users_files(app, users):
    script_dir = _ad_users_script_dir(app)
    os.makedirs(script_dir, exist_ok=True)
    csv_path = SysUtils.make_temp_script_path("easydeploy_ad_users", ".csv")
    ps1_path = SysUtils.make_temp_script_path("easydeploy_create_ad_users", ".ps1")

    fieldnames = [
        "Name",
        "SamAccountName",
        "OrganizationalUnit",
        "Password",
        "MustChangePassword",
        "CannotChangePassword",
        "PasswordNeverExpires",
        "AccountDisabled",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for user in users:
            row = dict(user)
            for key in (
                "MustChangePassword",
                "CannotChangePassword",
                "PasswordNeverExpires",
                "AccountDisabled",
            ):
                row[key] = "true" if row.get(key) else "false"
            writer.writerow(row)

    with open(ps1_path, "w", encoding="utf-8-sig") as handle:
        handle.write(_ad_create_users_script())

    return csv_path, ps1_path


def _ad_create_users_script():
    return r'''
param(
    [string]$CsvPath = $(Join-Path $PSScriptRoot 'easydeploy_ad_users.csv')
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$ErrorActionPreference = 'Continue'

$created = New-Object System.Collections.Generic.List[object]
$failed = New-Object System.Collections.Generic.List[object]

function Add-Failed {
    param([string]$Sam, [string]$Name, [string]$Reason)
    $script:failed.Add([pscustomobject]@{
        Sam = $Sam
        Name = $Name
        Reason = $Reason
    }) | Out-Null
    Write-Output "[FALLIDO] $Name -> $Reason"
}

function Escape-LdapFilterValue {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    $text = [string]$Value
    $text = $text.Replace('\', '\5c')
    $text = $text.Replace('*', '\2a')
    $text = $text.Replace('(', '\28')
    $text = $text.Replace(')', '\29')
    $text = $text.Replace(([string][char]0), '\00')
    return $text
}

function ConvertTo-DomainDn {
    param([string]$DomainName)
    $parts = @($DomainName.Split('.') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($parts.Count -eq 0) { throw "Dominio no válido: $DomainName" }
    return (($parts | ForEach-Object { 'DC=' + $_ }) -join ',')
}

function Test-AdObjectExists {
    param([string]$Identity, [string]$Server)
    try {
        $null = Get-ADObject -Identity $Identity -Server $Server -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Resolve-TargetContainerDn {
    param(
        [string]$RawOu,
        [string]$DomainName,
        [string]$Server
    )

    $domainDn = ConvertTo-DomainDn -DomainName $DomainName
    $defaultContainer = "CN=Users,$domainDn"
    $raw = ([string]$RawOu).Trim()
    $domainShort = ($DomainName.Split('.')[0])

    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $defaultContainer
    }

    if ($raw -ieq $domainShort -or $raw -ieq $DomainName -or $raw -ieq 'Users' -or $raw -ieq 'User') {
        return $defaultContainer
    }

    if ($raw -match '(?i)(^|,)(OU|CN|DC)=') {
        if (Test-AdObjectExists -Identity $raw -Server $Server) { return $raw }
        throw "No existe en Active Directory la ruta DN indicada: $raw"
    }

    $canonical = $raw -replace '\\', '/'
    if ($canonical.Contains('/')) {
        $parts = @($canonical.Split('/') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($parts.Count -eq 0) { return $defaultContainer }

        $canonicalDomain = $DomainName
        $containerParts = $parts
        if ($parts[0] -match '\.') {
            $canonicalDomain = $parts[0]
            if ($parts.Count -gt 1) {
                $containerParts = @($parts[1..($parts.Count - 1)])
            } else {
                $containerParts = @()
            }
        }

        if ($containerParts.Count -eq 0) { return $defaultContainer }

        $candidateDomainDn = ConvertTo-DomainDn -DomainName $canonicalDomain
        $dnParts = New-Object System.Collections.Generic.List[string]
        for ($i = $containerParts.Count - 1; $i -ge 0; $i--) {
            $part = [string]$containerParts[$i]
            if ($part -ieq 'Users' -or $part -ieq 'User') {
                $dnParts.Add('CN=Users') | Out-Null
            } else {
                $dnParts.Add(('OU=' + $part)) | Out-Null
            }
        }
        $candidate = (($dnParts.ToArray()) -join ',') + ',' + $candidateDomainDn
        if (Test-AdObjectExists -Identity $candidate -Server $Server) { return $candidate }
        throw "No existe la OU/contenedor indicado: $raw. Usa por ejemplo $DomainName/Users o una OU real."
    }

    $escaped = Escape-LdapFilterValue $raw
    $matches = @(Get-ADObject -LDAPFilter "(|(&(objectClass=organizationalUnit)(ou=$escaped))(&(objectClass=container)(cn=$escaped)))" -SearchBase $domainDn -Server $Server -ErrorAction SilentlyContinue | Select-Object -First 2)
    if ($matches.Count -eq 1) { return [string]$matches[0].DistinguishedName }
    if ($matches.Count -gt 1) { throw "La ruta '$raw' es ambigua. Escribe la ruta completa, por ejemplo $DomainName/Users." }

    throw "No existe la OU/contenedor '$raw'. Usa por ejemplo $DomainName/Users."
}

function ConvertTo-Bool {
    param([object]$Value, [bool]$Default = $false)
    if ($null -eq $Value) { return $Default }
    $text = ([string]$Value).Trim().ToLowerInvariant()
    if ($text -in @('true','1','yes','si','sí','y')) { return $true }
    if ($text -in @('false','0','no','n')) { return $false }
    return $Default
}

function ConvertTo-Ascii {
    param([string]$Text)
    if ($null -eq $Text) { return '' }
    $normalized = $Text.Normalize([Text.NormalizationForm]::FormD)
    $builder = New-Object System.Text.StringBuilder
    foreach ($ch in $normalized.ToCharArray()) {
        $category = [Globalization.CharUnicodeInfo]::GetUnicodeCategory($ch)
        if ($category -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$builder.Append($ch)
        }
    }
    return $builder.ToString().Normalize([Text.NormalizationForm]::FormC)
}

function New-SamAccountName {
    param([string]$Name, [string]$ProvidedSam)
    $source = if ([string]::IsNullOrWhiteSpace($ProvidedSam)) { $Name } else { $ProvidedSam }
    $clean = ConvertTo-Ascii $source
    $clean = $clean.Trim().ToLowerInvariant()
    $clean = $clean -replace '\s+', '.'
    $clean = $clean -replace '[^A-Za-z0-9._-]', ''
    $clean = $clean.Trim('._-')
    if ([string]::IsNullOrWhiteSpace($clean)) {
        $clean = 'user' + ([guid]::NewGuid().ToString('N').Substring(0, 8))
    }
    if ($clean.Length -gt 20) { $clean = $clean.Substring(0, 20) }
    return $clean
}

function Try-SyncAdReplication {
    param([string]$Server)
    try {
        $repadmin = Get-Command repadmin.exe -ErrorAction SilentlyContinue
        if (-not $repadmin) {
            Write-Output "[AVISO] repadmin.exe no está disponible. Se omite la sincronización AD."
            return
        }

        Write-Output "[INFO] Solicitando sincronización AD desde $Server..."
        & repadmin.exe /syncall $Server /AdeP *> $null
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0 -or $null -eq $exitCode) {
            Write-Output "[OK] Sincronización AD solicitada correctamente desde $Server."
        } else {
            Write-Output "[AVISO] repadmin finalizó con código $exitCode. Revisa la replicación AD si los cambios tardan en verse."
        }
    } catch {
        Write-Output "[AVISO] No se pudo solicitar la sincronización AD: $($_.Exception.Message)"
    }
}

try {
    if (-not (Test-Path -LiteralPath $CsvPath)) {
        throw "No existe el archivo de usuarios: $CsvPath"
    }

    try {
        $computerSystem = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
        if ([int]$computerSystem.DomainRole -lt 4) {
            Write-Output '[AVISO] Este equipo no se ha detectado como Controlador de Dominio. Se intentará continuar usando el módulo ActiveDirectory.'
        } else {
            Write-Output '[OK] Equipo detectado como Controlador de Dominio.'
        }
    } catch {
        Write-Output "[AVISO] No se pudo comprobar si el equipo es DC: $($_.Exception.Message). Se intentará continuar."
    }

    try { Import-Module ActiveDirectory -ErrorAction Stop } catch {
        throw 'No se pudo cargar el módulo ActiveDirectory. Ejecuta esta tarea desde un DC con AD DS instalado o instala las herramientas RSAT de Active Directory.'
    }

    $domain = Get-ADDomain -ErrorAction Stop
    $domainName = [string]$domain.DNSRoot
    $domainDn = [string]$domain.DistinguishedName
    $writeDc = if ($domain.PDCEmulator) { [string]$domain.PDCEmulator } else { [string]$env:COMPUTERNAME }

    $users = @(Import-Csv -LiteralPath $CsvPath)
    if ($users.Count -eq 0) {
        throw 'El archivo de usuarios no contiene filas.'
    }

    Write-Output "[INFO] Dominio: $domainName"
    Write-Output "[INFO] Controlador usado: $writeDc"
    Write-Output "[INFO] Usuarios a procesar: $($users.Count)"

    foreach ($user in $users) {
        $name = ([string]$user.Name).Trim()
        $providedSam = ([string]$user.SamAccountName).Trim()
        $sam = New-SamAccountName -Name $name -ProvidedSam $providedSam
        $ou = ([string]$user.OrganizationalUnit).Trim()
        $plainPassword = [string]$user.Password
        $mustChange = ConvertTo-Bool $user.MustChangePassword $false
        $cannotChange = ConvertTo-Bool $user.CannotChangePassword $false
        $neverExpires = ConvertTo-Bool $user.PasswordNeverExpires $false
        $disabled = ConvertTo-Bool $user.AccountDisabled $false
        $upn = "$sam@$domainName"

        Write-Output "[USUARIO] $name"

        if ([string]::IsNullOrWhiteSpace($name) -or [string]::IsNullOrWhiteSpace($plainPassword)) {
            Add-Failed -Sam $sam -Name $name -Reason 'Datos incompletos: Nombre y contraseña son obligatorios. El destino puede quedar vacío y se usará Users.'
            continue
        }
        if ($name -match '[\\/\[\]:;|=,+*?<>@"\r\n]') {
            Add-Failed -Sam $sam -Name $name -Reason 'Nombre no válido para Active Directory.'
            continue
        }
        if ($mustChange -and ($cannotChange -or $neverExpires)) {
            Add-Failed -Sam $sam -Name $name -Reason 'Opciones incompatibles: cambiar contraseña al inicio no puede combinarse con no cambiar contraseña o contraseña nunca expira.'
            continue
        }

        try {
            $targetContainerDn = Resolve-TargetContainerDn -RawOu $ou -DomainName $domainName -Server $writeDc
            Write-Output "[AD] Contenedor destino: $targetContainerDn"

            $escapedSam = Escape-LdapFilterValue $sam
            $escapedUpn = Escape-LdapFilterValue $upn
            $existingAd = Get-ADUser -LDAPFilter "(|(sAMAccountName=$escapedSam)(userPrincipalName=$escapedUpn))" -SearchBase $domainDn -Server $writeDc -Properties DistinguishedName -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($existingAd) {
                Add-Failed -Sam $sam -Name $name -Reason "Ya existe un usuario en AD: $($existingAd.DistinguishedName)"
                continue
            }

            $escapedName = Escape-LdapFilterValue $name
            $existingSameContainer = Get-ADObject -LDAPFilter "(cn=$escapedName)" -SearchBase $targetContainerDn -SearchScope OneLevel -Server $writeDc -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($existingSameContainer) {
                Add-Failed -Sam $sam -Name $name -Reason "Ya existe un objeto con ese nombre en el contenedor destino: $targetContainerDn"
                continue
            }

            $securePassword = ConvertTo-SecureString $plainPassword -AsPlainText -Force
            New-ADUser `
                -Name $name `
                -DisplayName $name `
                -GivenName $name `
                -UserPrincipalName $upn `
                -SamAccountName $sam `
                -Path $targetContainerDn `
                -AccountPassword $securePassword `
                -Enabled (-not $disabled) `
                -ChangePasswordAtLogon $mustChange `
                -CannotChangePassword $cannotChange `
                -PasswordNeverExpires $neverExpires `
                -Server $writeDc `
                -ErrorAction Stop

            $adUser = Get-ADUser -Identity $sam -Server $writeDc -Properties DistinguishedName,UserPrincipalName,Enabled -ErrorAction Stop
            if (-not $adUser) { throw 'New-ADUser no devolvió un usuario verificable.' }

            $created.Add([pscustomobject]@{
                Sam = $sam
                Name = $name
                UserPrincipalName = $upn
                DistinguishedName = $adUser.DistinguishedName
                DomainController = $writeDc
            }) | Out-Null
            Write-Output "[OK] Usuario AD creado: $($adUser.DistinguishedName)"
        } catch {
            Add-Failed -Sam $sam -Name $name -Reason $_.Exception.Message
        }
    }

    Try-SyncAdReplication -Server $writeDc

    Write-Output ''
    Write-Output '=== RESUMEN EASY DEPLOY AD ==='
    Write-Output "Creados: $($created.Count)"
    foreach ($item in $created) {
        Write-Output "CREADO|$($item.Sam)|$($item.Name)|$($item.DistinguishedName)"
    }
    Write-Output "Fallidos: $($failed.Count)"
    foreach ($item in $failed) {
        Write-Output "FALLIDO|$($item.Sam)|$($item.Name)|$($item.Reason)"
    }

    if ($failed.Count -gt 0) { exit 1 }
    exit 0
} catch {
    Write-Output "[ERROR] $($_.Exception.Message)"
    exit 10
}
'''



def _decode_process_line(raw_line):
    """Decodifica líneas de PowerShell/native tools sin romper tildes ni ñ."""
    if isinstance(raw_line, str):
        return raw_line.rstrip("\r\n")
    if not raw_line:
        return ""

    raw = raw_line.rstrip(b"\r\n")
    encodings = []
    for encoding in (
        "utf-8-sig",
        "utf-8",
        getattr(SysUtils, "oem_encoding", lambda: "")(),
        locale.getpreferredencoding(False),
        "cp1252",
        "cp850",
    ):
        if encoding and encoding not in encodings:
            encodings.append(encoding)

    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")

def task_ad_create_users(app, users):
    if not users:
        app._notify_task_error("Crear usuarios AD", "No hay usuarios para procesar.")
        return

    if not app._require_windows_server(
        "Crear usuarios AD",
        "La creación de usuarios AD debe ejecutarse en Windows Server dentro de un Controlador de Dominio.",
    ):
        return

    csv_path = ""
    ps1_path = ""
    created = []
    failed = []

    try:
        print("Preparando creación de usuarios Active Directory...")
        print(f"Usuarios recibidos: {len(users)}")
        print("El archivo temporal de usuarios se borrará automáticamente al finalizar.")
        app.update_progress(0.05)

        csv_path, ps1_path = _write_ad_users_files(app, users)
        print(f"Script temporal: {ps1_path}")
        print("CSV temporal creado. No se mostrarán contraseñas en consola.")
        app.update_progress(0.10)

        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            ps1_path,
            "-CsvPath",
            csv_path,
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        processed = 0
        total = max(1, len(users))
        while True:
            if app.stop_event.is_set():
                print("[AVISO] Cancelación solicitada. Deteniendo script AD...")
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
                return

            line = process.stdout.readline() if process.stdout else ""
            if line:
                clean = _decode_process_line(line)
                print(clean)
                if clean.startswith("[USUARIO]"):
                    processed += 1
                    app.update_progress(0.10 + min(0.80, 0.80 * (processed / total)))
                elif clean.startswith("CREADO|"):
                    parts = clean.split("|", 3)
                    if len(parts) >= 4:
                        created.append((parts[1], parts[2], parts[3]))
                elif clean.startswith("FALLIDO|"):
                    parts = clean.split("|", 3)
                    if len(parts) >= 4:
                        failed.append((parts[1], parts[2], parts[3]))

            if process.poll() is not None:
                if process.stdout:
                    for remaining in process.stdout:
                        clean = _decode_process_line(remaining)
                        if clean:
                            print(clean)
                            if clean.startswith("CREADO|"):
                                parts = clean.split("|", 3)
                                if len(parts) >= 4:
                                    created.append((parts[1], parts[2], parts[3]))
                            elif clean.startswith("FALLIDO|"):
                                parts = clean.split("|", 3)
                                if len(parts) >= 4:
                                    failed.append((parts[1], parts[2], parts[3]))
                break

            if not line:
                time.sleep(0.2)

        app.update_progress(1.0)
        if process.returncode == 0 and not failed:
            app.ui_showinfo(
                "Crear usuarios AD",
                f"Proceso completado correctamente.\n\nUsuarios creados: {len(created)}\nFallidos: 0",
            )
            return

        failed_preview = "\n".join(f"- {name} ({sam}): {reason}" for sam, name, reason in failed[:12])
        if len(failed) > 12:
            failed_preview += f"\n- ... y {len(failed) - 12} fallo(s) más. Revisa el log."
        if not failed_preview:
            failed_preview = "El script devolvió código no correcto. Revisa el log para ver el detalle."

        app._notify_task_warning(
            "Crear usuarios AD",
            f"Proceso finalizado con incidencias.\n\n"
            f"Usuarios creados: {len(created)}\n"
            f"Usuarios fallidos: {len(failed)}\n\n"
            f"{failed_preview}",
        )
    except Exception as exc:
        app._notify_task_error(
            "Crear usuarios AD",
            f"No se pudo crear o ejecutar el script de usuarios AD.\n\nDetalle: {exc}",
        )
    finally:
        for path in (csv_path, ps1_path):
            SysUtils.cleanup_temp_file(path)
