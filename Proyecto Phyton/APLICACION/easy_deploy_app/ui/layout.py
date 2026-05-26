import os
import re
import subprocess
import sys
import threading
import json
import hashlib
import urllib.parse
import urllib.request

import customtkinter as ctk

from ..constants import APP_DISPLAY_TITLE, APP_VERSION
from ..core.sysutils import SysUtils
from ..network_tools.addressing import show_addressing_placeholder
from ..network_tools.asa import show_asa_placeholder
from ..network_tools.checkpoint import show_checkpoint_placeholder
from ..network_tools.topology import show_topology_placeholder
from ..tasks.ad_users import show_ad_users_tool
from ..tasks.gpo import show_group_policy_placeholder
from ..tasks.jchat_rooms import show_jchat_rooms_placeholder
from ..tasks.replication import show_d2_d4_tool, show_repadmin_tool
from ..tasks.skype import pre_task_skype_dns, pre_task_skype_install, pre_task_skype_permissions, pre_task_skype_prereqs
from .design_tokens import DEFAULT_SKIN, SKIN_ORDER, SKINS, get_skin_tokens


class LayoutMixin:
    def _ui_settings_path(self):
        return os.path.join(SysUtils.app_data_dir(), "ui_settings.json")

    def _load_ui_settings(self):
        try:
            with open(self._ui_settings_path(), "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_ui_settings(self):
        try:
            data = {
                "skin": getattr(self, "current_skin", DEFAULT_SKIN),
                "appearance_mode": ctk.get_appearance_mode(),
            }
            with open(self._ui_settings_path(), "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _skin_display_name(self, skin_key):
        skin = SKINS.get(skin_key, SKINS.get(DEFAULT_SKIN, {}))
        return skin.get("name", skin_key)

    def _skin_key_from_display_name(self, display_name):
        text = str(display_name or "").strip()
        for skin_key in SKIN_ORDER:
            if self._skin_display_name(skin_key) == text:
                return skin_key
        return DEFAULT_SKIN

    def _build_colors_from_skin(self, skin_key):
        skin = get_skin_tokens(skin_key)
        light = skin["light"]
        dark = skin["dark"]
        state = skin["state"]
        return {
            "canvas_light": light["canvas"],
            "canvas_dark": dark["canvas"],
            "sidebar": (light["canvas"], dark["canvas"]),
            "sidebar_hover": (light["card_hover"], dark["card_hover"]),
            "sidebar_active": (light["border_soft"], dark["border_soft"]),
            "sidebar_text": (light["text_primary"], dark["text_secondary"]),
            "sidebar_text_active": (state["accent_hover"], dark["text_primary"]),
            "accent": state["accent"],
            "accent_hover": state["accent_hover"],
            "warning": state["warning"],
            "danger": state["danger"],
            "success": state["success"],
            "info": state["info"],
            "muted": state["secondary"],
            "secondary": state["secondary"],
            "secondary_hover": state["secondary_hover"],
            "panel_light": light["panel"],
            "panel_dark": dark["panel"],
            "card_light": light["card"],
            "card_dark": dark["card"],
            "card_hover_light": light["card_hover"],
            "card_hover_dark": dark["card_hover"],
            "border_light": light["border"],
            "border_dark": dark["border"],
            "text_primary_light": light["text_primary"],
            "text_primary_dark": dark["text_primary"],
            "text_secondary_light": light["text_secondary"],
            "text_secondary_dark": dark["text_secondary"],
            "text_muted_light": light["text_muted"],
            "text_muted_dark": dark["text_muted"],
        }

    def _init_ui(self):
        ui_settings = self._load_ui_settings()
        saved_skin = ui_settings.get("skin", DEFAULT_SKIN)
        self.current_skin = saved_skin if saved_skin in SKINS else DEFAULT_SKIN
        saved_mode = ui_settings.get("appearance_mode")
        if str(saved_mode).lower() in {"light", "dark"}:
            try:
                ctk.set_appearance_mode("Dark" if str(saved_mode).lower() == "dark" else "Light")
            except Exception:
                pass
        self.colors = self._build_colors_from_skin(self.current_skin)
        self._secondary_windows = {}
        self._restore_chips = {}
        self._skinnable_widgets = []
        self._appearance_panel_outside_active = False
        self._appearance_panel_outside_bind_installed = False
        self._restore_chip_menu_outside_active = False
        self._restore_chip_menu_outside_bind_installed = False
        self.logo_image = None
        self.nav_buttons = {}
        self.current_frame_name = "Selection"
        self.return_frame_after_console = "Menu"
        self.return_frame_after_versions = "Selection"
        self._keyboard_status = None
        self._keyboard_check_running = False
        self._keyboard_check_watchdog = None
        self._firewall_status = None
        self._firewall_check_running = False
        self._firewall_check_watchdog = None
        self._disk_refresh_after = None
        self._disk_status_cache = []
        self._disk_status_refresh_running = False
        self._versions_view_built = False
        self.console_finish_state = "finished"
        self.dialog_button_width = 160
        self.dialog_button_height = 44

        self.shell = ctk.CTkFrame(self, fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]))
        self.shell.pack(fill="both", expand=True)
        self.shell.columnconfigure(1, weight=1)
        self.shell.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_sidebar_separator()

        self.content_shell = ctk.CTkFrame(self.shell, fg_color="transparent")
        self.content_shell.grid(row=0, column=1, sticky="nsew")
        self.content_shell.rowconfigure(1, weight=1)
        self.content_shell.columnconfigure(0, weight=1)

        self._build_top_bar()

        self.main_container = ctk.CTkFrame(self.content_shell, fg_color="transparent")
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=18, pady=(12, 6))
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for frame_name in [
            "Selection",
            "Menu",
            "SharePoint",
            "Exchange",
            "DC",
            "JCHAT",
            "Skype",
            "Network",
            "Programs",
            "Guides",
            "Security",
            "Firewall",
            "Guide",
            "Versions",
            "Update",
            "Console",
        ]:
            frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
            frame._easydeploy_frame_name = frame_name
            self.frames[frame_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_remove()

        self._build_selection_screen()
        self._build_menu_principal()
        self._build_menu_sharepoint()
        self._build_menu_exchange()
        self._build_menu_dc()
        self._build_menu_jchat()
        self._build_menu_skype()
        self._build_network_view()
        self._build_programs_view()
        self._build_guides_view()
        self._build_security_view()
        self._build_firewall_view()
        self._build_guide_view()
        self._build_update_view()
        self._build_console_view()
        self.after(500, self._disk_status_refresh_tick)

        self.control_frame = ctk.CTkFrame(self.content_shell, height=54, fg_color="transparent")
        self.control_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))

        self.btn_restart = ctk.CTkButton(
            self.control_frame,
            text="Reiniciar sistema",
            height=36,
            fg_color=self.colors["warning"],
            hover_color="#B45309",
            text_color="white",
            command=self.reiniciar_sistema,
        )
        self.btn_back = ctk.CTkButton(
            self.control_frame,
            text="Volver",
            height=36,
            fg_color=self.colors["secondary"],
            hover_color=self.colors["secondary_hover"],
            command=lambda: self.show_frame("Menu"),
        )
        self.btn_cancel = ctk.CTkButton(
            self.control_frame,
            text="Cancelar proceso",
            height=36,
            fg_color=self.colors["danger"],
            hover_color="#8F1D14",
            command=self.cancelar_proceso,
        )
        self.control_frame.grid_remove()

    def _set_control_bar_visible(self, visible):
        if visible:
            self.control_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        else:
            self.control_frame.grid_remove()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.shell, width=238, fg_color=self.colors["sidebar"], corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        for row_idx in range(3, 14):
            self.sidebar.rowconfigure(row_idx, weight=0)

        logo_path = os.path.join(self.base_path, "iconos", "EscudoRt.png")
        if os.path.exists(logo_path):
            try:
                from PIL import Image

                img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(img, size=(90, 90))
                ctk.CTkLabel(self.sidebar, image=self.logo_image, text="").grid(row=0, column=0, padx=(38, 20), pady=(18, 8), sticky="w")
            except Exception:
                pass

        self.lbl_brand = ctk.CTkLabel(
            self.sidebar,
            text="Easy Deploy",
            font=("Segoe UI", 22, "bold"),
            text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
            anchor="w",
        )
        self.lbl_brand.grid(row=1, column=0, padx=20, pady=(4, 0), sticky="ew")
        self.lbl_unit = ctk.CTkLabel(
            self.sidebar,
            text="RT 21 III/BON BURGOS",
            font=("Segoe UI", 11, "bold"),
            text_color=(self.colors["accent"], "#A7D8CF"),
            anchor="w",
        )
        self.lbl_unit.grid(row=2, column=0, padx=20, pady=(0, 22), sticky="ew")

        nav_items = [
            ("Selection", "Inicio", "⌂"),
            ("Menu", "Sistemas", "▦"),
            ("Network", "Redes", "R"),
            ("Programs", "Programas", "P"),
            ("Guides", "Guías", "G"),
            ("Security", "Seguridad", "S"),
            ("Guide", "Guía rápida", "?"),
            ("Update", "Actualizar", "â†»"),
            ("Console", "Consola", ">"),
        ]
        for idx, (frame_name, label, icon) in enumerate(nav_items, start=3):
            self.nav_buttons[frame_name] = self._sidebar_button(frame_name, label, icon)
            self.nav_buttons[frame_name].grid(row=idx, column=0, padx=14, pady=4, sticky="ew")

        footer_row = 3 + len(nav_items)
        self.sidebar.rowconfigure(footer_row, weight=1)

        self.btn_archivo = ctk.CTkButton(
            self.sidebar,
            text="☰  Herramientas",
            height=38,
            anchor="w",
            corner_radius=10,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            hover_color=self.colors["sidebar_hover"],
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            text_color=self.colors["sidebar_text"],
            font=("Segoe UI", 13, "bold"),
            command=self._menu_archivo_popup,
        )
        self.btn_archivo.grid(row=footer_row + 1, column=0, padx=14, pady=(12, 6), sticky="ew")

        self.lbl_env_status = ctk.CTkFrame(
            self.sidebar,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=9,
        )
        self.lbl_env_status.grid(row=footer_row + 2, column=0, padx=14, pady=(5, 7), sticky="ew")
        self._track_skin_widget(self.lbl_env_status, "card")
        self.lbl_env_status.grid_columnconfigure(0, weight=0)
        self.lbl_env_status.grid_columnconfigure(1, weight=0)
        self.lbl_env_status.grid_columnconfigure(2, weight=1)
        self.lbl_env_admin_status = ctk.CTkLabel(
            self.lbl_env_status,
            text="",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.lbl_env_admin_status.grid(row=0, column=0, padx=(10, 0), pady=8, sticky="w")
        self.lbl_env_separator = ctk.CTkLabel(
            self.lbl_env_status,
            text=" | ",
            font=("Segoe UI", 10, "bold"),
            text_color=("gray46", "gray52"),
        )
        self.lbl_env_separator.grid(row=0, column=1, pady=8, sticky="w")
        self.lbl_env_payload_status = ctk.CTkLabel(
            self.lbl_env_status,
            text="",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            wraplength=110,
        )
        self.lbl_env_payload_status.grid(row=0, column=2, padx=(0, 10), pady=8, sticky="w")

        self.lbl_firma = ctk.CTkLabel(
            self.sidebar,
            text="Adrian Mata Cifre © 2026\nJuan Jesús Cañas Ramirez",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray52"),
            anchor="w",
            justify="left",
        )
        self.lbl_firma.grid(row=footer_row + 3, column=0, padx=18, pady=(0, 12), sticky="ew")

        self._update_environment_status()

    def _sidebar_separator_color(self):
        return self.colors.get("accent", "#2F9E8F")

    def _build_sidebar_separator(self):
        """Separador visual sutil entre barra lateral y contenido principal."""
        self.sidebar_separator = ctk.CTkFrame(
            self.shell,
            width=2,
            fg_color=self._sidebar_separator_color(),
            corner_radius=2,
        )
        try:
            self.sidebar_separator.place(x=238, rely=0.14, relheight=0.72, anchor="n")
            self.sidebar_separator.lift()
        except Exception:
            pass

    def _build_top_bar(self):
        self.top_bar = ctk.CTkFrame(
            self.content_shell,
            height=44,
            fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]),
            corner_radius=0,
        )
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(10, 0))
        self.top_bar.grid_propagate(False)
        self.top_bar.grid_columnconfigure(0, weight=1)

        self.btn_appearance = ctk.CTkButton(
            self.top_bar,
            text="Apariencia",
            width=122,
            height=32,
            corner_radius=9,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="white",
            command=self._toggle_appearance_panel,
        )
        self.btn_appearance.grid(row=0, column=1, padx=(10, 0), sticky="e")

    def _hide_appearance_panel(self):
        panel = getattr(self, "appearance_panel", None)
        self.appearance_panel = None
        self._appearance_panel_outside_active = False
        if self._widget_exists(panel):
            try:
                panel.destroy()
            except Exception:
                pass

    def _is_descendant(self, widget, parent):
        if widget is None or parent is None:
            return False
        try:
            if not parent.winfo_exists():
                return False
        except Exception:
            return False
        current = widget
        while current is not None:
            if current is parent:
                return True
            try:
                current = current.master
            except Exception:
                return False
        return False

    def _is_appearance_dropdown_widget(self, widget):
        current = widget
        while current is not None:
            try:
                widget_class = str(current.winfo_class()).lower()
                widget_path = str(current).lower()
            except Exception:
                return False
            if "dropdown" in widget_class or "dropdown" in widget_path or widget_class == "menu":
                return True
            try:
                current = current.master
            except Exception:
                return False
        return False

    def _handle_appearance_panel_outside_click(self, event):
        if not getattr(self, "_appearance_panel_outside_active", False):
            return
        panel = getattr(self, "appearance_panel", None)
        if not self._widget_exists(panel):
            self._appearance_panel_outside_active = False
            self.appearance_panel = None
            return
        widget = getattr(event, "widget", None)
        if self._is_descendant(widget, panel):
            return
        if self._is_descendant(widget, getattr(self, "btn_appearance", None)):
            return
        if self._is_appearance_dropdown_widget(widget):
            return
        self._hide_appearance_panel()

    def _install_appearance_panel_outside_close(self):
        if getattr(self, "_appearance_panel_outside_bind_installed", False):
            return
        try:
            self.bind_all("<Button-1>", self._handle_appearance_panel_outside_click, add="+")
            self._appearance_panel_outside_bind_installed = True
        except Exception:
            self._appearance_panel_outside_bind_installed = False

    def _toggle_appearance_panel(self):
        panel = getattr(self, "appearance_panel", None)
        if self._widget_exists(panel):
            self._hide_appearance_panel()
            return
        self._show_appearance_panel()

    def _show_appearance_panel(self):
        self._hide_appearance_panel()

        panel_width = 292
        panel_min_height = 306
        panel = ctk.CTkFrame(
            self.content_shell,
            width=panel_width,
            height=panel_min_height,
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=10,
        )
        panel.grid_columnconfigure(0, weight=1)
        try:
            panel.place(relx=1.0, x=-16, y=48, anchor="ne")
        except Exception:
            panel.place(relx=1.0, y=48, anchor="ne")
        self.appearance_panel = panel

        accent_line = ctk.CTkFrame(panel, height=2, fg_color=self.colors["accent"], corner_radius=3)
        accent_line.grid(row=0, column=0, sticky="ew", padx=14, pady=(11, 0))
        self._track_skin_widget(accent_line, "accent_bar")

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.grid(row=1, column=0, sticky="ew", padx=14, pady=(9, 7))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Apariencia",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            header,
            text="Paleta y modo visual",
            font=("Segoe UI", 10),
            anchor="w",
            text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
        ).grid(row=1, column=0, sticky="ew", pady=(1, 0))
        ctk.CTkButton(
            header,
            text="×",
            width=26,
            height=26,
            corner_radius=7,
            fg_color="transparent",
            hover_color=self.colors["sidebar_hover"],
            text_color=self.colors["sidebar_text"],
            command=self._hide_appearance_panel,
        ).grid(row=0, column=1, rowspan=2, padx=(8, 0), sticky="ne")

        body = ctk.CTkFrame(panel, fg_color="transparent")
        body.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        body.grid_columnconfigure(0, weight=1)

        palette_box = ctk.CTkFrame(
            body,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=7,
        )
        palette_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        palette_box.grid_columnconfigure(0, weight=1)
        self._track_skin_widget(palette_box, "card")
        ctk.CTkLabel(
            palette_box,
            text="Paleta",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(9, 4))
        self.om_appearance_skin = ctk.CTkOptionMenu(
            palette_box,
            values=[self._skin_display_name(name) for name in SKIN_ORDER],
            command=self._change_skin,
            height=32,
            corner_radius=7,
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            button_color=self.colors["secondary"],
            button_hover_color=self.colors["secondary_hover"],
            dropdown_fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            dropdown_hover_color=self.colors["sidebar_hover"],
            text_color=self.colors["sidebar_text"],
        )
        self.om_appearance_skin.set(self._skin_display_name(getattr(self, "current_skin", DEFAULT_SKIN)))
        self.om_appearance_skin.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        mode_box = ctk.CTkFrame(
            body,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=7,
        )
        mode_box.grid(row=1, column=0, sticky="ew")
        mode_box.grid_columnconfigure(0, weight=1)
        self._track_skin_widget(mode_box, "card")
        ctk.CTkLabel(
            mode_box,
            text="Modo",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(9, 4))
        self.om_appearance_mode = ctk.CTkOptionMenu(
            mode_box,
            values=["Light", "Dark"],
            command=self._change_appearance_mode,
            height=32,
            corner_radius=7,
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            button_color=self.colors["accent"],
            button_hover_color=self.colors["accent_hover"],
            dropdown_fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            dropdown_hover_color=self.colors["sidebar_hover"],
            text_color=self.colors["sidebar_text"],
        )
        self.om_appearance_mode.set(ctk.get_appearance_mode())
        self.om_appearance_mode.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        try:
            panel.update_idletasks()
            shell_height = max(1, self.content_shell.winfo_height())

            # Calcula una altura real con el contenido ya renderizado.
            # Se añade margen extra para que CTkOptionMenu no quede justo en el borde.
            requested_height = max(panel_min_height, panel.winfo_reqheight() + 18)
            available_height = max(260, shell_height - 24)
            target_height = min(requested_height, available_height)

            target_y = 48
            if target_y + target_height > shell_height - 12:
                target_y = max(12, shell_height - target_height - 12)

            panel.configure(width=panel_width, height=target_height)
            panel.grid_propagate(False)
            panel.place_configure(y=target_y)
            panel.lift()
        except Exception:
            try:
                panel.configure(width=panel_width, height=panel_min_height)
                panel.grid_propagate(False)
                panel.lift()
            except Exception:
                pass
        self._appearance_panel_outside_active = True
        self._install_appearance_panel_outside_close()

    def _safe_configure_widget(self, widget, **kwargs):
        try:
            if widget and widget.winfo_exists():
                widget.configure(**kwargs)
        except Exception:
            pass

    def _ensure_window_registries(self):
        if not hasattr(self, "_secondary_windows"):
            self._secondary_windows = {}
        if not hasattr(self, "_restore_chips") or not isinstance(getattr(self, "_restore_chips", None), dict):
            self._restore_chips = {}
        if not hasattr(self, "_restore_chip_bar"):
            self._restore_chip_bar = None
        if not hasattr(self, "_restore_chip_menu"):
            self._restore_chip_menu = None

    def _secondary_key(self, prefix, *parts):
        raw = ":".join(str(part or "").strip() for part in (prefix, *parts))
        return re.sub(r"[^a-zA-Z0-9_.:-]+", "_", raw).strip("_")[:160]

    def _get_secondary_window(self, key):
        self._ensure_window_registries()
        window = self._secondary_windows.get(key)
        if self._widget_exists(window):
            return window
        self._secondary_windows.pop(key, None)
        return None

    def _unregister_secondary_window(self, key):
        self._ensure_window_registries()
        self._secondary_windows.pop(key, None)
        self._destroy_restore_chip(key)

    def _register_secondary_window(self, key, window):
        self._ensure_window_registries()
        if not key or not self._widget_exists(window):
            return window
        self._secondary_windows[key] = window
        try:
            window._easydeploy_secondary_key = key
        except Exception:
            pass

        def cleanup(event=None):
            try:
                if event is not None and event.widget is not window:
                    return
            except Exception:
                pass
            if self._secondary_windows.get(key) is window:
                self._secondary_windows.pop(key, None)
            self._destroy_restore_chip(key)

        try:
            window.bind("<Destroy>", cleanup, add="+")
        except Exception:
            pass
        return window

    def _focus_secondary_window(self, key_or_window, topmost_ms=400):
        key = key_or_window if isinstance(key_or_window, str) else None
        window = self._get_secondary_window(key_or_window) if key else key_or_window
        if not self._widget_exists(window):
            return False
        key = key or getattr(window, "_easydeploy_secondary_key", None)
        if key:
            self._destroy_restore_chip(key)

        def release_topmost():
            try:
                if window.winfo_exists():
                    window.attributes("-topmost", False)
            except Exception:
                pass

        try:
            if window.state() in {"iconic", "withdrawn"}:
                window.deiconify()
        except Exception:
            try:
                window.deiconify()
            except Exception:
                pass
        try:
            window.update_idletasks()
        except Exception:
            pass
        try:
            window.lift(self)
        except Exception:
            try:
                window.lift()
            except Exception:
                pass
        try:
            window.attributes("-topmost", True)
        except Exception:
            pass
        try:
            window.focus_force()
        except Exception:
            try:
                window.focus_set()
            except Exception:
                pass
        try:
            window.after(max(120, int(topmost_ms or 400)), release_topmost)
        except Exception:
            release_topmost()
        return True

    def _destroy_restore_chip(self, key):
        """Elimina una ventana del panel de avisos minimizados y refresca el desplegable."""
        self._ensure_window_registries()
        self._restore_chips.pop(key, None)
        self._refresh_restore_chip_bar()

    def _hide_restore_chip_menu(self):
        self._ensure_window_registries()
        self._restore_chip_menu_outside_active = False
        menu = getattr(self, "_restore_chip_menu", None)
        self._restore_chip_menu = None
        if self._widget_exists(menu):
            try:
                menu.destroy()
            except Exception:
                pass

    def _handle_restore_chip_menu_outside_click(self, event):
        if not getattr(self, "_restore_chip_menu_outside_active", False):
            return
        menu = getattr(self, "_restore_chip_menu", None)
        if not self._widget_exists(menu):
            self._restore_chip_menu_outside_active = False
            self._restore_chip_menu = None
            return
        widget = getattr(event, "widget", None)
        if self._is_descendant(widget, menu):
            return
        if self._is_descendant(widget, getattr(self, "_restore_chip_bar", None)):
            return
        self._hide_restore_chip_menu()

    def _install_restore_chip_menu_outside_close(self):
        if getattr(self, "_restore_chip_menu_outside_bind_installed", False):
            return
        try:
            self.bind_all("<Button-1>", self._handle_restore_chip_menu_outside_click, add="+")
            self._restore_chip_menu_outside_bind_installed = True
        except Exception:
            self._restore_chip_menu_outside_bind_installed = False

    def _hide_restore_chip_bar(self):
        self._hide_restore_chip_menu()
        bar = getattr(self, "_restore_chip_bar", None)
        self._restore_chip_bar = None
        if self._widget_exists(bar):
            try:
                bar.destroy()
            except Exception:
                pass

    def _restore_chip_text(self):
        total = len(getattr(self, "_restore_chips", {}) or {})
        if total <= 0:
            return ""
        if total == 1:
            item = next(iter(self._restore_chips.values()))
            return item.get("text", "Ventana minimizada")
        return f"Ventanas minimizadas ({total})"

    def _refresh_restore_chip_bar(self):
        """Mantiene un único botón superior para abrir el panel de ventanas minimizadas."""
        self._ensure_window_registries()
        if not self._restore_chips:
            self._hide_restore_chip_bar()
            return

        text = self._restore_chip_text()
        first = next(iter(self._restore_chips.values()))
        panel_fg = first.get("panel_fg", (self.colors["panel_light"], self.colors["panel_dark"]))
        border_color = first.get("border_color", (self.colors["border_light"], self.colors["border_dark"]))
        fg_color = first.get("fg_color", self.colors.get("accent", "#2F9E8F"))
        hover_color = first.get("hover_color", self.colors.get("accent_hover", "#258176"))

        bar = getattr(self, "_restore_chip_bar", None)
        if not self._widget_exists(bar):
            bar = ctk.CTkFrame(
                self,
                fg_color=panel_fg,
                border_width=1,
                border_color=border_color,
                corner_radius=8,
            )
            place_host = getattr(self, "content_shell", self)
            try:
                bar.place(in_=place_host, relx=0.5, y=54, anchor="n")
            except Exception:
                bar.place(relx=0.5, y=54, anchor="n")
            self._restore_chip_bar = bar
        else:
            try:
                bar.configure(fg_color=panel_fg, border_color=border_color)
            except Exception:
                pass

        for child in bar.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        ctk.CTkButton(
            bar,
            text=text,
            height=32,
            fg_color=fg_color,
            hover_color=hover_color,
            command=self._toggle_restore_chip_menu,
        ).pack(padx=10, pady=8)
        try:
            bar.lift()
        except Exception:
            pass

    def _toggle_restore_chip_menu(self):
        menu = getattr(self, "_restore_chip_menu", None)
        if self._widget_exists(menu):
            self._hide_restore_chip_menu()
            return
        self._show_restore_chip_menu()

    def _show_restore_chip_menu(self):
        """Muestra un desplegable con todas las ventanas minimizadas para restaurar solo la elegida."""
        self._ensure_window_registries()
        self._hide_restore_chip_menu()
        if not self._restore_chips:
            self._hide_restore_chip_bar()
            return

        items = list(self._restore_chips.items())
        count = len(items)
        first = items[0][1]
        panel_fg = first.get("panel_fg", (self.colors["panel_light"], self.colors["panel_dark"]))
        border_color = first.get("border_color", (self.colors["border_light"], self.colors["border_dark"]))

        menu_width = 360
        menu_height = min(470, 120 + count * 44)
        menu = ctk.CTkFrame(
            self,
            width=menu_width,
            height=menu_height,
            fg_color=panel_fg,
            border_width=1,
            border_color=border_color,
            corner_radius=10,
        )
        menu.grid_propagate(False)
        menu.grid_columnconfigure(0, weight=1)
        menu.grid_rowconfigure(1, weight=1)
        place_host = getattr(self, "content_shell", self)
        try:
            menu.place(in_=place_host, relx=0.5, y=96, anchor="n")
        except Exception:
            menu.place(relx=0.5, y=96, anchor="n")
        self._restore_chip_menu = menu

        header = ctk.CTkFrame(menu, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Ventanas minimizadas",
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            header,
            text="x",
            width=30,
            height=26,
            fg_color="transparent",
            hover_color=("#E5E7EB", "#303034"),
            command=self._hide_restore_chip_menu,
        ).grid(row=0, column=1, padx=(8, 0), sticky="e")

        body = ctk.CTkScrollableFrame(menu, fg_color="transparent") if count > 6 else ctk.CTkFrame(menu, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1)

        def restore_item(item_key):
            item = self._restore_chips.get(item_key)
            if not item:
                self._refresh_restore_chip_bar()
                return
            command = item.get("command")
            self._destroy_restore_chip(item_key)
            self._hide_restore_chip_menu()
            if callable(command):
                command()

        def close_all_minimized():
            keys = list(getattr(self, "_restore_chips", {}).keys())
            for item_key in keys:
                item = self._restore_chips.get(item_key) or {}
                close_command = item.get("close_command")
                window = item.get("window") or self._secondary_windows.get(item_key)
                self._destroy_restore_chip(item_key)
                if callable(close_command):
                    try:
                        close_command()
                        continue
                    except Exception:
                        pass
                if self._widget_exists(window):
                    try:
                        window.destroy()
                    except Exception:
                        pass
            self._hide_restore_chip_menu()
            self._refresh_restore_chip_bar()

        for row, (item_key, item) in enumerate(items):
            ctk.CTkButton(
                body,
                text=item.get("text", item_key),
                height=36,
                anchor="w",
                fg_color=(self.colors.get("card_light", "#F7F8FA"), self.colors.get("card_dark", "#26262A")),
                hover_color=self.colors.get("sidebar_hover", ("#E5E7EB", "#303034")),
                border_width=1,
                border_color=border_color,
                text_color=self.colors.get("sidebar_text", ("gray20", "gray86")),
                command=lambda k=item_key: restore_item(k),
            ).grid(row=row, column=0, sticky="ew", padx=2, pady=3)

        footer = ctk.CTkFrame(menu, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            footer,
            text="Cerrar todas",
            height=32,
            width=140,
            fg_color=self.colors.get("danger", "#B42318"),
            hover_color="#8F1D14",
            command=close_all_minimized,
        ).grid(row=0, column=0)

        try:
            menu.lift()
        except Exception:
            pass
        self._restore_chip_menu_outside_active = True
        self._install_restore_chip_menu_outside_close()

    def _show_restore_chip(self, key, text, command, panel_fg, border_color, fg_color, hover_color, window=None, close_command=None):
        self._ensure_window_registries()
        self._restore_chips[key] = {
            "text": text,
            "command": command,
            "window": window,
            "close_command": close_command,
            "panel_fg": panel_fg,
            "border_color": border_color,
            "fg_color": fg_color,
            "hover_color": hover_color,
        }
        self._refresh_restore_chip_bar()
        return getattr(self, "_restore_chip_bar", None)

    def _track_skin_widget(self, widget, role):
        if not hasattr(self, "_skinnable_widgets"):
            self._skinnable_widgets = []
        self._skinnable_widgets.append((widget, role))
        return widget

    def _apply_skin_live(self):
        """Aplica la paleta a la estructura estable sin reconstruir páginas."""
        self._safe_configure_widget(self.shell, fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]))
        self._safe_configure_widget(self.sidebar, fg_color=self.colors["sidebar"])
        self._safe_configure_widget(getattr(self, "sidebar_separator", None), fg_color=self._sidebar_separator_color())
        self._safe_configure_widget(self.top_bar, fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]))
        self._safe_configure_widget(
            getattr(self, "lbl_brand", None),
            text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
        )
        self._safe_configure_widget(
            getattr(self, "lbl_unit", None),
            text_color=(self.colors["accent"], self.colors["text_secondary_dark"]),
        )

        for button in getattr(self, "nav_buttons", {}).values():
            self._safe_configure_widget(
                button,
                hover_color=self.colors["sidebar_hover"],
                text_color=self.colors["sidebar_text"],
            )
        self._set_active_nav(getattr(self, "current_frame_name", "Selection"))

        topbar_style = {
            "fg_color": (self.colors["card_light"], self.colors["card_dark"]),
            "hover_color": self.colors["sidebar_hover"],
            "border_color": (self.colors["border_light"], self.colors["border_dark"]),
            "text_color": self.colors["sidebar_text"],
        }
        self._safe_configure_widget(
            getattr(self, "btn_appearance", None),
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="white",
        )
        self._safe_configure_widget(getattr(self, "btn_versions", None), **topbar_style)
        self._safe_configure_widget(getattr(self, "btn_creditos", None), **topbar_style)
        for skin_widget_name in ("om_skin", "om_appearance_skin"):
            self._safe_configure_widget(
                getattr(self, skin_widget_name, None),
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                button_color=self.colors["secondary"],
                button_hover_color=self.colors["secondary_hover"],
                dropdown_fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                dropdown_hover_color=self.colors["sidebar_hover"],
                text_color=self.colors["sidebar_text"],
            )
        for mode_widget_name in ("om_tema", "om_appearance_mode"):
            self._safe_configure_widget(
                getattr(self, mode_widget_name, None),
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                button_color=self.colors["accent"],
                button_hover_color=self.colors["accent_hover"],
                dropdown_fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                dropdown_hover_color=self.colors["sidebar_hover"],
                text_color=self.colors["sidebar_text"],
            )
        self._safe_configure_widget(
            getattr(self, "appearance_panel", None),
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
        )
        self._safe_configure_widget(
            getattr(self, "btn_archivo", None),
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            hover_color=self.colors["sidebar_hover"],
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            text_color=self.colors["sidebar_text"],
        )
        self._safe_configure_widget(getattr(self, "btn_restart", None), fg_color=self.colors["warning"])
        self._safe_configure_widget(
            getattr(self, "btn_back", None),
            fg_color=self.colors["secondary"],
            hover_color=self.colors["secondary_hover"],
        )
        self._safe_configure_widget(getattr(self, "btn_cancel", None), fg_color=self.colors["danger"])
        self._safe_configure_widget(getattr(self, "progress_bar", None), progress_color=self.colors["accent"])

        alive = []
        for widget, role in getattr(self, "_skinnable_widgets", []):
            if not self._widget_exists(widget):
                continue
            alive.append((widget, role))
            if role == "card":
                self._safe_configure_widget(
                    widget,
                    fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                )
            elif role == "page_surface":
                self._safe_configure_widget(widget, fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]))
                canvas = getattr(widget, "_parent_canvas", None)
                if canvas is not None:
                    canvas_bg = self.colors["canvas_dark"] if ctk.get_appearance_mode() == "Dark" else self.colors["canvas_light"]
                    self._safe_configure_widget(canvas, bg=canvas_bg)
            elif role == "accent_bar":
                self._safe_configure_widget(widget, fg_color=self.colors["accent"])
            elif role == "warning_bar":
                self._safe_configure_widget(widget, fg_color=self.colors["warning"])
            elif role == "accent_box":
                self._safe_configure_widget(widget, fg_color=self.colors["sidebar_active"])
            elif role == "accent_text":
                self._safe_configure_widget(widget, text_color=self.colors["accent"])
            elif role == "primary_button":
                self._safe_configure_widget(
                    widget,
                    fg_color=self.colors["accent"],
                    hover_color=self.colors["accent_hover"],
                )
            elif role == "guide_button":
                self._safe_configure_widget(
                    widget,
                    fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                    hover_color=self.colors["sidebar_hover"],
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                    text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                )
            elif role == "guide_tabs":
                self._safe_configure_widget(
                    widget,
                    fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                    segmented_button_selected_color=self.colors["accent"],
                    segmented_button_selected_hover_color=self.colors["accent_hover"],
                    segmented_button_unselected_color=(self.colors["card_light"], self.colors["card_dark"]),
                    segmented_button_unselected_hover_color=self.colors["sidebar_hover"],
                    text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                )
            elif role == "guide_tab":
                self._safe_configure_widget(
                    widget,
                    fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                )
            elif role == "primary_text":
                self._safe_configure_widget(
                    widget,
                    text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                )
            elif role == "secondary_text":
                self._safe_configure_widget(
                    widget,
                    text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                )
            elif role == "muted_text":
                self._safe_configure_widget(
                    widget,
                    text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
                )
            elif role == "console_chip":
                self._safe_configure_widget(
                    widget,
                    fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                    text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                )
            elif role == "terminal_text":
                self._safe_configure_widget(
                    widget,
                    fg_color=("#F8F7F2", "#101114"),
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                    text_color=(self.colors["text_primary_light"], "#DDE6E8"),
                )
            elif role == "console_input":
                self._safe_configure_widget(
                    widget,
                    fg_color=("#F8F7F2", "#121417"),
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                    text_color=(self.colors["text_primary_light"], "#DDE6E8"),
                    placeholder_text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                )
            elif role == "danger_button":
                self._safe_configure_widget(widget, fg_color=self.colors["danger"])
        self._skinnable_widgets = alive

        try:
            self.console_text.tag_config("ok", foreground=self.colors["success"])
            self.console_text.tag_config("error", foreground=self.colors["danger"])
            self.console_text.tag_config("warning", foreground=self.colors["warning"])
            self.console_text.tag_config("step", foreground=self.colors["accent"])
        except Exception:
            pass

    def _change_skin(self, display_name):
        target_skin = self._skin_key_from_display_name(display_name)
        if target_skin not in SKINS:
            target_skin = DEFAULT_SKIN
        self.current_skin = target_skin
        self.colors = self._build_colors_from_skin(target_skin)
        for widget_name in ("om_skin", "om_appearance_skin"):
            try:
                widget = getattr(self, widget_name, None)
                if widget is not None:
                    widget.set(self._skin_display_name(target_skin))
            except Exception:
                pass
        self._apply_skin_live()
        self._save_ui_settings()

    def _change_appearance_mode(self, mode):
        """Cambia Light/Dark sin reiniciar ni dejar la ventana oculta."""
        target_mode = "Dark" if str(mode).lower() == "dark" else "Light"
        for widget_name in ("om_tema", "om_appearance_mode"):
            try:
                widget = getattr(self, widget_name, None)
                if widget is not None:
                    widget.configure(state="disabled")
            except Exception:
                pass

        def apply_mode():
            try:
                ctk.set_appearance_mode(target_mode)
                self.update_idletasks()
                try:
                    if self.state() == "withdrawn":
                        self.deiconify()
                except Exception:
                    pass
                try:
                    self.lift()
                except Exception:
                    pass
                if hasattr(self, "_schedule_tools_drawer_scroll_refresh"):
                    self._schedule_tools_drawer_scroll_refresh()
                current_frame = self.frames.get(getattr(self, "current_frame_name", ""))
                queue_check = getattr(current_frame, "_easydeploy_queue_adaptive_check", None)
                if queue_check:
                    queue_check(80)
                for widget_name in ("om_tema", "om_appearance_mode"):
                    try:
                        widget = getattr(self, widget_name, None)
                        if widget is not None:
                            widget.set(ctk.get_appearance_mode())
                    except Exception:
                        pass
                self._save_ui_settings()
            except Exception as exc:
                try:
                    for widget_name in ("om_tema", "om_appearance_mode"):
                        widget = getattr(self, widget_name, None)
                        if widget is not None:
                            widget.set(ctk.get_appearance_mode())
                except Exception:
                    pass
                self.ui_showerror("Modo visual", f"No se pudo cambiar el modo visual:\n{exc}")
            finally:
                for widget_name in ("om_tema", "om_appearance_mode"):
                    try:
                        widget = getattr(self, widget_name, None)
                        if widget is not None:
                            widget.configure(state="normal")
                    except Exception:
                        pass

        self.after(20, apply_mode)

    def _open_versions_view(self):
        if not getattr(self, "_versions_view_built", False):
            self._build_versions_view()
        current = getattr(self, "current_frame_name", "Selection")
        if current != "Versions":
            self.return_frame_after_versions = current
        self.show_frame("Versions")

    def _open_creditos_dialog(self):
        key = "creditos"
        existing = self._get_secondary_window(key)

        def bring_forward(window):
            def release_topmost():
                try:
                    if window.winfo_exists():
                        window.attributes("-topmost", False)
                except Exception:
                    pass

            try:
                if window.state() in {"iconic", "withdrawn"}:
                    window.deiconify()
            except Exception:
                try:
                    window.deiconify()
                except Exception:
                    pass
            try:
                window.lift(self)
            except Exception:
                try:
                    window.lift()
                except Exception:
                    pass
            try:
                window.attributes("-topmost", True)
                window.after(260, release_topmost)
            except Exception:
                release_topmost()
            try:
                window.focus_set()
            except Exception:
                pass

        if existing is not None:
            bring_forward(existing)
            return existing

        dialog = ctk.CTkToplevel(self)
        dialog.withdraw()
        dialog.title(f"Acerca de Easy Deploy v{APP_VERSION}")
        try:
            credit_width = min(820, max(760, self.winfo_screenwidth() - 180))
            credit_height = min(760, max(640, self.winfo_screenheight() - 110))
        except Exception:
            credit_width, credit_height = 800, 720
        dialog.geometry(f"{credit_width}x{credit_height}")
        dialog.minsize(680, 560)
        dialog.resizable(True, True)
        dialog.overrideredirect(False)
        dialog.configure(fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]))
        try:
            dialog.transient(self)
        except Exception:
            pass
        self._register_secondary_window(key, dialog)

        shell = ctk.CTkFrame(
            dialog,
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=10,
        )
        shell.pack(fill="both", expand=True, padx=18, pady=18)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(2, weight=1)
        self._track_skin_widget(shell, "card")

        accent_line = ctk.CTkFrame(shell, height=3, fg_color=self.colors["accent"], corner_radius=3)
        accent_line.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 0))
        self._track_skin_widget(accent_line, "accent_bar")

        header = ctk.CTkFrame(shell, fg_color="transparent")
        header.grid(row=1, column=0, sticky="ew", padx=22, pady=(16, 10))
        header.grid_columnconfigure(1, weight=1)

        logo_box = ctk.CTkFrame(
            header,
            width=58,
            height=58,
            fg_color=self.colors["sidebar_active"],
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=10,
        )
        logo_box.grid(row=0, column=0, rowspan=2, padx=(0, 14), sticky="n")
        logo_box.grid_propagate(False)
        self._track_skin_widget(logo_box, "accent_box")
        logo_image = self._load_startup_logo_image(size=(48, 48))
        if logo_image:
            ctk.CTkLabel(logo_box, image=logo_image, text="").pack(fill="both", expand=True, padx=5, pady=5)
        else:
            logo_label = ctk.CTkLabel(logo_box, text="ED", font=("Segoe UI", 16, "bold"), text_color=self.colors["accent"])
            logo_label.pack(fill="both", expand=True)
            self._track_skin_widget(logo_label, "accent_text")

        title = ctk.CTkLabel(
            header,
            text="Acerca de Easy Deploy",
            font=("Segoe UI", 22, "bold"),
            anchor="w",
            text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
        )
        title.grid(row=0, column=1, sticky="ew")
        self._track_skin_widget(title, "primary_text")

        subtitle = ctk.CTkLabel(
            header,
            text="Créditos del proyecto y reparto interno de desarrollo declarado para el programa.",
            font=("Segoe UI", 12),
            anchor="w",
            text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
            wraplength=500,
            justify="left",
        )
        subtitle.grid(row=1, column=1, sticky="ew", pady=(2, 0))
        self._track_skin_widget(subtitle, "secondary_text")

        version_label = ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION}",
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["accent"],
            anchor="e",
        )
        version_label.grid(row=0, column=2, padx=(14, 0), sticky="ne")
        self._track_skin_widget(version_label, "accent_text")

        content = ctk.CTkScrollableFrame(
            shell,
            fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]),
            corner_radius=8,
        )
        content.grid(row=2, column=0, sticky="nsew", padx=22, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        self._track_skin_widget(content, "page_surface")

        def refresh_credit_scrollbar(event=None):
            try:
                scrollbar = getattr(content, "_scrollbar", None)
                canvas = getattr(content, "_parent_canvas", None)
                if scrollbar is None or canvas is None:
                    return
                canvas.update_idletasks()
                bbox = canvas.bbox("all")
                content_height = (bbox[3] - bbox[1]) if bbox else 0
                visible_height = canvas.winfo_height()
                needs_scroll = content_height > visible_height + 4
                if needs_scroll:
                    try:
                        scrollbar.grid()
                    except Exception:
                        pass
                else:
                    try:
                        scrollbar.grid_remove()
                    except Exception:
                        pass
            except Exception:
                pass

        def add_author_card(row, name, modules_text):
            card = ctk.CTkFrame(
                content,
                fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                border_width=1,
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                corner_radius=8,
            )
            card.grid(row=row, column=0, sticky="ew", padx=2, pady=(0, 10))
            card.grid_columnconfigure(0, weight=1)
            self._track_skin_widget(card, "card")

            name_label = ctk.CTkLabel(
                card,
                text=name,
                font=("Segoe UI", 15, "bold"),
                anchor="w",
                text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
            )
            name_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 4))
            self._track_skin_widget(name_label, "primary_text")

            modules_label = ctk.CTkLabel(
                card,
                text=modules_text,
                font=("Segoe UI", 12),
                justify="left",
                anchor="w",
                wraplength=610,
                text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
            )
            modules_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
            self._track_skin_widget(modules_label, "secondary_text")

        add_author_card(
            0,
            "Juan Jesús Cañas Ramirez",
            "- Idea principal fundamental de desarrollo del programa y parte de redes.\n"
            "- Redes: Switch Allied, Switch Cisco, Router, ASA, Checkpoint, Topo e IP.\n"
            "- Script Crear usuarios EXC.\n"
            "- Guía Exchange.",
        )
        add_author_card(
            1,
            "Adrián Mata Cifre",
            "- Sistemas, menús, Front End, Backend de UI y estética general.\n"
            "- Inicio: Admin, Recursos, Logs, Teclado ESP, Firewall, entorno, roles, CPU, Ping y discos.\n"
            "- Sistemas: DC1/DC2, unión a dominio, Repadmin, D2/D4, .NET 3.5 con ISO local, hora, KMS, SQL, JCHAT, Exchange, SharePoint y Skype.\n"
            "- AD/Exchange: Crear usuarios AD/EXC, avisos, validaciones visuales y estados fijos.\n"
            "- Skype: prerrequisitos offline, permisos de usuario, punteros DNS e instalación desde ISO.\n"
            "- Programas/recursos: Firefox, WinRAR, Adobe Reader, Office + Skype offline, validación de recursos y desmontaje controlado de ISOs.\n"
            "- Guías, Seguridad y Consola: biblioteca PDF, Firewall, Auditoría, Guía rápida, logs y herramientas administrativas.\n"
            "- Apariencia, Versiones, Créditos, ventanas minimizadas y Monitor de ping con favoritos, scroll y formulario integrado.",
        )

        legal_label = ctk.CTkLabel(
            content,
            text=(
                "Nota: esta pantalla es una declaración de créditos del proyecto; no sustituye acuerdos, "
                "licencias o contratos externos entre autores.\n\n"
                "Copyright © 2026 Easy Deploy. Todos los derechos reservados. Queda prohibida la reproducción "
                "total o parcial, distribución, modificación, cesión, venta o cualquier uso lucrativo del programa "
                "sin autorización expresa. Los derechos de uso, explotación y distribución quedan reservados."
            ),
            font=("Segoe UI", 11),
            justify="left",
            anchor="w",
            wraplength=610,
            text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
        )
        legal_label.grid(row=2, column=0, sticky="ew", padx=4, pady=(4, 14))
        self._track_skin_widget(legal_label, "muted_text")

        footer = ctk.CTkFrame(shell, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        close_button = ctk.CTkButton(
            footer,
            text="Cerrar",
            width=132,
            height=38,
            corner_radius=8,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=dialog.destroy,
            font=("Segoe UI", 12, "bold"),
        )
        close_button.grid(row=0, column=1, sticky="e")
        self._track_skin_widget(close_button, "primary_button")

        def close_dialog():
            self._unregister_secondary_window(key)
            try:
                dialog.destroy()
            except Exception:
                pass

        close_button.configure(command=close_dialog)
        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

        try:
            dialog.update_idletasks()
            x = self.winfo_rootx() + max(0, (self.winfo_width() - credit_width) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - credit_height) // 2)
            dialog.geometry(f"{credit_width}x{credit_height}+{x}+{y}")
        except Exception:
            pass
        try:
            content.bind("<Configure>", refresh_credit_scrollbar, add="+")
            dialog.bind("<Configure>", lambda _event=None: content.after(80, refresh_credit_scrollbar), add="+")
            content.after(180, refresh_credit_scrollbar)
        except Exception:
            pass
        dialog.deiconify()
        bring_forward(dialog)
        return dialog

    def _sidebar_button(self, frame_name, label, icon):
        return ctk.CTkButton(
            self.sidebar,
            text=f"{icon}  {label}",
            height=42,
            anchor="w",
            corner_radius=10,
            fg_color="transparent",
            hover_color=self.colors["sidebar_hover"],
            text_color=self.colors["sidebar_text"],
            font=("Segoe UI", 14, "bold"),
            command=lambda name=frame_name: self.show_frame(name),
        )

    def _set_active_nav(self, frame_name):
        if frame_name == "Versions":
            frame_name = getattr(self, "return_frame_after_versions", "Selection")
        if frame_name in {"SharePoint", "Exchange", "DC", "JCHAT", "Skype"}:
            frame_name = "Menu"
        elif frame_name == "Firewall":
            frame_name = "Security"
        for name, button in self.nav_buttons.items():
            if name == frame_name:
                button.configure(fg_color=self.colors["sidebar_active"], text_color=self.colors["sidebar_text_active"])
            else:
                button.configure(fg_color="transparent", text_color=self.colors["sidebar_text"])

    def _set_page_header(self, title, hint):
        return

    def _show_not_implemented(self, feature_name):
        self.ui_showinfo(feature_name, "En proceso de implementación.")

    def _clear_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def _content_required_height(self, container):
        """Devuelve la altura real ocupada por los widgets del contenedor."""
        required_height = 0
        try:
            bbox = container.grid_bbox()
            if bbox and bbox[3] > 1:
                required_height = max(required_height, bbox[3])
        except Exception:
            pass

        try:
            for child in container.winfo_children():
                if not child.winfo_ismapped():
                    continue
                required_height = max(required_height, child.winfo_y() + child.winfo_reqheight())
            return max(required_height, container.winfo_reqheight())
        except Exception:
            return required_height

    def _build_adaptive_page(self, frame, populate, initial_mode="normal"):
        """Construye la pagina una vez con scroll estable."""
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self._clear_frame(frame)
        page = ctk.CTkScrollableFrame(
            frame,
            fg_color=(self.colors["canvas_light"], self.colors["canvas_dark"]),
            corner_radius=0,
        )
        page.grid(row=0, column=0, sticky="nsew")
        self._track_skin_widget(page, "page_surface")
        canvas = getattr(page, "_parent_canvas", None)
        if canvas is not None:
            canvas_bg = self.colors["canvas_dark"] if ctk.get_appearance_mode() == "Dark" else self.colors["canvas_light"]
            self._safe_configure_widget(canvas, bg=canvas_bg)
        populate(page)
        self._install_scrollbar_autohide(frame, page)
        frame._easydeploy_queue_adaptive_check = lambda delay=280: None
        self.after_idle(self._update_environment_status)

    def _install_scrollbar_autohide(self, frame, page):
        canvas = getattr(page, "_parent_canvas", None)
        scrollbar = getattr(page, "_scrollbar", None)
        if canvas is None or scrollbar is None:
            return

        state = {
            "after_id": None,
            "visible": True,
            "grid_info": dict(scrollbar.grid_info()),
        }

        def set_visible(visible):
            if state["visible"] == visible:
                return
            state["visible"] = visible
            try:
                if visible:
                    scrollbar.grid(**state["grid_info"])
                else:
                    scrollbar.grid_remove()
            except Exception:
                pass

        def check():
            state["after_id"] = None
            if not self._widget_exists(frame) or not self._widget_exists(page):
                return
            frame_name = getattr(frame, "_easydeploy_frame_name", None)
            if frame_name and frame_name != getattr(self, "current_frame_name", None):
                return
            try:
                visible_height = canvas.winfo_height()
                bbox = canvas.bbox("all")
                content_height = bbox[3] - bbox[1] if bbox else page.winfo_reqheight()
                set_visible(content_height > visible_height + 2)
            except Exception:
                set_visible(True)

        def schedule(event=None, delay=140):
            if state["after_id"] is not None:
                try:
                    frame.after_cancel(state["after_id"])
                except Exception:
                    pass
            state["after_id"] = frame.after(delay, check)

        frame._easydeploy_scrollbar_autohide = schedule
        page._easydeploy_scrollbar_autohide = schedule
        canvas.bind("<Configure>", schedule, add="+")
        page.bind("<Configure>", schedule, add="+")
        frame.after_idle(lambda: schedule(delay=40))

    def _page_title(self, parent, title, subtitle, action_text=None, action_command=None):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, padx=2, pady=(0, 3), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(header, width=4, height=32, fg_color=self.colors["accent"], corner_radius=3).grid(
            row=0, column=0, padx=(0, 10), pady=(3, 0), sticky="nsw"
        )
        ctk.CTkLabel(
            header,
            text=title,
            font=("Segoe UI", 23, "bold"),
            anchor="w",
            justify="left",
            wraplength=860,
        ).grid(
            row=0, column=1, sticky="ew"
        )
        if action_text and action_command:
            ctk.CTkButton(
                header,
                text=action_text,
                width=110,
                height=34,
                corner_radius=9,
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                command=action_command,
            ).grid(
                row=0, column=2, padx=(12, 0), sticky="e"
            )
        ctk.CTkLabel(
            parent,
            text=subtitle,
            font=("Segoe UI", 12),
            text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
            anchor="w",
            justify="left",
            wraplength=920,
        ).grid(
            row=1, column=0, columnspan=2, padx=2, pady=(0, 16), sticky="ew"
        )

    def _action_card(self, parent, row, column, icon, title, description, command, accent="#2F9E8F", width=320):
        normal_fg = (self.colors["card_light"], self.colors["card_dark"])
        normal_border = (self.colors["border_light"], self.colors["border_dark"])
        hover_fg = (self.colors["card_hover_light"], self.colors["card_hover_dark"])
        card = ctk.CTkFrame(
            parent,
            fg_color=normal_fg,
            border_width=1,
            border_color=normal_border,
            corner_radius=9,
        )
        card.grid(row=row, column=column, padx=6, pady=6, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        card.configure(width=width, height=128)
        card.grid_propagate(False)
        self._track_skin_widget(card, "card")

        accent_bar = ctk.CTkFrame(card, width=2, fg_color=accent, corner_radius=3)
        accent_bar.place(x=0, y=22, relheight=0.50)
        self._track_skin_widget(accent_bar, "accent_bar")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew", padx=(17, 15), pady=(11, 9))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure((0, 1, 2), weight=1)

        icon_box = ctk.CTkFrame(content, width=42, height=30, fg_color=self.colors["sidebar_active"], corner_radius=8)
        icon_box.grid(row=0, column=0, pady=(0, 4), sticky="sw")
        icon_box.grid_propagate(False)
        self._track_skin_widget(icon_box, "accent_box")
        icon_lbl = ctk.CTkLabel(icon_box, text=icon, font=("Segoe UI", 14, "bold"), anchor="center")
        icon_lbl.pack(fill="both", expand=True)
        self._track_skin_widget(icon_lbl, "accent_text")

        title_lbl = ctk.CTkLabel(
            content,
            text=title,
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            justify="left",
            wraplength=max(180, width - 84),
        )
        title_lbl.grid(
            row=1, column=0, padx=4, pady=(0, 2), sticky="ew"
        )
        desc_lbl = ctk.CTkLabel(
            content,
            text=description,
            font=("Segoe UI", 11),
            text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
            justify="left",
            anchor="nw",
            wraplength=max(210, width - 82),
        )
        self._track_skin_widget(desc_lbl, "secondary_text")
        desc_lbl.grid(row=2, column=0, padx=4, pady=(0, 0), sticky="new")

        def on_enter(event=None):
            card.configure(
                fg_color=(self.colors["card_hover_light"], self.colors["card_hover_dark"]),
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
            )
            icon_box.configure(fg_color=self.colors["sidebar_hover"])
            accent_bar.configure(width=4)

        def on_leave(event=None):
            card.configure(
                fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
            )
            icon_box.configure(fg_color=self.colors["sidebar_active"])
            accent_bar.configure(width=2)

        for widget in (card, accent_bar, content, icon_box, icon_lbl, title_lbl, desc_lbl):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        self._make_clickable((card, accent_bar, content, icon_box, icon_lbl, title_lbl, desc_lbl), command)
        return card

    def _make_clickable(self, widgets, command):
        def invoke(event=None):
            try:
                command()
            except Exception as exc:
                self.ui_showerror(
                    "Acción no completada",
                    "No se pudo ejecutar la acción seleccionada.\n\n"
                    f"Detalle: {exc}",
                )

        for widget in widgets:
            try:
                widget.configure(cursor="hand2")
            except Exception:
                pass
            widget.bind("<Button-1>", invoke)

    def _info_tile(self, parent, column, title, value, color, command=None):
        tile = ctk.CTkFrame(
            parent,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=9,
        )
        tile.grid(row=0, column=column, padx=6, pady=6, sticky="nsew")
        tile.grid_propagate(False)
        tile.configure(height=82)
        self._track_skin_widget(tile, "card")
        title_label = ctk.CTkLabel(
            tile,
            text=title,
            font=("Segoe UI", 11, "bold"),
            text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
            anchor="w",
        )
        title_label.pack(
            fill="x", padx=14, pady=(11, 0)
        )
        value_label = ctk.CTkLabel(tile, text=value, font=("Segoe UI", 16, "bold"), text_color=color, anchor="w")
        value_label.pack(
            fill="x", padx=14, pady=(7, 11)
        )
        tile.status_label = value_label
        if command:
            normal_fg = (self.colors["card_light"], self.colors["card_dark"])
            hover_fg = (self.colors["card_hover_light"], self.colors["card_hover_dark"])

            def on_enter(event=None):
                tile.configure(
                    fg_color=(self.colors["card_hover_light"], self.colors["card_hover_dark"]),
                    border_color=self.colors["accent"],
                )

            def on_leave(event=None):
                tile.configure(
                    fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                )

            self._make_clickable((tile, title_label, value_label), command)
            for widget in (tile, title_label, value_label):
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
        return tile

    def _build_disk_status_panel(self, parent):
        normal_fg = (self.colors["card_light"], self.colors["card_dark"])
        hover_fg = (self.colors["card_hover_light"], self.colors["card_hover_dark"])
        normal_border = (self.colors["border_light"], self.colors["border_dark"])
        accent = self.colors["accent"]
        panel = ctk.CTkFrame(
            parent,
            fg_color=normal_fg,
            border_width=1,
            border_color=normal_border,
            corner_radius=8,
        )
        panel.grid(row=4, column=0, columnspan=2, sticky="ew", padx=7, pady=(18, 7))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)
        panel.configure(height=132)
        panel.grid_propagate(False)
        self._track_skin_widget(panel, "card")
        self.disk_status_panel = panel
        self._make_clickable((panel,), self._accion_abrir_disk_management)

        accent_bar = ctk.CTkFrame(panel, width=4, fg_color=accent, corner_radius=3)
        accent_bar.place(x=0, y=12, relheight=0.72)
        self._track_skin_widget(accent_bar, "accent_bar")

        def on_enter(event=None):
            panel.configure(
                fg_color=(self.colors["card_hover_light"], self.colors["card_hover_dark"]),
                border_color=self.colors["accent"],
            )
            accent_bar.configure(width=6)

        def on_leave(event=None):
            panel.configure(
                fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
            )
            accent_bar.configure(width=4)

        content = ctk.CTkFrame(panel, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew", padx=(20, 18), pady=14)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_columnconfigure(2, weight=1)
        content.grid_rowconfigure(0, weight=0)
        content.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            content,
            text="SSD - Estado de discos",
            font=("Segoe UI", 16, "bold"),
            anchor="center",
            justify="center",
        )
        title.grid(row=0, column=0, columnspan=3, padx=4, pady=(0, 8), sticky="ew")

        self.disk_status_rows = ctk.CTkFrame(content, fg_color="transparent")
        self.disk_status_rows.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(12, 12), pady=(0, 0))
        self.disk_status_rows.grid_columnconfigure((0, 1, 2), weight=1)

        disk_button = ctk.CTkButton(
            content,
            text="Disk Management",
            width=156,
            height=34,
            corner_radius=9,
            font=("Segoe UI", 12, "bold"),
            fg_color=accent,
            hover_color=self.colors["accent_hover"],
            command=self._accion_abrir_disk_management,
        )
        disk_button.grid(row=1, column=2, padx=(12, 0), pady=(0, 4), sticky="e")
        self._track_skin_widget(disk_button, "primary_button")

        self._make_clickable((panel, accent_bar, content, title, self.disk_status_rows), self._accion_abrir_disk_management)
        for widget in (panel, accent_bar, content, title, self.disk_status_rows):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        self._update_disk_status_panel()
        return panel

    def _disk_status_refresh_tick(self):
        self._refresh_disk_status_async()
        try:
            self._disk_refresh_after = self.after(60000, self._disk_status_refresh_tick)
        except Exception:
            self._disk_refresh_after = None

    def _get_local_disk_status(self):
        cached = getattr(self, "_disk_status_cache", None)
        if cached:
            return cached
        return self._scan_drive_letter_status()

    def _scan_drive_letter_status(self):
        import shutil

        disks = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if not os.path.isdir(drive):
                continue
            try:
                usage = shutil.disk_usage(drive)
            except Exception:
                continue
            if usage.total <= 0:
                continue
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            used_pct = usage.used / usage.total
            disks.append(
                {
                    "drive": drive,
                    "free_gb": free_gb,
                    "total_gb": total_gb,
                    "used_pct": used_pct,
                    "free_pct": 1 - used_pct,
                    "kind": "volume",
                    "status": "Correcto",
                }
            )
        return disks

    def _scan_disk_inventory_status(self):
        import re

        fallback = self._scan_drive_letter_status()
        script = r"""
        $culture = [System.Globalization.CultureInfo]::InvariantCulture
        $volumeDiskNumbers = @{}
        Get-Partition -ErrorAction SilentlyContinue | Where-Object DriveLetter | ForEach-Object {
            $volumeDiskNumbers[[int]$_.DiskNumber] = $true
        }
        Get-Volume -ErrorAction SilentlyContinue |
            Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' -and $_.Size -gt 0 } |
            Sort-Object DriveLetter |
            ForEach-Object {
                $free = ([double]$_.SizeRemaining).ToString($culture)
                $size = ([double]$_.Size).ToString($culture)
                "VOL|$($_.DriveLetter):\|$free|$size|$($_.HealthStatus)"
            }
        Get-Disk -ErrorAction SilentlyContinue |
            Sort-Object Number |
            ForEach-Object {
                if (-not $volumeDiskNumbers.ContainsKey([int]$_.Number)) {
                    $size = ([double]$_.Size).ToString($culture)
                    "DISK|$($_.Number)|$size|$($_.OperationalStatus)|$($_.PartitionStyle)|$($_.FriendlyName)"
                }
            }
        """
        try:
            ok, output = SysUtils.run_powershell(script, capture=True, timeout=18)
        except Exception:
            ok, output = False, ""
        if not ok or not output.strip():
            return fallback

        disks = []
        seen_volumes = set()
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("|")
            try:
                if len(parts) >= 5 and parts[0] == "VOL":
                    drive = parts[1]
                    free = float(parts[2].replace(",", "."))
                    total = float(parts[3].replace(",", "."))
                    if total <= 0:
                        continue
                    used_pct = max(0.0, min(1.0, 1 - (free / total)))
                    seen_volumes.add(drive.upper())
                    disks.append(
                        {
                            "drive": drive,
                            "free_gb": free / (1024 ** 3),
                            "total_gb": total / (1024 ** 3),
                            "used_pct": used_pct,
                            "free_pct": 1 - used_pct,
                            "kind": "volume",
                            "status": parts[4] or "Correcto",
                        }
                    )
                elif len(parts) >= 6 and parts[0] == "DISK":
                    size = float(parts[2].replace(",", "."))
                    if size <= 0:
                        continue
                    status = " / ".join(value for value in (parts[3], parts[4]) if value)
                    friendly_name = re.sub(r"\s+", " ", parts[5]).strip()
                    disks.append(
                        {
                            "drive": f"Disco {parts[1]}",
                            "free_gb": size / (1024 ** 3),
                            "total_gb": size / (1024 ** 3),
                            "used_pct": 0.0,
                            "free_pct": 1.0,
                            "kind": "disk",
                            "status": status or "Sin volumen",
                            "name": friendly_name,
                        }
                    )
            except Exception:
                continue

        if not disks:
            return fallback

        for disk in fallback:
            if disk["drive"].upper() not in seen_volumes:
                disks.append(disk)
        return disks

    def _refresh_disk_status_async(self, force=False):
        if getattr(self, "_disk_status_refresh_running", False):
            return
        self._disk_status_refresh_running = True

        def worker():
            disks = self._scan_disk_inventory_status()

            def apply_status():
                self._disk_status_cache = disks
                self._disk_status_refresh_running = False
                self._update_disk_status_panel()

            self.after(0, apply_status)

        threading.Thread(target=worker, daemon=True).start()

    def _update_disk_status_panel(self):
        rows = getattr(self, "disk_status_rows", None)
        if not self._widget_exists(rows):
            return

        for child in rows.winfo_children():
            child.destroy()

        disks = self._get_local_disk_status()
        panel = getattr(self, "disk_status_panel", None)
        visible_disks = list(disks)
        row_count = max(1, (len(visible_disks) + 2) // 3)
        target_height = 132 + ((row_count - 1) * 64)
        if self._widget_exists(panel):
            panel.configure(height=target_height)
            try:
                queue_check = getattr(self.frames.get("Selection"), "_easydeploy_queue_adaptive_check", None)
                if queue_check:
                    queue_check(40)
            except Exception:
                pass

        if not disks:
            label = ctk.CTkLabel(
                rows,
                text="No se han detectado unidades locales.",
                font=("Segoe UI", 12),
                text_color=("gray35", "gray72"),
                anchor="w",
            )
            label.grid(row=0, column=0, sticky="ew", padx=2, pady=8)
            self._make_clickable((label,), self._accion_abrir_disk_management)
            return

        for index, disk in enumerate(visible_disks):
            row = index // 3
            col = index % 3
            card = ctk.CTkFrame(rows, fg_color="transparent")
            card.grid(row=row, column=col, sticky="ew", padx=8, pady=(0, 10))
            card.grid_columnconfigure(0, weight=1)

            free_pct = disk["free_pct"]
            color = self.colors["danger"] if free_pct < 0.10 else self.colors["warning"] if free_pct < 0.20 else self.colors["accent"]
            is_raw_disk = disk.get("kind") == "disk"
            title_text = disk["drive"]
            if is_raw_disk:
                title_text = f"{disk['drive']}  sin letra"
            else:
                title_text = f"{disk['drive']}  {disk['free_gb']:.1f} GB libres"

            title = ctk.CTkLabel(
                card,
                text=title_text,
                font=("Segoe UI", 12, "bold"),
                anchor="center",
                justify="center",
            )
            title.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 2))
            detail_text = (
                f"Total {disk['total_gb']:.1f} GB | {disk.get('status', 'Sin volumen')}"
                if is_raw_disk
                else f"Total {disk['total_gb']:.1f} GB | Uso {int(disk['used_pct'] * 100)}%"
            )
            detail = ctk.CTkLabel(
                card,
                text=detail_text,
                font=("Segoe UI", 11),
                text_color=("gray35", "gray72"),
                anchor="center",
                justify="center",
            )
            detail.grid(row=1, column=0, sticky="ew", padx=2, pady=(0, 6))
            progress = ctk.CTkProgressBar(card, progress_color=color)
            progress.grid(row=2, column=0, sticky="ew", padx=2, pady=(0, 0))
            progress.set(disk["used_pct"])
            self._make_clickable((card, title, detail, progress), self._accion_abrir_disk_management)

    def _build_selection_screen(self):
        f = self.frames["Selection"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)
    
            self._page_title(
                page,
                "Panel de despliegue",
                "Empieza por las comprobaciones, valida recursos y ejecuta cada tarea con registro automático.",
            )
    
            status = ctk.CTkFrame(page, fg_color="transparent")
            status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            status.grid_columnconfigure((0, 2, 3, 4), weight=1)
            status.grid_columnconfigure(1, weight=2)
    
            self.admin_tile = self._info_tile(
                status,
                0,
                "Privilegios",
                "Comprobando",
                self.colors["warning"],
                command=self._accion_check_admin,
            )
            self.payload_tile = self._info_tile(
                status,
                1,
                "Recursos",
                "Comprobando",
                self.colors["warning"],
                command=self._accion_abrir_recursos,
            )
            self.logs_tile = self._info_tile(
                status,
                2,
                "Logs",
                "Activados",
                self.colors["success"],
                command=self._accion_abrir_logs,
            )
            self.keyboard_tile = self._info_tile(
                status,
                3,
                "Teclado ESP",
                "Comprobando",
                self.colors["warning"],
                command=self._accion_teclado_es,
            )
            self.firewall_tile = self._info_tile(
                status,
                4,
                "Firewall",
                "Comprobando",
                self.colors["warning"],
                command=lambda: self.show_frame("Firewall"),
            )
    
            quick = ctk.CTkFrame(page, fg_color="transparent")
            quick.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 0))
            quick.grid_columnconfigure((0, 1), weight=1)
    
            self._action_card(
                quick, 0, 0, "✓", "Comprobar entorno",
                "Revisa permisos de administrador, red y datos básicos del servidor.",
                self._accion_info_sistema,
                self.colors["accent"],
            )
            self._action_card(
                quick, 0, 1, "R", "Ver roles instalados",
                "Lista los roles y características instalados en Windows Server.",
                self._accion_ver_roles,
                "#4F46E5",
            )
            self._action_card(
                quick, 1, 0, "CPU", "Top procesos",
                "Muestra los procesos que más consumen CPU y memoria.",
                self._accion_top_procesos,
                "#7C3AED",
            )
            self._action_card(
                quick, 1, 1, "PING", "Ping",
                "Comprueba conectividad con una IP o dominio desde una ventana guiada.",
                self._accion_ping_tool,
                "#0F766E",
            )
    
            self.disk_status_panel = self._build_disk_status_panel(page)

        self._build_adaptive_page(f, populate)

    def _build_menu_principal(self):
        f = self.frames["Menu"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)
    
            self._page_title(
                page,
                "Sistemas y tareas",
                "Selecciona el bloque que necesitas. Las tareas críticas se registran automáticamente.",
            )
    
            cards = [
                ("D", "Controlador de dominio", "Promoción de DC1, DC2 y preparación de Active Directory.", lambda: self.show_frame("DC"), "#C2410C"),
                ("T", "Sincronizar hora", "Ajusta zona horaria y sincronización para entorno de dominio.", lambda: self.iniciar_tarea(self.task_time_sync), "#047857"),
                ("K", "KMS", "Convierte Evaluation cuando aplica y configura activación KMS.", lambda: self.iniciar_tarea(self.task_kms), "#7C3AED"),
                ("Q", "SQL Server", "Drivers, SSMS y montaje de ISO de SQL Server.", lambda: self.iniciar_tarea(self.task_install_sql), "#4338CA"),
                ("J", "JCHAT", "Instalación de Java/Openfire y gestión de usuarios o salas.", lambda: self.show_frame("JCHAT"), "#0F766E"),
                ("X", "Exchange", "Instala características, prerrequisitos y prepara AD/schema.", lambda: self.show_frame("Exchange"), "#2563EB"),
                ("◇", "SharePoint", "Roles, características y prerrequisitos de SharePoint.", lambda: self.show_frame("SharePoint"), self.colors["accent"]),
                ("S", "Skype for Business", "Prerrequisitos e instalación guiada del servidor Skype for Business.", lambda: self.show_frame("Skype"), "#B45309"),
            ]
    
            for idx, item in enumerate(cards):
                row = 2 + idx // 2
                col = idx % 2
                self._action_card(page, row, col, *item)

        self._build_adaptive_page(f, populate)

    def _build_menu_sharepoint(self):
        f = self.frames["SharePoint"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)
    
            self._page_title(
                page,
                "SharePoint",
                "Ejecuta primero roles y características, después prerrequisitos y SharePoint.",
            )
    
            self._action_card(
                page, 2, 0, "1", "Roles y características",
                "Instala los roles de Windows necesarios para preparar el servidor.",
                lambda: self.iniciar_tarea(self.task_sp_roles),
                self.colors["accent"],
            )
            self._action_card(
                page, 2, 1, "2", "Prerrequisitos y SharePoint",
                "Instala prerrequisitos, ejecuta PrerequisiteInstaller y lanza SharePoint.",
                lambda: self.iniciar_tarea(self.task_sp_prereqs),
                "#2563EB",
            )

        self._build_adaptive_page(f, populate)

    def _build_menu_exchange(self):
        f = self.frames["Exchange"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)

            self._page_title(
                page,
                "Exchange",
                "Elige si quieres instalar prerrequisitos o preparar AD/schema desde el medio de Exchange.",
            )

            self._action_card(
                page, 2, 0, "PRE", "Prerrequisitos Exchange",
                "Instala roles, características y prerrequisitos locales antes de ejecutar Setup.",
                self.pre_task_exchange_prereqs,
                "#2563EB",
            )
            self._action_card(
                page, 2, 1, "AD", "Prepare Schema",
                "Comprueba el dominio y ejecuta PrepareSchema, PrepareAD y PrepareAllDomains.",
                self.pre_task_exchange_schema,
                "#0F766E",
            )
            self._action_card(
                page, 3, 0, "X", "Instalar Exchange",
                "Lanza Setup desde el medio de Exchange.",
                self.pre_task_exchange_install,
                "#2563EB",
            )
            self._action_card(
                page, 3, 1, "U", "Crear usuarios EXC",
                "Alta rapida de usuarios AD con buzon Exchange y resumen de resultados.",
                self.pre_task_exchange_create_users,
                "#7C3AED",
            )
            self._action_card(
                page, 4, 0, "REC", "RecoverServer Exchange",
                "Recupera un servidor Exchange registrado en AD sin borrar objetos del dominio.",
                self.pre_task_exchange_recover_server,
                "#B45309",
            )

        self._build_adaptive_page(f, populate)

    def _build_menu_dc(self):
        f = self.frames["DC"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)
    
            self._page_title(
                page,
                "Dominio y Active Directory",
                "Confirma red, discos y DNS antes de ejecutar una promoción.",
            )
    
            self._action_card(
                page, 2, 0, "DC1", "Nuevo bosque",
                "Instala AD DS, DNS y promociona el servidor como primer controlador.",
                self.pre_task_dc1,
                "#C2410C",
            )
            self._action_card(
                page, 2, 1, "DC2", "Controlador adicional",
                "Une un controlador adicional a un dominio existente.",
                self.pre_task_dc2,
                "#B45309",
            )
            self._action_card(
                page, 3, 0, "+", "Unir equipo a dominio",
                "Une este equipo a dominio y cambia el nombre si lo necesitas.",
                self.pre_task_join_domain,
                self.colors["accent"],
            )
            self._action_card(
                page, 3, 1, "GPO", "Políticas de grupo",
                "Acceso reservado para crear y gestionar GPO de dominio.",
                lambda: show_group_policy_placeholder(self),
                "#4F46E5",
            )
            self._action_card(
                page, 4, 0, "AD", "Crear usuarios AD",
                "Alta rapida de usuarios en Active Directory sin buzon Exchange.",
                lambda: show_ad_users_tool(self),
                "#0F766E",
            )
            self._action_card(
                page, 4, 1, ".NET", "Net Framework 3.5",
                "Instala Net-Framework-Core desde el CD/ISO local de Windows Server.",
                lambda: self.iniciar_tarea(self.task_netfx35),
                "#2563EB",
            )
            self._action_card(
                page, 5, 0, "REP", "Repadmin",
                "Fuerza KCC, SyncAll y muestra resumen de replicación entre controladores de dominio.",
                lambda: show_repadmin_tool(self),
                "#0F766E",
            )
            self._action_card(
                page, 5, 1, "D2/D4", "D2 D4",
                "Asistente guiado para recuperación DFSR SYSVOL no autoritativa/autoritativa.",
                lambda: show_d2_d4_tool(self),
                "#D97706",
            )

        self._build_adaptive_page(f, populate)

    def _build_menu_jchat(self):
        f = self.frames["JCHAT"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)

            self._page_title(
                page,
                "JCHAT",
                "Instala Java/Openfire y prepara futuras acciones de usuarios y salas.",
            )

            self._action_card(
                page, 2, 0, "J", "Instalar Java y Openfire",
                "Instala Java si falta y lanza el instalador de Openfire.",
                lambda: self.iniciar_tarea(self.task_jchat),
                "#0F766E",
            )
            self._action_card(
                page, 2, 1, "CLI", "Instalar Jchat CLI",
                "Instala el cliente JCHAT CLI desde el MSI offline de recursos.",
                lambda: self.iniciar_tarea(self.task_jchat_cli),
                "#2563EB",
            )
            self._action_card(
                page, 3, 0, "U", "Crear usuarios Jchat",
                "Acceso reservado para alta guiada de usuarios en JCHAT/Openfire.",
                lambda: self._show_not_implemented("Crear usuarios Jchat"),
                "#4F46E5",
            )
            self._action_card(
                page, 3, 1, "S", "Crear salas Jchat",
                "Acceso reservado para crear salas y configuracion inicial de chat.",
                lambda: show_jchat_rooms_placeholder(self),
                "#7C3AED",
            )

        self._build_adaptive_page(f, populate)


    def _build_menu_skype(self):
        f = self.frames["Skype"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)

            self._page_title(
                page,
                "Skype for Business Server",
                "Instala prerrequisitos, prepara permisos y abre el asistente de implementación. Revisa la Guía Skype si tienes dudas.",
            )

            self._action_card(
                page, 2, 0, "PRE", "Prerrequisitos Skype",
                "Instala roles/características de Windows, RSAT-ADDS, IIS, Media Foundation, Silverlight y UCMA.",
                lambda: pre_task_skype_prereqs(self),
                "#0F766E",
            )
            self._action_card(
                page, 2, 1, "ISO", "Instalar Skype",
                "Monta la ISO de Skype for Business Server 2019 y abre Setup/Deployment Wizard para continuar guiado.",
                lambda: pre_task_skype_install(self),
                "#B45309",
            )
            ctk.CTkFrame(page, height=12, fg_color="transparent").grid(row=3, column=0, columnspan=2, sticky="ew")
            self._action_card(
                page, 4, 0, "PERM", "Permisos a usuario",
                "Comprueba o añade un usuario a los grupos necesarios para preparar AD o administrar Skype.",
                lambda: pre_task_skype_permissions(self),
                "#7C3AED",
            )
            self._action_card(
                page, 4, 1, "DNS", "Puntero DNS Skype",
                "Crea los registros DNS internos mínimos para que el servidor/pool de Skype resuelva correctamente.",
                lambda: pre_task_skype_dns(self),
                "#0F766E",
            )

        self._build_adaptive_page(f, populate)

    def _build_network_view(self):
        f = self.frames["Network"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)

            self._page_title(
                page,
                "Redes",
                "Ejecuta las herramientas interactivas de switching y routing desde la consola integrada.",
            )

            self._action_card(
                page, 2, 0, "AT", "Switch Allied",
                "Abre una consola con deteccion AlliedWare Plus y comandos Allied Telesis.",
                self.open_switch_allied_tool,
                "#2563EB",
            )
            self._action_card(
                page, 2, 1, "CS", "Switch Cisco",
                "Abre una consola con deteccion Cisco IOS y comandos propios de Cisco.",
                self.open_switch_cisco_tool,
                "#7C3AED",
            )
            self._action_card(
                page, 3, 0, "RT", "Router",
                "Abre una consola integrada para configurar y administrar routers.",
                self.open_router_tool,
                "#0F766E",
            )
            self._action_card(
                page, 3, 1, "ASA", "Asa",
                "Acceso reservado para futuras tareas de firewall Cisco ASA.",
                lambda: show_asa_placeholder(self),
                "#B45309",
            )
            self._action_card(
                page, 4, 0, "CP", "Checkpoint",
                "Acceso reservado para futuras tareas de Check Point.",
                lambda: show_checkpoint_placeholder(self),
                "#2563EB",
            )
            self._action_card(
                page, 4, 1, "TOPO", "Generación de topologías de red",
                "Acceso reservado para generar topologias y mapas de red.",
                lambda: show_topology_placeholder(self),
                "#7C3AED",
            )
            self._action_card(
                page, 5, 0, "IP", "Gestión de direccionamiento",
                "Acceso reservado para gestionar direccionamiento IP y rangos.",
                lambda: show_addressing_placeholder(self),
                self.colors["accent"],
            )

        self._build_adaptive_page(f, populate)

    def _build_programs_view(self):
        f = self.frames["Programs"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)

            self._page_title(
                page,
                "Programas",
                "Instaladores offline y utilidades desde recursos locales.",
            )

            self._action_card(
                page, 2, 0, "FF", "Firefox",
                "Lanza el instalador de Mozilla Firefox desde OTROS.",
                lambda: self.iniciar_tarea(self.task_install_firefox),
                "#B7791F",
            )
            self._action_card(
                page, 2, 1, "WR", "WinRAR",
                "Lanza el instalador de WinRAR desde OTROS.",
                lambda: self.iniciar_tarea(self.task_install_winrar),
                "#3B6EA8",
            )
            self._action_card(
                page, 3, 0, "PDF", "Adobe Reader",
                "Lanza el instalador de Adobe Reader desde OTROS.",
                lambda: self.iniciar_tarea(self.task_install_adobe_reader),
                "#A34848",
            )
            self._action_card(
                page, 3, 1, "365", "Office + Skype",
                "Lanza Office y Skype for Business desde el mismo origen offline.",
                self.pre_task_install_office_skype,
                self.colors["accent"],
            )

        self._build_adaptive_page(f, populate)

    def _build_guides_view(self):
        f = self.frames["Guides"]

        guide_categories = [
            (
                "AD",
                "Dominio y Active Directory",
                "Controladores, roles FSMO, confianza y recuperación SYSVOL.",
                {
                    "accent": ("#76B7C8", "#6DB8C8"),
                    "soft": ("#EAF6F8", "#172D33"),
                    "text": ("#256B78", "#A7DDE6"),
                    "border": ("#B9DCE4", "#315762"),
                },
                ["Guía DC1", "Guía DC2", "Guía Intercambio Roles", "Guía Relación de Confianza", "Guía D2 D4"],
            ),
            (
                "CORE",
                "Core y Coi",
                "Guías de correo, colaboración y servicios de comunicación.",
                {
                    "accent": ("#9FA7D9", "#A8B1E8"),
                    "soft": ("#F0F1FA", "#22263A"),
                    "text": ("#4E5797", "#C3C9F4"),
                    "border": ("#D2D6EF", "#454B74"),
                },
                ["Guía Exchange", "Guía Skype", "Guía Jchat", "Guía Sharepoint"],
            ),
            (
                "WIN",
                "Servicios Windows",
                "Servicios de infraestructura, certificados y despliegue de red.",
                {
                    "accent": ("#9BBE7B", "#A8C885"),
                    "soft": ("#F0F6EA", "#243020"),
                    "text": ("#5E7A3D", "#C3DEA6"),
                    "border": ("#D4E4C4", "#4B603B"),
                },
                ["Guía Certificados", "Guía DHCP", "Guía WDS", "Guía WSUS"],
            ),
        ]

        def populate(page):
            page.grid_columnconfigure(0, weight=1)

            self._page_title(
                page,
                "Guías",
                "Biblioteca técnica local organizada por área de despliegue.",
            )

            for idx, (badge_text, category_title, description, group_style, guides) in enumerate(guide_categories):
                category = ctk.CTkFrame(
                    page,
                    fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                    border_width=1,
                    border_color=group_style["border"],
                    corner_radius=8,
                )
                category.grid(row=2 + idx, column=0, sticky="ew", padx=7, pady=(7, 10))
                category.grid_columnconfigure(0, weight=1)
                self._track_skin_widget(category, "card")

                accent_bar = ctk.CTkFrame(category, height=4, fg_color=group_style["accent"], corner_radius=3)
                accent_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))

                header = ctk.CTkFrame(category, fg_color="transparent")
                header.grid(row=1, column=0, sticky="ew", padx=18, pady=(14, 8))
                header.grid_columnconfigure(1, weight=1)

                badge = ctk.CTkFrame(
                    header,
                    width=50,
                    height=34,
                    fg_color=group_style["soft"],
                    border_width=1,
                    border_color=group_style["border"],
                    corner_radius=8,
                )
                badge.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="n")
                badge.grid_propagate(False)
                badge_label = ctk.CTkLabel(
                    badge,
                    text=badge_text,
                    font=("Segoe UI", 12, "bold"),
                    text_color=group_style["text"],
                )
                badge_label.pack(fill="both", expand=True)

                ctk.CTkLabel(
                    header,
                    text=category_title,
                    font=("Segoe UI", 17, "bold"),
                    text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                    anchor="w",
                ).grid(row=0, column=1, sticky="ew")
                ctk.CTkLabel(
                    header,
                    text=description,
                    font=("Segoe UI", 12),
                    text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                    anchor="w",
                    justify="left",
                    wraplength=820,
                ).grid(row=1, column=1, sticky="ew", pady=(2, 0))

                list_frame = ctk.CTkFrame(category, fg_color="transparent")
                list_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
                list_frame.grid_columnconfigure((0, 1), weight=1)

                for guide_idx, guide_name in enumerate(guides):
                    guide_button = ctk.CTkButton(
                        list_frame,
                        text=guide_name,
                        height=40,
                        corner_radius=8,
                        border_width=1,
                        border_color=(self.colors["border_light"], self.colors["border_dark"]),
                        fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                        hover_color=self.colors["sidebar_hover"],
                        text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                        font=("Segoe UI", 12, "bold"),
                        anchor="w",
                        command=lambda guide_name=guide_name: self.open_guide_pdf(guide_name),
                    )
                    guide_button.grid(
                        row=guide_idx // 2,
                        column=guide_idx % 2,
                        sticky="ew",
                        padx=(0, 8) if guide_idx % 2 == 0 else (8, 0),
                        pady=5,
                    )
                    self._track_skin_widget(guide_button, "guide_button")

        self._build_adaptive_page(f, populate)

    def _build_security_view(self):
        f = self.frames["Security"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)

            self._page_title(
                page,
                "Seguridad",
                "Accesos reservados para endurecimiento, firewall y auditoria del sistema.",
            )

            self._action_card(
                page, 2, 0, "FW", "Firewall",
                "Activa, desactiva y revisa el estado de Windows Firewall.",
                lambda: self.show_frame("Firewall"),
                "#B42318",
            )
            self._action_card(
                page, 2, 1, "AUD", "Auditoria",
                "Acceso reservado para futuras tareas de auditoria y registro de seguridad.",
                lambda: self._show_not_implemented("Auditoria"),
                "#7C3AED",
            )

        self._build_adaptive_page(f, populate)

    def _build_firewall_view(self):
        f = self.frames["Firewall"]

        def populate(page):
            page.grid_columnconfigure((0, 1), weight=1)

            self._page_title(
                page,
                "Firewall",
                "Gestiona Windows Firewall en los perfiles Domain, Private y Public.",
            )

            self._action_card(
                page, 2, 0, "OFF", "Desactivar firewall",
                "Desactiva Windows Firewall en los perfiles Domain, Private y Public.",
                self.pre_task_disable_windows_firewall,
                "#B42318",
            )
            self._action_card(
                page, 2, 1, "ON", "Activar firewall",
                "Activa Windows Firewall en los perfiles Domain, Private y Public.",
                lambda: self.iniciar_tarea(self.task_enable_windows_firewall),
                self.colors["accent"],
            )

        self._build_adaptive_page(f, populate)

    def _build_guide_view(self):
        f = self.frames["Guide"]

        def populate(page):
            page.grid_columnconfigure(0, weight=1)
            selected_guide_tab = getattr(self, "_guide_active_tab", "Inicio")

            self._page_title(
                page,
                "Guía rápida",
                "Manual práctico para usar Easy Deploy con seguridad y orden.",
            )

            def add_block(parent, row, title, body, accent=None):
                item = ctk.CTkFrame(
                    parent,
                    fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                    border_width=1,
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                    corner_radius=8,
                )
                item.grid(row=row, column=0, padx=8, pady=3, sticky="ew")
                item.grid_columnconfigure(1, weight=1)
                self._track_skin_widget(item, "card")
                if accent:
                    accent_bar = ctk.CTkFrame(item, width=4, fg_color=accent, corner_radius=3)
                    accent_bar.grid(
                        row=0, column=0, rowspan=2, padx=(0, 8), pady=6, sticky="nsw"
                    )
                    bar_role = "warning_bar" if accent == self.colors["warning"] else "accent_bar"
                    self._track_skin_widget(accent_bar, bar_role)
                title_label = ctk.CTkLabel(
                    item,
                    text=title,
                    font=("Segoe UI", 14, "bold"),
                    anchor="w",
                    text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                )
                title_label.grid(
                    row=0, column=1, padx=(8, 14), pady=(6, 0), sticky="ew"
                )
                self._track_skin_widget(title_label, "primary_text")
                body_label = ctk.CTkLabel(
                    item,
                    text=body,
                    font=("Segoe UI", 13),
                    text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                    anchor="w",
                    justify="left",
                    wraplength=900,
                )
                body_label.grid(row=1, column=1, padx=(8, 14), pady=(0, 6), sticky="ew")
                self._track_skin_widget(body_label, "secondary_text")
                return item

            tab_heights = {}
            guide_tab_height = {"value": 300}

            def estimate_tab_height(blocks):
                estimated = 70
                for _title, body in blocks:
                    text_len = len(str(body or ""))
                    line_count = max(1, (text_len // 90) + 1)
                    estimated += 36 + (line_count * 17)
                return max(300, estimated)

            def request_guide_reflow():
                return

            def adjust_tab_height():
                try:
                    active_tab = tabs.get()
                    self._guide_active_tab = active_tab
                    request_guide_reflow()
                except Exception:
                    pass

            tabs = ctk.CTkTabview(
                page,
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                segmented_button_selected_color=self.colors["accent"],
                segmented_button_selected_hover_color=self.colors["accent_hover"],
                segmented_button_unselected_color=(self.colors["card_light"], self.colors["card_dark"]),
                segmented_button_unselected_hover_color=self.colors["sidebar_hover"],
                text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                corner_radius=8,
                border_width=1,
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                height=guide_tab_height["value"],
                command=adjust_tab_height,
            )
            tabs.grid(row=2, column=0, padx=8, pady=(0, 10), sticky="ew")
            self._track_skin_widget(tabs, "guide_tabs")

            tab_data = {
                "Inicio": [
                    (
                        "Qué revisar al abrir",
                        "Comprueba las tarjetas superiores: Privilegios, Recursos, Logs y Teclado ESP. "
                        "Si alguna aparece en naranja, pulsa sobre ella para corregir o revisar el estado antes de iniciar tareas.",
                    ),
                    (
                        "Accesos rápidos",
                        "Desde Inicio puedes revisar el entorno, ver roles instalados, abrir Top procesos y lanzar Ping. "
                        "También puedes abrir Recursos, Logs, Disk Management o cambiar el teclado pulsando sus tarjetas.",
                    ),
                    (
                        "Antes de desplegar",
                        "Confirma que tienes red correcta, DNS apuntando donde toca, recursos presentes y permisos de administrador. "
                        "Si falta alguno, corrígelo antes de ejecutar tareas largas.",
                    ),
                ],
                "Sistemas": [
                    (
                        "Qué contiene",
                        "Aquí están Controlador de dominio, Sincronizar hora, KMS, SQL Server, JCHAT/Openfire, Exchange, SharePoint y Skype for Business.",
                    ),
                    (
                        "Cómo se usan las funciones",
                        "Pulsa la tarjeta completa de la tarea. Algunas abrirán un submenú, como Dominio o Exchange, y otras ejecutarán directamente la tarea en la consola.",
                    ),
                    (
                        "Datos que puede pedir",
                        "La app puede solicitar dominio, usuario administrador, contraseña, nombre NetBIOS, Organization Name, IP de KMS o rutas detectadas. "
                        "Escribe los datos exactamente como los usarías en Windows o PowerShell.",
                    ),
                    (
                        "Durante una instalación",
                        "No cierres la app mientras una tarea está en curso. Revisa la barra de progreso y la consola. "
                        "Si aparece Cancelar, úsalo solo si sabes que la tarea puede interrumpirse sin dejar la instalación a medias.",
                    ),
                ],
                "Redes": [
                    (
                        "Switch y Router",
                        "Redes abre consolas integradas para Switch Allied, Switch Cisco y Router con comandos adaptados a cada dispositivo.",
                    ),
                    (
                        "Entrada por consola",
                        "Cuando el programa espere una selección, escribe en el campo inferior y pulsa Enviar o Enter. "
                        "Si necesitas salir de esa herramienta, usa Cancelar junto al botón Enviar.",
                    ),
                    (
                        "Cambiar entre herramientas",
                        "Si tienes Switch Allied, Switch Cisco o Router abierto y quieres usar otra herramienta, cancela primero el proceso activo. La app evita lanzar dos programas interactivos a la vez.",
                    ),
                ],
                "Recursos": [
                    (
                        "Carpeta crítica",
                        "No renombres, borres ni muevas la carpeta de recursos que contiene EXCHANGE, SHAPRE, SQL y JCHAT. "
                        "Easy Deploy la usa para localizar instaladores, ISOs y prerrequisitos.",
                    ),
                    (
                        "Medios externos",
                        "Para Exchange o SQL puede ser necesario tener montada la ISO o insertado el medio correcto. "
                        "Si la app no detecta Setup.exe, revisa la unidad o monta la imagen antes de repetir.",
                    ),
                    (
                        "Logs",
                        "Cada tarea genera un log en LOCALAPPDATA\\EasyDeploy\\logs. Si algo falla, abre Logs desde Inicio y revisa el archivo más reciente.",
                    ),
                ],
                "Consola": [
                    (
                        "Qué muestra",
                        "La consola enseña salida en directo, pasos, avisos, errores y la ruta del log actual. "
                        "Sirve para entender qué está haciendo la tarea y en qué punto ha terminado.",
                    ),
                    (
                        "Interacción",
                        "Algunas tareas piden datos mediante ventanas y otras mediante la consola integrada. "
                        "Cuando el campo inferior esté activo, introduce la respuesta y pulsa Enviar.",
                    ),
                    (
                        "Reinicios",
                        "Si aparece Reiniciar sistema al terminar, úsalo cuando proceda. En cambios de dominio, roles o licenciamiento, reiniciar suele ser parte normal del proceso.",
                    ),
                ],
                "Seguridad": [
                    (
                        "Firewall",
                        "El apartado Seguridad incluye acciones para activar o desactivar Windows Firewall en los perfiles Domain, Private y Public. "
                        "Usa Desactivar firewall solo en redes controladas y durante pruebas concretas.",
                    ),
                    (
                        "Indicador de Inicio",
                        "La tarjeta Firewall de Inicio se pone verde solo si los tres perfiles estan activados. "
                        "Si alguno esta apagado, la tarjeta aparece en rojo para avisar antes de continuar con despliegues.",
                    ),
                    (
                        "Buenas practicas",
                        "Antes de desactivar firewall, confirma conectividad, permisos de administrador y politicas de dominio. "
                        "Despues de una prueba, vuelve a activarlo desde Seguridad y comprueba que el estado queda en Firewall OK.",
                    ),
                    (
                        "Auditoria",
                        "La tarjeta Auditoria queda preparada para futuras comprobaciones de registro y seguridad. "
                        "Cuando se implemente, deberia usarse para revisar eventos, cambios relevantes y trazas de administracion.",
                    ),
                ],
                "Errores": [
                    (
                        "No aparece Admin OK",
                        "Cierra Easy Deploy y vuelve a abrirlo con Ejecutar como administrador. "
                        "Comprueba con: whoami /groups | findstr /i \"S-1-5-32-544\"",
                    ),
                    (
                        "Recursos no encontrados",
                        "Pulsa Recursos en Inicio y revisa que existan EXCHANGE, SHAPRE, SQL o JCHAT. "
                        "No cambies el nombre de la carpeta principal ni muevas ISOs mientras la app está abierta.",
                    ),
                    (
                        "Unión a dominio falla",
                        "Si el ping falla, revisa red y DNS. Pruebas rápidas: ipconfig /all, ping DOMINIO, nslookup DOMINIO. "
                        "Si el ping funciona, revisa duplicidad del nombre del equipo en DNS o Active Directory.",
                    ),
                    (
                        "Sincronizar hora no encuentra DC",
                        "Revisa que el equipo resuelva y alcance un controlador de dominio. Prueba: nltest /dsgetdc:TU_DOMINIO, "
                        "w32tm /query /source y w32tm /resync /rediscover.",
                    ),
                    (
                        "Forzar políticas no aplica",
                        "Comprueba conectividad con el DC y DNS del dominio. Prueba manual: gpupdate /force y después gpresult /r "
                        "para ver qué GPO se aplican al usuario y al equipo.",
                    ),
                    (
                        "Switch o Router no detecta puerto COM",
                        "Conecta el cable consola antes de abrir la herramienta. Revisa drivers USB/Serial en Administrador de dispositivos. "
                        "Prueba en PowerShell: [System.IO.Ports.SerialPort]::getportnames()",
                    ),
                    (
                        "Switch o Router queda bloqueado",
                        "Solo puede haber una herramienta interactiva abierta. Usa Cancelar junto a Enviar, desconecta/reconecta el cable consola "
                        "y vuelve a lanzar Switch o Router.",
                    ),
                    (
                        "KMS no activa",
                        "Comprueba edición y estado con slmgr /dlv. Revisa servidor KMS con slmgr /skms IP_O_HOSTNAME y lanza slmgr /ato. "
                        "Si acabas de convertir Evaluation, reinicia Windows antes de activar.",
                    ),
                    (
                        "Exchange Prepare Schema falla",
                        "Verifica permisos Schema Admins/Enterprise Admins, conectividad con el dominio y que Setup.exe sea del medio correcto. "
                        "Prueba: ping DOMINIO y netdom query fsmo.",
                    ),
                    (
                        "SQL o Exchange no encuentra instalador",
                        "Monta la ISO o inserta el medio antes de ejecutar la tarea. Revisa la letra de unidad y que exista Setup.exe en la raíz esperada.",
                    ),
                    (
                        "La app parece congelada",
                        "Algunos instaladores tardan sin imprimir salida. Espera unos minutos, mira Top procesos y revisa el log actual antes de cerrar.",
                    ),
                    (
                        "Teclado, región u hora incorrectos",
                        "Usa Teclado ESP desde Inicio y Sincronizar hora desde Sistemas. Comprueba región con intl.cpl y hora con timedate.cpl.",
                    ),
                ],
            }

            for tab_name, blocks in tab_data.items():
                tab_heights[tab_name] = estimate_tab_height(blocks)
            guide_tab_height["value"] = max(tab_heights.values()) if tab_heights else 300
            tabs.configure(height=guide_tab_height["value"])

            for tab_name, blocks in tab_data.items():
                tab = tabs.add(tab_name)
                tab.configure(fg_color=(self.colors["panel_light"], self.colors["panel_dark"]))
                tab.grid_columnconfigure(0, weight=1)
                self._track_skin_widget(tab, "guide_tab")
                accent = self.colors["warning"] if tab_name == "Errores" else self.colors["accent"]
                for idx, (title, body) in enumerate(blocks):
                    add_block(tab, idx, title, body, accent)

            if selected_guide_tab in tab_data:
                tabs.set(selected_guide_tab)
            adjust_tab_height()

        self._build_adaptive_page(f, populate)

    def _default_update_url(self):
        return "https://www.dropbox.com/scl/fi/p8qbe0fzn17nk7qdah75x/update.json?rlkey=7yb1odpc9aptdrek0mk7iafgk&st=3yg87fc3&dl=1"

    def _update_settings_path(self):
        return os.path.join(SysUtils.app_data_dir(), "update_settings.json")

    def _updates_dir(self):
        path = os.path.join(SysUtils.app_data_dir(), "updates")
        os.makedirs(path, exist_ok=True)
        return path

    def _load_update_settings(self):
        default_data = {"url": self._default_update_url()}
        try:
            with open(self._update_settings_path(), "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                url = str(data.get("url") or "").strip()
                if url:
                    return {"url": url}
        except Exception:
            pass
        return default_data

    def _save_update_settings(self, url=None):
        next_url = str(url if url is not None else self._default_update_url()).strip()
        try:
            with open(self._update_settings_path(), "w", encoding="utf-8") as handle:
                json.dump({"url": next_url}, handle, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _normalize_dropbox_download_url(self, url):
        text = str(url or "").strip()
        if not text:
            return ""
        parsed = urllib.parse.urlparse(text)
        if parsed.scheme not in {"http", "https"}:
            return text
        if "dropbox.com" not in parsed.netloc.lower():
            return text
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(key, value) for key, value in query if key.lower() not in {"dl", "raw"}]
        filtered.append(("dl", "1"))
        return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(filtered)))

    def _compare_versions(self, remote_version, local_version=None):
        def parts(value):
            found = re.findall(r"\d+", str(value or ""))
            return [int(item) for item in found] if found else [0]

        remote = parts(remote_version)
        local = parts(local_version or APP_VERSION)
        length = max(len(remote), len(local))
        remote.extend([0] * (length - len(remote)))
        local.extend([0] * (length - len(local)))
        if remote > local:
            return 1
        if remote < local:
            return -1
        return 0

    def _is_http_url(self, url):
        try:
            return urllib.parse.urlparse(str(url or "").strip()).scheme in {"http", "https"}
        except Exception:
            return False

    def _safe_update_filename(self, filename, version):
        clean = os.path.basename(str(filename or "").strip())
        clean = re.sub(r"[^A-Za-z0-9_. -]+", "_", clean).strip(" .")
        if not clean:
            clean = f"EasyDeploy_Setup_v{str(version or APP_VERSION).lstrip('vV')}.exe"
        if not clean.lower().endswith(".exe"):
            clean += ".exe"
        return clean

    def _set_update_status(self, text, tone="info"):
        label = getattr(self, "update_status_label", None)
        if not self._widget_exists(label):
            return
        color = {
            "success": self.colors["success"],
            "warning": self.colors["warning"],
            "danger": self.colors["danger"],
            "info": self.colors["info"],
        }.get(tone, self.colors["info"])
        label.configure(text=text, text_color=color)

    def _set_update_busy(self, busy, text=None):
        button = getattr(self, "update_check_button", None)
        if self._widget_exists(button):
            button.configure(state="disabled" if busy else "normal", text=text or ("Buscando..." if busy else "Comprobar"))

    def _set_update_remote_info(self, version="-", notes=None):
        remote_label = getattr(self, "update_remote_version_label", None)
        notes_label = getattr(self, "update_notes_label", None)
        if self._widget_exists(remote_label):
            remote_label.configure(text=f"Versión remota: {version or '-'}")
        if self._widget_exists(notes_label):
            note_items = notes if isinstance(notes, list) else []
            note_text = "\n".join(f"- {item}" for item in note_items if str(item).strip())
            notes_label.configure(text=note_text or "Notas: sin notas publicadas.")

    def _fetch_update_json(self, url):
        direct_url = self._normalize_dropbox_download_url(url)
        request = urllib.request.Request(direct_url, headers={"User-Agent": f"EasyDeploy/{APP_VERSION}"})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(1024 * 1024)
        return json.loads(raw.decode("utf-8-sig"))

    def _check_for_updates(self):
        entry = getattr(self, "update_url_entry", None)
        update_url = entry.get().strip() if self._widget_exists(entry) else ""
        if not update_url:
            self.ui_showwarning("Actualizar", "Indica la ruta del endpoint update.json antes de comprobar actualizaciones.")
            return
        if not self._is_http_url(update_url):
            self.ui_showerror("Actualizar", "La ruta del update.json debe empezar por http:// o https://.")
            return

        self._save_update_settings(update_url)
        self._set_update_busy(True)
        self._set_update_status("Conectando con el servidor de actualizaciones...", "info")
        self._set_update_remote_info("-", [])

        def worker():
            try:
                data = self._fetch_update_json(update_url)
                if not isinstance(data, dict):
                    raise ValueError("El endpoint no ha devuelto un objeto JSON válido.")
                remote_version = str(data.get("version") or "").strip()
                installer_url = str(data.get("url") or data.get("downloadUrl") or data.get("download_url") or "").strip()
                if not remote_version:
                    raise ValueError("El JSON de actualización no contiene el campo obligatorio version.")
                if self._compare_versions(remote_version, APP_VERSION) <= 0:
                    self.after(0, lambda: self._handle_update_current(remote_version, data))
                    return
                if not installer_url:
                    raise ValueError("El JSON de actualización no contiene url/downloadUrl del instalador.")
                self.after(0, lambda: self._handle_update_available(data, remote_version, installer_url))
            except Exception as exc:
                self.after(0, lambda exc=exc: self._handle_update_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_update_current(self, remote_version, data):
        notes = data.get("notes") if isinstance(data.get("notes"), list) else data.get("cambios")
        self._set_update_busy(False)
        self._set_update_remote_info(remote_version, notes if isinstance(notes, list) else [])
        self._set_update_status(f"Easy Deploy está actualizado. Versión local: {APP_VERSION}.", "success")

    def _handle_update_available(self, data, remote_version, installer_url):
        notes = data.get("notes") if isinstance(data.get("notes"), list) else data.get("cambios")
        notes = notes if isinstance(notes, list) else []
        self._set_update_busy(False)
        self._set_update_remote_info(remote_version, notes)
        self._set_update_status(f"Nueva versión disponible: {remote_version}.", "warning")
        note_text = "\n".join(f"- {item}" for item in notes[:6]) if notes else "Sin notas publicadas."
        if not self.ui_askyesno(
            "Actualización disponible",
            "Hay una nueva versión de Easy Deploy.\n\n"
            f"Versión local: {APP_VERSION}\n"
            f"Versión remota: {remote_version}\n\n"
            f"{note_text}\n\n"
            "Se descargará el instalador y Easy Deploy se cerrará para aplicar la actualización.\n\n"
            "¿Quieres continuar?",
        ):
            self._set_update_status("Actualización disponible. Descarga cancelada por el usuario.", "warning")
            return
        self._download_update_installer(data, remote_version, installer_url)

    def _handle_update_error(self, exc):
        self._set_update_busy(False)
        self._set_update_status("No se pudo comprobar la actualización.", "danger")
        self.ui_showerror("Actualizar", f"No se pudo comprobar la actualización.\n\nDetalle: {exc}")

    def _download_update_installer(self, data, remote_version, installer_url):
        direct_url = self._normalize_dropbox_download_url(installer_url)
        parsed = urllib.parse.urlparse(direct_url)
        if parsed.scheme not in {"http", "https"}:
            self.ui_showerror("Actualizar", "La URL del instalador debe empezar por http:// o https://.")
            return
        if not parsed.path.lower().endswith(".exe"):
            self.ui_showerror("Actualizar", "Por seguridad, solo se permite descargar instaladores .exe.")
            return

        filename = self._safe_update_filename(data.get("filename") or os.path.basename(parsed.path), remote_version)
        target_path = os.path.join(self._updates_dir(), filename)
        expected_sha = str(data.get("sha256") or "").strip().lower()
        self._set_update_busy(True, "Descargando...")
        self._set_update_status("Descargando instalador de actualización...", "info")

        def worker():
            try:
                request = urllib.request.Request(direct_url, headers={"User-Agent": f"EasyDeploy/{APP_VERSION}"})
                digest = hashlib.sha256()
                with urllib.request.urlopen(request, timeout=120) as response, open(target_path, "wb") as handle:
                    total = int(response.headers.get("content-length") or 0)
                    downloaded = 0
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        handle.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            progress = min(100, int(downloaded * 100 / total))
                            self.after(0, lambda progress=progress: self._set_update_status(f"Descargando instalador... {progress}%", "info"))
                if expected_sha and digest.hexdigest().lower() != expected_sha:
                    try:
                        os.remove(target_path)
                    except Exception:
                        pass
                    raise ValueError("La verificación SHA256 no coincide. No se ejecutará el instalador.")
                self.after(0, lambda: self._launch_downloaded_update(target_path))
            except Exception as exc:
                self.after(0, lambda exc=exc: self._handle_update_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _launch_downloaded_update(self, installer_path):
        update_dir = os.path.abspath(self._updates_dir())
        installer_path = os.path.abspath(installer_path)
        if not installer_path.lower().startswith(update_dir.lower() + os.sep):
            self._set_update_busy(False)
            self.ui_showerror("Actualizar", "El instalador descargado no está en la carpeta segura de actualizaciones.")
            return
        if not os.path.exists(installer_path) or not installer_path.lower().endswith(".exe"):
            self._set_update_busy(False)
            self.ui_showerror("Actualizar", "No se encontró un instalador .exe válido para ejecutar.")
            return

        helper_path = os.path.join(update_dir, f"easydeploy_update_{os.getpid()}.cmd")
        script = "\r\n".join(
            [
                "@echo off",
                "setlocal",
                "timeout /t 2 /nobreak >nul",
                f'start "" /wait "{installer_path}"',
                "for /l %%i in (1,1,20) do (",
                f'  del /f /q "{installer_path}" >nul 2>nul && goto cleanup',
                "  timeout /t 2 /nobreak >nul",
                ")",
                ":cleanup",
                'del /f /q "%~f0" >nul 2>nul',
            ]
        )
        with open(helper_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(script)

        self._set_update_status("Instalador listo. Easy Deploy se cerrará para aplicar la actualización.", "success")
        self.ui_showinfo(
            "Instalar actualización",
            "El instalador se ha descargado correctamente.\n\n"
            "Al aceptar, Easy Deploy se cerrará y se abrirá el instalador. "
            "Cuando termine, el archivo descargado se eliminará automáticamente.",
        )
        try:
            flags = 0
            for attr in ("CREATE_NO_WINDOW", "DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
                flags |= getattr(subprocess, attr, 0)
            subprocess.Popen(["cmd.exe", "/c", helper_path], creationflags=flags)
        except Exception as exc:
            self._set_update_busy(False)
            self.ui_showerror("Actualizar", f"No se pudo lanzar el instalador.\n\nDetalle: {exc}")
            return
        self.after(250, self.destroy)

    def _save_update_endpoint_from_ui(self):
        entry = getattr(self, "update_url_entry", None)
        update_url = entry.get().strip() if self._widget_exists(entry) else ""
        if not update_url:
            self.ui_showwarning("Actualizar", "Indica una ruta de update.json antes de guardar.")
            return
        if not self._is_http_url(update_url):
            self.ui_showerror("Actualizar", "La ruta del update.json debe empezar por http:// o https://.")
            return
        if self._save_update_settings(update_url):
            self._set_update_status("Ruta de actualización guardada.", "success")
        else:
            self.ui_showerror("Actualizar", "No se pudo guardar la ruta de actualización.")

    def _build_update_view(self):
        f = self.frames["Update"]

        def populate(page):
            page.grid_columnconfigure(0, weight=1)
            settings = self._load_update_settings()

            self._page_title(
                page,
                "Actualizar",
                "Comprueba nuevas versiones desde un endpoint update.json y aplica el instalador publicado.",
            )

            card = ctk.CTkFrame(
                page,
                fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                border_width=1,
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                corner_radius=10,
            )
            card.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 12))
            card.grid_columnconfigure(0, weight=1)
            self._track_skin_widget(card, "card")

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 12))
            header.grid_columnconfigure(1, weight=1)

            icon_box = ctk.CTkFrame(header, width=40, height=40, fg_color=self.colors["sidebar_active"], corner_radius=9)
            icon_box.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="w")
            icon_box.grid_propagate(False)
            self._track_skin_widget(icon_box, "accent_box")
            icon_label = ctk.CTkLabel(icon_box, text="â†»", font=("Segoe UI", 18, "bold"), text_color=self.colors["accent"])
            icon_label.pack(fill="both", expand=True)
            self._track_skin_widget(icon_label, "accent_text")

            ctk.CTkLabel(
                header,
                text="Actualizar Aplicación",
                font=("Segoe UI", 15, "bold"),
                anchor="w",
                text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
            ).grid(row=0, column=1, sticky="ew")
            ctk.CTkLabel(
                header,
                text="actualizador automático",
                font=("Consolas", 11),
                anchor="w",
                text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
            ).grid(row=1, column=1, sticky="ew", pady=(2, 0))

            self.update_check_button = ctk.CTkButton(
                header,
                text="Comprobar",
                width=122,
                height=34,
                corner_radius=8,
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                command=self._check_for_updates,
            )
            self.update_check_button.grid(row=0, column=2, rowspan=2, padx=(14, 0), sticky="e")
            self._track_skin_widget(self.update_check_button, "primary_button")

            info = ctk.CTkFrame(
                card,
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_width=1,
                border_color=self.colors["accent"],
                corner_radius=9,
            )
            info.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))
            info.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(info, text="i", width=24, font=("Segoe UI", 13, "bold"), text_color=self.colors["accent"]).grid(
                row=0, column=0, padx=(12, 8), pady=12, sticky="nw"
            )
            ctk.CTkLabel(
                info,
                text=(
                    "Las actualizaciones del programa pueden incorporar mejoras de estabilidad, seguridad, rendimiento "
                    "y nuevas funciones. Cuando haya una versión disponible, Easy Deploy descargará el instalador, "
                    "cerrará la aplicación para aplicarla y conservará los datos locales durante el proceso."
                ),
                font=("Segoe UI", 11),
                text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                anchor="w",
                justify="left",
                wraplength=890,
            ).grid(row=0, column=1, padx=(0, 12), pady=12, sticky="ew")

            ctk.CTkLabel(
                card,
                text="RUTA DEL ENDPOINT UPDATE.JSON",
                font=("Consolas", 10, "bold"),
                text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
                anchor="w",
            ).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 5))

            route_row = ctk.CTkFrame(card, fg_color="transparent")
            route_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 7))
            route_row.grid_columnconfigure(0, weight=1)
            self.update_url_entry = ctk.CTkEntry(
                route_row,
                height=36,
                corner_radius=8,
                font=("Consolas", 11, "bold"),
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
            )
            self.update_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            self.update_url_entry.insert(0, settings.get("url", self._default_update_url()))

            ctk.CTkButton(
                route_row,
                text="Guardar ruta",
                width=130,
                height=36,
                corner_radius=8,
                fg_color=self.colors["secondary"],
                hover_color=self.colors["secondary_hover"],
                command=self._save_update_endpoint_from_ui,
            ).grid(row=0, column=1, sticky="e")

            ctk.CTkLabel(
                card,
                text="Dirección de consulta del actualizador para comprobar nuevas versiones del programa.",
                font=("Segoe UI", 10),
                text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
                anchor="w",
            ).grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 16))

            status_panel = ctk.CTkFrame(
                card,
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_width=1,
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                corner_radius=9,
            )
            status_panel.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
            status_panel.grid_columnconfigure(0, weight=1)
            self._track_skin_widget(status_panel, "card")

            self.update_local_version_label = ctk.CTkLabel(
                status_panel,
                text=f"Versión local: {APP_VERSION}",
                font=("Consolas", 11, "bold"),
                anchor="w",
            )
            self.update_local_version_label.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
            self.update_remote_version_label = ctk.CTkLabel(
                status_panel,
                text="Versión remota: -",
                font=("Consolas", 11),
                text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                anchor="w",
            )
            self.update_remote_version_label.grid(row=1, column=0, sticky="ew", padx=14, pady=2)
            self.update_status_label = ctk.CTkLabel(
                status_panel,
                text="Estado: pendiente de comprobación.",
                font=("Segoe UI", 11, "bold"),
                text_color=self.colors["info"],
                anchor="w",
                justify="left",
                wraplength=900,
            )
            self.update_status_label.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 2))
            self.update_notes_label = ctk.CTkLabel(
                status_panel,
                text="Notas: sin notas cargadas.",
                font=("Segoe UI", 11),
                text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                anchor="w",
                justify="left",
                wraplength=900,
            )
            self.update_notes_label.grid(row=3, column=0, sticky="ew", padx=14, pady=(2, 12))

        self._build_adaptive_page(f, populate)

    def _build_versions_view(self):
        if getattr(self, "_versions_view_built", False):
            return
        from ..changelog import CHANGELOG

        f = self.frames["Versions"]

        def populate(page):
            page.grid_columnconfigure(0, weight=1)
            self._page_title(
                page,
                "Historial de versiones",
                "Cambios publicados de Easy Deploy, ordenados de más reciente a más antiguo.",
            )

            for row, entry in enumerate(CHANGELOG, start=2):
                if len(entry) == 3:
                    version, date, changes = entry
                else:
                    version, changes = entry
                    date = ""

                latest = row == 2
                version_text = str(version)
                if not version_text.lower().startswith("v"):
                    version_text = f"v{version_text}"

                card = ctk.CTkFrame(
                    page,
                    fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                    border_width=1,
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                    corner_radius=8,
                )
                card.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 10))
                card.grid_columnconfigure(0, weight=1)
                self._track_skin_widget(card, "card")

                accent_bar = ctk.CTkFrame(
                    card,
                    height=4,
                    fg_color=self.colors["accent"],
                    corner_radius=3,
                )
                accent_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
                self._track_skin_widget(accent_bar, "accent_bar")

                header = ctk.CTkFrame(card, fg_color="transparent")
                header.grid(row=1, column=0, sticky="ew", padx=16, pady=(14, 8))
                header.grid_columnconfigure(2, weight=1)

                version_label = ctk.CTkLabel(
                    header,
                    text=version_text,
                    font=("Segoe UI", 15, "bold"),
                    text_color="white",
                    fg_color=self.colors["accent"],
                    padx=10,
                    pady=3,
                    corner_radius=8,
                )
                version_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
                self._track_skin_widget(version_label, "accent_bar")

                if latest:
                    latest_label = ctk.CTkLabel(
                        header,
                        text="Más reciente",
                        font=("Segoe UI", 11, "bold"),
                        text_color=self.colors["accent"],
                    )
                    latest_label.grid(row=0, column=1, sticky="w", padx=(0, 8))
                    self._track_skin_widget(latest_label, "accent_text")

                date_label = ctk.CTkLabel(
                    header,
                    text=date or "Sin fecha",
                    font=("Segoe UI", 11),
                    text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                    anchor="e",
                )
                date_label.grid(row=0, column=3, sticky="e")
                self._track_skin_widget(date_label, "secondary_text")

                count_label = ctk.CTkLabel(
                    header,
                    text=f"{len(changes)} cambios",
                    font=("Segoe UI", 11),
                    text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
                    anchor="w",
                )
                count_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
                self._track_skin_widget(count_label, "secondary_text")

                changes_label = ctk.CTkLabel(
                    card,
                    text="\n".join(f"- {change}" for change in changes),
                    font=("Segoe UI", 12),
                    text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
                    justify="left",
                    anchor="w",
                    wraplength=940,
                )
                changes_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
                self._track_skin_widget(changes_label, "primary_text")

        self._build_adaptive_page(f, populate, initial_mode="scroll")
        self._versions_view_built = True

    def _build_console_view(self):
        f = self.frames["Console"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(3, weight=1)

        self._page_title(
            f,
            "Consola de ejecución",
            "Salida en directo y registro persistente",
            action_text="Abrir logs",
            action_command=self._accion_abrir_logs,
        )

        progress_panel = ctk.CTkFrame(
            f,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=8,
        )
        progress_panel.grid(row=2, column=0, sticky="ew", padx=2, pady=(0, 12))
        progress_panel.grid_columnconfigure(0, weight=1)
        self._track_skin_widget(progress_panel, "card")

        progress_accent = ctk.CTkFrame(progress_panel, height=4, fg_color=self.colors["accent"], corner_radius=3)
        progress_accent.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 0))
        self._track_skin_widget(progress_accent, "accent_bar")

        progress_header = ctk.CTkFrame(progress_panel, fg_color="transparent")
        progress_header.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 6))
        progress_header.grid_columnconfigure(0, weight=1)
        progress_title = ctk.CTkLabel(
            progress_header,
            text="Estado de ejecución",
            font=("Segoe UI", 13, "bold"),
            text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
            anchor="w",
        )
        progress_title.grid(row=0, column=0, sticky="w")
        self._track_skin_widget(progress_title, "primary_text")

        self.progress_bar = ctk.CTkProgressBar(progress_panel, progress_color=self.colors["accent"])
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.progress_bar.set(0)
        self.lbl_percent = ctk.CTkLabel(
            progress_panel,
            text="0%",
            font=("Segoe UI", 12, "bold"),
            fg_color=self.colors["sidebar_active"],
            text_color=self.colors["accent"],
            corner_radius=8,
            width=58,
        )
        self.lbl_percent.grid(row=2, column=1, padx=(0, 16), pady=(0, 8), sticky="e")
        self._track_skin_widget(self.lbl_percent, "accent_box")
        self.lbl_log_path = ctk.CTkLabel(
            progress_panel,
            text="Los registros se guardarán automáticamente al iniciar una tarea.",
            font=("Segoe UI", 11),
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            text_color=(self.colors["text_secondary_light"], self.colors["text_secondary_dark"]),
            corner_radius=8,
            padx=10,
            pady=5,
            anchor="w",
            wraplength=760,
        )
        self.lbl_log_path.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
        self._track_skin_widget(self.lbl_log_path, "console_chip")

        self.console_text = ctk.CTkTextbox(
            f,
            font=("Consolas", 12),
            corner_radius=8,
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            fg_color=("#F8F7F2", "#101114"),
            text_color=(self.colors["text_primary_light"], "#DDE6E8"),
        )
        self.console_text.grid(row=3, column=0, sticky="nsew", padx=2, pady=(0, 4))
        self.console_text.configure(state="disabled")
        self._track_skin_widget(self.console_text, "terminal_text")
        self._configure_console_tags()

        self.console_input_var = ctk.StringVar()
        self.console_input_frame = ctk.CTkFrame(
            f,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=8,
        )
        self.console_input_frame.grid(row=4, column=0, sticky="ew", padx=2, pady=(8, 2))
        self.console_input_frame.grid_columnconfigure(0, weight=1)
        self._track_skin_widget(self.console_input_frame, "card")
        self.console_input = ctk.CTkEntry(
            self.console_input_frame,
            textvariable=self.console_input_var,
            height=38,
            font=("Consolas", 12),
            placeholder_text="La entrada se activara con las herramientas interactivas.",
            fg_color=("#F8F7F2", "#121417"),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=8,
        )
        self.console_input.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=10)
        self._track_skin_widget(self.console_input, "console_input")
        self.console_input.bind("<Return>", self._send_console_input)
        self.console_send_button = ctk.CTkButton(
            self.console_input_frame,
            text="Enviar",
            width=92,
            height=38,
            corner_radius=8,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=self._send_console_input,
        )
        self.console_send_button.grid(row=0, column=1, padx=(0, 8), pady=10)
        self._track_skin_widget(self.console_send_button, "primary_button")
        self.console_cancel_button = ctk.CTkButton(
            self.console_input_frame,
            text="Cancelar",
            width=98,
            height=38,
            corner_radius=8,
            fg_color=self.colors["danger"],
            hover_color="#8F1D14",
            command=self._cancel_console_program,
        )
        self.console_cancel_button.grid(row=0, column=2, padx=(0, 12), pady=10)
        self._track_skin_widget(self.console_cancel_button, "danger_button")
        self.console_com_buttons_frame = ctk.CTkFrame(self.console_input_frame, fg_color="transparent")
        self.console_com_buttons_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 10))
        self.console_com_buttons_frame.grid_remove()
        self.console_input_queue = None
        self.console_input_sensitive = False
        self._set_console_input_enabled(False)

    def mostrar_splash(self):
        self.show_frame("Selection")
        self.deiconify()
        self.after(180, self._show_startup_warnings)

    def _schedule_frame_reflow(self, name):
        return

    def show_frame(self, name):
        if name not in self.frames:
            name = "Selection"
        if hasattr(self, "tools_drawer") and self.tools_drawer.winfo_exists():
            self.tools_drawer.place_forget()
        for frame_name, frame in self.frames.items():
            if frame_name == name:
                frame.grid(row=0, column=0, sticky="nsew")
                frame.tkraise()
            else:
                frame.grid_remove()
        self.current_frame_name = name
        self._set_active_nav(name)
        autohide = getattr(self.frames[name], "_easydeploy_scrollbar_autohide", None)
        if autohide:
            autohide(delay=80)

        titles = {
            "Selection": ("", ""),
            "Menu": ("Sistemas", "Elige el despliegue o tarea administrativa"),
            "SharePoint": ("SharePoint", "Roles, prerrequisitos y SharePoint"),
            "Exchange": ("Exchange", "Instalacion y preparacion de schema"),
            "JCHAT": ("JCHAT", "Java, Openfire, usuarios y salas"),
            "Skype": ("Skype for Business Server", "Prerrequisitos e instalación guiada"),
            "Network": ("Redes", "Switch y Router"),
            "Programs": ("Programas", "Instaladores auxiliares"),
            "Guides": ("Guías", "Documentación PDF"),
            "Security": ("Seguridad", "Firewall y auditoria"),
            "Firewall": ("Firewall", "Windows Firewall"),
            "DC": ("Dominio", "Controladores y unión a dominio"),
            "Guide": ("Guía rápida", "Pasos seguros para usar la herramienta"),
            "Versions": ("Versiones", "Historial de cambios"),
            "Console": ("Consola", "Salida en directo y registro persistente"),
        }
        self._set_page_header(*titles.get(name, titles["Selection"]))

        self.btn_restart.grid_forget()
        self.btn_back.grid_forget()
        self.btn_cancel.grid_forget()
        self._set_control_bar_visible(False)

        if name in {"SharePoint", "Exchange", "DC", "JCHAT", "Skype"}:
            self._set_control_bar_visible(True)
            self.btn_back.grid(row=0, column=1, padx=8, pady=8, sticky="e")
            self.btn_back.configure(command=lambda: self.show_frame("Menu"))
        elif name == "Firewall":
            self._set_control_bar_visible(True)
            self.btn_back.grid(row=0, column=1, padx=8, pady=8, sticky="e")
            self.btn_back.configure(command=lambda: self.show_frame("Security"))
        elif name == "Versions":
            target_frame = getattr(self, "return_frame_after_versions", "Selection")
            if target_frame == "Versions":
                target_frame = "Selection"
            self._set_control_bar_visible(True)
            self.btn_back.grid(row=0, column=1, padx=8, pady=8, sticky="e")
            self.btn_back.configure(command=lambda frame=target_frame: self.show_frame(frame))
        elif name == "Console":
            pass

    def _default_return_frame_for_current_context(self):
        current = getattr(self, "current_frame_name", "Menu")
        if current in {"Menu", "SharePoint", "Exchange", "DC", "JCHAT", "Skype", "Network", "Programs", "Guides", "Security", "Firewall", "Guide", "Versions"}:
            return current
        return "Menu"

    def update_control_bar(self, state):
        if threading.get_ident() != self.ui_thread_id:
            self.after(0, lambda: self.update_control_bar(state))
            return

        self.btn_restart.grid_forget()
        self.btn_back.grid_forget()
        self.btn_cancel.grid_forget()
        self._set_control_bar_visible(False)

        self.control_frame.grid_columnconfigure(0, weight=1)
        if state == "working":
            return
        elif state == "interactive":
            return
        elif state == "finished":
            self._set_control_bar_visible(True)
            target_frame = getattr(self, "return_frame_after_console", "Menu")
            self.btn_back.grid(row=0, column=1, padx=8, pady=8, sticky="e")
            self.btn_back.configure(command=lambda frame=target_frame: self.show_frame(frame))
        elif state == "restart":
            self._set_control_bar_visible(True)
            target_frame = getattr(self, "return_frame_after_console", "Menu")
            self.btn_restart.grid(row=0, column=1, padx=8, pady=8, sticky="e")
            self.btn_back.grid(row=0, column=2, padx=8, pady=8, sticky="e")
            self.btn_back.configure(command=lambda frame=target_frame: self.show_frame(frame))

    def _configure_console_tags(self):
        if not hasattr(self, "console_text"):
            return
        try:
            self.console_text.tag_config("ok", foreground=self.colors["success"])
            self.console_text.tag_config("error", foreground=self.colors["danger"])
            self.console_text.tag_config("warning", foreground=self.colors["warning"])
            self.console_text.tag_config("step", foreground=self.colors["accent"])
        except Exception:
            pass

    def _format_console_line(self, text):
        # Repara posibles caracteres mal decodificados procedentes de PowerShell
        # antes de colorear la linea en consola. Ej: ra├¡z -> raíz, a├▒adir -> añadir.
        try:
            texto_str = SysUtils.decode_process_bytes(str(text), prefer_utf8=True)
        except Exception:
            texto_str = str(text)
        stripped = texto_str.strip()
        if not stripped:
            return texto_str, None

        # Si una linea llega ya prefijada con ✓/✗/!, se analiza igualmente
        # para corregir falsos positivos como "✗ SyncAll terminated with no errors".
        marker = stripped[0] if stripped[0] in ("✓", "✗", "!") else ""
        content = stripped[1:].strip() if marker else stripped
        lower = content.casefold()

        success_tokens = (
            "[ok]",
            "[omitido]",
            "ya instalado",
            "ya estaba instalado",
            "correctamente",
            "successfully",
            "completed successfully",
            "replication completed successfully",
            "syncall finished",
            "syncall terminado",
            "syncall terminated with no errors",
            "terminated with no errors",
            "with no errors",
            "no errors",
            "sin errores",
            "sin error",
        )
        success_prefixes = (
            "creado|",
            "added|",
            "okmember|",
            "ok|",
            "updated|",
            "okdns|",
            "created|",
            "success|",
        )
        if lower.startswith(success_prefixes):
            return texto_str, "ok"

        if any(token in lower for token in success_tokens):
            clean = (
                content.replace("[OK]", "")
                .replace("[ok]", "")
                .replace("[OMITIDO]", "")
                .replace("[omitido]", "")
                .strip()
            )
            return "✓  " + clean, "ok"

        # Nombres técnicos de características Windows pueden contener la palabra
        # "Errors" sin indicar un fallo real. Ej.: Web-Http-Errors es una
        # característica IIS requerida por Skype, no un error de instalación.
        normalized_content = re.sub(r"\s+", " ", lower).strip()
        feature_like = normalized_content.lstrip("- ").strip()
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-errors", feature_like):
            return content, None

        if marker == "✓":
            return texto_str, "ok"
        if marker == "!":
            return texto_str, "warning"
        if marker == "✗":
            return texto_str, "error"

        if "[aviso]" in lower or "warning" in lower or "advertencia" in lower or "atención" in lower or "atencion" in lower:
            clean = content.replace("[AVISO]", "").replace("[aviso]", "").strip()
            return "!  " + clean, "warning"

        has_real_error = (
            "[falta]" in lower
            or "[error]" in lower
            or "[fail]" in lower
            or lower.startswith("fail|")
            or lower.startswith("fallido|")
            or "timeout" in lower
            or "access is denied" in lower
            or "access denied" in lower
            or "acceso denegado" in lower
            or "permiso denegado" in lower
            or "no autorizado" in lower
            or "exception" in lower
            or "excepción" in lower
            or "parsererror" in lower
            or "fullyqualifiederrorid" in lower
            or "cannot validate argument" in lower
            or "returned code" in lower
            or "devolvió código" in lower
            or "devolvio codigo" in lower
            or "no se encuentra" in lower
            or "no encontrado" in lower
            or "fallo" in lower
            or "falló" in lower
            or "falla" in lower
            or (
                "error" in lower
                and "no error" not in lower
                and "no errors" not in lower
                and "sin error" not in lower
                and "sin errores" not in lower
            )
        )
        if has_real_error:
            clean = (
                content.replace("[ERROR]", "")
                .replace("[FALTA]", "")
                .replace("[FAIL]", "")
                .strip()
            )
            return "✗  " + clean, "error"

        if ">>>" in texto_str:
            return "PASO  " + texto_str.replace(">>>", "").strip(), "step"

        return texto_str, None

    def log(self, text):
        if threading.get_ident() != self.ui_thread_id:
            self.after(0, lambda: self.log(text))
            return

        self.console_text.configure(state="normal")
        texto_str, tag = self._format_console_line(text)
        try:
            self.console_text.insert("end", texto_str + "\n", tag)
        except Exception:
            self.console_text.insert("end", texto_str + "\n")
        self.console_text.see("end")
        self.console_text.configure(state="disabled")
        if hasattr(self, "log_manager"):
            self.log_manager.write(texto_str)
        return

        texto_str = str(text)
        if "[OK]" in texto_str or "correctamente" in texto_str.lower():
            texto_str = "OK  " + texto_str.replace("[OK]", "")
        elif "Error" in texto_str or "Exception" in texto_str or "[ERROR]" in texto_str or "falla" in texto_str.lower():
            texto_str = "ERROR  " + texto_str
        elif "Warning" in texto_str or "Advertencia" in texto_str or "ATENCIÓN" in texto_str:
            texto_str = "AVISO  " + texto_str
        elif ">>>" in texto_str:
            texto_str = "PASO  " + texto_str

        self.console_text.insert("end", texto_str + "\n")
        self.console_text.see("end")
        self.console_text.configure(state="disabled")
        if hasattr(self, "log_manager"):
            self.log_manager.write(texto_str)

    def log_raw(self, text):
        if threading.get_ident() != self.ui_thread_id:
            self.after(0, lambda: self.log_raw(text))
            return

        texto_str = str(text)
        if not texto_str:
            return
        self.console_text.configure(state="normal")
        self.console_text.insert("end", texto_str)
        self.console_text.see("end")
        self.console_text.configure(state="disabled")
        if hasattr(self, "log_manager"):
            self.log_manager.write(texto_str)

    def _set_console_input_enabled(self, enabled, placeholder=None, cancel_enabled=None):
        if not hasattr(self, "console_input"):
            return
        state = "normal" if enabled else "disabled"
        cancel_state = "normal" if (enabled if cancel_enabled is None else cancel_enabled) else "disabled"
        placeholder_text = placeholder or (
            "Escribe aqui la respuesta y pulsa Enter."
            if enabled
            else "La entrada se activara con las herramientas interactivas."
        )
        self.console_input.configure(state=state, show="", placeholder_text=placeholder_text)
        self.console_send_button.configure(state=state)
        self.console_cancel_button.configure(state=cancel_state)
        if not enabled:
            self.console_input_sensitive = False
            self.console_input_var.set("")
            self._set_console_com_buttons_visible(False)
        else:
            self.console_input.focus_set()

    def _set_console_waiting_for_input(self, prompt="", sensitive=False):
        if not hasattr(self, "console_input"):
            return
        self.console_input_sensitive = sensitive
        prompt = (prompt or "").strip()
        placeholder = prompt if prompt else "Esperando entrada del usuario..."
        self.console_input.configure(show="*" if sensitive else "", placeholder_text=placeholder)
        self._set_console_com_buttons_visible(self._prompt_needs_com_buttons(prompt))
        self.console_input.focus_set()

    @staticmethod
    def _prompt_needs_com_buttons(prompt):
        prompt = (prompt or "").lower()
        return "puerto com" in prompt or "puerto a usar" in prompt

    def _set_console_com_buttons_visible(self, visible):
        frame = getattr(self, "console_com_buttons_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()
        if not visible:
            frame.grid_remove()
            return

        try:
            import serial.tools.list_ports

            ports = list(serial.tools.list_ports.comports())
        except Exception as exc:
            self.log(f"[AVISO] No se pudieron listar puertos COM: {exc}")
            frame.grid_remove()
            return

        if not ports:
            frame.grid_remove()
            return

        for idx, port in enumerate(ports):
            label = port.device
            btn = ctk.CTkButton(
                frame,
                text=label,
                width=76,
                height=30,
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                command=lambda value=port.device: self._send_console_value(value),
            )
            btn.grid(row=0, column=idx, padx=(0, 8), pady=0, sticky="w")
        frame.grid()

    def _send_console_value(self, value):
        self.console_input_var.set(value)
        self._send_console_input()

    def _send_console_input(self, event=None):
        input_queue = getattr(self, "console_input_queue", None)
        if input_queue is None:
            return
        value = self.console_input_var.get()
        self.console_input_var.set("")
        visible_value = "[oculto]" if getattr(self, "console_input_sensitive", False) else value
        self.log_raw(f"\n> {visible_value}\n")
        input_queue.put(value)

    def _request_active_process_cancel(self):
        if not (self.active_thread and self.active_thread.is_alive()):
            return False

        self.stop_event.set()
        input_queue = getattr(self, "console_input_queue", None)
        if input_queue is not None:
            input_queue.put(None)
        self.log("\n[!] CANCELANDO PROCESO ACTIVO...")
        self._set_console_input_enabled(False)
        if hasattr(self, "btn_cancel"):
            self.btn_cancel.configure(state="disabled")
        if hasattr(self, "console_cancel_button"):
            self.console_cancel_button.configure(state="disabled")
        return True

    def _cancel_console_program(self):
        if not self._request_active_process_cancel():
            self.log("[INFO] No hay ningun programa interactivo en ejecucion.")

    def _finish_interactive_console_run(self):
        status = "cancelada" if self.stop_event.is_set() else "finalizada"
        self.log(f"\n--- PROCESO {status.upper()} ---")
        if hasattr(self, "log_manager"):
            self.log_manager.finish_run(status)
        self.update_progress(1)
        self.update_control_bar("finished")
        self._set_console_input_enabled(False)
        self.console_input_queue = None

    def update_progress(self, val):
        if threading.get_ident() != self.ui_thread_id:
            self.after(0, lambda: self.update_progress(val))
            return

        if val < 0:
            val = 0
        if val > 1:
            val = 1
        self.progress_bar.set(val)
        self.lbl_percent.configure(text=f"{int(val * 100)}%")

    def _center_window(self, window, width, height):
        try:
            x = (window.winfo_screenwidth() // 2) - (width // 2)
            y = (window.winfo_screenheight() // 2) - (height // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            window.geometry(f"{width}x{height}")

    def _enable_frameless_drag(self, window, *widgets):
        drag = {"x": 0, "y": 0}

        def start_drag(event):
            drag["x"] = event.x_root - window.winfo_x()
            drag["y"] = event.y_root - window.winfo_y()

        def move_window(event):
            window.geometry(f"+{event.x_root - drag['x']}+{event.y_root - drag['y']}")

        for widget in widgets:
            widget.bind("<ButtonPress-1>", start_drag)
            widget.bind("<B1-Motion>", move_window)

    def _build_dialog_shell_header(
        self,
        dialog,
        panel_fg,
        border_color,
        accent_color,
        header_pady,
        badge_text,
        badge_text_color,
        heading_text,
        subtitle_text,
        before_header=None,
    ):
        panel = ctk.CTkFrame(
            dialog,
            fg_color=panel_fg,
            border_width=1,
            border_color=border_color,
            corner_radius=8,
        )
        panel.pack(fill="both", expand=True, padx=0, pady=0)
        accent_line = ctk.CTkFrame(panel, height=4, fg_color=accent_color, corner_radius=3)
        accent_line.pack(fill="x", padx=16, pady=(14, 0))

        if before_header is not None:
            before_header(panel)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=header_pady)
        header.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkFrame(header, width=48, height=48, fg_color=("#E7F5F2", "#263432"), corner_radius=8)
        badge.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="n")
        badge.grid_propagate(False)
        ctk.CTkLabel(badge, text=badge_text, font=("Segoe UI", 16, "bold"), text_color=badge_text_color).pack(fill="both", expand=True)

        heading_label = ctk.CTkLabel(header, text=heading_text, font=("Segoe UI", 20, "bold"), anchor="w")
        heading_label.grid(row=0, column=1, sticky="ew")
        subtitle_label = ctk.CTkLabel(
            header,
            text=subtitle_text,
            font=("Segoe UI", 12, "bold"),
            text_color=accent_color,
            anchor="w",
        )
        subtitle_label.grid(row=1, column=1, sticky="ew")
        return panel, accent_line, header, badge, heading_label, subtitle_label

    def _load_startup_logo_image(self, size=(74, 74)):
        if getattr(self, "_license_logo_image", None) is not None:
            return self._license_logo_image
        candidates = []
        base_path = getattr(self, "base_path", None)
        if base_path:
            candidates.append(base_path)
        if getattr(sys, "frozen", False):
            candidates.append(getattr(sys, "_MEIPASS", ""))
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        for base in candidates:
            if not base:
                continue
            for filename in ("EscudoRt.png", "EscudoRT.png"):
                logo_path = os.path.join(base, "iconos", filename)
                if not os.path.exists(logo_path):
                    continue
                try:
                    from PIL import Image

                    image = Image.open(logo_path)
                    self._license_logo_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
                    return self._license_logo_image
                except Exception:
                    continue
        return None

    def _license_access_dialog(self, prompt, initial_error=""):
        colors = getattr(self, "colors", None)
        if not colors:
            colors = self._build_colors_from_skin(DEFAULT_SKIN)

        result = {"value": None}
        dialog_width = 640
        dialog_height = 392
        dialog = ctk.CTkToplevel(self)
        dialog.title(APP_DISPLAY_TITLE)
        dialog.resizable(False, False)
        dialog.overrideredirect(True)
        outer_fg = (colors["panel_light"], colors["panel_dark"])
        transparent_color = "#010203"
        try:
            dialog.configure(fg_color=transparent_color)
            dialog.attributes("-transparentcolor", transparent_color)
            outer_fg = transparent_color
        except Exception:
            try:
                dialog.configure(fg_color=outer_fg)
            except Exception:
                pass
        self._center_window(dialog, dialog_width, dialog_height)

        shell = ctk.CTkFrame(dialog, fg_color=outer_fg)
        shell.pack(fill="both", expand=True, padx=16, pady=16)

        card = ctk.CTkFrame(
            shell,
            fg_color=(colors["panel_light"], colors["panel_dark"]),
            border_width=1,
            border_color=(colors["border_light"], colors["border_dark"]),
            corner_radius=12,
        )
        card.pack(fill="both", expand=True)

        accent_line = ctk.CTkFrame(card, height=4, fg_color=colors["accent"], corner_radius=3)
        accent_line.pack(fill="x", padx=18, pady=(14, 0))

        license_status = getattr(self, "license_status", None)
        days_remaining = getattr(license_status, "days_remaining", None) if license_status else None
        if isinstance(days_remaining, int):
            day_word = "día" if days_remaining == 1 else "días"
            status_text = f"Licencia activa · {days_remaining} {day_word}"
        else:
            status_text = getattr(license_status, "summary", "") or "Licencia local"

        meta_row = ctk.CTkFrame(card, fg_color="transparent")
        meta_row.pack(fill="x", padx=26, pady=(9, 0))
        meta_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            meta_row,
            text=APP_DISPLAY_TITLE,
            font=("Segoe UI", 10, "bold"),
            text_color=(colors["text_muted_light"], colors["text_muted_dark"]),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            meta_row,
            text=status_text,
            font=("Segoe UI", 10, "bold"),
            text_color=(colors["text_muted_light"], colors["text_muted_dark"]),
            anchor="e",
            justify="right",
        ).grid(row=0, column=1, padx=(12, 10), sticky="e")

        close_button = ctk.CTkButton(
            meta_row,
            text="x",
            width=34,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            hover_color=colors["sidebar_hover"],
            text_color=(colors["text_secondary_light"], colors["text_secondary_dark"]),
            font=("Segoe UI", 15, "bold"),
            command=lambda: close_dialog(),
        )
        close_button.grid(row=0, column=2, sticky="e")

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=26, pady=(14, 8))
        header.grid_columnconfigure(1, weight=1)

        logo_box = ctk.CTkFrame(
            header,
            width=70,
            height=70,
            fg_color=colors["sidebar_active"],
            border_width=1,
            border_color=(colors["border_light"], colors["border_dark"]),
            corner_radius=12,
        )
        logo_box.grid(row=0, column=0, rowspan=2, padx=(0, 16), sticky="n")
        logo_box.grid_propagate(False)
        logo_image = self._load_startup_logo_image(size=(66, 66))
        if logo_image:
            ctk.CTkLabel(logo_box, image=logo_image, text="").pack(fill="both", expand=True, padx=6, pady=6)
        else:
            ctk.CTkLabel(
                logo_box,
                text="ED",
                font=("Segoe UI", 26, "bold"),
                text_color=colors["accent"],
            ).pack(fill="both", expand=True)

        ctk.CTkLabel(
            header,
            text="Acceso a Easy Deploy",
            font=("Segoe UI", 25, "bold"),
            text_color=(colors["text_primary_light"], colors["text_primary_dark"]),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", pady=(3, 0))
        ctk.CTkLabel(
            header,
            text="Verificación local antes de abrir la consola de despliegue.",
            font=("Segoe UI", 13),
            text_color=(colors["text_secondary_light"], colors["text_secondary_dark"]),
            anchor="w",
            justify="left",
            wraplength=500,
        ).grid(row=1, column=1, sticky="ew", pady=(3, 0))

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=26, pady=(0, 4))

        prompt_text = str(prompt or "Introduce el código de licencia:").strip()
        ctk.CTkLabel(
            content,
            text=prompt_text,
            font=("Segoe UI", 12, "bold"),
            text_color=(colors["text_secondary_light"], colors["text_secondary_dark"]),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        entry_row = ctk.CTkFrame(content, fg_color="transparent")
        entry_row.pack(fill="x")
        entry_var = ctk.StringVar()
        entry = ctk.CTkEntry(
            entry_row,
            height=46,
            textvariable=entry_var,
            show="*",
            placeholder_text="Código de licencia",
            font=("Consolas", 16),
            justify="center",
            fg_color=(colors["card_light"], colors["card_dark"]),
            border_width=1,
            border_color=(colors["border_light"], colors["border_dark"]),
            corner_radius=8,
        )
        entry.pack(side="left", fill="x", expand=True)

        visible = {"value": False}

        def toggle_visible():
            visible["value"] = not visible["value"]
            entry.configure(show="" if visible["value"] else "*")
            view_button.configure(text="Ocultar" if visible["value"] else "Ver")
            entry.focus_set()

        view_button = ctk.CTkButton(
            entry_row,
            text="Ver",
            width=84,
            height=46,
            corner_radius=8,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            font=("Segoe UI", 12, "bold"),
            command=toggle_visible,
        )
        view_button.pack(side="left", padx=(10, 0))

        error_label = ctk.CTkLabel(
            content,
            text=str(initial_error or ""),
            font=("Segoe UI", 11, "bold"),
            text_color=colors["danger"],
            anchor="w",
            justify="left",
        )
        error_label.pack(fill="x", pady=(8, 0))

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=26, pady=(2, 16))
        footer.grid_columnconfigure(0, weight=1)

        def close_dialog(event=None):
            result["value"] = None
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        def focus_entry_once():
            if not self._widget_exists(dialog) or not self._widget_exists(entry):
                return
            try:
                entry.focus_set()
                entry.icursor("end")
            except Exception:
                pass

        def accept(event=None):
            value = entry.get().strip()
            if not value:
                entry.configure(border_color=colors["danger"])
                error_label.configure(text="Introduce un código de licencia para continuar.")
                focus_entry_once()
                return
            result["value"] = value
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        ctk.CTkButton(
            footer,
            text="Cancelar",
            width=128,
            height=42,
            corner_radius=8,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            font=("Segoe UI", 12, "bold"),
            command=close_dialog,
        ).grid(row=0, column=1, padx=(8, 0), sticky="e")
        ctk.CTkButton(
            footer,
            text="Entrar",
            width=132,
            height=42,
            corner_radius=8,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            font=("Segoe UI", 12, "bold"),
            command=accept,
        ).grid(row=0, column=2, padx=(8, 0), sticky="e")

        self._enable_frameless_drag(dialog, shell, card, accent_line, meta_row, header, logo_box)
        dialog.bind("<Return>", accept)
        dialog.bind("<Escape>", close_dialog)
        dialog.bind("<Alt-F4>", close_dialog)
        try:
            dialog.grab_set()
        except Exception:
            pass

        def release_topmost():
            try:
                if dialog.winfo_exists():
                    dialog.attributes("-topmost", False)
            except Exception:
                pass

        try:
            dialog.attributes("-topmost", True)
            dialog.after(350, release_topmost)
        except Exception:
            pass
        try:
            dialog.lift(self)
        except Exception:
            try:
                dialog.lift()
            except Exception:
                pass
        dialog.after(120, focus_entry_once)
        self.wait_window(dialog)
        return result["value"]

    def input_dialog(self, title, prompt, is_password=False, max_chars=None, auto_dash=False, initial_error=""):
        if is_password and str(title or "") == APP_DISPLAY_TITLE and "LICENCIA" in str(prompt or "").upper():
            return self._license_access_dialog(prompt, initial_error=initial_error)

        user_input = {"value": None}
        dialog_button_width = getattr(self, "dialog_button_width", 136)
        dialog_button_height = max(getattr(self, "dialog_button_height", 44), 44)
        colors = getattr(self, "colors", {
            "accent": "#2F9E8F",
            "accent_hover": "#258176",
            "panel_light": "#FFFFFF",
            "panel_dark": "#1F1F22",
            "border_light": "#D7DAE0",
            "border_dark": "#3A3A40",
        })

        prompt_text = str(prompt)
        dialog_key = None
        if not is_password:
            dialog_key = self._secondary_key("input", title, prompt_text[:80])
            if self._focus_secondary_window(dialog_key):
                return None

        dialog = ctk.CTkToplevel(self)
        dialog_title = APP_DISPLAY_TITLE if is_password else title
        dialog.title(dialog_title)
        prompt_lines = prompt_text.splitlines() or [prompt_text]
        visual_lines = sum(max(1, (len(line) + 54) // 55) for line in prompt_lines)
        extra_height = min(max(visual_lines - 2, 0) * 18, 160)
        dialog_width = 560 if is_password else 520
        license_extra_height = 18 if is_password else 0
        dialog_height = min(640, (280 if is_password else 300) + extra_height + license_extra_height)
        dialog.overrideredirect(True)
        dialog.configure(fg_color=(colors["panel_light"], colors["panel_dark"]))
        minimized = {"value": False}
        if dialog_key:
            self._register_secondary_window(dialog_key, dialog)

        dialog.update_idletasks()
        self._center_window(dialog, dialog_width, dialog_height)

        def add_password_license(parent):
            if not is_password:
                return
            license_status = getattr(self, "license_status", None)
            days_remaining = getattr(license_status, "days_remaining", 0) if license_status else 0
            day_word = "dia" if days_remaining == 1 else "dias"
            license_text = f"Licencia caduca en {days_remaining} {day_word}."
            ctk.CTkLabel(
                parent,
                text=license_text,
                font=("Segoe UI", 9),
                text_color=("gray55", "gray48"),
                anchor="e",
                justify="right",
            ).pack(fill="x", padx=22, pady=(3, 0))

        heading = "Acceso a Easy Deploy" if is_password else title
        panel, accent_line, header, badge, heading_label, subtitle_label = self._build_dialog_shell_header(
            dialog,
            (colors["panel_light"], colors["panel_dark"]),
            (colors["border_light"], colors["border_dark"]),
            colors["accent"],
            (10 if is_password else 18, 6),
            "ED",
            colors["accent"],
            heading,
            "Validacion requerida" if is_password else "Introduce el dato solicitado",
            before_header=add_password_license,
        )

        def close_dialog():
            if dialog_key:
                self._destroy_restore_chip(dialog_key)
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        def on_cancel(event=None):
            close_dialog()

        def restore_dialog():
            minimized["value"] = False
            try:
                dialog.deiconify()
                dialog.grab_set()
                try:
                    dialog.lift(self)
                except Exception:
                    dialog.lift()
                dialog.after(80, focus_entry_once)
            except Exception:
                pass

        def show_restore_chip():
            if not dialog_key:
                return
            self._show_restore_chip(
                dialog_key,
                f"Restaurar aviso: {heading}",
                restore_dialog,
                (colors["panel_light"], colors["panel_dark"]),
                (colors["border_light"], colors["border_dark"]),
                colors["accent"],
                colors["accent_hover"],
                window=dialog,
                close_command=close_dialog,
            )

        def minimize_dialog(event=None):
            minimized["value"] = True
            try:
                dialog.grab_release()
            except Exception:
                pass
            try:
                dialog.withdraw()
                show_restore_chip()
            except Exception:
                pass

        close_column = 2
        if not is_password:
            minimize_button = ctk.CTkButton(
                header,
                text="-",
                width=34,
                height=34,
                corner_radius=8,
                fg_color="transparent",
                hover_color=("#E5E7EB", "#303034"),
                text_color=("gray25", "#E5E7EB"),
                font=("Segoe UI", 18, "bold"),
                command=minimize_dialog,
            )
            minimize_button.grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="ne")
            close_column = 3

        close_button = ctk.CTkButton(
            header,
            text="×",
            width=42,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#E5E7EB", "#303034"),
            text_color=("gray25", "#E5E7EB"),
            font=("Segoe UI", 18, "bold"),
            command=on_cancel,
        )
        close_button.grid(row=0, column=close_column, rowspan=2, padx=(6 if not is_password else 8, 0), sticky="ne")
        self._enable_frameless_drag(dialog, panel, accent_line, header, badge, heading_label, subtitle_label)

        btn_frame = ctk.CTkFrame(panel, fg_color="transparent", height=dialog_button_height + 16)
        btn_frame.pack(side="bottom", fill="x", padx=22, pady=(8, 18))
        btn_frame.pack_propagate(False)

        lbl = ctk.CTkLabel(
            panel,
            text=prompt_text,
            font=("Segoe UI", 13),
            text_color=("gray28", "gray78"),
            wraplength=dialog_width - 80,
            justify="left",
            anchor="w",
        )
        lbl.pack(fill="x", padx=22, pady=(4, 14))

        entry_var = ctk.StringVar()

        def on_text_change(*args):
            text = entry_var.get().upper()
            if auto_dash:
                clean_text = text.replace("-", "").replace(" ", "")
                new_text = ""
                for i, char in enumerate(clean_text):
                    if i > 0 and i % 5 == 0:
                        new_text += "-"
                    new_text += char
                text = new_text
            if max_chars is not None and len(text) > max_chars:
                text = text[:max_chars]
            if entry_var.get() != text:
                entry_var.set(text)

        if auto_dash or max_chars:
            entry_var.trace_add("write", on_text_change)

        entry_row = ctk.CTkFrame(panel, fg_color="transparent")
        entry_row.pack(fill="x", padx=22, pady=(0, 6))

        entry = ctk.CTkEntry(
            entry_row,
            height=42,
            textvariable=entry_var,
            font=("Consolas", 15) if is_password or auto_dash else ("Segoe UI", 13),
            justify="center" if is_password or auto_dash else "left",
            border_width=2,
            border_color=(colors["border_light"], colors["border_dark"]),
        )
        if is_password:
            entry.configure(show="*")
        entry.pack(side="left", fill="x", expand=True)

        password_visible = {"value": False}

        def toggle_password():
            password_visible["value"] = not password_visible["value"]
            entry.configure(show="" if password_visible["value"] else "*")
            btn_toggle.configure(text="Ocultar" if password_visible["value"] else "Ver")
            entry.focus_set()

        if is_password:
            btn_toggle = ctk.CTkButton(
                entry_row,
                text="Ver",
                width=74,
                height=42,
                fg_color=("#E5E7EB", "#2B2B2F"),
                hover_color=("#D1D5DB", "#3A3A40"),
                text_color=("gray15", "#F4F4F5"),
                command=toggle_password,
            )
            btn_toggle.pack(side="left", padx=(8, 0))

        def focus_entry_once(event=None):
            """Da foco inicial sin reprogramar capturas agresivas.

            La versión anterior lanzaba muchas llamadas a focus_force/grab_set en cascada
            y provocaba parpadeo/pérdida de foco en las cajas de escritura.
            """
            if minimized["value"]:
                return
            if not self._widget_exists(dialog) or not self._widget_exists(entry):
                return
            try:
                entry.configure(state="normal")
                entry.focus_set()
                entry.icursor("end")
            except Exception:
                pass

        try:
            dialog.grab_set()
        except Exception:
            pass
        try:
            dialog.attributes("-topmost", True)
            dialog.after(250, lambda: dialog.attributes("-topmost", False))
        except Exception:
            pass
        try:
            dialog.lift(self)
        except Exception:
            try:
                dialog.lift()
            except Exception:
                pass
        dialog.after(120, focus_entry_once)

        error_lbl = ctk.CTkLabel(panel, text="", text_color="#DC2626", font=("Segoe UI", 11, "bold"), anchor="w")
        error_lbl.pack(fill="x", padx=22, pady=(0, 2))

        def on_ok(event=None):
            text = entry.get().strip()
            if not text:
                entry.configure(border_color="#DC2626")
                error_lbl.configure(text="Introduce un valor para continuar.")
                focus_entry_once()
                return
            user_input["value"] = text
            close_dialog()

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=on_cancel,
            fg_color="#6B7280",
            hover_color="#4B5563",
            width=dialog_button_width,
            height=dialog_button_height,
        ).pack(side="right", padx=(8, 0), pady=4)
        ctk.CTkButton(
            btn_frame,
            text="Aceptar",
            command=on_ok,
            width=dialog_button_width,
            height=dialog_button_height,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
        ).pack(side="right", pady=4)

        dialog.bind("<Return>", on_ok)
        dialog.bind("<Escape>", on_cancel)
        dialog.bind("<Alt-F4>", on_cancel)
        self.wait_window(dialog)
        return user_input["value"]

    def input_dialog_kms(self, title, text, max_chars=None, auto_dash=False):
        return self.input_dialog(title, text, max_chars=max_chars, auto_dash=auto_dash)

    def _call_ui_thread(self, callback, *args, **kwargs):
        if threading.get_ident() == self.ui_thread_id:
            return callback(*args, **kwargs)

        done = threading.Event()
        result = {"value": None, "error": None}

        def runner():
            try:
                result["value"] = callback(*args, **kwargs)
            except Exception as exc:
                result["error"] = exc
            finally:
                done.set()

        self.after(0, runner)
        done.wait()
        if result["error"]:
            raise result["error"]
        return result["value"]

    def modal_dialog(self, title, message, kind="info", buttons=None, topmost=False):
        result = {"value": None}
        dialog_button_width = getattr(self, "dialog_button_width", 136)
        dialog_button_height = max(getattr(self, "dialog_button_height", 44), 44)
        colors = getattr(self, "colors", {})
        dialog_key = self._secondary_key("modal", title, kind)
        if self._focus_secondary_window(dialog_key):
            return None
        kind_map = {
            "info": ("i", colors.get("accent", "#2F9E8F"), "Informacion"),
            "success": ("OK", colors.get("success", "#16803C"), "Completado"),
            "warning": ("!", colors.get("warning", "#D97706"), "Atencion"),
            "error": ("!", colors.get("danger", "#B42318"), "Error"),
            "question": ("?", colors.get("accent", "#2F9E8F"), "Confirmacion"),
        }
        badge_text, accent_color, subtitle = kind_map.get(kind, kind_map["info"])
        if buttons is None:
            buttons = [("Aceptar", True, "primary")]

        message_text = str(message or "")
        lines = max(2, message_text.count("\n") + 1)
        longest_button = max((len(str(text or "")) for text, _value, _style in buttons), default=8)
        dialog_button_width = max(dialog_button_width, min(170, longest_button * 7 + 34))
        if kind == "question":
            dialog_button_width = max(dialog_button_width, 190)
        required_button_width = (dialog_button_width * len(buttons)) + (8 * max(0, len(buttons) - 1)) + 44
        dialog_width = min(820, max(560, required_button_width))
        message_wrap_width = max(420, dialog_width - 72)
        chars_per_line = max(48, message_wrap_width // 7)
        wrapped_lines = 0
        for raw_line in (message_text.splitlines() or [""]):
            text_len = max(1, len(raw_line.rstrip()))
            wrapped_lines += max(1, (text_len + chars_per_line - 1) // chars_per_line)
        estimated_message_height = max(52, wrapped_lines * 20 + 18)
        estimated_shell_height = 154 + (dialog_button_height + 44)
        try:
            max_dialog_height = max(420, min(820, self.winfo_screenheight() - 90))
        except Exception:
            max_dialog_height = 720
        wanted_dialog_height = max(310, estimated_shell_height + estimated_message_height)
        dialog_height = min(max_dialog_height, wanted_dialog_height)
        message_needs_scroll = wanted_dialog_height > max_dialog_height
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.overrideredirect(True)
        if topmost:
            try:
                dialog.attributes("-topmost", True)
            except Exception:
                pass
        dialog.configure(fg_color=(colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")))
        self._register_secondary_window(dialog_key, dialog)

        dialog.update_idletasks()
        self._center_window(dialog, dialog_width, dialog_height)

        panel, accent_line, header, badge, heading_label, subtitle_label = self._build_dialog_shell_header(
            dialog,
            (colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")),
            (colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40")),
            accent_color,
            (18, 8),
            badge_text,
            accent_color,
            title,
            subtitle,
        )

        def restore_dialog():
            try:
                dialog.deiconify()
                if topmost:
                    dialog.attributes("-topmost", True)
                dialog.grab_set()
                self._focus_secondary_window(dialog)
            except Exception:
                pass

        def show_restore_chip():
            self._show_restore_chip(
                dialog_key,
                f"Restaurar aviso: {title}",
                restore_dialog,
                (colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")),
                (colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40")),
                accent_color,
                colors.get("accent_hover", "#258176"),
                window=dialog,
                close_command=close_default,
            )

        def finish_dialog(value):
            self._destroy_restore_chip(dialog_key)
            result["value"] = value
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        def close_default(event=None):
            value = buttons[-1][1] if len(buttons) > 1 else False
            finish_dialog(value)

        def minimize_dialog(event=None):
            try:
                dialog.grab_release()
            except Exception:
                pass
            try:
                dialog.withdraw()
                show_restore_chip()
            except Exception:
                pass

        minimize_button = ctk.CTkButton(
            header,
            text="-",
            width=34,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#E5E7EB", "#303034"),
            text_color=("gray25", "#E5E7EB"),
            font=("Segoe UI", 18, "bold"),
            command=minimize_dialog,
        )
        minimize_button.grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="ne")

        close_button = ctk.CTkButton(
            header,
            text="x",
            width=42,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#E5E7EB", "#303034"),
            text_color=("gray25", "#E5E7EB"),
            font=("Segoe UI", 18, "bold"),
            command=close_default,
        )
        close_button.grid(row=0, column=3, rowspan=2, padx=(6, 0), sticky="ne")
        self._enable_frameless_drag(dialog, panel, accent_line, header, badge, heading_label, subtitle_label)
        dialog.protocol("WM_DELETE_WINDOW", close_default)

        if message_needs_scroll:
            message_scroll_height = max(180, min(460, max_dialog_height - estimated_shell_height - 28))
            message_widget = ctk.CTkTextbox(
                panel,
                height=message_scroll_height,
                fg_color="transparent",
                border_width=0,
                wrap="word",
                font=("Segoe UI", 13),
                text_color=("gray25", "gray82"),
                activate_scrollbars=True,
            )
            message_widget.insert("1.0", message_text)
            message_widget.configure(state="disabled")
            message_widget.pack(fill="x", padx=22, pady=(4, 12))
        else:
            ctk.CTkLabel(
                panel,
                text=message_text,
                font=("Segoe UI", 13),
                justify="left",
                anchor="nw",
                wraplength=message_wrap_width,
                text_color=("gray25", "gray82"),
            ).pack(fill="x", padx=22, pady=(4, 12))

        btn_frame = ctk.CTkFrame(panel, fg_color="transparent", height=dialog_button_height + 18)
        btn_frame.pack(fill="x", padx=22, pady=(2, 16))
        btn_frame.pack_propagate(False)

        def style_colors(style):
            if style == "danger":
                return colors.get("danger", "#B42318"), "#991B1B"
            if style == "warning":
                return colors.get("warning", "#D97706"), "#B45309"
            if style == "secondary":
                return "#6B7280", "#4B5563"
            return colors.get("accent", "#2F9E8F"), colors.get("accent_hover", "#258176")

        for text, value, style in reversed(buttons):
            fg_color, hover_color = style_colors(style)

            def choose(v=value):
                finish_dialog(v)

            ctk.CTkButton(
                btn_frame,
                text=text,
                command=choose,
                fg_color=fg_color,
                hover_color=hover_color,
                width=dialog_button_width,
                height=dialog_button_height,
                corner_radius=8,
                font=("Segoe UI", 13, "bold"),
            ).pack(side="right", padx=(10, 0), pady=8)

        dialog.update_idletasks()
        try:
            compact_height = min(max_dialog_height, max(240, panel.winfo_reqheight()))
            self._center_window(dialog, dialog_width, compact_height)
        except Exception:
            pass

        dialog.bind("<Return>", lambda _event=None: finish_dialog(buttons[0][1]))
        dialog.bind("<Escape>", close_default)
        dialog.grab_set()
        if topmost:
            try:
                dialog.attributes("-topmost", True)
            except Exception:
                pass
        self._focus_secondary_window(dialog)
        self.wait_window(dialog)
        return result["value"]

    def ui_askyesno(self, title, message):
        return self._call_ui_thread(
            self.modal_dialog,
            title,
            message,
            "question",
            [("Sí", True, "primary"), ("No", False, "secondary")],
        )

    def ask_reboot_dialog(self, title, message):
        return self.modal_dialog(
            title,
            message,
            "warning",
            [("Reiniciar", True, "warning"), ("Mas tarde", False, "secondary")],
        )

    def ui_ask_reboot(self, title, message):
        return self._call_ui_thread(self.ask_reboot_dialog, title, message)

    def ui_showinfo(self, title, message):
        return self._call_ui_thread(self.modal_dialog, title, message, "info", [("Aceptar", True, "primary")])

    def ui_showinfo_topmost(self, title, message):
        return self._call_ui_thread(
            self.modal_dialog,
            title,
            message,
            "info",
            [("Aceptar", True, "primary")],
            True,
        )

    def ui_showwarning(self, title, message):
        return self._call_ui_thread(self.modal_dialog, title, message, "warning", [("Aceptar", True, "warning")])

    def ui_showerror(self, title, message):
        return self._call_ui_thread(self.modal_dialog, title, message, "error", [("Aceptar", True, "danger")])

    def ui_input_dialog(self, *args, **kwargs):
        return self._call_ui_thread(self.input_dialog, *args, **kwargs)

    def iniciar_tarea(self, target_func, *args):
        if self.active_thread and self.active_thread.is_alive():
            self.ui_showwarning(
                "Proceso en curso",
                "Ya hay una tarea ejecutandose.\n\n"
                "Vuelve a Consola para revisar el progreso o pulsa Cancelar antes de iniciar otra tarea.",
            )
            self.show_frame("Console")
            return

        self._update_environment_status()
        if not SysUtils.is_admin():
            self.ui_showerror(
                "Permisos de administrador",
                "Esta tarea necesita permisos de Administrador.\n\n"
                "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
            )
            return

        self.return_frame_after_console = self._default_return_frame_for_current_context()
        self.show_frame("Console")
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", "end")
        self.console_text.configure(state="disabled")
        self.update_progress(0)

        self.stop_event.clear()
        self.console_finish_state = "finished"
        self.console_input_queue = None
        self._set_console_input_enabled(
            False,
            "Proceso en curso. Pulsa Cancelar para detenerlo.",
            cancel_enabled=True,
        )
        self.update_control_bar("working")
        if hasattr(self, "log_manager"):
            log_path = self.log_manager.start_run(target_func.__name__)
            self.lbl_log_path.configure(text=f"Log actual: {log_path}")
            self.log(f"[LOG] Guardando registro en: {log_path}")

        sys.stdout = self
        self.active_thread = threading.Thread(target=self._thread_wrapper, args=(target_func, args), daemon=True)
        self.active_thread.start()

    def _thread_wrapper(self, func, args):
        try:
            func(*args)
        except Exception as e:
            self.log(f"\nERROR CRÍTICO: {e}")
            self.ui_showerror(
                "Error inesperado",
                "La tarea se ha detenido por un error no controlado.\n\n"
                f"Detalle: {e}\n\n"
                "Revisa el log actual antes de repetir la operacion.",
            )
        finally:
            self.log("\n--- PROCESO FINALIZADO ---")
            if hasattr(self, "log_manager"):
                self.log_manager.finish_run()
            self.update_control_bar(getattr(self, "console_finish_state", "finished"))
            self._set_console_input_enabled(False)
            sys.stdout = sys.__stdout__
            self.active_thread = None

    def write(self, text):
        self.after(0, lambda: self.log(text.strip()) if text.strip() else None)

    def flush(self):
        pass

    def cancelar_proceso(self):
        if self.active_thread and self.active_thread.is_alive():
            if self.ui_askyesno("Cancelar", "Seguro que deseas cancelar?"):
                self._request_active_process_cancel()

    def close_app(self):
        if self.active_thread and self.active_thread.is_alive():
            if not self.ui_askyesno(
                "Salir",
                "Hay una tarea en ejecucion.\n\n"
                "Si sales ahora se solicitara cancelar el proceso actual.\n\n"
                "Quieres salir de Easy Deploy?",
            ):
                return
            self._request_active_process_cancel()
        self.destroy()

    def reiniciar_sistema(self):
        if self.ui_ask_reboot("Reiniciar", "Reiniciar el sistema ahora?"):
            subprocess.run(["shutdown", "/r", "/t", "0"], creationflags=subprocess.CREATE_NO_WINDOW)
