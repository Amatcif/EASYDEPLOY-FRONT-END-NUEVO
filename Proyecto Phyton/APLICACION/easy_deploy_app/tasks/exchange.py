import csv
import os
import re
import subprocess
import time
import unicodedata

import customtkinter as ctk

from ..core.sysutils import SysUtils
from ..ui.dialog_utils import askyesno_child_dialog


class ExchangeTasksMixin:
    EXCHANGE_CU15_MEDIA_NAME = "ExchangeServer2019-x64-cu15"
    EXCHANGE_EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)
    EXCHANGE_2019_CU15_SCHEMA_VERSION = 17003
    EXCHANGE_2019_CU15_DOMAIN_VERSION = 13243
    EXCHANGE_2019_CU15_CONFIG_VERSION = 16763

    def _is_exchange_setup_path(self, setup_path):
        if not setup_path:
            return False
        if not os.path.isfile(setup_path) or os.path.basename(setup_path).lower() != "setup.exe":
            return False
        root = os.path.dirname(setup_path)
        return (
            os.path.exists(os.path.join(root, "ExchangeServer.msi"))
            or os.path.isdir(os.path.join(root, "Setup"))
            or os.path.isdir(os.path.join(root, "UCMARedist"))
        )

    def _exchange_setup_from_directory(self, directory):
        if not directory or not os.path.isdir(directory):
            return ""

        direct_setup = os.path.join(directory, "Setup.exe")
        if self._is_exchange_setup_path(direct_setup):
            return direct_setup

        for root, dirs, files in os.walk(directory):
            if "Setup.exe" in files:
                setup_path = os.path.join(root, "Setup.exe")
                if self._is_exchange_setup_path(setup_path):
                    return setup_path
            if root != directory:
                dirs[:] = []
        return ""

    def _exchange_media_resource_candidates(self):
        base = self.payload_path("EXCHANGE")
        media_name = self.EXCHANGE_CU15_MEDIA_NAME
        candidates = [
            os.path.join(base, media_name),
            os.path.join(base, media_name + ".iso"),
            os.path.join(base, media_name + ".img"),
        ]

        if os.path.isdir(base):
            for item_name in os.listdir(base):
                if item_name.lower().startswith(media_name.lower()):
                    candidate = os.path.join(base, item_name)
                    if candidate not in candidates:
                        candidates.append(candidate)
        return candidates

    def _setup_from_exchange_media_resource(self):
        self._exchange_prepare_schema_image_path = ""
        for candidate in self._exchange_media_resource_candidates():
            if os.path.isdir(candidate):
                setup_path = self._exchange_setup_from_directory(candidate)
                if setup_path:
                    return setup_path

            if os.path.isfile(candidate):
                extension = os.path.splitext(candidate)[1].lower()
                if extension in {"", ".iso", ".img"}:
                    ok, drive_or_error = SysUtils.mount_disk_image(candidate)
                    if ok:
                        self._exchange_prepare_schema_image_path = candidate
                        setup_path = os.path.join(f"{drive_or_error}:\\", "Setup.exe")
                        if self._is_exchange_setup_path(setup_path):
                            return setup_path
                        detected = self._find_exchange_setup(prefer_resources=False)
                        if detected:
                            return detected
                        SysUtils.dismount_disk_image(candidate)
                        self._exchange_prepare_schema_image_path = ""
                elif os.path.basename(candidate).lower() == "setup.exe" and self._is_exchange_setup_path(candidate):
                    return candidate
        return ""

    def _find_exchange_setup(self, prefer_resources=True):
        if prefer_resources:
            resource_setup = self._setup_from_exchange_media_resource()
            if resource_setup:
                return resource_setup

        candidates = []
        preferred = r"E:\Setup.exe"
        if os.path.exists(preferred):
            candidates.append(preferred)

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            setup_path = os.path.join(drive, "Setup.exe")
            if os.path.exists(setup_path) and setup_path not in candidates:
                candidates.append(setup_path)

        valid_candidates = [path for path in candidates if self._is_exchange_setup_path(path)]
        candidates = valid_candidates or candidates
        if not candidates:
            return ""

        def score(path):
            root = os.path.dirname(path)
            points = 1
            if os.path.exists(os.path.join(root, "ExchangeServer.msi")):
                points += 5
            if os.path.isdir(os.path.join(root, "Setup")):
                points += 2
            if os.path.isdir(os.path.join(root, "UCMARedist")):
                points += 2
            if os.path.normcase(path) == os.path.normcase(preferred):
                points += 1
            return points

        return max(candidates, key=score)

    def _is_valid_exchange_org_name(self, value):
        if not SysUtils.is_plain_value(value, max_len=64):
            return False
        return not any(char in str(value) for char in '<>;"')

    def _is_exchange_installed(self):
        return (
            SysUtils.is_service_installed("MSExchangeServiceHost")
            or SysUtils.is_service_installed("MSExchangeADTopology")
            or SysUtils.is_program_installed(["*Microsoft Exchange Server*"])
        )

    def pre_task_exchange_create_users(self):
        if not SysUtils.is_admin():
            self.ui_showerror(
                "Permisos de administrador",
                "Crear usuarios EXC necesita permisos de Administrador.\n\n"
                "Cierra Easy Deploy y ejecutalo con 'Ejecutar como administrador'.",
            )
            return

        if not self.ui_askyesno(
            "Crear usuarios EXC",
            "Requisitos antes de continuar:\n\n"
            "1. Ejecuta esta función dentro de la MV donde Exchange ya está instalado.\n\n"
            "2. Usa una cuenta con permisos para crear usuarios en AD y buzones en Exchange.\n\n"
            "3. El dominio del correo debe existir y responder desde esta máquina.\n\n"
            "4. El destino en AD es opcional. Ejemplo: et.ms.esp/Users o una ruta OU válida.\n"
            "   Si escribes solo ET, Users o User, Easy Deploy usará automáticamente et.ms.esp/Users.\n\n"
            "Easy Deploy generará un archivo temporal con los usuarios. Si el usuario no existe en AD, lo creará; si ya existe en AD y no tiene buzón, lo habilitará en Exchange sin tener que borrarlo.\n\n"
            "¿Quieres abrir el creador de usuarios?",
        ):
            return

        if not self._is_exchange_installed():
            if not self.ui_askyesno(
                "Exchange no detectado",
                "Easy Deploy no detecta claramente una instalación local de Exchange.\n\n"
                "Si estás en la MV correcta y Exchange Management Shell funciona, puedes continuar.\n\n"
                "¿Quieres continuar igualmente?",
            ):
                return

        users = self._exchange_users_dialog()
        if not users:
            return

        preview = "\n".join(f"- {user['Email']} ({user['FirstName']})" for user in users[:12])
        if len(users) > 12:
            preview += f"\n- ... y {len(users) - 12} usuario(s) mas"

        if self.ui_askyesno(
            "Confirmar usuarios Exchange",
            f"Se van a crear {len(users)} usuario(s) y buzon(es) en Exchange.\n\n"
            f"{preview}\n\n"
            "Continuar con la ejecucion?",
        ):
            self.iniciar_tarea(self.task_exchange_create_users, users)

    def _exchange_users_dialog(self):
        window_key = "crear_usuarios_exchange"
        if self._focus_secondary_window(window_key):
            return None

        result = {"users": None}
        users = []
        verified_domains = set()
        common = {"domain": "", "ou": "", "password": ""}
        colors = getattr(self, "colors", {})
        try:
            width = min(1120, max(1040, self.winfo_screenwidth() - 100))
        except Exception:
            width = 1120
        form_width = 430
        list_min_width = 500
        field_wrap = form_width - 64
        field_padx = (16, 24)
        try:
            height = max(720, min(900, self.winfo_screenheight() - 45))
        except Exception:
            height = 860

        dialog = ctk.CTkToplevel(self)
        dialog.title("Crear usuarios EXC")
        dialog.resizable(True, True)
        dialog.minsize(1040, 680)
        dialog.overrideredirect(False)
        dialog.configure(fg_color=(colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")))
        self._center_window(dialog, width, height)
        self._register_secondary_window(window_key, dialog)

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
        ctk.CTkLabel(badge, text="EXC", font=("Segoe UI", 13, "bold"), text_color=colors.get("accent", "#2F9E8F")).pack(fill="both", expand=True)

        title_label = ctk.CTkLabel(header, text="Crear usuarios Exchange", font=("Segoe UI", 20, "bold"), anchor="w")
        title_label.grid(row=0, column=1, sticky="ew")
        subtitle_label = ctk.CTkLabel(
            header,
            text="Alta rápida o masiva de usuarios en Exchange con correo",
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

        form_fields = ctk.CTkScrollableFrame(form, width=form_width - 28, fg_color="transparent")
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

        email_var = ctk.StringVar()
        first_name_var = ctk.StringVar()
        ou_var = ctk.StringVar()
        password_var = ctk.StringVar()
        reuse_var = ctk.BooleanVar(value=False)
        reuse_confirmed = {"value": False}
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
            "Correo completo o alias; destino vacío usa Users. El dominio se comprueba al ejecutar."
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
        add_label(form_fields, "Correo o alias", pady=(8, 4))
        email_entry = form_entry(
            form_fields,
            variable=email_var,
            placeholder_text="usuario@dominio o alias",
        )
        email_entry.pack(fill="x", padx=field_padx, pady=(0, 4))

        add_label(form_fields, "Nombre visible")
        first_entry = form_entry(
            form_fields,
            variable=first_name_var,
            placeholder_text="Ej: PC.COLAG.JEFE",
        )
        first_entry.pack(fill="x", padx=field_padx, pady=(0, 4))

        add_section_label(form_fields, "Destino y contraseña")
        add_label(form_fields, "Destino en AD (opcional / avanzado)")
        ou_entry = form_entry(
            form_fields,
            variable=ou_var,
            placeholder_text="Ej: et.ms.esp/Users o ET",
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
        reuse_check.pack(fill="x", padx=field_padx, pady=(12, 6))

        domain_label = ctk.CTkLabel(
            form_fields,
            text="Dominio actual: pendiente",
            font=("Segoe UI", 11, "bold"),
            text_color=colors.get("warning", "#D97706"),
            anchor="w",
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

        def set_status(text, error=True):
            status_label.configure(
                text=text,
                text_color=colors.get("danger", "#B42318") if error else colors.get("success", "#16803C"),
            )

        def refresh_list():
            users_box.configure(state="normal")
            users_box.delete("1.0", "end")
            if users:
                for idx, user in enumerate(users, start=1):
                    users_box.insert(
                        "end",
                        f"{idx:02d}. {user['Email']:<38} | {user['FirstName']:<28} | {user['OrganizationalUnit']}\n",
                    )
            else:
                users_box.insert("end", "Todavía no hay usuarios preparados.\n")
            users_box.configure(state="disabled")
            count_label.configure(text=f"{len(users)} usuario(s)")

        def update_domain_label():
            domain = common.get("domain") or ""
            if domain:
                domain_label.configure(text=f"Dominio actual: @{domain}", text_color=colors.get("success", "#16803C"))
                email_entry.configure(placeholder_text=f"Alias, correo completo o vacío para usar @{domain}")
            else:
                domain_label.configure(text="Dominio actual: pendiente", text_color=colors.get("warning", "#D97706"))
                email_entry.configure(placeholder_text="usuario@dominio o alias")

        def apply_reuse_lock():
            if not reuse_var.get():
                reuse_confirmed["value"] = False
            locked = bool(users and reuse_var.get() and reuse_confirmed["value"])
            state = "disabled" if locked else "normal"
            for widget in (email_entry, ou_entry, password_entry, password_toggle):
                try:
                    widget.configure(state=state)
                except Exception:
                    pass

        reuse_check.configure(command=apply_reuse_lock)

        def normalize_user_input():
            raw_email = email_var.get().strip()
            first_name = first_name_var.get().strip()
            ou = ou_var.get().strip() or common.get("ou", "")
            password = password_var.get().strip() or common.get("password", "")
            domain = common.get("domain", "")

            if not SysUtils.is_plain_value(first_name, max_len=128):
                return None, "Introduce un nombre visible válido."

            if raw_email:
                if "@" in raw_email:
                    email = raw_email
                else:
                    if not domain:
                        return None, "Para usar solo alias primero debes introducir un correo completo con @dominio."
                    email = f"{raw_email}@{domain}"
            else:
                if not domain:
                    return None, "El primer usuario necesita correo completo para detectar el dominio."
                local = self._exchange_email_local_from_name(first_name)
                if not local:
                    return None, "No se puede generar correo desde ese nombre visible. Escribe el correo o alias manualmente."
                email = f"{local}@{domain}"

            email = email.strip().lower()
            if not self.EXCHANGE_EMAIL_RE.match(email):
                return None, "Introduce un correo válido. Ejemplo: usuario@et.ms.esp"

            email_domain = email.split("@", 1)[1].lower()
            if not SysUtils.is_valid_domain(email_domain):
                return None, "El dominio del correo no tiene formato válido."

            if ou and not SysUtils.is_plain_value(ou, max_len=256):
                return None, "Introduce un destino en AD válido. Puedes dejarlo vacío para usar Users."
            if not SysUtils.is_plain_value(password, max_len=128):
                return None, "Introduce una contraseña válida."

            email_key = email.lower()
            name_key = first_name.lower()
            if any(user["Email"].lower() == email_key for user in users):
                return None, "Ese correo ya está en la lista."
            if any(user["FirstName"].lower() == name_key for user in users):
                return None, "Ya existe un usuario en la lista con ese nombre visible."

            return {
                "Email": email,
                "FirstName": first_name,
                "OrganizationalUnit": ou,
                "Password": password,
                "Domain": email_domain,
            }, ""

        def verify_domain(domain):
            if domain in verified_domains:
                return True
            set_status(f"Comprobando dominio @{domain}...", error=False)
            dialog.update_idletasks()
            ok, detail = self._exchange_probe_domain(domain)
            if ok:
                verified_domains.add(domain)
                set_status(f"Dominio comprobado: {detail}", error=False)
                return True
            set_status(
                "No se ha podido comprobar el dominio.\n"
                f"Detalle: {detail}\n"
                "Revisa DNS, conexión con dominio y que ejecutas esta función en la MV de Exchange.",
                error=True,
            )
            return False

        def add_user():
            user, error = normalize_user_input()
            if error:
                set_status(error, error=True)
                return
            if not verify_domain(user["Domain"]):
                return

            reuse_requested = bool(reuse_var.get())
            users.append(user)
            common["domain"] = user["Domain"]
            common["ou"] = user["OrganizationalUnit"]
            common["password"] = user["Password"]
            refresh_list()
            update_domain_label()

            if reuse_requested and not reuse_confirmed["value"]:
                try:
                    dialog.grab_release()
                except Exception:
                    pass
                reuse = askyesno_child_dialog(
                    self,
                    dialog,
                    "Reutilizar datos",
                    "¿Quieres reutilizar el dominio, destino en AD y contraseña para los siguientes usuarios?\n\n"
                    "Si aceptas, después podrás introducir solo el nombre visible y Easy Deploy generará el correo con el mismo dominio.",
                    "Sí",
                    "No",
                    key="exchange_reutilizar_datos",
                )
                reuse_confirmed["value"] = bool(reuse)
                reuse_var.set(bool(reuse))
                try:
                    self._focus_secondary_window(dialog)
                except Exception:
                    pass
            elif not reuse_requested:
                reuse_confirmed["value"] = False

            if reuse_var.get() and reuse_confirmed["value"]:
                email_var.set("")
                first_name_var.set("")
                ou_var.set(common["ou"])
                password_var.set(common["password"])
                apply_reuse_lock()
                first_entry.focus_set()
            else:
                email_var.set("")
                first_name_var.set("")
                ou_var.set("")
                password_var.set("")
                apply_reuse_lock()
                email_entry.focus_set()
            set_status(f"Usuario preparado: {user['Email']}", error=False)

        def remove_last():
            if not users:
                set_status("No hay usuarios para eliminar.", error=True)
                return
            removed = users.pop()
            refresh_list()
            apply_reuse_lock()
            set_status(f"Eliminado de la lista: {removed['Email']}", error=False)

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
        update_domain_label()
        apply_reuse_lock()
        self._focus_secondary_window(dialog)
        email_entry.focus_set()
        self.wait_window(dialog)
        return result["users"]

    def _exchange_email_local_from_name(self, name):
        text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
        text = text.strip().lower()
        text = re.sub(r"\s+", ".", text)
        text = re.sub(r"[^a-z0-9._-]", "", text)
        text = re.sub(r"\.+", ".", text).strip("._-")
        return text[:64]

    def _exchange_probe_domain(self, domain):
        script = f"""
        $domain = {SysUtils.ps_quote(domain)}
        function Try-ExchangeShell {{
            if (Get-Command Get-AcceptedDomain -ErrorAction SilentlyContinue) {{ return }}
            try {{
                if ($env:ExchangeInstallPath) {{
                    $remote = Join-Path $env:ExchangeInstallPath 'bin\\RemoteExchange.ps1'
                    if (Test-Path $remote) {{
                        . $remote
                        Connect-ExchangeServer -auto -ClientApplication:ManagementShell -ErrorAction SilentlyContinue | Out-Null
                    }}
                }}
            }} catch {{ }}
            try {{ Add-PSSnapin Microsoft.Exchange.Management.PowerShell.SnapIn -ErrorAction SilentlyContinue }} catch {{ }}
        }}

        Try-ExchangeShell
        try {{
            if (Get-Command Get-AcceptedDomain -ErrorAction SilentlyContinue) {{
                $accepted = Get-AcceptedDomain -ErrorAction SilentlyContinue | Where-Object {{
                    $_.DomainName.ToString().Equals($domain, [System.StringComparison]::OrdinalIgnoreCase) -or
                    $_.Name.ToString().Equals($domain, [System.StringComparison]::OrdinalIgnoreCase)
                }} | Select-Object -First 1
                if ($accepted) {{
                    "OK|Dominio aceptado en Exchange"
                    exit 0
                }}
            }}
        }} catch {{ }}

        try {{
            Import-Module ActiveDirectory -ErrorAction SilentlyContinue
            if (Get-Command Get-ADDomain -ErrorAction SilentlyContinue) {{
                $adDomain = Get-ADDomain -Identity $domain -ErrorAction Stop
                if ($adDomain) {{
                    "OK|Dominio detectado en Active Directory"
                    exit 0
                }}
            }}
        }} catch {{ }}

        try {{
            [System.Net.Dns]::GetHostEntry($domain) | Out-Null
            "OK|Dominio resuelve por DNS"
            exit 0
        }} catch {{ }}

        try {{
            if (Test-Connection -ComputerName $domain -Count 1 -Quiet -ErrorAction SilentlyContinue) {{
                "OK|Dominio responde a ping"
                exit 0
            }}
        }} catch {{ }}

        "FAIL|No se encontro el dominio en Exchange, AD, DNS ni ping"
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=25)
        if not ok:
            return False, output.strip() or "PowerShell no pudo comprobar el dominio"
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        result = lines[-1] if lines else ""
        if result.startswith("OK|"):
            return True, result.split("|", 1)[1]
        if result.startswith("FAIL|"):
            return False, result.split("|", 1)[1]
        return False, result or "Respuesta no reconocida al comprobar dominio"

    def _exchange_users_script_dir(self):
        return SysUtils.get_easydeploy_temp_scripts_dir()

    def _write_exchange_users_files(self, users):
        script_dir = self._exchange_users_script_dir()
        os.makedirs(script_dir, exist_ok=True)
        csv_path = SysUtils.make_temp_script_path("easydeploy_exchange_users", ".txt")
        ps1_path = SysUtils.make_temp_script_path("easydeploy_create_exchange_users", ".ps1")

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Email", "FirstName", "OrganizationalUnit", "Password"])
            writer.writeheader()
            for user in users:
                writer.writerow({
                    "Email": user["Email"],
                    "FirstName": user["FirstName"],
                    "OrganizationalUnit": user["OrganizationalUnit"],
                    "Password": user["Password"],
                })

        with open(ps1_path, "w", encoding="utf-8-sig") as handle:
            handle.write(self._exchange_create_users_script())

        return csv_path, ps1_path

    def _exchange_create_users_script(self):
        return r'''
param(
    [string]$CsvPath = $(Join-Path $PSScriptRoot 'matriz_usuarios.csv')
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$ErrorActionPreference = 'Continue'

$created = New-Object System.Collections.Generic.List[object]
$failed = New-Object System.Collections.Generic.List[object]

function Write-Step {
    param([string]$Message)
    Write-Output $Message
}

function Add-Failed {
    param([string]$Email, [string]$Name, [string]$Reason)
    $script:failed.Add([pscustomobject]@{
        Email = $Email
        Name = $Name
        Reason = $Reason
    }) | Out-Null
    Write-Output "[FALLIDO] $Email -> $Reason"
}

function Initialize-ExchangeShell {
    if (Get-Command New-Mailbox -ErrorAction SilentlyContinue) { return $true }
    if (Get-Command Enable-Mailbox -ErrorAction SilentlyContinue) { return $true }

    try {
        if ($env:ExchangeInstallPath) {
            $remote = Join-Path $env:ExchangeInstallPath 'bin\RemoteExchange.ps1'
            if (Test-Path $remote) {
                . $remote
                Connect-ExchangeServer -auto -ClientApplication:ManagementShell -ErrorAction SilentlyContinue | Out-Null
            }
        }
    } catch { }

    if (Get-Command Enable-Mailbox -ErrorAction SilentlyContinue) { return $true }

    try { Add-PSSnapin Microsoft.Exchange.Management.PowerShell.SnapIn -ErrorAction SilentlyContinue } catch { }
    return [bool](Get-Command Enable-Mailbox -ErrorAction SilentlyContinue)
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
    if ($parts.Count -eq 0) { throw "Dominio no valido: $DomainName" }
    return (($parts | ForEach-Object { 'DC=' + $_ }) -join ',')
}

function Get-WriteDomainController {
    param([string]$DomainName)
    try {
        $domain = Get-ADDomain -Identity $DomainName -ErrorAction Stop
        if ($domain.PDCEmulator) { return [string]$domain.PDCEmulator }
    } catch { }

    $dc = Get-ADDomainController -DomainName $DomainName -Discover -Writable -ErrorAction Stop
    return [string]$dc.HostName
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

    # Si el usuario escribe solo ET, et.ms.esp, Users o User, se fuerza el contenedor correcto de usuarios.
    if ($raw -ieq $domainShort -or $raw -ieq $DomainName -or $raw -ieq 'Users' -or $raw -ieq 'User') {
        return $defaultContainer
    }

    # Distinguished Name directo: OU=Usuarios,DC=et,DC=ms,DC=esp o CN=Users,DC=...
    if ($raw -match '(?i)(^|,)(OU|CN|DC)=') {
        if (Test-AdObjectExists -Identity $raw -Server $Server) { return $raw }
        throw "No existe en Active Directory la ruta DN indicada: $raw"
    }

    # Ruta canonica: et.ms.esp/Users, et.ms.esp/User, et.ms.esp/OU1/OU2
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
        throw "No existe la OrganizationalUnit/contenedor indicado: $raw. Usa por ejemplo $DomainName/Users o una OU real."
    }

    # Nombre simple de OU/contenedor: se acepta solo si es unico en el dominio.
    $escaped = Escape-LdapFilterValue $raw
    $matches = @(Get-ADObject -LDAPFilter "(|(&(objectClass=organizationalUnit)(ou=$escaped))(&(objectClass=container)(cn=$escaped)))" -SearchBase $domainDn -Server $Server -ErrorAction SilentlyContinue | Select-Object -First 2)
    if ($matches.Count -eq 1) { return [string]$matches[0].DistinguishedName }
    if ($matches.Count -gt 1) { throw "La ruta '$raw' es ambigua. Escribe la ruta completa, por ejemplo $DomainName/Users." }

    throw "No existe la OrganizationalUnit/contenedor '$raw'. Usa por ejemplo $DomainName/Users."
}

function New-SamAccountName {
    param([string]$Email)
    $local = ($Email -split '@')[0]
    $clean = $local -replace '[^A-Za-z0-9._-]', ''
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
        if ($repadmin) {
            Write-Output "[INFO] Solicitando sincronizacion AD desde $Server..."
            & repadmin.exe /syncall $Server /AdeP 2>$null | Out-String | ForEach-Object { $_.TrimEnd() } | Where-Object { $_ } | Write-Output
        }
    } catch { }
}

try {
    if (-not (Test-Path -LiteralPath $CsvPath)) {
        throw "No existe el archivo de usuarios: $CsvPath"
    }

    $users = @(Import-Csv -LiteralPath $CsvPath)
    if ($users.Count -eq 0) {
        throw 'El archivo de usuarios no contiene filas.'
    }

    Write-Step 'Inicializando Exchange Management Shell...'
    if (-not (Initialize-ExchangeShell)) {
        throw 'No se han podido cargar los cmdlets de Exchange. Ejecuta esta tarea en la MV de Exchange con Exchange instalado.'
    }

    try { Import-Module ActiveDirectory -ErrorAction Stop } catch {
        throw 'No se pudo cargar el modulo ActiveDirectory. Instala RSAT-ADDS-Tools o ejecuta desde un servidor con herramientas AD.'
    }

    Write-Output "[INFO] Usuarios a procesar: $($users.Count)"
    $usedDcs = New-Object System.Collections.Generic.HashSet[string]

    foreach ($user in $users) {
        $email = ([string]$user.Email).Trim().ToLowerInvariant()
        $firstName = ([string]$user.FirstName).Trim()
        $ou = ([string]$user.OrganizationalUnit).Trim()
        $plainPassword = [string]$user.Password

        Write-Output "[USUARIO] $email"

        if ([string]::IsNullOrWhiteSpace($email) -or [string]::IsNullOrWhiteSpace($firstName) -or [string]::IsNullOrWhiteSpace($plainPassword)) {
            Add-Failed -Email $email -Name $firstName -Reason 'Datos incompletos: Email, FirstName y Password son obligatorios.'
            continue
        }
        if ($email -notmatch '^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$') {
            Add-Failed -Email $email -Name $firstName -Reason 'Email no valido.'
            continue
        }

        try {
            $domainName = ($email -split '@', 2)[1]
            $writeDc = Get-WriteDomainController -DomainName $domainName
            $null = $usedDcs.Add($writeDc)
            if ([string]::IsNullOrWhiteSpace($ou)) {
                Write-Output "[INFO] OU vacía: se usará el contenedor Users del dominio."
            }
            $targetContainerDn = Resolve-TargetContainerDn -RawOu $ou -DomainName $domainName -Server $writeDc
            $sam = New-SamAccountName -Email $email
            $alias = $sam

            Write-Output "[AD] Controlador usado: $writeDc"
            Write-Output "[AD] Contenedor destino: $targetContainerDn"

            $escapedEmail = Escape-LdapFilterValue $email
            $escapedSam = Escape-LdapFilterValue $sam
            $domainDn = ConvertTo-DomainDn -DomainName $domainName
            $existingAd = Get-ADUser -LDAPFilter "(|(userPrincipalName=$escapedEmail)(mail=$escapedEmail)(sAMAccountName=$escapedSam))" -SearchBase $domainDn -Server $writeDc -Properties mail,userPrincipalName,distinguishedName,Enabled -ErrorAction SilentlyContinue | Select-Object -First 1

            $existingRecipient = Get-Recipient -Identity $email -DomainController $writeDc -ErrorAction SilentlyContinue
            if ($existingRecipient) {
                Add-Failed -Email $email -Name $firstName -Reason 'Ya existe un destinatario o buzon en Exchange con ese email.'
                continue
            }

            if ($existingAd) {
                $adUser = Get-ADUser -Identity $existingAd.DistinguishedName -Server $writeDc -Properties DistinguishedName,UserPrincipalName,mail,Enabled -ErrorAction Stop
                Write-Output "[INFO] Usuario AD existente detectado: $($adUser.DistinguishedName). Se habilitara buzon Exchange."

                $recipientForUser = Get-Recipient -Identity $adUser.DistinguishedName -DomainController $writeDc -ErrorAction SilentlyContinue
                if ($recipientForUser) {
                    Add-Failed -Email $email -Name $firstName -Reason "El usuario AD ya tiene destinatario o buzon Exchange: $($recipientForUser.PrimarySmtpAddress)"
                    continue
                }

                try {
                    Set-ADUser -Identity $adUser.DistinguishedName -UserPrincipalName $email -EmailAddress $email -Server $writeDc -ErrorAction SilentlyContinue
                } catch { }
            } else {
                $securePassword = ConvertTo-SecureString $plainPassword -AsPlainText -Force
                New-ADUser `
                    -Name $firstName `
                    -DisplayName $firstName `
                    -GivenName $firstName `
                    -UserPrincipalName $email `
                    -SamAccountName $sam `
                    -Path $targetContainerDn `
                    -AccountPassword $securePassword `
                    -Enabled $true `
                    -ChangePasswordAtLogon $false `
                    -Server $writeDc `
                    -ErrorAction Stop

                $adUser = Get-ADUser -Identity $sam -Server $writeDc -Properties DistinguishedName,UserPrincipalName,mail,Enabled -ErrorAction Stop
                if (-not $adUser) { throw 'New-ADUser no devolvio un usuario verificable.' }
                Write-Output "[OK] Usuario AD creado: $($adUser.DistinguishedName)"
            }

            try {
                Enable-Mailbox -Identity $adUser.DistinguishedName -Alias $alias -DomainController $writeDc -ErrorAction Stop | Out-Null
            } catch {
                throw "No se pudo habilitar el buzon Exchange para el usuario AD: $($_.Exception.Message)"
            }

            try {
                Set-Mailbox -Identity $adUser.DistinguishedName -PrimarySmtpAddress $email -EmailAddressPolicyEnabled $false -DomainController $writeDc -ErrorAction Stop | Out-Null
            } catch {
                Write-Output "[AVISO] Buzon habilitado, pero no se pudo fijar PrimarySmtpAddress manualmente: $($_.Exception.Message)"
            }

            try {
                Set-ADUser -Identity $adUser.DistinguishedName -EmailAddress $email -Server $writeDc -ErrorAction SilentlyContinue
            } catch { }

            $mailbox = Get-Mailbox -Identity $email -DomainController $writeDc -ErrorAction Stop
            if (-not $mailbox) { throw 'No se pudo verificar el buzon despues de habilitarlo.' }

            $created.Add([pscustomobject]@{ Email = $email; Name = $firstName; DistinguishedName = $adUser.DistinguishedName; DomainController = $writeDc }) | Out-Null
            Write-Output "[OK] Buzon Exchange habilitado: $email"
        } catch {
            Add-Failed -Email $email -Name $firstName -Reason $_.Exception.Message
        }
    }

    foreach ($dc in $usedDcs) { Try-SyncAdReplication -Server $dc }

    Write-Output ''
    Write-Output '=== RESUMEN EASY DEPLOY EXCHANGE ==='
    Write-Output "Creados: $($created.Count)"
    foreach ($item in $created) {
        Write-Output "CREADO|$($item.Email)|$($item.Name)"
        Write-Output "ADPATH|$($item.Email)|$($item.DistinguishedName)|$($item.DomainController)"
    }
    Write-Output "Fallidos: $($failed.Count)"
    foreach ($item in $failed) {
        Write-Output "FALLIDO|$($item.Email)|$($item.Name)|$($item.Reason)"
    }

    if ($failed.Count -gt 0) { exit 1 }
    exit 0
} catch {
    Write-Output "[ERROR] $($_.Exception.Message)"
    exit 10
}

'''

    def task_exchange_create_users(self, users):
        if not users:
            self._notify_task_error("Crear usuarios EXC", "No hay usuarios para procesar.")
            return

        if not self._require_windows_server(
            "Crear usuarios EXC",
            "La creacion de usuarios Exchange debe ejecutarse en Windows Server dentro de la VM de Exchange.",
        ):
            return

        csv_path = ""
        ps1_path = ""
        created = []
        failed = []

        try:
            print("Preparando creacion de usuarios Exchange...")
            print(f"Usuarios recibidos: {len(users)}")
            print("El archivo temporal de usuarios se borrara automaticamente al finalizar.")
            self.update_progress(0.05)

            csv_path, ps1_path = self._write_exchange_users_files(users)
            print(f"Script temporal: {ps1_path}")
            print("CSV/TXT temporal creado. No se mostraran passwords en consola.")
            self.update_progress(0.10)

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
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            processed = 0
            total = max(1, len(users))
            while True:
                if self.stop_event.is_set():
                    print("[AVISO] Cancelacion solicitada. Deteniendo script Exchange...")
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
                    clean = line.rstrip()
                    print(clean)
                    if clean.startswith("[USUARIO]"):
                        processed += 1
                        self.update_progress(0.10 + min(0.80, 0.80 * (processed / total)))
                    elif clean.startswith("CREADO|"):
                        parts = clean.split("|", 2)
                        if len(parts) >= 3:
                            created.append((parts[1], parts[2]))
                    elif clean.startswith("FALLIDO|"):
                        parts = clean.split("|", 3)
                        if len(parts) >= 4:
                            failed.append((parts[1], parts[2], parts[3]))

                if process.poll() is not None:
                    if process.stdout:
                        for remaining in process.stdout:
                            clean = remaining.rstrip()
                            if clean:
                                print(clean)
                                if clean.startswith("CREADO|"):
                                    parts = clean.split("|", 2)
                                    if len(parts) >= 3:
                                        created.append((parts[1], parts[2]))
                                elif clean.startswith("FALLIDO|"):
                                    parts = clean.split("|", 3)
                                    if len(parts) >= 4:
                                        failed.append((parts[1], parts[2], parts[3]))
                    break

                if not line:
                    time.sleep(0.2)

            self.update_progress(1.0)
            if process.returncode == 0 and not failed:
                self.ui_showinfo(
                    "Crear usuarios EXC",
                    f"Proceso completado correctamente.\n\nUsuarios creados: {len(created)}\nFallidos: 0",
                )
                return

            failed_preview = "\n".join(f"- {email}: {reason}" for email, _name, reason in failed[:12])
            if len(failed) > 12:
                failed_preview += f"\n- ... y {len(failed) - 12} fallo(s) mas. Revisa el log."
            if not failed_preview:
                failed_preview = "El script devolvio codigo no correcto. Revisa el log para ver el detalle."

            self._notify_task_warning(
                "Crear usuarios EXC",
                f"Proceso finalizado con incidencias.\n\n"
                f"Usuarios creados: {len(created)}\n"
                f"Usuarios fallidos: {len(failed)}\n\n"
                f"{failed_preview}",
            )
        except Exception as exc:
            self._notify_task_error(
                "Crear usuarios EXC",
                f"No se pudo crear o ejecutar el script de usuarios Exchange.\n\nDetalle: {exc}",
            )
        finally:
            for path in (csv_path, ps1_path):
                SysUtils.cleanup_temp_file(path)

    def pre_task_exchange_prereqs(self):
        if not SysUtils.is_admin():
            self.ui_showerror(
                "Permisos de administrador",
                "Prerrequisitos Exchange necesita permisos de Administrador.\n\n"
                "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
            )
            return

        if not self.ui_askyesno(
            "Prerrequisitos Exchange",
            "Esta tarea instalará roles, características y prerrequisitos locales necesarios para Exchange.\n\n"
            "No lanzará el Setup principal de Exchange.\n\n"
            "Antes de continuar, confirma que la máquina virtual está unida al dominio y que la carpeta EXCHANGE contiene los recursos necesarios.\n\n"
            "¿Quieres instalar los prerrequisitos de Exchange ahora?"
        ):
            print("Instalacion de prerrequisitos Exchange cancelada por el usuario.")
            return

        self.iniciar_tarea(self.task_exchange_prereqs)

    def pre_task_exchange_install(self):
        if not self.ui_askyesno(
            "Confirmar requisitos Exchange",
            "Antes de continuar, confirma que se cumplen TODOS estos requisitos:\n\n"
            "1. DOMINIO: La maquina virtual donde vas a instalar Exchange ya esta unida al dominio.\n\n"
            "2. PREPARACION: Ya se ha ejecutado Prepare Schema/Prepare AD desde este apartado.\n\n"
            "3. PRERREQUISITOS: Ya se ha ejecutado Prerrequisitos Exchange y no hay reinicio pendiente.\n\n"
            "4. RECURSOS: La carpeta EXCHANGE contiene la ISO o el medio de Exchange Server 2019 CU15 esta montado.\n\n"
            "5. PERMISOS: Estas usando una cuenta con permisos suficientes para instalar Exchange.\n\n"
            "Easy Deploy no comprobara prerrequisitos desde este boton; Exchange Setup hara su propio Readiness Check.\n\n"
            "Quieres continuar con la instalacion de Exchange?"
        ):
            print("Instalacion de Exchange cancelada por el usuario en la confirmacion de requisitos.")
            return

        self.iniciar_tarea(self.task_exchange)

    def pre_task_exchange_recover_server(self):
        task_started = False
        if not SysUtils.is_admin():
            self.ui_showerror(
                "Permisos de administrador",
                "RecoverServer necesita permisos de Administrador.\n\n"
                "Cierra Easy Deploy y ejecutalo con 'Ejecutar como administrador'.",
            )
            return

        if not self.ui_askyesno(
            "RecoverServer Exchange",
            "Esta función NO borra objetos de Exchange en Active Directory.\n\n"
            "Ejecuta el modo oficial RecoverServer cuando el instalador indica que Exchange está en un estado inconsistente y AD ya tiene registrado este servidor.\n\n"
            "Requisitos importantes:\n\n"
            "- El servidor debe tener el MISMO nombre de equipo que el objeto Exchange registrado en AD.\n"
            "- Debe estar unido al mismo dominio.\n"
            "- Usa una cuenta con permisos de administrador de dominio y administración de Exchange.\n"
            "- El medio debe ser la misma CU o una CU posterior a la registrada en AD.\n"
            "- Si Exchange estaba en una ruta personalizada, debe recuperarse en esa misma ruta.\n\n"
            "¿Quieres ejecutar RecoverServer ahora?",
        ):
            return

        try:
            setup_path = self._find_exchange_setup(prefer_resources=True)
            if not setup_path:
                expected_paths = "\n".join(f"- {path}" for path in self._exchange_media_resource_candidates())
                self.ui_showerror(
                    "Medio de Exchange no encontrado",
                    "No he podido preparar automaticamente el medio de Exchange.\n\n"
                    "Comprueba que exista ExchangeServer2019-x64-cu15 dentro de la carpeta EXCHANGE de recursos.\n\n"
                    f"Rutas esperadas:\n{expected_paths}",
                )
                return

            if not self._is_exchange_setup_path(setup_path):
                self.ui_showerror(
                    "Setup.exe no valido",
                    "El medio detectado no parece un Setup.exe valido de Exchange.",
                )
                return

            target_dir = self._detect_exchange_target_dir()
            target_message = (
                f"Ruta Exchange detectada: {target_dir}\n"
                "Easy Deploy anadira /TargetDir para recuperar en esa ruta."
                if target_dir
                else "No se ha detectado una ruta personalizada. RecoverServer usara la ruta por defecto de Exchange."
            )
            if self.ui_askyesno(
                "Confirmar RecoverServer",
                f"Setup.exe: {setup_path}\n\n"
                f"{target_message}\n\n"
                "Confirma que el nombre de equipo actual coincide con el servidor Exchange registrado en AD.\n\n"
                "Continuar?",
            ):
                task_started = True
                self.iniciar_tarea(self.task_exchange_recover_server, setup_path, target_dir)
        finally:
            mounted_image = getattr(self, "_exchange_prepare_schema_image_path", "")
            if mounted_image and not task_started:
                self._dismount_task_media(mounted_image, "cancelada")
                self._exchange_prepare_schema_image_path = ""

    def _exchange_prereq_checks(self):
        return {
            "Net Framework 4.8.exe": (
                ".NET Framework 4.8 o superior",
                lambda: SysUtils.is_dotnet_release_at_least(528040),
            ),
            "rewrite_amd64_es-ES.msi": (
                "IIS URL Rewrite Module 2",
                lambda: self._is_iis_url_rewrite_installed(),
            ),
            "UcmaRuntimeSetup.exe": (
                "Unified Communications Managed API 4.0 Runtime",
                lambda: SysUtils.is_program_installed([
                    "*Unified Communications Managed API 4.0*",
                    "*UCMA 4.0*",
                ]),
            ),
            "vcredist_x64 2012.exe": (
                "Microsoft Visual C++ 2012 Redistributable x64",
                lambda: SysUtils.is_program_installed([
                    "*Microsoft Visual C++ 2012*Redistributable*x64*",
                    "*Microsoft Visual C++ 2012*x64*",
                ]),
            ),
            "vcredist_x64 2013.exe": (
                "Microsoft Visual C++ 2013 Redistributable x64",
                lambda: SysUtils.is_program_installed([
                    "*Microsoft Visual C++ 2013*Redistributable*x64*",
                    "*Microsoft Visual C++ 2013*x64*",
                ]),
            ),
        }

    def _detect_iis_url_rewrite_display_name(self):
        script = r"""
        $paths = @(
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
        )
        foreach ($path in $paths) {
            Get-ItemProperty -Path $path -ErrorAction SilentlyContinue | ForEach-Object {
                $display = [string]$_.DisplayName
                if (-not [string]::IsNullOrWhiteSpace($display)) {
                    if ($display -match 'URL\s*Rewrite' -and ($display -match 'IIS|Microsoft')) {
                        $display
                        exit 0
                    }
                }
            }
        }
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=20)
        if not ok:
            return ""
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines[-1] if lines else ""

    def _is_iis_url_rewrite_installed(self):
        return bool(self._detect_iis_url_rewrite_display_name())

    def _exchange_prereq_files(self):
        return [
            "Net Framework 4.8.exe",
            "rewrite_amd64_es-ES.msi",
            "UcmaRuntimeSetup.exe",
            "vcredist_x64 2012.exe",
            "vcredist_x64 2013.exe",
        ]

    def _exchange_required_features(self):
        return [
            "Server-Media-Foundation", "NET-Framework-45-Features", "NET-Framework-45-Core",
            "NET-Framework-45-ASPNET", "NET-WCF-HTTP-Activation45", "NET-WCF-Pipe-Activation45",
            "NET-WCF-TCP-Activation45", "NET-WCF-TCP-PortSharing45", "RPC-over-HTTP-Proxy",
            "RSAT-Clustering", "RSAT-Clustering-CmdInterface", "RSAT-Clustering-Mgmt", "RSAT-Clustering-PowerShell",
            "WAS-Process-Model", "Web-Asp-Net45", "Web-Basic-Auth", "Web-Client-Auth", "Web-Digest-Auth",
            "Web-Dir-Browsing", "Web-Dyn-Compression", "Web-Http-Errors", "Web-Http-Logging", "Web-Http-Redirect",
            "Web-Http-Tracing", "Web-ISAPI-Ext", "Web-ISAPI-Filter", "Web-Lgcy-Mgmt-Console", "Web-Metabase",
            "Web-Mgmt-Console", "Web-Mgmt-Service", "Web-Net-Ext45", "Web-Request-Monitor", "Web-Server",
            "Web-Stat-Compression", "Web-Static-Content", "Web-Windows-Auth", "Web-WMI",
            "Windows-Identity-Foundation", "RSAT-ADDS",
        ]

    def _exchange_prerequisite_status(self, base=None, verbose=True):
        base = base or self.payload_path("EXCHANGE")
        exchange_features = self._exchange_required_features()
        missing_features = SysUtils.missing_windows_features(exchange_features)
        missing_lookup = {feature.casefold() for feature in missing_features}

        if verbose:
            print("Comprobando caracteristicas de Windows necesarias para Exchange...")
            for feature in exchange_features:
                if feature.casefold() in missing_lookup:
                    print(f"[FALTA] {feature}")
                else:
                    print(f"[OK] Ya instalado: {feature}")

            print("\nComprobando prerrequisitos locales Exchange...")

        prereq_checks = self._exchange_prereq_checks()
        missing_prereqs = []
        missing_files = []

        for prereq_file in self._exchange_prereq_files():
            prereq_label, prereq_check = prereq_checks.get(prereq_file, (prereq_file, lambda: False))
            if verbose:
                print(f">>> Verificando: {prereq_label}")

            try:
                already_installed = bool(prereq_check())
            except Exception as exc:
                already_installed = False
                if verbose:
                    print(f"   [AVISO] No se pudo comprobar {prereq_label}: {exc}")

            if already_installed:
                if prereq_file == "rewrite_amd64_es-ES.msi":
                    display_name = self._detect_iis_url_rewrite_display_name()
                    if verbose and display_name:
                        print(f"   [OK] Detectado por DisplayName: {display_name}")
                if verbose:
                    print(f"   [OK] {prereq_label} ya esta instalado.")
                continue

            missing_prereqs.append(prereq_label)
            prereq_path = os.path.join(base, prereq_file)
            if not os.path.exists(prereq_path):
                missing_files.append(prereq_file)
                if verbose:
                    print(f"   [FALTA] No instalado y falta el recurso: {prereq_file}")
            elif verbose:
                print(f"   [FALTA] No instalado. Recurso disponible: {prereq_file}")

        return {
            "missing_features": missing_features,
            "missing_prereqs": missing_prereqs,
            "missing_files": missing_files,
        }

    def _format_exchange_prereq_status_message(self, status):
        details = []
        missing_features = status.get("missing_features") or []
        missing_prereqs = status.get("missing_prereqs") or []
        missing_files = status.get("missing_files") or []

        if missing_features:
            details.append("Características Windows pendientes:\n- " + "\n- ".join(missing_features))
        if missing_prereqs:
            details.append("Prerrequisitos locales pendientes:\n- " + "\n- ".join(missing_prereqs))
        if missing_files:
            details.append("Recursos que faltan en EXCHANGE:\n- " + "\n- ".join(missing_files))

        return "\n\n".join(details)

    def _install_exchange_windows_features(self):
        print("Comprobando caracteristicas de Windows necesarias para Exchange...")
        if self.stop_event.is_set():
            return False

        exchange_features = self._exchange_required_features()
        missing_features = SysUtils.missing_windows_features(exchange_features)
        missing_lookup = {feature.casefold() for feature in missing_features}
        for feature in exchange_features:
            if feature.casefold() in missing_lookup:
                print(f"[FALTA] {feature}")
            else:
                print(f"[OMITIDO] Ya instalado: {feature}")

        if not missing_features:
            print("[OK] Todas las caracteristicas de Windows necesarias ya estaban instaladas.")
            self.update_progress(0.1)
            return True

        print(f"Instalando {len(missing_features)} caracteristicas pendientes...")
        sxs_source = SysUtils.find_sxs_source()
        features_cmd = (
            "Install-WindowsFeature -Name "
            + ",".join(missing_features)
            + " -IncludeManagementTools -Restart:$false"
            + (f" -Source {SysUtils.ps_quote(sxs_source)}" if sxs_source else "")
        )
        res, feature_output = SysUtils.run_powershell(features_cmd, capture=True, timeout=1800)
        if feature_output.strip():
            print(feature_output.strip())
        remaining_features = SysUtils.missing_windows_features(exchange_features)
        if (not res) or remaining_features:
            if remaining_features:
                print("[ERROR] Siguen faltando caracteristicas Exchange: " + ", ".join(remaining_features))
            self._notify_task_error(
                "Exchange",
                "No se han podido instalar todas las caracteristicas de Windows necesarias para Exchange.\n\n"
                + (
                    "Siguen pendientes:\n- " + "\n- ".join(remaining_features) + "\n\n"
                    if remaining_features
                    else ""
                )
                + "Revisa permisos de administrador y el origen de Windows Features. Si la VM no tiene origen local, monta el ISO de Windows Server para que Easy Deploy pueda usar Sources\\SxS.",
            )
            return False

        print("[OK] Caracteristicas de Windows instaladas correctamente.")
        self.update_progress(0.1)
        return True

    def _install_exchange_local_prereqs(self, base):
        print("Comprobando prerrequisitos locales Exchange...")
        prereqs = self._exchange_prereq_files()
        total_steps = len(prereqs)
        prereq_checks = self._exchange_prereq_checks()
        all_ok = True
        restart_required = False

        for i, prereq_file in enumerate(prereqs):
            if self.stop_event.is_set():
                return False, restart_required
            path = os.path.join(base, prereq_file)
            prereq_label, prereq_check = prereq_checks.get(prereq_file, (prereq_file, lambda: False))
            print(f"\n>>> Verificando: {prereq_label}")

            try:
                already_installed = bool(prereq_check())
            except Exception:
                already_installed = False

            if already_installed:
                if prereq_file == "rewrite_amd64_es-ES.msi":
                    display_name = self._detect_iis_url_rewrite_display_name()
                    if display_name:
                        print(f"   [OMITIDO] Detectado por DisplayName: {display_name}")
                print(f"   [OMITIDO] {prereq_label} ya esta instalado.")
                self.update_progress(0.1 + (0.8 * ((i + 1) / total_steps)))
                continue

            if os.path.exists(path):
                print(f"   Ruta encontrada: {path}")
                cmd = ["msiexec.exe", "/i", path, "/quiet", "/norestart"] if prereq_file.endswith(".msi") else [path, "/quiet", "/norestart"]
                print("   Comando: " + " ".join(f'"{part}"' if " " in str(part) else str(part) for part in cmd))
                try:
                    result = subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                    print(f"   Codigo de salida: {result.returncode}")
                    if result.returncode in (0, 3010, 1641):
                        print("   [OK] Instalado correctamente.")
                        if result.returncode in (3010, 1641):
                            restart_required = True
                    else:
                        all_ok = False
                        print(f"   [AVISO] Instalacion finalizada con codigo de salida: {result.returncode}. Revisar log.")
                    if prereq_file == "rewrite_amd64_es-ES.msi":
                        display_name = self._detect_iis_url_rewrite_display_name()
                        if display_name:
                            print(f"   [OK] Deteccion posterior por DisplayName: {display_name}")
                        else:
                            all_ok = False
                            print("   [AVISO] Deteccion posterior por DisplayName: no se encontro URL Rewrite.")
                except Exception as exc:
                    all_ok = False
                    print(f"   [ERROR] Error ejecutando instalador: {exc}")
            else:
                all_ok = False
                self._notify_task_warning(
                    "Prerequisito Exchange",
                    f"No se encuentra el archivo de prerrequisito:\n\n{prereq_file}\n\n"
                    "Easy Deploy continuara con el resto, pero Exchange podria fallar si falta este componente.",
                )

            self.update_progress(0.1 + (0.8 * ((i + 1) / total_steps)))

        return all_ok, restart_required

    def _notify_exchange_restart_required(self, title="Reinicio requerido"):
        self.console_finish_state = "restart"
        print("[AVISO] Windows indica que hay un reinicio pendiente antes de continuar con Exchange.")
        self.ui_showwarning(
            title,
            "Windows indica que hay un reinicio pendiente.\n\n"
            "Reinicia el servidor antes de continuar con Exchange. "
            "El boton Reiniciar sistema aparece abajo en Easy Deploy.",
        )

    def _launch_exchange_setup_from_media(self, base, iso_exchange):
        print(f"\n>>> Paso Final: Procesando ISO {iso_exchange}")
        iso_path = os.path.join(base, iso_exchange)
        mounted_image = ""
        if not os.path.exists(iso_path):
            setup_path = self._find_exchange_setup(prefer_resources=False)
            if setup_path and self._is_exchange_setup_path(setup_path):
                print(f"   [OK] Setup.exe detectado en medio ya disponible: {setup_path}")
                print("   Lanzando instalador principal de Exchange...")
                process = subprocess.Popen([setup_path], creationflags=0)
                if not self._wait_for_media_installer_confirmation(process, "Exchange Setup"):
                    print("   [AVISO] Instalacion de Exchange cancelada desde Easy Deploy.")
                    return False
                print("   [OK] Usuario confirmo fin/cancelacion del instalador de Exchange.")
                return True

            self._notify_task_error(
                "Exchange",
                f"No se encuentra la ISO de Exchange:\n\n{iso_path}\n\n"
                "Coloca ExchangeServer2019-x64-cu15.iso en la carpeta EXCHANGE o monta el medio de Exchange y vuelve a intentarlo.",
            )
            return False

        try:
            print("   Montando imagen ISO en Windows...")
            mounted, drive_or_error = SysUtils.mount_disk_image(iso_path)
            if not mounted:
                self._notify_task_error(
                    "Exchange",
                    "No se pudo montar la ISO de Exchange automaticamente.\n\n"
                    f"Detalle: {drive_or_error}",
                )
                return False

            mounted_image = iso_path
            print(f"   [OK] ISO montada en unidad [{drive_or_error}:]")
            setup_path = f"{drive_or_error}:\\Setup.exe"

            if not os.path.exists(setup_path):
                self._notify_task_error(
                    "Exchange",
                    f"La ISO se ha montado en {drive_or_error}: pero no se encuentra Setup.exe.\n\n"
                    "Comprueba que la ISO corresponde a Exchange Server 2019 CU15.",
                )
                return False

            print(f"   [OK] Setup.exe detectado: {setup_path}")
            print("   Lanzando instalador principal de Exchange...")
            print("   Completa la instalacion. Easy Deploy NO extraera el CD/ISO hasta que pulses Aceptar.")
            process = subprocess.Popen([setup_path], creationflags=0)
            if not self._wait_for_media_installer_confirmation(process, "Exchange Setup"):
                print("   [AVISO] Instalacion de Exchange cancelada desde Easy Deploy.")
                return False
            print("   [OK] Usuario confirmo fin/cancelacion del instalador de Exchange.")
            return True
        except Exception as exc:
            self._notify_task_error(
                "Exchange",
                f"Fallo al gestionar la ISO o lanzar el instalador.\n\nDetalle: {exc}",
            )
            return False
        finally:
            if mounted_image:
                reason = "cancelada" if self.stop_event.is_set() else "finalizada"
                self._dismount_task_media(mounted_image, reason, ask_user=False)

    def _detect_exchange_target_dir(self):
        script = r"""
        $paths = @(
            'HKLM:\SOFTWARE\Microsoft\ExchangeServer\v15\Setup',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\ExchangeServer\v15\Setup'
        )
        foreach ($path in $paths) {
            if (Test-Path $path) {
                $item = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue
                foreach ($name in @('MsiInstallPath','InstallPath')) {
                    $value = $item.$name
                    if ($value) {
                        $clean = [string]$value
                        $clean = $clean.TrimEnd('\')
                        if ($clean -and $clean -ine "$env:ProgramFiles\Microsoft\Exchange Server\V15") {
                            $clean
                            exit 0
                        }
                    }
                }
            }
        }
        ''
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=15)
        if not ok:
            return ""
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines[-1] if lines else ""

    def pre_task_exchange_schema(self):
        task_started = False
        if not SysUtils.is_admin():
            self.ui_showerror(
                "Permisos de administrador",
                "Prepare Schema necesita permisos de Administrador.\n\n"
                "Cierra Easy Deploy y ejecutalo con 'Ejecutar como administrador'.",
            )
            return

        if not self.ui_askyesno(
            "Prepare Schema",
            "Antes de preparar el schema comprueba estos requisitos:\n\n"
            "- Ejecuta Easy Deploy como administrador.\n"
            "- Inicia sesion con una cuenta DEL DOMINIO, no con un administrador local del equipo.\n"
            "- La cuenta debe pertenecer a Schema Admins y Enterprise Admins.\n"
            "- Si acabas de anadir la cuenta a esos grupos, cierra sesion y vuelve a entrar.\n"
            "- El equipo debe resolver el dominio por DNS.\n"
            "- RSAT-ADDS-Tools debe estar instalado. Easy Deploy lo comprobara e intentara instalarlo si falta.\n\n"
            "Easy Deploy preparara automaticamente el medio ExchangeServer2019-x64-cu15 desde recursos.\n\n"
            "Quieres preparar el schema ahora?"
        ):
            return

        try:
            setup_path = self._find_exchange_setup(prefer_resources=True)
            if not setup_path:
                expected_paths = "\n".join(f"- {path}" for path in self._exchange_media_resource_candidates())
                self.ui_showerror(
                    "Medio de Exchange no encontrado",
                    "No he podido preparar automaticamente el medio de Exchange.\n\n"
                    "Comprueba que exista ExchangeServer2019-x64-cu15 dentro de la carpeta EXCHANGE de recursos.\n\n"
                    f"Rutas esperadas:\n{expected_paths}"
                )
                return

            domain_name = self.input_dialog("Dominio", "Nombre DNS del dominio a comprobar\nEj: et.ms.esp")
            if not domain_name:
                return
            domain_name = domain_name.strip()
            if not self._validate_or_show(
                domain_name,
                SysUtils.is_valid_domain,
                "Dominio no valido",
                "Introduce un dominio DNS valido. Ejemplo: et.ms.esp"
            ):
                return

            organization_name = self.input_dialog("Organization Name", "Nombre de organizacion de Exchange\nEj: EXOIP")
            if not organization_name:
                return
            organization_name = organization_name.strip()
            if not self._validate_or_show(
                organization_name,
                self._is_valid_exchange_org_name,
                "Organization Name no valido",
                "Introduce un nombre sin comillas, punto y coma, < o >. Maximo 64 caracteres."
            ):
                return

            if not self._is_exchange_setup_path(setup_path):
                self.ui_showerror(
                    "Setup.exe no valido",
                    "El medio detectado no parece un Setup.exe valido de Exchange."
                )
                return

            if self.ui_askyesno(
                "Confirmar Prepare Schema",
                f"Dominio: {domain_name}\n"
                f"Organization Name: {organization_name}\n"
                "Medio de Exchange: detectado automaticamente\n\n"
                "Continuar?"
            ):
                task_started = True
                self.iniciar_tarea(self.task_exchange_prepare_schema, domain_name, organization_name, setup_path)
        finally:
            mounted_image = getattr(self, "_exchange_prepare_schema_image_path", "")
            if mounted_image and not task_started:
                self._dismount_task_media(mounted_image, "cancelada")
                self._exchange_prepare_schema_image_path = ""

    def _ensure_exchange_schema_ad_tools(self):
        """Comprueba e instala las herramientas AD necesarias para Prepare Schema."""
        script = r"""
        $names = @('RSAT-ADDS-Tools','RSAT-ADDS','RSAT-AD-PowerShell')
        $available = @()
        foreach ($name in $names) {
            $feature = Get-WindowsFeature -Name $name -ErrorAction SilentlyContinue
            if ($feature) { $available += $feature }
        }

        if ($available.Count -eq 0) {
            'FAIL|No se encontraron caracteristicas RSAT-ADDS en este Windows Server.'
            return
        }

        $missing = @($available | Where-Object { -not $_.Installed } | Select-Object -ExpandProperty Name)
        if ($missing.Count -gt 0) {
            'INSTALL|' + ($missing -join ', ')
            Install-WindowsFeature -Name $missing -IncludeManagementTools -Restart:$false | Out-String
        }

        $failed = @()
        foreach ($feature in $available) {
            $current = Get-WindowsFeature -Name $feature.Name -ErrorAction SilentlyContinue
            if ($current -and -not $current.Installed) { $failed += $feature.Name }
        }

        if ($failed.Count -gt 0) {
            'FAIL|No se pudieron instalar: ' + ($failed -join ', ')
            return
        }

        'OK|Herramientas RSAT/ADDS disponibles.'
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=900)
        cleaned = output.strip()
        if cleaned:
            print(cleaned)
        if not ok:
            return False, (
                "No se pudo comprobar o instalar RSAT-ADDS-Tools.\n\n"
                "Ejecuta Easy Deploy como administrador y revisa que Windows pueda instalar caracteristicas.\n\n"
                f"Detalle:\n{cleaned}"
            )
        for line in cleaned.splitlines():
            if line.startswith("FAIL|"):
                return False, line.split("|", 1)[1].strip()
        return any(line.startswith("OK|") for line in cleaned.splitlines()), cleaned

    def _exchange_schema_environment_report(self, domain_name):
        domain_literal = SysUtils.ps_quote(domain_name)
        script = f"""
        $domainName = {domain_literal}
        $cs = Get-CimInstance Win32_ComputerSystem
        $who = whoami
        $groups = whoami /groups /fo csv /nh 2>$null
        "WHOAMI=$who"
        "USERDOMAIN=$env:USERDOMAIN"
        "COMPUTERNAME=$env:COMPUTERNAME"
        "PART_OF_DOMAIN=$($cs.PartOfDomain)"
        "COMPUTER_DOMAIN=$($cs.Domain)"
        "LOCAL_USER=$($env:USERDOMAIN -ieq $env:COMPUTERNAME)"
        "HAS_SCHEMA_ADMINS=$([bool]($groups -match '-518'))"
        "HAS_ENTERPRISE_ADMINS=$([bool]($groups -match '-519'))"
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $forest = Get-ADForest -Server $domainName -ErrorAction Stop
            "FOREST_MODE=$($forest.ForestMode)"
        }} catch {{
            "AD_ERROR=$($_.Exception.Message)"
        }}
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=60)
        data = {}
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip()
        return ok, output.strip(), data

    def _validate_exchange_schema_environment(self, domain_name):
        print("\n>>> Comprobando herramientas AD para Prepare Schema")
        tools_ok, tools_message = self._ensure_exchange_schema_ad_tools()
        if not tools_ok:
            self._notify_task_error(
                "Prepare Schema",
                "Falta RSAT-ADDS-Tools o no se ha podido instalar.\n\n"
                "Exchange Setup necesita estas herramientas para leer y modificar Active Directory.\n\n"
                f"{tools_message}",
            )
            return False

        print("\n>>> Comprobando sesion de dominio y permisos")
        ok, output, data = self._exchange_schema_environment_report(domain_name)
        if output:
            print(output)
        if not ok:
            self._notify_task_error(
                "Prepare Schema",
                "No se pudo comprobar la sesion de dominio ni los grupos del usuario.\n\n"
                "Revisa que RSAT-ADDS-Tools este instalado y que el equipo pueda consultar Active Directory.",
            )
            return False

        whoami = data.get("WHOAMI", "desconocido")
        if data.get("PART_OF_DOMAIN", "").lower() != "true":
            self._notify_task_error(
                "Prepare Schema",
                "Este equipo no parece estar unido a un dominio de Active Directory.\n\n"
                "Prepare Schema debe ejecutarse desde un DC o desde un servidor unido al dominio.",
            )
            return False

        if data.get("LOCAL_USER", "").lower() == "true":
            self._notify_task_error(
                "Prepare Schema",
                "Easy Deploy se esta ejecutando con una cuenta LOCAL del equipo:\n\n"
                f"{whoami}\n\n"
                "Exchange PrepareSchema requiere una cuenta DEL DOMINIO con permisos de Schema Admins y Enterprise Admins.\n\n"
                "Solucion: cierra sesion en Windows e inicia sesion como usuario del dominio. Ejemplo: ET\\Administrador o et.ms.esp\\administrador.",
            )
            return False

        missing_groups = []
        if data.get("HAS_SCHEMA_ADMINS", "").lower() != "true":
            missing_groups.append("Schema Admins")
        if data.get("HAS_ENTERPRISE_ADMINS", "").lower() != "true":
            missing_groups.append("Enterprise Admins")
        if missing_groups:
            self._notify_task_error(
                "Prepare Schema",
                "La cuenta actual no tiene todos los grupos requeridos por Exchange.\n\n"
                f"Usuario actual: {whoami}\n"
                "Faltan en el token de sesion: " + ", ".join(missing_groups) + "\n\n"
                "Anade la cuenta a esos grupos y cierra sesion/vuelve a entrar para refrescar el token.",
            )
            return False

        ad_error = data.get("AD_ERROR", "")
        if ad_error:
            self._notify_task_error(
                "Prepare Schema",
                "No se pudo consultar el bosque de Active Directory.\n\n"
                "Aunque el ping responda, Exchange necesita consultar AD con RSAT y permisos correctos.\n\n"
                f"Detalle: {ad_error}",
            )
            return False

        forest_mode = data.get("FOREST_MODE", "")
        if forest_mode and any(old in forest_mode for old in ("2000", "2003", "2008", "Windows2012Forest")):
            self._notify_task_error(
                "Prepare Schema",
                f"El nivel funcional detectado del bosque es {forest_mode}.\n\n"
                "Exchange Server 2019 requiere Windows Server 2012 R2 o superior.",
            )
            return False

        print("[OK] Prerrequisitos de Prepare Schema comprobados.")
        return True

    def _exchange_prepare_schema_failure_message(self, label, output):
        text = (output or "").lower()
        details = []
        if (
            "front end transport service cannot be installed without mailbox service" in text
            or "client access front end service cannot be installed without mailbox service" in text
            or "validating options for the 0 requested roles" in text
        ):
            details.append(
                "Exchange Setup ha entrado en una validacion interna de roles aunque Easy Deploy estaba ejecutando una preparacion AD. "
                "Normalmente ocurre cuando ese paso ya estaba preparado o cuando existen restos de una instalacion anterior de Exchange. "
                "Easy Deploy ahora comprueba las versiones de Active Directory antes de cada paso y saltara automaticamente los pasos que ya esten preparados."
            )
        if "rsat-adds-tools" in text or "rsat-adds" in text:
            details.append(
                "Falta RSAT-ADDS-Tools. Easy Deploy intenta instalarlo antes de ejecutar Exchange, "
                "pero si vuelve a aparecer revisa que Windows pueda instalar caracteristicas y reinicia si lo pide."
            )
        if "isn't logged on to an active directory domain" in text or "is not logged on to an active directory domain" in text:
            details.append(
                "La sesion actual no es una cuenta de dominio. Entra en Windows con un usuario del dominio, no con el administrador local del equipo."
            )
        if "supplied credential" in text and "invalid" in text:
            details.append(
                "Exchange ve la credencial actual como no valida para Active Directory. Normalmente ocurre al ejecutar como cuenta local."
            )
        if "schema admins" in text or "enterprise admins" in text:
            details.append(
                "La cuenta debe pertenecer a Schema Admins y Enterprise Admins. Si acabas de anadirla, cierra sesion y vuelve a entrar."
            )
        if "reboot from a previous installation is pending" in text:
            details.append(
                "Hay un reinicio pendiente. Reinicia el servidor y vuelve a ejecutar Prepare Schema."
            )
        if "forest functional level" in text:
            details.append(
                "Exchange no ha podido validar el nivel funcional del bosque o lo detecta inferior a Windows Server 2012 R2."
            )
        if "active directory doesn't exist" in text or "can't be contacted" in text:
            details.append(
                "No se pudo contactar con Active Directory. Revisa DNS, conectividad y que el dominio indicado sea correcto."
            )

        if not details:
            details.append("Revisa el log de Exchange y el log actual de Easy Deploy para ver la salida completa.")

        return (
            f"El paso '{label}' no se ha completado correctamente.\n\n"
            "Causas detectadas:\n\n- "
            + "\n- ".join(details)
            + "\n\nSe detiene la preparacion para evitar continuar tras un fallo."
        )

    def _exchange_ad_preparation_state(self, domain_name):
        """Lee versiones AD de Exchange para no repetir pasos ya preparados."""
        domain_literal = SysUtils.ps_quote(domain_name)
        script = f"""
        $domainName = {domain_literal}
        Import-Module ActiveDirectory -ErrorAction Stop
        $root = Get-ADRootDSE -Server $domainName -ErrorAction Stop
        $schemaDn = $root.schemaNamingContext
        $configDn = $root.configurationNamingContext
        $defaultDn = $root.defaultNamingContext

        $schemaVersion = 0
        $schemaObject = Get-ADObject -Server $domainName -Identity "CN=ms-Exch-Schema-Version-Pt,$schemaDn" -Properties rangeUpper -ErrorAction SilentlyContinue
        if ($schemaObject -and $schemaObject.rangeUpper) {{ $schemaVersion = [int]$schemaObject.rangeUpper }}

        $configVersion = 0
        $orgName = ""
        $exchangeRoot = "CN=Microsoft Exchange,CN=Services,$configDn"
        $exchangeRootObject = Get-ADObject -Server $domainName -Identity $exchangeRoot -ErrorAction SilentlyContinue
        if ($exchangeRootObject) {{
            $org = Get-ADObject -Server $domainName -SearchBase $exchangeRoot -LDAPFilter "(objectClass=msExchOrganizationContainer)" -SearchScope OneLevel -Properties objectVersion -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($org) {{
                $orgName = $org.Name
                if ($org.objectVersion) {{ $configVersion = [int]$org.objectVersion }}
            }}
        }}

        $domainVersion = 0
        $systemObjectsDn = "CN=Microsoft Exchange System Objects,$defaultDn"
        $systemObjects = Get-ADObject -Server $domainName -Identity $systemObjectsDn -Properties objectVersion -ErrorAction SilentlyContinue
        if ($systemObjects -and $systemObjects.objectVersion) {{ $domainVersion = [int]$systemObjects.objectVersion }}

        "SCHEMA_RANGE_UPPER=$schemaVersion"
        "CONFIG_OBJECT_VERSION=$configVersion"
        "DOMAIN_OBJECT_VERSION=$domainVersion"
        "EXCHANGE_ORG_NAME=$orgName"
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=60)
        state = {
            "schema": 0,
            "config": 0,
            "domain": 0,
            "org": "",
            "raw": output.strip(),
        }
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().upper()
            value = value.strip()
            if key == "SCHEMA_RANGE_UPPER":
                state["schema"] = self._safe_int(value)
            elif key == "CONFIG_OBJECT_VERSION":
                state["config"] = self._safe_int(value)
            elif key == "DOMAIN_OBJECT_VERSION":
                state["domain"] = self._safe_int(value)
            elif key == "EXCHANGE_ORG_NAME":
                state["org"] = value
        return ok, state

    def _safe_int(self, value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    def _print_exchange_ad_state(self, state):
        print(
            "Estado AD Exchange: "
            f"schema={state.get('schema', 0)}, "
            f"config={state.get('config', 0)}, "
            f"dominio={state.get('domain', 0)}, "
            f"organizacion={state.get('org') or 'no detectada'}"
        )

    def _exchange_step_already_prepared(self, label, state):
        label_lower = label.lower()
        if "prepareschema" in label_lower:
            return state.get("schema", 0) >= self.EXCHANGE_2019_CU15_SCHEMA_VERSION
        if "preparead" in label_lower:
            return state.get("config", 0) >= self.EXCHANGE_2019_CU15_CONFIG_VERSION
        if "preparealldomains" in label_lower:
            return state.get("domain", 0) >= self.EXCHANGE_2019_CU15_DOMAIN_VERSION
        return False

    def _exchange_role_validation_without_mailbox(self, output):
        text = (output or "").lower()
        return (
            "front end transport service cannot be installed without mailbox service" in text
            or "client access front end service cannot be installed without mailbox service" in text
            or "validating options for the 0 requested roles" in text
        )

    def _run_exchange_setup_step(self, label, args, setup_dir):
        print(f"\n>>> {label}")
        print("Comando: " + " ".join(f'"{part}"' if " " in part else part for part in args))
        output_lines = []
        try:
            process = subprocess.Popen(
                args,
                cwd=setup_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=SysUtils.oem_encoding(),
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as exc:
            print(f"[ERROR] No se pudo iniciar Exchange Setup: {exc}")
            self._notify_task_error(
                "Exchange Setup",
                f"No se pudo iniciar Exchange Setup.\n\nDetalle: {exc}",
            )
            return False, str(exc)

        while True:
            if self.stop_event.is_set():
                print("[AVISO] Cancelacion solicitada. Deteniendo Exchange Setup...")
                try:
                    process.terminate()
                except Exception:
                    pass
                return False, "Cancelacion solicitada por el usuario."

            line = process.stdout.readline() if process.stdout else ""
            if line:
                clean_line = line.rstrip()
                output_lines.append(clean_line)
                print(clean_line)

            if process.poll() is not None:
                if process.stdout:
                    for remaining in process.stdout:
                        if remaining.strip():
                            clean_line = remaining.rstrip()
                            output_lines.append(clean_line)
                            print(clean_line)
                break

            if not line:
                time.sleep(0.2)

        if process.returncode in (0, 3010):
            print(f"[OK] {label} completado. Codigo de salida: {process.returncode}")
            return True, "\n".join(output_lines)

        print(f"[ERROR] {label} fallo. Codigo de salida: {process.returncode}")
        return False, "\n".join(output_lines)

    def task_exchange_prepare_schema(self, domain_name, organization_name, setup_path):
        mounted_image = getattr(self, "_exchange_prepare_schema_image_path", "")
        try:
            print("Iniciando preparacion de schema de Exchange.")
            print(f"Dominio indicado: {domain_name}")
            print(f"Organization Name: {organization_name}")
            print(f"Setup.exe detectado: {setup_path}")
            self.update_progress(0.05)

            if not os.path.exists(setup_path):
                self._notify_task_error(
                    "Prepare Schema",
                    "Setup.exe ya no existe en la ruta indicada.\n\n"
                    "Revisa que el medio de Exchange siga montado o que la carpeta ExchangeServer2019-x64-cu15 exista en recursos.",
                )
                return

            if not self._validate_exchange_schema_environment(domain_name):
                return
            self.update_progress(0.12)

            print(f"\n>>> Comprobando conectividad con el dominio: {domain_name}")
            ping_ok, ping_output = SysUtils.ping_host(domain_name, count=2, timeout_ms=2000)
            if ping_output.strip():
                print(ping_output.strip())

            if not ping_ok:
                self._notify_task_error(
                    "Prepare Schema",
                    "El dominio no responde al ping.\n\n"
                    "No se ejecuta PrepareSchema para evitar preparar AD contra un dominio incorrecto.\n\n"
                    "Revisa DNS, conectividad y que estas en el DC1 o en un servidor con acceso al dominio.",
                )
                return

            self.update_progress(0.15)
            setup_dir = os.path.dirname(setup_path)
            license_arg = "/IAcceptExchangeServerLicenseTerms_DiagnosticDataOFF"
            steps = [
                ("PrepareSchema", [setup_path, license_arg, "/PrepareSchema"], 0.35),
                ("PrepareAD con OrganizationName", [setup_path, license_arg, "/PrepareAD", f"/OrganizationName:{organization_name}"], 0.60),
                ("PrepareAD", [setup_path, license_arg, "/PrepareAD"], 0.80),
                ("PrepareAllDomains", [setup_path, license_arg, "/PrepareAllDomains"], 1.00),
            ]

            for label, command, progress in steps:
                if self.stop_event.is_set():
                    print("[AVISO] Proceso cancelado por el usuario.")
                    return

                state_ok, state = self._exchange_ad_preparation_state(domain_name)
                if state_ok:
                    self._print_exchange_ad_state(state)
                    if self._exchange_step_already_prepared(label, state):
                        print(f"[OMITIDO] {label} ya esta preparado en Active Directory. Se pasa al siguiente paso.")
                        self.update_progress(progress)
                        continue
                else:
                    print("[AVISO] No se pudo leer el estado AD de Exchange antes de este paso.")

                step_ok, step_output = self._run_exchange_setup_step(label, command, setup_dir)
                if not step_ok:
                    if self._exchange_role_validation_without_mailbox(step_output):
                        state_ok, state = self._exchange_ad_preparation_state(domain_name)
                        if state_ok:
                            self._print_exchange_ad_state(state)
                            if self._exchange_step_already_prepared(label, state):
                                print(
                                    f"[AVISO] {label} devolvio validacion interna de roles, "
                                    "pero Active Directory indica que el paso ya esta preparado. Se continua."
                                )
                                self.update_progress(progress)
                                continue
                    self._notify_task_error(
                        "Prepare Schema",
                        self._exchange_prepare_schema_failure_message(label, step_output),
                    )
                    return
                self.update_progress(progress)

            print("\n[OK] Preparacion de schema/AD de Exchange completada.")
        finally:
            if mounted_image:
                reason = "cancelada" if self.stop_event.is_set() else "finalizada"
                self._dismount_task_media(mounted_image, reason)
                self._exchange_prepare_schema_image_path = ""

    def task_exchange_recover_server(self, setup_path, target_dir=""):
        mounted_image = getattr(self, "_exchange_prepare_schema_image_path", "")
        try:
            if not self._require_windows_server(
                "RecoverServer Exchange",
                "RecoverServer solo debe ejecutarse en Windows Server.",
            ):
                return

            print("Iniciando recuperacion de servidor Exchange con /Mode:RecoverServer.")
            print("Esta tarea no borra objetos de Active Directory. Usa la configuracion guardada en AD para reconstruir Exchange.")
            print(f"Setup.exe detectado: {setup_path}")
            print(f"Equipo actual: {os.environ.get('COMPUTERNAME', 'desconocido')}")
            if target_dir:
                print(f"TargetDir detectado: {target_dir}")
            else:
                print("TargetDir no detectado. Se usara la ruta por defecto de Exchange.")
            self.update_progress(0.10)

            if not os.path.exists(setup_path):
                self._notify_task_error(
                    "RecoverServer Exchange",
                    "Setup.exe ya no existe en la ruta indicada.\n\n"
                    "Revisa que el medio de Exchange siga montado o que la carpeta ExchangeServer2019-x64-cu15 exista en recursos.",
                )
                return

            setup_dir = os.path.dirname(setup_path)
            license_arg = "/IAcceptExchangeServerLicenseTerms_DiagnosticDataOFF"
            command = [setup_path, license_arg, "/Mode:RecoverServer"]
            if target_dir:
                command.append(f"/TargetDir:{target_dir}")

            self.update_progress(0.20)
            ok, output = self._run_exchange_setup_step("RecoverServer", command, setup_dir)
            if not ok:
                self._notify_task_error(
                    "RecoverServer Exchange",
                    self._exchange_recover_server_failure_message(output),
                )
                return

            self.update_progress(1.0)
            self.console_finish_state = "restart"
            self._notify_task_info(
                "RecoverServer Exchange",
                "RecoverServer ha finalizado correctamente.\n\n"
                "Reinicia el servidor antes de volver a lanzar la instalacion o aplicar actualizaciones de seguridad.",
            )
        finally:
            if mounted_image:
                reason = "cancelada" if self.stop_event.is_set() else "finalizada"
                self._dismount_task_media(mounted_image, reason)
                self._exchange_prepare_schema_image_path = ""

    def _exchange_recover_server_failure_message(self, output):
        text = (output or "").lower()
        details = []
        if "version" in text and "recover" in text:
            details.append(
                "El medio de Exchange parece ser anterior a la version registrada en AD. Usa la misma CU o una CU posterior."
            )
        if "targetdir" in text or "location" in text:
            details.append(
                "Exchange podria haber estado instalado en una ruta personalizada. Debe recuperarse con la misma ruta usando /TargetDir."
            )
        if "domain admins" in text or "organization management" in text or "permission" in text:
            details.append(
                "La cuenta actual no tiene permisos suficientes. Usa una cuenta con Domain Admins y administracion de Exchange."
            )
        if "same name" in text or "computer name" in text:
            details.append(
                "El nombre del equipo no coincide con el servidor Exchange registrado en Active Directory."
            )
        if "reboot" in text or "restart" in text:
            details.append("Hay un reinicio pendiente. Reinicia el servidor y repite RecoverServer.")
        if not details:
            details.append(
                "Revisa C:\\ExchangeSetupLogs\\ExchangeSetup.log. Busca Error, RecoverServer, Prerequisite o Version."
            )

        return (
            "RecoverServer no se ha completado correctamente.\n\n"
            "Causas posibles:\n\n- "
            + "\n- ".join(details)
            + "\n\nNo borres objetos de Exchange en AD salvo que tengas snapshot/backup y sepas exactamente que objeto estas retirando."
        )

    def task_exchange_prereqs(self):
        if not self._require_windows_server(
            "Exchange",
            "Exchange no puede instalar sus roles ni prerrequisitos en Windows cliente.",
        ):
            return

        if self._is_exchange_installed():
            print("[OK] Microsoft Exchange ya parece instalado. Se omite la instalacion completa.")
            self.update_progress(1.0)
            self.ui_showinfo(
                "Exchange",
                "Microsoft Exchange ya parece instalado.\n\n"
                "No se reinstalan caracteristicas, prerrequisitos ni se monta de nuevo la ISO.",
            )
            return

        base = self.payload_path("EXCHANGE")

        if not os.path.exists(base):
            self._notify_task_error(
                "Exchange",
                f"No se encuentra la carpeta de recursos de Exchange:\n\n{base}\n\n"
                "Comprueba que la carpeta EXCHANGE exista dentro de los recursos de Easy Deploy.",
            )
            return

        self._warn_missing_files(base, self._exchange_prereq_files(), abort=False)
        print("=== PRERREQUISITOS EXCHANGE ===")

        if not self._install_exchange_windows_features():
            return

        local_ok, installer_restart = self._install_exchange_local_prereqs(base)
        if self.stop_event.is_set():
            return

        status = self._exchange_prerequisite_status(base, verbose=False)
        status_message = self._format_exchange_prereq_status_message(status)
        reboot_pending = installer_restart or SysUtils.is_reboot_pending()

        print("\n=== PRERREQUISITOS EXCHANGE FINALIZADOS ===")

        if status_message or not local_ok:
            if reboot_pending:
                self._notify_exchange_restart_required("Prerrequisitos Exchange")
            self._notify_task_warning(
                "Prerrequisitos Exchange",
                "No se han completado todos los prerrequisitos de Exchange.\n\n"
                + (status_message + "\n\n" if status_message else "")
                + "Revisa la consola y vuelve a ejecutar Prerrequisitos Exchange antes de instalar Exchange.",
            )
            self.update_progress(1.0)
            return

        if reboot_pending:
            self._notify_exchange_restart_required("Prerrequisitos Exchange")
            self.update_progress(1.0)
            return

        self.update_progress(1.0)
        self.ui_showinfo(
            "Prerrequisitos Exchange",
            "Los prerrequisitos de Exchange han finalizado.\n\n"
            "No se ha lanzado el Setup principal de Exchange.",
        )

    def task_exchange(self):
        if not self._require_windows_server(
            "Exchange",
            "Exchange no puede instalar sus roles ni prerrequisitos en Windows cliente.",
        ):
            return

        if self._is_exchange_installed():
            print("[OK] Microsoft Exchange ya parece instalado. Se omite la instalacion completa.")
            self.update_progress(1.0)
            self.ui_showinfo(
                "Exchange",
                "Microsoft Exchange ya parece instalado.\n\n"
                "No se monta de nuevo la ISO ni se abre el instalador principal.",
            )
            return

        iso_exchange = "ExchangeServer2019-x64-cu15.iso"
        base = self.payload_path("EXCHANGE")

        if not os.path.exists(base):
            print(f"[AVISO] No se encuentra la carpeta de recursos de Exchange: {base}")
            print("[INFO] Se intentara localizar un medio de Exchange ya montado.")

        print("=== INSTALACION EXCHANGE ===")
        print("[INFO] No se comprueban ni instalan prerrequisitos desde este boton.")
        print("[INFO] Si falta algun prerrequisito, Exchange Setup lo indicara en su Readiness Check.")
        self.update_progress(0.2)
        if self.stop_event.is_set():
            return

        if self._launch_exchange_setup_from_media(base, iso_exchange):
            self.update_progress(1.0)
            print("\nPROCESO EXCHANGE COMPLETO.")
