import os
import json
import subprocess
import sys
import tempfile
import threading
import time

import customtkinter as ctk

from ..core.sysutils import SysUtils


class ActionsMixin:
    def _run_ping_subprocess(
        self,
        command,
        process_holder,
        should_stop,
        on_stdout,
        on_stderr,
        terminate_after_output=False,
        wait_timeout=None,
        ignore_wait_errors=False,
    ):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=SysUtils.oem_encoding(),
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        process_holder["process"] = process
        for line in process.stdout:
            if should_stop():
                break
            on_stdout(line)
        if should_stop() and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                pass
        err = process.stderr.read() if process.stderr else ""
        if err.strip():
            on_stderr(err)
        if terminate_after_output and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                pass
        if wait_timeout is None:
            process.wait()
            return
        try:
            process.wait(timeout=wait_timeout)
        except Exception:
            if not ignore_wait_errors:
                raise

    def _shell_execute(self, title, executable, parameters="", elevated=False):
        """Abre herramientas de Windows por ejecutable/snap-in, independiente del idioma del SO."""
        import ctypes

        verb = "runas" if elevated else "open"
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                verb,
                executable,
                parameters,
                None,
                1,
            )
            if result <= 32:
                raise OSError(f"ShellExecuteW devolvio codigo {result}")
        except Exception as exc:
            self.ui_showerror(
                title,
                "No se pudo abrir la utilidad.\n\n"
                "Comprueba que la herramienta/RSAT correspondiente este instalada en Windows.\n\n"
                f"Detalle: {exc}",
            )

    def _open_mmc_snapin(self, title, snapin_name):
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        snapin_path = os.path.join(system_root, "System32", snapin_name)
        self._shell_execute(title, snapin_path)

    def _open_ad_users_and_computers(self):
        self._open_mmc_snapin("AD Users and Computers", "dsa.msc")

    def _open_dns_manager(self):
        self._open_mmc_snapin("DNS Manager", "dnsmgmt.msc")

    def _open_group_policy_management(self):
        self._open_mmc_snapin("Group Policy Management", "gpmc.msc")

    def _accion_abrir_disk_management(self):
        self._open_mmc_snapin("Disk Management", "diskmgmt.msc")
        if hasattr(self, "_refresh_disk_status_async"):
            self.after(5000, lambda: self._refresh_disk_status_async(force=True))

    def _open_admin_cmd(self):
        self._shell_execute("CMD", "cmd.exe", elevated=True)

    def _open_admin_powershell(self):
        self._shell_execute("PowerShell", "powershell.exe", "-NoExit", elevated=True)

    def _open_control_applet(self, applet_name):
        subprocess.Popen(["control", applet_name], creationflags=subprocess.CREATE_NO_WINDOW)

    def _legacy_window_tokens(self):
        colors = getattr(self, "colors", {})
        return {
            "panel": (colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22")),
            "card": (colors.get("card_light", "#F7F8FA"), colors.get("card_dark", "#26262A")),
            "card_hover": ("#F1F5F4", "#2A2A2F"),
            "border": (colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40")),
            "accent": colors.get("accent", "#2F9E8F"),
            "accent_hover": colors.get("accent_hover", "#258176"),
            "secondary": "#4B5563",
            "secondary_hover": "#374151",
            "text": ("gray20", "gray86"),
            "muted": ("gray35", "gray72"),
        }

    def _center_legacy_window(self, window, width, height):
        try:
            self._center_window(window, width, height)
        except Exception:
            window.geometry(f"{width}x{height}")
            try:
                window.update_idletasks()
                x = (self.winfo_screenwidth() - width) // 2
                y = (self.winfo_screenheight() - height) // 2
                window.geometry(f"+{x}+{y}")
            except Exception:
                pass

    def _create_legacy_panel_window(
        self,
        title,
        width,
        height,
        resizable=False,
        topmost=False,
        temporary_topmost=False,
        transient=False,
        minsize=None,
        bring_to_front=True,
        window_key=None,
    ):
        tokens = self._legacy_window_tokens()
        window = ctk.CTkToplevel(self)
        window.title(title)
        window.geometry(f"{width}x{height}")
        window.resizable(resizable, resizable)
        if minsize:
            try:
                window.minsize(*minsize)
            except Exception:
                pass
        if transient:
            window.transient(self)
        if topmost or temporary_topmost:
            try:
                window.attributes("-topmost", True)
                if temporary_topmost:
                    def release_topmost():
                        try:
                            if window.winfo_exists():
                                window.attributes("-topmost", False)
                        except Exception:
                            pass

                    window.after(300, release_topmost)
            except Exception:
                pass
        window.configure(fg_color=tokens["panel"])
        self._center_legacy_window(window, width, height)
        panel = ctk.CTkFrame(
            window,
            fg_color=tokens["panel"],
            border_width=1,
            border_color=tokens["border"],
            corner_radius=8,
        )
        panel.pack(fill="both", expand=True, padx=0, pady=0)
        if window_key:
            self._register_secondary_window(window_key, window)
        if bring_to_front:
            self._focus_secondary_window(window)
        return window, panel, tokens

    def _accion_estado_discos(self):
        """Muestra visualmente el espacio ocupado en cada disco."""
        window_key = "estado_almacenamiento"
        if self._focus_secondary_window(window_key):
            return
        win = ctk.CTkToplevel(self)
        win.title("Estado de Almacenamiento")
        win.geometry("400x300")
        self._register_secondary_window(window_key, win)
        try:
            win.attributes("-topmost", True)

            def release_storage_topmost():
                try:
                    if win.winfo_exists():
                        win.attributes("-topmost", False)
                except Exception:
                    pass

            win.after(300, release_storage_topmost)
        except Exception:
            pass
        win.resizable(True, True)
        
        # Centrar
        win.update_idletasks()
        x = (self.winfo_screenwidth() - 400) // 2
        y = (self.winfo_screenheight() - 300) // 2
        win.geometry(f"+{x}+{y}")
        try:
            self._focus_secondary_window(win)
        except Exception:
            pass

        ctk.CTkLabel(win, text="Unidades de Disco", font=("Segoe UI", 16, "bold")).pack(pady=15)

        disks = [
            disk for disk in self._get_local_disk_status()
            if disk.get("kind", "volume") == "volume" and str(disk.get("drive", "")).endswith("\\")
        ]

        for disk in disks:
            try:
                drive = disk["drive"]
                total_gb = disk["total_gb"]
                free_gb = disk["free_gb"]
                used_pct = disk["used_pct"]
                
                # Frame fila
                f = ctk.CTkFrame(win, fg_color="transparent")
                f.pack(fill="x", padx=20, pady=5)
                
                # Texto: C:\ - 50GB Libres de 100GB
                txt = f"{drive}  Libre: {free_gb:.1f} GB  (Total: {total_gb:.1f} GB)"
                ctk.CTkLabel(f, text=txt, font=("Consolas", 12), anchor="w").pack(fill="x")
                
                # Barra de progreso
                # Color: Rojo si queda menos del 10% (uso > 0.9), Azul si está bien
                color = self.colors["danger"] if used_pct > 0.9 else self.colors["accent"]
                
                prog = ctk.CTkProgressBar(f, progress_color=color)
                prog.set(used_pct)
                prog.pack(fill="x", pady=(2, 5))
                
            except: pass
            
        ctk.CTkButton(
            win,
            text="Cerrar",
            command=win.destroy,
            height=34,
            width=128,
            fg_color=self.colors["muted"],
            hover_color="#4B5563",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=12, side="bottom")

    def _accion_top_procesos(self):
        """Muestra los 5 procesos que más consumen CPU/RAM."""
        window_key = "top_procesos"
        if self._focus_secondary_window(window_key):
            return
        win, panel, tokens = self._create_legacy_panel_window(
            "Top Procesos (Snapshot)",
            560,
            480,
            resizable=True,
            minsize=(480, 360),
            temporary_topmost=True,
            window_key=window_key,
        )

        ctk.CTkFrame(panel, height=4, fg_color=tokens["accent"], corner_radius=3).pack(
            fill="x", padx=16, pady=(14, 0)
        )
        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Top Procesos",
            font=("Segoe UI", 20, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        lbl_status = ctk.CTkLabel(
            header,
            text="Analizando procesos...",
            font=("Segoe UI", 12, "bold"),
            text_color=tokens["muted"],
            anchor="w",
        )
        lbl_status.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        textbox = ctk.CTkTextbox(
            panel,
            font=("Consolas", 12),
            border_width=1,
            border_color=tokens["border"],
            fg_color=tokens["card"],
        )
        textbox.pack(fill="both", expand=True, padx=22, pady=(0, 14))

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.pack(fill="x", padx=22, pady=(0, 18))
        ctk.CTkButton(
            footer,
            text="Cerrar",
            width=130,
            height=38,
            fg_color=tokens["secondary"],
            hover_color=tokens["secondary_hover"],
            font=("Segoe UI", 12, "bold"),
            command=win.destroy,
        ).pack(side="right")
        
        def tarea_ps():
            # Script PS para sacar Top 5 CPU y Top 5 RAM
            cmd = """
            Write-Output "--- TOP 5 MEMORIA RAM ---"
            Get-Process | Sort-Object -Descending WS | Select-Object -First 5 Name, @{N='MB';E={[math]::Round($_.WS/1MB,1)}}, Id | Format-Table -AutoSize | Out-String
            
            Write-Output "`n--- TOP 5 CPU ---"
            Get-Process | Sort-Object -Descending CPU | Select-Object -First 5 Name, CPU, Id | Format-Table -AutoSize | Out-String
            """
            res, out = SysUtils.run_powershell(cmd, capture=True, timeout=15)

            def update_result():
                if not self._widget_exists(textbox):
                    return
                lbl_status.configure(text="Consumo de Recursos Actual" if res else "No se pudo analizar procesos")
                textbox.insert("0.0", out)
                textbox.configure(state="disabled")

            self._call_ui_thread(update_result)

        # Ejecutar en hilo para no congelar
        threading.Thread(target=tarea_ps, daemon=True).start()

    def _accion_ping_tool(self, preset_host=None, continuous=False):
        """Herramienta de ping moderna, con ping continuo y accesos comunes."""
        if preset_host:
            self._show_ping_result_window(preset_host, continuous, 2, "")
            return
        self._show_ping_result_window("", continuous, 2, "", show_add_panel=True)

    def _ping_target_dialog(self, preset_host=None, continuous=False, preset_name="", parent_window=None, on_submit=None, on_cancel=None):
        dialog_key = "ping_target"
        if self._focus_secondary_window(dialog_key):
            return None

        parent = parent_window if self._widget_exists(parent_window) else self
        dialog_width = 600
        dialog_height = 450
        dialog = ctk.CTkToplevel(parent)
        dialog.title("Ping")
        dialog.resizable(False, False)
        dialog.overrideredirect(True)
        dialog.configure(fg_color=(self.colors["panel_light"], self.colors["panel_dark"]))
        minimized = {"value": False}
        try:
            dialog.transient(parent)
        except Exception:
            pass
        try:
            parent.update_idletasks()
            x = parent.winfo_rootx() + max(20, (parent.winfo_width() - dialog_width) // 2)
            y = parent.winfo_rooty() + max(20, (parent.winfo_height() - dialog_height) // 2)
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            self._center_window(dialog, dialog_width, dialog_height)
        self._register_secondary_window(dialog_key, dialog)
        completed = {"value": False}

        panel = ctk.CTkFrame(
            dialog,
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=8,
        )
        panel.pack(fill="both", expand=True)

        accent_line = ctk.CTkFrame(panel, height=4, fg_color=self.colors["accent"], corner_radius=3)
        accent_line.pack(fill="x", padx=16, pady=(14, 0))

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 8))
        header.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkFrame(header, width=48, height=48, fg_color=("#E7F5F2", "#263432"), corner_radius=8)
        badge.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="n")
        badge.grid_propagate(False)
        ctk.CTkLabel(badge, text="PING", font=("Segoe UI", 12, "bold"), text_color=self.colors["accent"]).pack(fill="both", expand=True)

        title_lbl = ctk.CTkLabel(header, text="Ping", font=("Segoe UI", 20, "bold"), anchor="w")
        title_lbl.grid(row=0, column=1, sticky="ew")
        subtitle_lbl = ctk.CTkLabel(
            header,
            text="Introduce destino o usa Favoritos",
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["accent"],
            anchor="w",
        )
        subtitle_lbl.grid(row=1, column=1, sticky="ew")

        def close_dialog(event=None, notify_cancel=True):
            if completed["value"]:
                notify_cancel = False
            completed["value"] = True
            self._unregister_secondary_window(dialog_key)
            try:
                dialog.grab_release()
            except Exception:
                pass
            if self._widget_exists(dialog):
                dialog.destroy()
            if notify_cancel and callable(on_cancel):
                try:
                    on_cancel()
                except Exception:
                    pass

        def restore_dialog():
            minimized["value"] = False
            self._destroy_restore_chip(dialog_key)
            try:
                dialog.deiconify()
                try:
                    dialog.lift(parent)
                except Exception:
                    dialog.lift()
                dialog.after(80, focus_entry_once)
            except Exception:
                pass

        def show_restore_chip():
            self._show_restore_chip(
                dialog_key,
                text="Restaurar aviso: Ping",
                command=restore_dialog,
                panel_fg=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
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

        ctk.CTkButton(
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
        ).grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="ne")

        close_btn = ctk.CTkButton(
            header,
            text="x",
            width=42,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#E5E7EB", "#303034"),
            text_color=("gray25", "#E5E7EB"),
            font=("Segoe UI", 18, "bold"),
            command=close_dialog,
        )
        close_btn.grid(row=0, column=3, rowspan=2, padx=(6, 0), sticky="ne")
        self._enable_frameless_drag(dialog, panel, accent_line, header, badge, title_lbl, subtitle_lbl)

        ctk.CTkLabel(
            panel,
            text="IP o nombre DNS:",
            font=("Segoe UI", 13),
            text_color=("gray28", "gray78"),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(4, 8))

        entry_var = ctk.StringVar(value=preset_host or "")
        entry = ctk.CTkEntry(
            panel,
            height=42,
            textvariable=entry_var,
            font=("Segoe UI", 13),
            border_width=2,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
        )
        entry.pack(fill="x", padx=22, pady=(0, 8))

        ctk.CTkLabel(
            panel,
            text="Nombre del ping (opcional):",
            font=("Segoe UI", 13),
            text_color=("gray28", "gray78"),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(2, 8))

        name_var = ctk.StringVar(value=preset_name or "")
        name_entry = ctk.CTkEntry(
            panel,
            height=38,
            textvariable=name_var,
            font=("Segoe UI", 13),
            border_width=2,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            placeholder_text="Ej: Router principal, DNS, Core switch...",
        )
        name_entry.pack(fill="x", padx=22, pady=(0, 10))

        continuous_var = ctk.BooleanVar(value=bool(continuous))
        interval_var = ctk.StringVar(value="2")
        options_row = ctk.CTkFrame(panel, fg_color="transparent")
        options_row.pack(fill="x", padx=22, pady=(0, 8))
        ctk.CTkCheckBox(
            options_row,
            text="Ping continuo",
            variable=continuous_var,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
        ).pack(side="left")
        ctk.CTkLabel(
            options_row,
            text="Intervalo:",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray35", "gray72"),
        ).pack(side="left", padx=(18, 6))
        ctk.CTkOptionMenu(
            options_row,
            values=["1", "2", "3", "5", "10", "15", "30", "60"],
            variable=interval_var,
            width=82,
            height=32,
            fg_color="#4B5563",
            button_color=self.colors["accent"],
            button_hover_color=self.colors["accent_hover"],
        ).pack(side="left")
        ctk.CTkLabel(
            options_row,
            text="segundos",
            font=("Segoe UI", 12),
            text_color=("gray35", "gray72"),
        ).pack(side="left", padx=(6, 0))
        error_lbl = ctk.CTkLabel(panel, text="", text_color="#DC2626", font=("Segoe UI", 11, "bold"), anchor="w")
        error_lbl.pack(fill="x", padx=22, pady=(0, 2))

        def accept_host(host_value=None, name_value=None):
            host = (host_value or entry_var.get()).strip()
            if not SysUtils.is_valid_host(host):
                entry.configure(border_color="#DC2626")
                error_lbl.configure(text="Introduce una IP o nombre DNS valido.")
                entry.focus_set()
                return
            display_name = (name_var.get() if name_value is None else name_value or "").strip()
            if display_name and not SysUtils.is_plain_value(display_name, max_len=60):
                name_entry.configure(border_color="#DC2626")
                error_lbl.configure(text="El nombre no puede contener saltos de linea ni superar 60 caracteres.")
                name_entry.focus_set()
                return
            try:
                interval = max(1, int(interval_var.get()))
            except Exception:
                interval = 2
            request = {
                "host": host,
                "name": display_name,
                "continuous": bool(continuous_var.get()),
                "interval": interval,
            }
            close_dialog(notify_cancel=False)
            if callable(on_submit):
                try:
                    on_submit(request)
                except Exception:
                    pass

        def open_common_targets():
            try:
                dialog.grab_release()
            except Exception:
                pass
            self._show_common_ping_targets(
                notify=lambda message, _kind="info": error_lbl.configure(text=message),
                parent_window=dialog,
                on_select=lambda selected: accept_host(selected["host"], selected.get("name", "")),
            )
            if self._widget_exists(dialog):
                try:
                    dialog.lift(parent)
                except Exception:
                    pass

        btn_frame = ctk.CTkFrame(panel, fg_color="transparent", height=58)
        btn_frame.pack(side="bottom", fill="x", padx=22, pady=(8, 18))
        btn_frame.pack_propagate(False)

        ctk.CTkButton(
            btn_frame,
            text="Favoritos",
            command=open_common_targets,
            fg_color="#4B5563",
            hover_color="#374151",
            width=132,
            height=38,
        ).pack(side="left", pady=8)
        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=close_dialog,
            fg_color="#6B7280",
            hover_color="#4B5563",
            width=126,
            height=38,
        ).pack(side="right", padx=(8, 0), pady=8)
        ctk.CTkButton(
            btn_frame,
            text="Aceptar",
            command=lambda: accept_host(),
            width=126,
            height=38,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
        ).pack(side="right", pady=8)

        dialog.bind("<Return>", lambda _event=None: accept_host())
        dialog.bind("<Escape>", close_dialog)

        def focus_entry_once():
            if minimized["value"] or not self._widget_exists(dialog) or not self._widget_exists(entry):
                return
            try:
                entry.configure(state="normal")
                entry.focus_set()
                entry.icursor("end")
            except Exception:
                pass

        try:
            dialog.lift(parent)
        except Exception:
            try:
                dialog.lift()
            except Exception:
                pass
        dialog.after_idle(focus_entry_once)
        return dialog

    def _ping_favorites_path(self):
        return os.path.join(SysUtils.app_data_dir(), "ping_favorites.json")

    def _load_ping_favorites(self):
        try:
            with open(self._ping_favorites_path(), "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            data = []
        if isinstance(data, dict):
            data = data.get("favorites", [])
        favorites = []
        seen = set()
        for item in data if isinstance(data, list) else []:
            host = str(item.get("host") if isinstance(item, dict) else item).strip()
            name = str(item.get("name", "") if isinstance(item, dict) else "").strip()
            key = host.lower()
            if host and SysUtils.is_valid_host(host) and key not in seen:
                seen.add(key)
                favorites.append({"name": name[:60], "host": host})
        return favorites

    def _save_ping_favorites(self, favorites):
        clean = []
        seen = set()
        for item in favorites:
            host = str(item.get("host") if isinstance(item, dict) else item).strip()
            name = str(item.get("name", "") if isinstance(item, dict) else "").strip()
            key = host.lower()
            if host and SysUtils.is_valid_host(host) and key not in seen:
                seen.add(key)
                clean.append({"name": name[:60], "host": host})
        try:
            with open(self._ping_favorites_path(), "w", encoding="utf-8") as handle:
                json.dump({"favorites": clean}, handle, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _add_ping_favorite(self, host, name="", notify=None):
        host = (host or "").strip()
        name = (name or "").strip()[:60]

        def notify_user(inline_message, kind="info", modal_message=None):
            if callable(notify):
                try:
                    notify(inline_message, kind)
                    return
                except Exception:
                    pass

        if not SysUtils.is_valid_host(host):
            notify_user("Destino no valido.", "error", "Introduce una IP o nombre DNS valido.")
            return False
        if name and not SysUtils.is_plain_value(name, max_len=60):
            notify_user("Nombre de favorito no valido.", "error", "El nombre del favorito no es valido.")
            return False
        favorites = self._load_ping_favorites()
        for item in favorites:
            if item.get("host", "").lower() == host.lower():
                if name and item.get("name", "") != name:
                    item["name"] = name
                    if self._save_ping_favorites(favorites):
                        notify_user(
                            "Favorito actualizado.",
                            "success",
                            f"{name} ({host}) se ha actualizado en Favoritos.",
                        )
                        return True
                notify_user("Ya estaba en Favoritos.", "info", f"{host} ya esta guardado en Favoritos.")
                return True
        favorites.append({"name": name, "host": host})
        if self._save_ping_favorites(favorites):
            label = f"{name} ({host})" if name else host
            notify_user("Añadido a Favoritos.", "success", f"{label} se ha guardado en Favoritos.")
            return True
        notify_user("No se pudo guardar el favorito.", "error", "No se pudo guardar el favorito.")
        return False

    def _delete_ping_favorite(self, host):
        host = (host or "").strip().lower()
        if not host:
            return False
        favorites = self._load_ping_favorites()
        remaining = [item for item in favorites if item.get("host", "").lower() != host]
        if len(remaining) == len(favorites):
            return False
        return self._save_ping_favorites(remaining)

    def _show_common_ping_targets(self, notify=None, parent_window=None, on_select=None):
        dialog_key = "ping_favoritos"
        parent = parent_window if self._widget_exists(parent_window) else self

        existing_dialog = self._get_secondary_window(dialog_key)
        if self._widget_exists(existing_dialog):
            self._focus_secondary_window(existing_dialog)
            return None

        targets = self._load_ping_favorites()
        if not targets:
            if callable(notify):
                notify("Todavia no hay pings guardados en Favoritos.", "info")
            return None

        width = 560
        visible_rows = min(max(len(targets), 3), 5)
        height = min(580, max(360, 178 + visible_rows * 74))
        dialog = ctk.CTkToplevel(parent)
        dialog.title("Favoritos")
        dialog.resizable(False, False)
        dialog.overrideredirect(True)
        dialog.configure(fg_color=(self.colors["panel_light"], self.colors["panel_dark"]))
        try:
            dialog.transient(parent)
        except Exception:
            pass
        try:
            parent.update_idletasks()
            x = parent.winfo_rootx() + max(20, (parent.winfo_width() - width) // 2)
            y = parent.winfo_rooty() + max(20, (parent.winfo_height() - height) // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            self._center_window(dialog, width, height)
        self._register_secondary_window(dialog_key, dialog)

        panel = ctk.CTkFrame(
            dialog,
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=8,
        )
        panel.pack(fill="both", expand=True)
        accent_line = ctk.CTkFrame(panel, height=4, fg_color=self.colors["accent"], corner_radius=3)
        accent_line.pack(fill="x", padx=16, pady=(14, 0))

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        title_lbl = ctk.CTkLabel(header, text="Favoritos", font=("Segoe UI", 20, "bold"), anchor="w")
        title_lbl.grid(row=0, column=0, sticky="ew")
        subtitle_lbl = ctk.CTkLabel(
            header,
            text="Pulsa una caja para lanzar ping directamente",
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["accent"],
            anchor="w",
        )
        subtitle_lbl.grid(row=1, column=0, sticky="ew")

        def close_dialog(event=None):
            self._unregister_secondary_window(dialog_key)
            try:
                dialog.grab_release()
            except Exception:
                pass
            if self._widget_exists(dialog):
                dialog.destroy()

        def restore_dialog():
            self._destroy_restore_chip(dialog_key)
            try:
                dialog.deiconify()
                self._focus_secondary_window(dialog)
            except Exception:
                pass

        def show_restore_chip():
            self._show_restore_chip(
                dialog_key,
                text="Restaurar aviso: Favoritos",
                command=restore_dialog,
                panel_fg=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                window=dialog,
                close_command=close_dialog,
            )

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

        ctk.CTkButton(
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
        ).grid(row=0, column=1, rowspan=2, padx=(8, 0), sticky="ne")

        ctk.CTkButton(
            header,
            text="x",
            width=42,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#E5E7EB", "#303034"),
            text_color=("gray25", "#E5E7EB"),
            font=("Segoe UI", 18, "bold"),
            command=close_dialog,
        ).grid(row=0, column=2, rowspan=2, padx=(6, 0), sticky="ne")
        self._enable_frameless_drag(dialog, panel, accent_line, header, title_lbl, subtitle_lbl)

        dialog_notice = ctk.CTkLabel(
            panel,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color=("gray35", "gray72"),
            anchor="w",
        )
        dialog_notice.pack(fill="x", padx=22, pady=(0, 6))
        dialog_notice_after = {"id": None}

        def show_favorites_notice(message, kind="info"):
            if not self._widget_exists(dialog_notice):
                return
            after_id = dialog_notice_after.get("id")
            if after_id:
                try:
                    dialog_notice.after_cancel(after_id)
                except Exception:
                    pass
                dialog_notice_after["id"] = None
            color_map = {
                "success": self.colors.get("success", "#16803C"),
                "error": self.colors.get("danger", "#B42318"),
                "warning": self.colors.get("warning", "#D97706"),
                "info": self.colors.get("accent", "#2F9E8F"),
            }
            dialog_notice.configure(text=message, text_color=color_map.get(kind, color_map["info"]))

            def clear_notice():
                dialog_notice_after["id"] = None
                if self._widget_exists(dialog_notice):
                    dialog_notice.configure(text="")

            dialog_notice_after["id"] = dialog_notice.after(3500, clear_notice)

        body_height = max(190, height - 198)
        body = ctk.CTkScrollableFrame(panel, fg_color="transparent", height=body_height)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        try:
            body.pack_propagate(False)
        except Exception:
            pass
        body.grid_columnconfigure(0, weight=1)

        def choose(target):
            close_dialog()
            if callable(on_select):
                try:
                    on_select(target)
                except Exception:
                    pass

        def reindex_favorite_cards():
            try:
                cards = [child for child in body.winfo_children() if child.winfo_exists()]
                for idx, child in enumerate(cards):
                    child.grid_configure(row=idx)
            except Exception:
                pass

        def delete_target(target, card_widget):
            host = target.get("host", "")
            if not self._delete_ping_favorite(host):
                show_favorites_notice("No se pudo borrar el favorito.", "error")
                return
            try:
                if target in targets:
                    targets.remove(target)
            except Exception:
                pass
            try:
                if card_widget.winfo_exists():
                    card_widget.destroy()
            except Exception:
                pass
            reindex_favorite_cards()
            if not targets:
                close_dialog()
                if callable(notify):
                    notify("No quedan favoritos guardados.", "info")
            else:
                show_favorites_notice("Favorito borrado.", "success")

        for row, target in enumerate(targets):
            target_name = (target.get("name") or "").strip()
            target_host = target.get("host", "")
            card = ctk.CTkFrame(
                body,
                fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                border_width=1,
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                corner_radius=8,
            )
            card.grid(row=row, column=0, sticky="ew", padx=4, pady=5)
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)
            name_lbl = ctk.CTkLabel(card, text=target_name or target_host, font=("Segoe UI", 14, "bold"), anchor="w")
            name_lbl.grid(row=0, column=0, padx=14, pady=(10, 0), sticky="ew")
            host_lbl = ctk.CTkLabel(
                card,
                text=target_host if target_name else "Sin nombre personalizado",
                font=("Consolas", 12),
                text_color=("gray35", "gray72"),
                anchor="w",
            )
            host_lbl.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="ew")
            delete_btn = ctk.CTkButton(
                card,
                text="Borrar",
                width=86,
                height=34,
                fg_color=self.colors["danger"],
                hover_color="#8F1D14",
                command=lambda t=target, c=card: delete_target(t, c),
            )
            delete_btn.grid(row=0, column=1, rowspan=2, padx=(10, 14), pady=14, sticky="e")

            def on_enter(event=None, widget=card):
                widget.configure(fg_color=("#EEF7F5", "#2B3031"), border_color=self.colors["accent"])

            def on_leave(event=None, widget=card):
                widget.configure(
                    fg_color=(self.colors["card_light"], self.colors["card_dark"]),
                    border_color=(self.colors["border_light"], self.colors["border_dark"]),
                )

            for widget in (card, name_lbl, host_lbl):
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
            self._make_clickable((card, name_lbl, host_lbl), lambda t=target: choose(t))

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkButton(
            footer,
            text="Cerrar",
            width=118,
            height=36,
            fg_color="#6B7280",
            hover_color="#4B5563",
            command=close_dialog,
        ).pack(side="right")

        dialog.bind("<Escape>", close_dialog)
        self._focus_secondary_window(dialog)
        return dialog

    def _get_common_ping_targets(self):
        script = r"""
        $seen = @{}
        $configs = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
            Where-Object { $_.IPv4Address -and ($_.IPv4DefaultGateway -or $_.DNSServer.ServerAddresses) }
        foreach ($cfg in $configs) {
            if ($cfg.IPv4DefaultGateway.NextHop) {
                $gw = [string]$cfg.IPv4DefaultGateway.NextHop
                if ($gw -match '^\d{1,3}(\.\d{1,3}){3}$' -and -not $seen.ContainsKey("GW|$gw")) {
                    $seen["GW|$gw"] = $true
                    "Puerta de enlace|$gw"
                }
            }
            $index = 1
            foreach ($dns in @($cfg.DNSServer.ServerAddresses)) {
                $dnsText = [string]$dns
                if ($dnsText -match '^\d{1,3}(\.\d{1,3}){3}$' -and -not $seen.ContainsKey("DNS|$dnsText")) {
                    $seen["DNS|$dnsText"] = $true
                    "DNS $index|$dnsText"
                    $index++
                }
            }
        }
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=12)
        if not ok:
            return []
        targets = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if "|" not in line:
                continue
            name, host = line.split("|", 1)
            host = host.strip()
            if SysUtils.is_valid_host(host):
                targets.append({"name": name.strip(), "host": host})
        return targets

    def _show_ping_result_window(self, input_host="", continuous=False, interval=2, name="", show_add_panel=False):
        """Monitor multi-ping con tarjetas reanudables y frecuencia configurable."""
        window_key = "ping_monitor"
        if self._focus_secondary_window(window_key):
            return

        win = ctk.CTkToplevel(self)
        win.title("Monitor de ping")
        win.geometry("1040x660")
        win.minsize(640, 430)
        win.resizable(True, True)
        win.update_idletasks()
        self._center_window(win, 1040, 660)
        self._register_secondary_window(window_key, win)

        monitor = {
            "cards": [],
            "closed": False,
            "default_continuous": bool(continuous),
            "default_interval": max(1, int(interval or 2)),
            "columns": 1,
            "card_width": 372,
            "card_height": 314,
            "reflow_after": None,
            "stop_all_button": None,
        }

        success_fg = ("#EAF7EE", "#123322")
        success_border = ("#25A55B", "#38D67A")
        success_text = ("#14532D", "#BBF7D0")
        error_fg = ("#FDECEC", "#3A1515")
        error_border = ("#DC2626", "#EF4444")
        error_text = ("#7F1D1D", "#FECACA")
        neutral_fg = (self.colors["card_light"], self.colors["card_dark"])
        neutral_border = (self.colors["border_light"], self.colors["border_dark"])
        neutral_text = ("gray25", "gray82")

        root = ctk.CTkFrame(
            win,
            fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=8,
        )
        root.pack(fill="both", expand=True, padx=12, pady=12)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Monitor de ping",
            font=("Segoe UI", 24, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            header,
            text="Ejecuta varios pings a la vez. Verde indica respuesta, rojo indica perdida o error.",
            font=("Segoe UI", 12),
            text_color=("gray35", "gray70"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 0))

        toolbar = ctk.CTkFrame(root, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 10))
        toolbar.grid_columnconfigure(4, weight=1)
        monitor_notice = ctk.CTkLabel(
            toolbar,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color=("gray35", "gray72"),
            anchor="e",
        )
        monitor_notice.grid(row=0, column=4, sticky="e")
        monitor_notice_after = {"id": None}

        def show_monitor_notice(message, kind="info"):
            if not self._widget_exists(monitor_notice):
                return
            after_id = monitor_notice_after.get("id")
            if after_id:
                try:
                    monitor_notice.after_cancel(after_id)
                except Exception:
                    pass
                monitor_notice_after["id"] = None
            color_map = {
                "success": self.colors.get("success", "#16803C"),
                "error": self.colors.get("danger", "#B42318"),
                "warning": self.colors.get("warning", "#D97706"),
                "info": self.colors.get("accent", "#2F9E8F"),
            }
            monitor_notice.configure(text=message, text_color=color_map.get(kind, color_map["info"]))

            def clear_notice():
                monitor_notice_after["id"] = None
                if self._widget_exists(monitor_notice):
                    monitor_notice.configure(text="")

            monitor_notice_after["id"] = monitor_notice.after(3500, clear_notice)

        add_panel = ctk.CTkFrame(
            root,
            fg_color=(self.colors["card_light"], self.colors["card_dark"]),
            border_width=1,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            corner_radius=8,
        )
        add_panel.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        add_panel.grid_remove()
        add_panel.grid_columnconfigure(0, weight=1)
        add_panel.grid_columnconfigure(1, weight=1)

        inline_title = ctk.CTkLabel(
            add_panel,
            text="Añadir ping manual",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        )
        inline_title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 2))

        inline_error = ctk.CTkLabel(
            add_panel,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors.get("danger", "#DC2626"),
            anchor="w",
        )
        inline_error.grid(row=0, column=2, columnspan=3, sticky="ew", padx=14, pady=(12, 2))

        inline_host_var = ctk.StringVar(value="")
        inline_name_var = ctk.StringVar(value="")
        inline_continuous_var = ctk.BooleanVar(value=monitor["default_continuous"])
        inline_interval_var = ctk.StringVar(value=str(monitor["default_interval"]))

        ctk.CTkLabel(
            add_panel,
            text="IP o nombre DNS",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray30", "gray76"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=(14, 8), pady=(8, 4))
        ctk.CTkLabel(
            add_panel,
            text="Nombre del ping (opcional)",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray30", "gray76"),
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", padx=8, pady=(8, 4))

        inline_host_entry = ctk.CTkEntry(
            add_panel,
            height=36,
            textvariable=inline_host_var,
            font=("Segoe UI", 12),
            border_width=2,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
        )
        inline_host_entry.grid(row=2, column=0, sticky="ew", padx=(14, 8), pady=(0, 10))
        inline_name_entry = ctk.CTkEntry(
            add_panel,
            height=36,
            textvariable=inline_name_var,
            font=("Segoe UI", 12),
            border_width=2,
            border_color=(self.colors["border_light"], self.colors["border_dark"]),
            placeholder_text="Ej: Router principal, DNS, Core switch...",
        )
        inline_name_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 10))

        inline_options = ctk.CTkFrame(add_panel, fg_color="transparent")
        inline_options.grid(row=2, column=2, columnspan=3, sticky="e", padx=(8, 14), pady=(0, 10))
        ctk.CTkCheckBox(
            inline_options,
            text="Ping continuo",
            variable=inline_continuous_var,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            inline_options,
            text="Intervalo:",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray35", "gray72"),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(
            inline_options,
            values=["1", "2", "3", "5", "10", "15", "30", "60"],
            variable=inline_interval_var,
            width=78,
            height=32,
            fg_color="#4B5563",
            button_color=self.colors["accent"],
            button_hover_color=self.colors["accent_hover"],
        ).pack(side="left")
        ctk.CTkLabel(
            inline_options,
            text="s",
            font=("Segoe UI", 12),
            text_color=("gray35", "gray72"),
        ).pack(side="left", padx=(5, 0))

        inline_buttons = ctk.CTkFrame(add_panel, fg_color="transparent")
        inline_buttons.grid(row=3, column=0, columnspan=5, sticky="ew", padx=14, pady=(0, 12))

        def reset_inline_borders():
            inline_host_entry.configure(border_color=(self.colors["border_light"], self.colors["border_dark"]))
            inline_name_entry.configure(border_color=(self.colors["border_light"], self.colors["border_dark"]))

        def focus_inline_host():
            if not self._widget_exists(inline_host_entry):
                return
            try:
                inline_host_entry.configure(state="normal")
                inline_host_entry.focus_set()
                inline_host_entry.icursor("end")
            except Exception:
                pass

        def show_inline_add_panel():
            reset_inline_borders()
            inline_error.configure(text="")
            inline_continuous_var.set(bool(monitor["default_continuous"]))
            inline_interval_var.set(str(monitor["default_interval"]))
            try:
                add_panel.grid()
            except Exception:
                pass
            win.after_idle(focus_inline_host)

        def hide_inline_add_panel():
            inline_error.configure(text="")
            reset_inline_borders()
            try:
                add_panel.grid_remove()
            except Exception:
                pass

        def submit_inline_ping(host_value=None, name_value=None):
            reset_inline_borders()
            host = (host_value if host_value is not None else inline_host_var.get()).strip()
            if not SysUtils.is_valid_host(host):
                inline_host_entry.configure(border_color="#DC2626")
                inline_error.configure(text="Introduce una IP o nombre DNS válido.")
                focus_inline_host()
                return

            display_name = (name_value if name_value is not None else inline_name_var.get()).strip()
            if display_name and not SysUtils.is_plain_value(display_name, max_len=60):
                inline_name_entry.configure(border_color="#DC2626")
                inline_error.configure(text="El nombre no puede contener saltos de línea ni superar 60 caracteres.")
                try:
                    inline_name_entry.focus_set()
                except Exception:
                    pass
                return

            try:
                selected_interval = max(1, int(inline_interval_var.get()))
            except Exception:
                selected_interval = 2

            monitor["default_continuous"] = bool(inline_continuous_var.get())
            monitor["default_interval"] = selected_interval
            added = add_ping_card(host, monitor["default_continuous"], selected_interval, display_name)
            if added is False:
                inline_error.configure(text="Ping duplicado no añadido.")
                focus_inline_host()
                return
            if added:
                inline_host_var.set("")
                inline_name_var.set("")
                inline_error.configure(text="")
                show_monitor_notice(f"Ping añadido: {host}", "success")
                focus_inline_host()

        def open_inline_favorites():
            self._show_common_ping_targets(
                notify=lambda message, _kind="info": inline_error.configure(text=message),
                parent_window=win,
                on_select=lambda selected: submit_inline_ping(selected["host"], selected.get("name", "")),
            )

        ctk.CTkButton(
            inline_buttons,
            text="Favoritos",
            command=open_inline_favorites,
            fg_color="#4B5563",
            hover_color="#374151",
            width=118,
            height=34,
        ).pack(side="left")
        ctk.CTkButton(
            inline_buttons,
            text="Añadir",
            command=submit_inline_ping,
            width=116,
            height=34,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
        ).pack(side="right")
        ctk.CTkButton(
            inline_buttons,
            text="Cancelar",
            command=hide_inline_add_panel,
            fg_color="#6B7280",
            hover_color="#4B5563",
            width=116,
            height=34,
        ).pack(side="right", padx=(0, 8))

        inline_host_entry.bind("<Return>", lambda _event=None: submit_inline_ping())
        inline_name_entry.bind("<Return>", lambda _event=None: submit_inline_ping())

        cards_area = ctk.CTkScrollableFrame(root, fg_color="transparent")
        cards_area.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 12))

        def is_success_line(line):
            text = (line or "").lower()
            return (
                ("reply from" in text or "respuesta desde" in text or "bytes=" in text)
                and "unreachable" not in text
                and "inaccesible" not in text
                and "agotado" not in text
            )

        def is_failure_line(line):
            text = (line or "").lower()
            failure_tokens = (
                "request timed out",
                "tiempo de espera agotado",
                "host de destino inaccesible",
                "destination host unreachable",
                "could not find host",
                "no se pudo encontrar",
                "general failure",
                "error",
                "100% loss",
                "100% perdidos",
            )
            return any(token in text for token in failure_tokens)

        def state_colors(state):
            if state == "success":
                return success_fg, success_border, success_text
            if state == "error":
                return error_fg, error_border, error_text
            return neutral_fg, neutral_border, neutral_text

        def recolor_card(card_state, state):
            if not self._widget_exists(card_state.get("frame")):
                return
            fg, border, text_color = state_colors(state)
            card_state["frame"].configure(fg_color=fg, border_color=border)
            card_state["status"].configure(text_color=text_color)
            card_state["title"].configure(text_color=text_color)
            card_state["stats"].configure(text_color=text_color)
            card_state["textbox"].configure(fg_color=fg, text_color=text_color, border_color=border)

        def update_stop_all_button():
            button = monitor.get("stop_all_button")
            if not self._widget_exists(button):
                return
            has_running = any(card.get("running") for card in monitor["cards"])
            has_stopped = any(not card.get("running") for card in monitor["cards"])
            if has_running:
                button.configure(text="Detener todos", state="normal", fg_color=self.colors["danger"], hover_color="#8F1D14")
            elif has_stopped:
                button.configure(text="Reanudar todos", state="normal", fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"])
            else:
                button.configure(text="Detener todos", state="disabled", fg_color="#6B7280", hover_color="#4B5563")

        def append_line(card_state, raw_line):
            if not self._widget_exists(card_state.get("frame")):
                return
            line = raw_line.rstrip("\r\n")
            if not line:
                return

            stamp = time.strftime("%H:%M:%S")
            display_line = f"[{stamp}] {line}\n"

            if is_success_line(line):
                card_state["sent"] += 1
                card_state["received"] += 1
                card_state["last_state"] = "success"
                card_state["status"].configure(text="Responde")
                recolor_card(card_state, "success")
            elif is_failure_line(line):
                card_state["sent"] += 1
                card_state["lost"] += 1
                card_state["last_state"] = "error"
                card_state["status"].configure(text="Sin respuesta")
                recolor_card(card_state, "error")

            card_state["stats"].configure(
                text=f"Enviados: {card_state['sent']}  Recibidos: {card_state['received']}  Perdidos: {card_state['lost']}"
            )
            card_state["textbox"].configure(state="normal")
            card_state["textbox"].insert("end", display_line)
            card_state["textbox"].see("end")
            card_state["textbox"].configure(state="disabled")

        def configure_action_button(card_state, running):
            button = card_state["action_button"]
            if running:
                button.configure(
                    text="Stop",
                    state="normal",
                    fg_color=self.colors["danger"],
                    hover_color="#8F1D14",
                    command=lambda state=card_state: stop_card(state),
                )
            else:
                button.configure(
                    text="Reanudar",
                    state="normal",
                    fg_color=self.colors["accent"],
                    hover_color=self.colors["accent_hover"],
                    command=lambda state=card_state: resume_card(state),
                )

        def stop_card(card_state):
            if not card_state.get("running"):
                return
            card_state["cancelled"] = True
            process = card_state.get("process")
            if process and process.poll() is None:
                try:
                    process.terminate()
                except Exception:
                    pass
            if self._widget_exists(card_state.get("action_button")):
                card_state["action_button"].configure(state="disabled", text="Deteniendo")
            if self._widget_exists(card_state.get("status")):
                card_state["status"].configure(text="Deteniendo")
            recolor_card(card_state, "neutral")
            update_stop_all_button()

        def finish_card(card_state, cancelled=False, error_text=""):
            if not self._widget_exists(card_state.get("frame")):
                return
            card_state["running"] = False
            card_state["process"] = None
            if error_text:
                card_state["status"].configure(text="Error")
                recolor_card(card_state, "error")
            elif cancelled:
                card_state["status"].configure(text="Detenido")
                recolor_card(card_state, "neutral")
            elif card_state.get("last_state") == "success":
                card_state["status"].configure(text="Finalizado OK")
            elif card_state.get("last_state") == "error":
                card_state["status"].configure(text="Finalizado con perdida")
            else:
                card_state["status"].configure(text="Finalizado")
            configure_action_button(card_state, False)
            update_stop_all_button()

        def resume_card(card_state):
            if monitor["closed"] or card_state.get("running") or not self._widget_exists(card_state.get("frame")):
                return
            card_state["cancelled"] = False
            card_state["running"] = True
            configure_action_button(card_state, True)
            card_state["status"].configure(text="Ejecutando")
            append_line(card_state, f"Reanudando ping a {card_state['host']}")
            update_stop_all_button()
            threading.Thread(target=run_card_ping, args=(card_state,), daemon=True).start()

        def remove_card(card_state):
            stop_card(card_state)
            if self._widget_exists(card_state.get("frame")):
                card_state["frame"].destroy()
            if card_state in monitor["cards"]:
                monitor["cards"].remove(card_state)
            reflow_cards()
            update_stop_all_button()

        def columns_for_width():
            try:
                width = max(cards_area.winfo_width(), win.winfo_width() - 80)
            except Exception:
                width = 900
            card_slot = monitor["card_width"] + 24
            return max(1, min(4, int(width // card_slot)))

        def reflow_cards():
            columns = columns_for_width()
            monitor["columns"] = columns
            for column in range(4):
                cards_area.grid_columnconfigure(
                    column,
                    weight=0,
                    minsize=monitor["card_width"] if column < columns else 0,
                    uniform="",
                )
            for idx, card_state in enumerate(list(monitor["cards"])):
                if not self._widget_exists(card_state.get("frame")):
                    continue
                row = idx // columns
                column = idx % columns
                card_state["frame"].grid(row=row, column=column, sticky="nw", padx=8, pady=8)

        def schedule_reflow(event=None):
            after_id = monitor.get("reflow_after")
            if after_id:
                try:
                    win.after_cancel(after_id)
                except Exception:
                    pass
            monitor["reflow_after"] = win.after(120, reflow_cards)

        def wait_interval(card_state):
            end_at = time.time() + max(1, int(card_state.get("interval", 2)))
            while time.time() < end_at:
                if monitor["closed"] or card_state["cancelled"]:
                    return
                time.sleep(0.1)

        def run_process(card_state, command):
            def append_stderr(err):
                if not card_state["cancelled"]:
                    for line in err.splitlines():
                        self._call_ui_thread(append_line, card_state, line)

            self._run_ping_subprocess(
                command,
                card_state,
                lambda: monitor["closed"] or card_state["cancelled"],
                lambda line: self._call_ui_thread(append_line, card_state, line),
                append_stderr,
                terminate_after_output=True,
                wait_timeout=3,
                ignore_wait_errors=True,
            )

        def run_card_ping(card_state):
            host = card_state["host"]
            is_continuous = card_state["continuous"]
            self._call_ui_thread(card_state["status"].configure, text="Ejecutando")
            self._call_ui_thread(recolor_card, card_state, "neutral")
            try:
                if is_continuous:
                    while not monitor["closed"] and not card_state["cancelled"]:
                        run_process(card_state, ["ping", "-n", "1", "-w", "1200", host])
                        if monitor["closed"] or card_state["cancelled"]:
                            break
                        wait_interval(card_state)
                else:
                    run_process(card_state, ["ping", "-n", "4", host])
                self._call_ui_thread(finish_card, card_state, card_state["cancelled"], "")
            except Exception as exc:
                self._call_ui_thread(append_line, card_state, f"Error: {exc}")
                self._call_ui_thread(finish_card, card_state, False, str(exc))

        def ask_ping_duplicate(host):
            dialog_key = self._secondary_key("ping_duplicate", host)
            existing = self._get_secondary_window(dialog_key)
            if self._widget_exists(existing):
                self._focus_secondary_window(existing, topmost_ms=300)
                return False

            result = {"value": False}
            dialog_width = 520
            dialog_height = 238
            dialog = ctk.CTkToplevel(win)
            dialog.title("Ping duplicado")
            dialog.resizable(False, False)
            dialog.overrideredirect(True)
            dialog.configure(fg_color=(self.colors["panel_light"], self.colors["panel_dark"]))
            try:
                dialog.transient(win)
            except Exception:
                pass
            try:
                win.update_idletasks()
                x = win.winfo_rootx() + max(20, (win.winfo_width() - dialog_width) // 2)
                y = win.winfo_rooty() + max(20, (win.winfo_height() - dialog_height) // 2)
                dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            except Exception:
                self._center_window(dialog, dialog_width, dialog_height)
            self._register_secondary_window(dialog_key, dialog)

            panel = ctk.CTkFrame(
                dialog,
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_width=1,
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                corner_radius=8,
            )
            panel.pack(fill="both", expand=True)
            ctk.CTkFrame(panel, height=4, fg_color=self.colors["warning"], corner_radius=3).pack(
                fill="x", padx=16, pady=(14, 0)
            )
            ctk.CTkLabel(
                panel,
                text="Ping duplicado",
                font=("Segoe UI", 18, "bold"),
                anchor="w",
            ).pack(fill="x", padx=22, pady=(18, 6))
            ctk.CTkLabel(
                panel,
                text=f"Ya tienes un ping agregado para:\n\n{host}\n\n¿Quieres añadirlo igualmente?",
                font=("Segoe UI", 13),
                text_color=("gray25", "gray82"),
                justify="left",
                anchor="w",
                wraplength=460,
            ).pack(fill="x", padx=22, pady=(0, 12))

            button_row = ctk.CTkFrame(panel, fg_color="transparent")
            button_row.pack(fill="x", padx=22, pady=(0, 18))

            def close_with(value=False):
                result["value"] = bool(value)
                self._destroy_restore_chip(dialog_key)
                if self._widget_exists(dialog):
                    dialog.destroy()

            ctk.CTkButton(
                button_row,
                text="No",
                width=126,
                height=36,
                fg_color="#6B7280",
                hover_color="#4B5563",
                command=lambda: close_with(False),
            ).pack(side="right", padx=(8, 0))
            ctk.CTkButton(
                button_row,
                text="Sí, añadir",
                width=136,
                height=36,
                fg_color=self.colors["accent"],
                hover_color=self.colors["accent_hover"],
                command=lambda: close_with(True),
            ).pack(side="right")

            def focus_duplicate_dialog():
                if not self._widget_exists(dialog):
                    return
                try:
                    dialog.deiconify()
                except Exception:
                    pass
                try:
                    dialog.lift(win)
                except Exception:
                    try:
                        dialog.lift()
                    except Exception:
                        pass
                try:
                    dialog.focus_force()
                except Exception:
                    try:
                        dialog.focus_set()
                    except Exception:
                        pass
                try:
                    dialog.attributes("-topmost", True)

                    def release_topmost():
                        try:
                            if dialog.winfo_exists():
                                dialog.attributes("-topmost", False)
                        except Exception:
                            pass

                    dialog.after(300, release_topmost)
                except Exception:
                    pass

            dialog.protocol("WM_DELETE_WINDOW", lambda: close_with(False))
            dialog.bind("<Escape>", lambda _event=None: close_with(False))
            dialog.bind("<Return>", lambda _event=None: close_with(True))
            focus_duplicate_dialog()
            self.wait_window(dialog)
            return result["value"]

        def add_ping_card(host, is_continuous=True, ping_interval=2, display_name=""):
            host = (host or "").strip()
            display_name = (display_name or "").strip()[:60]
            if not SysUtils.is_valid_host(host):
                show_monitor_notice("Introduce una IP o nombre DNS valido.", "error")
                return None

            duplicates = [card for card in monitor["cards"] if card.get("host", "").lower() == host.lower()]
            if duplicates:
                keep = ask_ping_duplicate(host)
                if not keep:
                    return False

            card = ctk.CTkFrame(
                cards_area,
                fg_color=neutral_fg,
                border_width=2,
                border_color=neutral_border,
                corner_radius=8,
            )
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
            top.grid_columnconfigure(0, weight=1)
            title = ctk.CTkLabel(
                top,
                text=display_name or host,
                font=("Segoe UI", 18, "bold"),
                anchor="w",
            )
            title.grid(row=0, column=0, sticky="ew")
            status = ctk.CTkLabel(
                top,
                text="Preparando",
                font=("Segoe UI", 12, "bold"),
                text_color=self.colors["accent"],
                anchor="e",
            )
            status.grid(row=0, column=1, padx=(8, 0), sticky="e")
            host_label = ctk.CTkLabel(
                top,
                text=f"IP: {host}" if display_name else "",
                font=("Consolas", 12, "bold"),
                text_color=("gray35", "gray72"),
                anchor="w",
            )
            host_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))

            textbox = ctk.CTkTextbox(
                card,
                height=142,
                width=monitor["card_width"] - 24,
                font=("Consolas", 10),
                corner_radius=8,
                border_width=1,
                border_color=neutral_border,
                fg_color=neutral_fg,
                text_color=neutral_text,
            )
            textbox.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
            textbox.configure(state="disabled")

            bottom = ctk.CTkFrame(card, fg_color="transparent")
            bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
            bottom.grid_columnconfigure(0, weight=1)
            stats = ctk.CTkLabel(
                bottom,
                text="Enviados: 0  Recibidos: 0  Perdidos: 0",
                font=("Segoe UI", 12, "bold"),
                anchor="w",
            )
            stats.grid(row=0, column=0, sticky="ew", pady=(0, 8))

            favorite_notice = ctk.CTkLabel(
                bottom,
                text="",
                font=("Segoe UI", 11, "bold"),
                text_color=("gray35", "gray72"),
                anchor="w",
            )
            favorite_notice.grid(row=1, column=0, sticky="ew", pady=(0, 6))
            favorite_notice_after = {"id": None}

            def show_favorite_notice(message, kind="info"):
                if not self._widget_exists(favorite_notice):
                    return
                after_id = favorite_notice_after.get("id")
                if after_id:
                    try:
                        favorite_notice.after_cancel(after_id)
                    except Exception:
                        pass
                    favorite_notice_after["id"] = None
                color_map = {
                    "success": self.colors.get("success", "#16803C"),
                    "error": self.colors.get("danger", "#B42318"),
                    "warning": self.colors.get("warning", "#D97706"),
                    "info": self.colors.get("accent", "#2F9E8F"),
                }
                favorite_notice.configure(text=message, text_color=color_map.get(kind, color_map["info"]))

                def clear_notice():
                    favorite_notice_after["id"] = None
                    if self._widget_exists(favorite_notice):
                        favorite_notice.configure(text="")

                favorite_notice_after["id"] = favorite_notice.after(3500, clear_notice)

            buttons = ctk.CTkFrame(bottom, fg_color="transparent")
            buttons.grid(row=2, column=0, columnspan=2, sticky="ew")
            buttons.grid_columnconfigure(0, weight=1)
            favorite_button = ctk.CTkButton(
                buttons,
                text="Añadir a Favoritos",
                width=156,
                height=32,
                fg_color="#4B5563",
                hover_color="#374151",
                command=lambda h=host, n=display_name: self._add_ping_favorite(h, n, notify=show_favorite_notice),
            )
            favorite_button.grid(row=0, column=0, sticky="w")
            action_button = ctk.CTkButton(
                buttons,
                text="Stop",
                width=82,
                height=32,
                fg_color=self.colors["danger"],
                hover_color="#8F1D14",
            )
            action_button.grid(row=0, column=1, padx=(8, 0), sticky="e")
            close_button = ctk.CTkButton(
                buttons,
                text="Cerrar",
                width=76,
                height=32,
                fg_color="#6B7280",
                hover_color="#4B5563",
            )
            close_button.grid(row=0, column=2, padx=(8, 0), sticky="e")

            card_state = {
                "frame": card,
                "title": title,
                "host_label": host_label,
                "status": status,
                "stats": stats,
                "textbox": textbox,
                "action_button": action_button,
                "close_button": close_button,
                "host": host,
                "name": display_name,
                "continuous": bool(is_continuous),
                "interval": max(1, int(ping_interval or 2)),
                "process": None,
                "running": True,
                "cancelled": False,
                "sent": 0,
                "received": 0,
                "lost": 0,
                "last_state": "neutral",
            }
            action_button.configure(command=lambda state=card_state: stop_card(state))
            close_button.configure(command=lambda state=card_state: remove_card(state))
            monitor["cards"].append(card_state)
            reflow_cards()
            mode_text = "continuo" if is_continuous else "normal"
            append_line(card_state, f"Inicio de ping {mode_text} a {host}")
            if is_continuous:
                append_line(card_state, f"Intervalo configurado: {card_state['interval']} segundos")
            update_stop_all_button()
            threading.Thread(target=run_card_ping, args=(card_state,), daemon=True).start()
            return True

        def add_host_from_dialog():
            show_inline_add_panel()

        def stop_or_resume_all():
            has_running = any(card.get("running") for card in monitor["cards"])
            if has_running:
                for card_state in list(monitor["cards"]):
                    if card_state.get("running"):
                        stop_card(card_state)
                return
            for card_state in list(monitor["cards"]):
                if not card_state.get("running"):
                    resume_card(card_state)

        def close_monitor():
            monitor["closed"] = True
            for card_state in list(monitor["cards"]):
                if card_state.get("running"):
                    stop_card(card_state)
            if self._widget_exists(win):
                win.destroy()

        ctk.CTkButton(
            toolbar,
            text="+ Añadir ping",
            width=132,
            height=36,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=add_host_from_dialog,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")
        stop_all_button = ctk.CTkButton(
            toolbar,
            text="Detener todos",
            width=142,
            height=36,
            fg_color=self.colors["danger"],
            hover_color="#8F1D14",
            command=stop_or_resume_all,
        )
        stop_all_button.grid(row=0, column=1, padx=(0, 8), sticky="w")
        monitor["stop_all_button"] = stop_all_button
        ctk.CTkButton(
            toolbar,
            text="Cerrar",
            width=110,
            height=36,
            fg_color="#6B7280",
            hover_color="#4B5563",
            command=close_monitor,
        ).grid(row=0, column=2, sticky="w")

        cards_area.bind("<Configure>", schedule_reflow, add="+")
        win.bind("<Configure>", schedule_reflow, add="+")
        win.protocol("WM_DELETE_WINDOW", close_monitor)
        input_host = (input_host or "").strip()
        if input_host:
            add_ping_card(input_host, continuous, monitor["default_interval"], name)
        if show_add_panel or not input_host:
            show_inline_add_panel()
        self._focus_secondary_window(win)

    def _show_popup_menu(self, anchor_widget, items):
        if hasattr(self, "tools_drawer") and self.tools_drawer.winfo_exists() and self.tools_drawer.winfo_ismapped():
            self._hide_tools_drawer()
            return

        self._ensure_tools_drawer()
        self._tools_drawer_anchor = anchor_widget
        self._tools_drawer_items = items
        self._render_tools_drawer_body(items, self._tools_drawer_needs_scroll(items))
        self.tools_drawer.place(x=246, y=14, relheight=0.94)
        self.tools_drawer.lift()
        self._install_tools_drawer_outside_close()

    def _hide_tools_drawer(self):
        if hasattr(self, "tools_drawer") and self.tools_drawer.winfo_exists():
            self.tools_drawer.place_forget()

    def _event_inside_widget(self, event, widget):
        if not widget or not widget.winfo_exists():
            return False
        try:
            widget.update_idletasks()
            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            right = left + widget.winfo_width()
            bottom = top + widget.winfo_height()
            return left <= event.x_root <= right and top <= event.y_root <= bottom
        except Exception:
            return False

    def _install_tools_drawer_outside_close(self):
        if getattr(self, "_tools_drawer_outside_bind_installed", False):
            return
        self.bind_all("<Button-1>", self._handle_tools_drawer_outside_click, add="+")
        self._tools_drawer_outside_bind_installed = True

    def _handle_tools_drawer_outside_click(self, event):
        if not hasattr(self, "tools_drawer") or not self.tools_drawer.winfo_exists() or not self.tools_drawer.winfo_ismapped():
            return
        if self._event_inside_widget(event, self.tools_drawer):
            return
        anchor = getattr(self, "_tools_drawer_anchor", None)
        if anchor is not None and self._event_inside_widget(event, anchor):
            return
        self._hide_tools_drawer()

    def _ensure_tools_drawer(self):
        if not hasattr(self, "tools_drawer") or not self.tools_drawer.winfo_exists():
            self.tools_drawer = ctk.CTkFrame(
                self.shell,
                width=286,
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_width=1,
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
                corner_radius=12,
            )
            self.tools_drawer.grid_propagate(False)
            self.tools_drawer.grid_columnconfigure(0, weight=1)
            self.tools_drawer.grid_rowconfigure(1, weight=1)
            self._tools_drawer_scroll_mode = None
            self._tools_drawer_resize_after = None

            header = ctk.CTkFrame(self.tools_drawer, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 7))
            header.grid_columnconfigure(0, weight=1)
            self.tools_drawer_title = ctk.CTkLabel(
                header,
                text="Herramientas",
                font=("Segoe UI", 15, "bold"),
                anchor="w",
                text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]),
            )
            self.tools_drawer_title.grid(row=0, column=0, sticky="ew")
            self.tools_drawer_subtitle = ctk.CTkLabel(
                header,
                text="Sistema, utilidades y Easy Deploy",
                font=("Segoe UI", 11),
                anchor="w",
                text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]),
            )
            self.tools_drawer_subtitle.grid(row=1, column=0, sticky="ew", pady=(1, 0))
            ctk.CTkButton(
                header,
                text="×",
                width=28,
                height=26,
                corner_radius=7,
                fg_color="transparent",
                hover_color=self.colors["sidebar_hover"],
                text_color=self.colors["sidebar_text"],
                command=self._hide_tools_drawer,
            ).grid(row=0, column=1, rowspan=2, sticky="ne")
            self.tools_drawer.bind("<Configure>", lambda event: self._schedule_tools_drawer_scroll_refresh())
        else:
            self.tools_drawer.configure(
                fg_color=(self.colors["panel_light"], self.colors["panel_dark"]),
                border_color=(self.colors["border_light"], self.colors["border_dark"]),
            )
            if self._widget_exists(getattr(self, "tools_drawer_title", None)):
                self.tools_drawer_title.configure(text_color=(self.colors["text_primary_light"], self.colors["text_primary_dark"]))
            if self._widget_exists(getattr(self, "tools_drawer_subtitle", None)):
                self.tools_drawer_subtitle.configure(text_color=(self.colors["text_muted_light"], self.colors["text_muted_dark"]))

    def _tools_drawer_estimated_height(self, items):
        height = 10
        for text, _cmd in items:
            height += 30 if text.startswith("---") else 36
        return height

    def _tools_drawer_needs_scroll(self, items):
        try:
            self.tools_drawer.update_idletasks()
            available_height = max(1, self.shell.winfo_height() - 86)
        except Exception:
            available_height = 700
        return self._tools_drawer_estimated_height(items) > available_height

    def _render_tools_drawer_body(self, items, use_scroll):
        if getattr(self, "_tools_drawer_scroll_mode", None) == use_scroll and hasattr(self, "tools_drawer_body"):
            for child in self.tools_drawer_body.winfo_children():
                child.destroy()
        else:
            if hasattr(self, "tools_drawer_body") and self.tools_drawer_body.winfo_exists():
                self.tools_drawer_body.destroy()
            if use_scroll:
                self.tools_drawer_body = ctk.CTkScrollableFrame(
                    self.tools_drawer,
                    fg_color="transparent",
                    scrollbar_button_color=(self.colors["border_light"], self.colors["border_dark"]),
                    scrollbar_button_hover_color=self.colors["sidebar_hover"],
                )
            else:
                self.tools_drawer_body = ctk.CTkFrame(self.tools_drawer, fg_color="transparent")
            self.tools_drawer_body.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
            self.tools_drawer_body.grid_columnconfigure(0, weight=1)
            self._tools_drawer_scroll_mode = use_scroll

        self._populate_tools_drawer_body(self.tools_drawer_body, items)

    def _populate_tools_drawer_body(self, target_parent, items):
        for text, cmd in items:
            if text.startswith("---"):
                section = text.strip("- ").strip()

                section_frame = ctk.CTkFrame(target_parent, fg_color="transparent")
                section_frame.pack(fill="x", padx=7, pady=(10, 4))
                section_frame.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(
                    section_frame,
                    text=section.upper() if section else "",
                    font=("Segoe UI", 9, "bold"),
                    text_color=self.colors["accent"],
                    anchor="w",
                ).grid(row=0, column=0, sticky="w", padx=(0, 8))
                ctk.CTkFrame(
                    section_frame,
                    height=1,
                    fg_color=(self.colors["border_light"], self.colors["border_dark"]),
                ).grid(row=0, column=1, sticky="ew")
                continue

            def run_command(c=cmd):
                self._hide_tools_drawer()
                c()

            button_color = "transparent"
            hover_color = self.colors["sidebar_hover"]
            text_color = (self.colors["text_primary_light"], self.colors["text_primary_dark"])
            if text == "Salir":
                text_color = ("#B42318", "#FCA5A5")
            elif text == "Reiniciar UI":
                text_color = ("#92400E", "#FCD34D")

            ctk.CTkButton(
                target_parent,
                text=text,
                anchor="w",
                height=32,
                corner_radius=7,
                fg_color=button_color,
                text_color=text_color,
                hover_color=hover_color,
                font=("Segoe UI", 12),
                border_spacing=7,
                command=run_command,
            ).pack(fill="x", padx=6, pady=1)

    def _schedule_tools_drawer_scroll_refresh(self):
        if not hasattr(self, "tools_drawer") or not self.tools_drawer.winfo_ismapped():
            return
        after_id = getattr(self, "_tools_drawer_resize_after", None)
        if after_id:
            try:
                self.tools_drawer.after_cancel(after_id)
            except Exception:
                pass
        self._tools_drawer_resize_after = self.tools_drawer.after(160, self._refresh_tools_drawer_scroll_mode)

    def _refresh_tools_drawer_scroll_mode(self):
        items = getattr(self, "_tools_drawer_items", None)
        if not items or not hasattr(self, "tools_drawer") or not self.tools_drawer.winfo_ismapped():
            return
        needs_scroll = self._tools_drawer_needs_scroll(items)
        if needs_scroll != getattr(self, "_tools_drawer_scroll_mode", None):
            self._render_tools_drawer_body(items, needs_scroll)

    def _menu_archivo_popup(self):
        items = [
            ("--- Sistema ---",    lambda: None),
            ("AD Users and Computers", self._open_ad_users_and_computers),
            ("DNS Manager",           self._open_dns_manager),
            ("Group Policy Management", self._open_group_policy_management),
            ("Abrir Logs/Temp",      self._accion_abrir_temp),

            ("--- Utilidades ---",    lambda: None),
            ("Forzar Políticas",      lambda: self.iniciar_tarea(self.task_gpupdate_force)),
            ("CMD",   self._open_admin_cmd),
            ("PowerShell", self._open_admin_powershell),

            ("--- Easy Deploy ---",    lambda: None),
            ("Versiones",             self._open_versions_view),
            ("Créditos",              self._open_creditos_dialog),
        ]
        self._show_popup_menu(self.btn_archivo, items)

    def _reiniciar_app(self):
        """Reinicia la aplicación lanzando un nuevo proceso y cerrando el actual."""
        if self.active_thread and self.active_thread.is_alive():
            if not self.ui_askyesno(
                "Reiniciar UI",
                "Hay una tarea en ejecucion.\n\n"
                "Para reiniciar la interfaz hay que cancelar primero la tarea actual.\n\n"
                "Quieres cancelarla y reiniciar Easy Deploy?",
            ):
                return
            self._request_active_process_cancel()

        env = os.environ.copy()
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        env["EASYDEPLOY_ALLOW_RESTART_INSTANCE"] = "1"
        for key in list(env):
            if key.startswith("_PYI_"):
                env.pop(key, None)

        try:
            if getattr(sys, "frozen", False):
                executable = sys.executable
                cwd = os.path.dirname(executable)
                subprocess.Popen([executable], cwd=cwd, env=env, close_fds=True)
            else:
                executable = sys.executable
                script_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "EASY DEPLOY.py")
                )
                subprocess.Popen([executable, script_path], cwd=os.path.dirname(script_path), env=env, close_fds=True)
        except Exception as exc:
            self.ui_showerror("Reiniciar UI", f"No se pudo reiniciar Easy Deploy:\n{exc}")
            return

        self.after(150, self.destroy)

    def _accion_teclado_es(self):
        """Cambia el teclado predeterminado de Windows a Español/España."""
        if getattr(self, "_keyboard_status", None) is True:
            self.ui_showinfo("Teclado ESP", "El teclado ya esta configurado como Español/España.")
            return

        self._set_tile_status(getattr(self, "keyboard_tile", None), "Cambiando...", self.colors["warning"])

        def worker():
            ok, detail = SysUtils.set_spanish_spain_keyboard()
            verified = SysUtils.is_spanish_spain_keyboard() if ok else False

            def finish():
                self._keyboard_status = bool(verified)
                self._keyboard_check_running = False
                self._update_environment_status()
                if verified:
                    self.ui_showinfo("Teclado ESP", "Teclado cambiado a Español/España correctamente.")
                else:
                    self.ui_showwarning(
                        "Teclado ESP",
                        "No se pudo confirmar el cambio de teclado.\n\n"
                        "Revisa la configuracion de idioma de Windows.\n\n"
                        f"Detalle: {detail or 'sin detalle'}",
                    )

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _accion_info_sistema(self):
        """Muestra sistema/red sin bloquear la ventana principal."""
        import socket
        window_key = "info_sistema"
        if self._focus_secondary_window(window_key):
            return

        loading = ctk.CTkToplevel(self)
        loading.title("Analizando sistema")
        loading.geometry("330x150")
        self._register_secondary_window(window_key, loading)
        try:
            loading.attributes("-topmost", True)

            def release_loading_topmost():
                try:
                    if loading.winfo_exists():
                        loading.attributes("-topmost", False)
                except Exception:
                    pass

            loading.after(300, release_loading_topmost)
        except Exception:
            pass
        loading.resizable(False, False)
        loading.transient(self)
        loading.update_idletasks()
        loading.geometry(
            f"+{(self.winfo_screenwidth() - 330) // 2}+{(self.winfo_screenheight() - 150) // 2}"
        )
        ctk.CTkLabel(loading, text="Analizando sistema y red...", font=("Segoe UI", 15, "bold")).pack(pady=(22, 10))
        progress = ctk.CTkProgressBar(loading)
        progress.pack(fill="x", padx=26, pady=(0, 18))
        progress.start()

        def collect_info():
            data = {
                "host": socket.gethostname(),
                "user": os.environ.get("USERNAME", "Desconocido"),
                "ip": "Error",
                "mask": "-",
                "gw": "-",
                "domain": "Unknown",
                "dns": "-",
            }

            cmd_net = """
            $i = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias *Ethernet* | Where-Object {$_.IPAddress -notlike "169.*"} | Select-Object -First 1
            if ($i) {
                $gw = (Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object -First 1).NextHop
                "$($i.IPAddress)|$($i.PrefixLength)|$gw"
            } else { "Unknown|0|Unknown" }
            """
            try:
                res_net, out_net = SysUtils.run_powershell(cmd_net, capture=True, timeout=12)
                if res_net:
                    parts = out_net.strip().split("|")
                    data["ip"] = parts[0] if len(parts) > 0 else "Unknown"
                    cidr = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                    masks = {24: "255.255.255.0", 16: "255.255.0.0", 8: "255.0.0.0"}
                    data["mask"] = masks.get(cidr, "Unknown" if cidr == 0 else f"/{cidr}")
                    data["gw"] = parts[2] if len(parts) > 2 else "Unknown"
            except Exception:
                pass

            try:
                _, out_dom = SysUtils.run_powershell(
                    "(Get-CimInstance Win32_ComputerSystem).Domain",
                    capture=True,
                    timeout=10,
                )
                data["domain"] = out_dom.strip() if out_dom.strip() else "WORKGROUP"
            except Exception:
                pass

            try:
                _, out_dns = SysUtils.run_powershell(
                    "(Get-DnsClientServerAddress -AddressFamily IPv4).ServerAddresses",
                    capture=True,
                    timeout=10,
                )
                dns_list = [d.strip() for d in out_dns.splitlines() if d.strip()]
                data["dns"] = ", ".join(sorted(set(dns_list))) if dns_list else "No detectado"
            except Exception:
                pass

            self._call_ui_thread(show_window, data)

        def show_window(data):
            if self._widget_exists(progress):
                progress.stop()
            if self._widget_exists(loading):
                loading.destroy()

            info_win, panel, tokens = self._create_legacy_panel_window(
                "Info Sistema",
                590,
                600,
                resizable=True,
                minsize=(520, 520),
                temporary_topmost=True,
                window_key=window_key,
            )

            def abrir_sysdm(e=None):
                self._open_control_applet("sysdm.cpl")

            def abrir_cuentas(e=None):
                self._open_control_applet("userpasswords2")

            def abrir_red(e=None):
                self._open_control_applet("ncpa.cpl")

            ctk.CTkFrame(panel, height=4, fg_color=tokens["accent"], corner_radius=3).pack(
                fill="x", padx=16, pady=(14, 0)
            )
            header = ctk.CTkFrame(panel, fg_color="transparent")
            header.pack(fill="x", padx=22, pady=(18, 10))
            ctk.CTkLabel(
                header,
                text="Info Sistema",
                font=("Segoe UI", 20, "bold"),
                anchor="w",
            ).pack(fill="x")
            ctk.CTkLabel(
                header,
                text="Resumen de equipo, usuario, dominio y red",
                font=("Segoe UI", 12, "bold"),
                text_color=tokens["accent"],
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

            def add_row_simple(parent, title, value, command, color_val=None):
                card = ctk.CTkFrame(
                    parent,
                    fg_color=tokens["card"],
                    border_width=1,
                    border_color=tokens["border"],
                    corner_radius=8,
                )
                card.pack(fill="x", pady=(0, 8))
                ctk.CTkLabel(
                    card,
                    text=title,
                    font=("Segoe UI", 11, "bold"),
                    text_color=tokens["muted"],
                    anchor="w",
                ).pack(fill="x", padx=14, pady=(10, 0))
                ctk.CTkButton(
                    card,
                    text=f"{value}  Editar",
                    font=("Consolas", 14),
                    fg_color="transparent",
                    hover_color=tokens["card_hover"],
                    anchor="w",
                    text_color=color_val if color_val else tokens["text"],
                    command=command,
                ).pack(fill="x", padx=8, pady=(2, 8))

            f1 = ctk.CTkFrame(panel, fg_color="transparent")
            f1.pack(padx=22, pady=(0, 10), fill="x")
            add_row_simple(f1, "Hostname", data["host"], abrir_sysdm)
            add_row_simple(f1, "Usuario", data["user"], abrir_cuentas)
            add_row_simple(f1, "Dominio", data["domain"], abrir_sysdm, tokens["accent"])

            f2 = ctk.CTkFrame(panel, fg_color="transparent")
            f2.pack(padx=22, pady=(0, 12), fill="x")
            ctk.CTkLabel(
                f2,
                text="CONFIGURACIÓN IP (Click para editar):",
                font=("Segoe UI", 12, "bold"),
                text_color=tokens["muted"],
                anchor="w",
            ).pack(fill="x", pady=(0, 6))

            f_net = ctk.CTkFrame(
                f2,
                fg_color=tokens["card"],
                border_width=1,
                border_color=tokens["border"],
                corner_radius=8,
            )
            f_net.pack(fill="x")
            net_text = (
                f"Dirección IP:       {data['ip']}\n"
                f"Máscara subred:     {data['mask']}\n"
                f"Puerta de enlace:   {data['gw']}\n"
                f"--------------------------------------\n"
                f"Servidores DNS:     {data['dns']}"
            )
            lbl_net = ctk.CTkLabel(
                f_net,
                text=net_text,
                font=("Consolas", 15),
                justify="left",
                anchor="w",
                text_color=tokens["text"],
            )
            lbl_net.pack(padx=16, pady=14, fill="x")

            for widget in [f_net, lbl_net]:
                widget.bind("<Button-1>", abrir_red)
                widget.bind("<Enter>", lambda e: f_net.configure(fg_color=tokens["card_hover"]))
                widget.bind("<Leave>", lambda e: f_net.configure(fg_color=tokens["card"]))

            footer = ctk.CTkFrame(panel, fg_color="transparent")
            footer.pack(fill="x", padx=22, pady=(0, 18))
            ctk.CTkButton(
                footer,
                text="Cerrar",
                command=info_win.destroy,
                width=130,
                height=38,
                fg_color=tokens["secondary"],
                hover_color=tokens["secondary_hover"],
                font=("Segoe UI", 12, "bold"),
            ).pack(side="right")

        threading.Thread(target=collect_info, daemon=True).start()

    def _accion_abrir_temp(self):
        """Abre la carpeta temporal donde está la DB de progreso."""
        try:
            ruta_temp = tempfile.gettempdir()
            os.startfile(ruta_temp)
        except Exception as e:
            self.ui_showerror("Error", f"No se pudo abrir carpeta: {e}")

    def _accion_abrir_recursos(self):
        """Abre recursos si están completos o muestra qué falta antes de seleccionar carpeta."""
        report, message = self._resource_report_message(self.payload_root, include_selector_hint=True)
        self._update_environment_status()
        if report["complete"]:
            try:
                root = os.path.abspath(report["root"])
                if not os.path.isdir(root):
                    raise OSError(f"La ruta no es una carpeta válida: {root}")
                subprocess.Popen(["explorer.exe", root], close_fds=True)
            except Exception as e:
                self.ui_showerror("Error", f"No se pudo abrir carpeta de recursos: {e}")
            return

        self._show_resource_report(report, message)
        self._accion_seleccionar_recursos()

    def _resource_report_message(self, path, include_selector_hint=False):
        report = SysUtils.payload_resource_report(path)
        message = SysUtils.format_payload_report(report)
        if include_selector_hint:
            message += "\n\nDespués de aceptar, se abrirá el selector para indicar la carpeta correcta de recursos."
        return report, message

    def _show_resource_report(self, report, message, invalid_as_error=False):
        if not report.get("root_exists") or not report.get("looks_like_payload_root"):
            if invalid_as_error:
                self.ui_showerror("Recursos no encontrados", message)
            else:
                self.ui_showwarning("Recursos no encontrados", message)
        else:
            self.ui_showwarning("Recursos incompletos", message)

    def _accion_seleccionar_recursos(self):
        """Permite indicar manualmente la carpeta de recursos y valida su contenido."""
        from tkinter import filedialog

        if getattr(self, "_resource_selector_open", False):
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
            return

        self._resource_selector_open = True
        initial_dir = self.payload_root if os.path.isdir(self.payload_root) else os.path.expanduser("~")
        try:
            selected = filedialog.askdirectory(
                parent=self,
                title="Selecciona la carpeta de recursos de Easy Deploy",
                initialdir=initial_dir,
            )
            if not selected:
                return

            report, message = self._resource_report_message(selected)

            if not report["looks_like_payload_root"]:
                self._show_resource_report(report, message, invalid_as_error=True)
                return

            self.payload_root = report["root"]
            SysUtils.save_configured_payload_root(self.payload_root)
            self._update_environment_status()

            if report["complete"]:
                self.ui_showinfo(
                    "Recursos detectados",
                    message + "\n\nLa ruta se ha guardado para futuros arranques.",
                )
            else:
                self._show_resource_report(report, message)
        finally:
            self._resource_selector_open = False

    def _accion_abrir_logs(self):
        """Abre la carpeta de logs persistentes de Easy Deploy."""
        try:
            if not hasattr(self, "log_manager"):
                self.ui_showerror("Logs", "El gestor de logs no está inicializado.")
                return
            os.makedirs(self.log_manager.logs_dir, exist_ok=True)
            os.startfile(self.log_manager.logs_dir)
        except Exception as e:
            self.ui_showerror("Error", f"No se pudo abrir carpeta de logs: {e}")

    def _accion_check_admin(self):
        """Comprueba si tenemos permisos de administrador."""
        is_admin = SysUtils.is_admin()
        self._update_environment_status()
            
        estado = "✅ TIENES permisos de Administrador." if is_admin else "⚠️ NO TIENES permisos de Administrador."
        self.ui_showinfo("Estado de Privilegios", estado)

    def _accion_ver_roles(self):
        """Muestra una lista de TODOS los Roles y Características instalados (Ordenados)."""

        window_key = "roles_instalados"
        if self._focus_secondary_window(window_key):
            return
        loading, panel, tokens = self._create_legacy_panel_window(
            "Analizando...",
            330,
            150,
            topmost=True,
            temporary_topmost=True,
            transient=True,
            window_key=window_key,
        )

        ctk.CTkLabel(
            panel,
            text="Escaneando Server...",
            font=("Segoe UI", 15, "bold"),
        ).pack(pady=(24, 10))
        progress = ctk.CTkProgressBar(panel, progress_color=tokens["accent"])
        progress.pack(fill="x", padx=28, pady=(0, 18))
        progress.start()

        def close_loading():
            if self._widget_exists(progress):
                progress.stop()
            if self._widget_exists(loading):
                loading.destroy()
        
        def buscar_roles():
            # CAMBIO: Añadido "Sort-Object DisplayName" para orden alfabético A-Z
            cmd = "Get-WindowsFeature | Where-Object {$_.InstallState -eq 'Installed'} | Sort-Object DisplayName | Select-Object DisplayName, FeatureType"
            
            try:
                res, out = SysUtils.run_powershell(cmd, capture=True, timeout=25)

                if not res or not out.strip():
                    self._call_ui_thread(close_loading)
                    self.ui_showinfo("Info", "No se encontraron roles instalados.")
                    return

                self._call_ui_thread(close_loading)
                self._call_ui_thread(self._mostrar_ventana_roles, out)
                
            except Exception as e:
                self._call_ui_thread(close_loading)
                self.ui_showerror("Error", f"Fallo al buscar roles: {e}")

        threading.Thread(target=buscar_roles, daemon=True).start()

    def _mostrar_ventana_roles(self, raw_output):
        window_key = "roles_instalados"
        if self._focus_secondary_window(window_key):
            return
        win, panel, tokens = self._create_legacy_panel_window(
            "Roles y Características Instalados",
            690,
            720,
            resizable=True,
            minsize=(560, 480),
            temporary_topmost=True,
            transient=True,
            window_key=window_key,
        )

        def bring_roles_to_front():
            if not self._widget_exists(win):
                return
            try:
                win.deiconify()
            except Exception:
                pass
            try:
                win.lift(self)
            except Exception:
                try:
                    win.lift()
                except Exception:
                    pass
            try:
                win.focus_set()
            except Exception:
                pass
            try:
                win.attributes("-topmost", True)

                def release_topmost():
                    try:
                        if win.winfo_exists():
                            win.attributes("-topmost", False)
                    except Exception:
                        pass

                win.after(300, release_topmost)
            except Exception:
                pass

        win.after(80, bring_roles_to_front)

        ctk.CTkFrame(panel, height=4, fg_color=tokens["accent"], corner_radius=3).pack(
            fill="x", padx=16, pady=(14, 0)
        )
        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 10))
        ctk.CTkLabel(
            header,
            text="Componentes Instalados (A-Z)",
            font=("Segoe UI", 20, "bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            header,
            text="Roles y características detectados por Windows Server",
            font=("Segoe UI", 12, "bold"),
            text_color=tokens["accent"],
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        scroll_frame = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        lines = raw_output.strip().split('\n')
        
        # Saltamos encabezados de PowerShell
        data_lines = []
        is_header = True
        for line in lines:
            if "--------" in line:
                is_header = False
                continue
            if not is_header and line.strip():
                data_lines.append(line.strip())

        count = 0
        for line in data_lines:
            # PowerShell devuelve "NombreDelRol          Role/Feature"
            # Vamos a intentar separar el tipo si está disponible
            parts = line.rsplit(' ', 1) # Separar por el último espacio
            name = parts[0].strip()
            
            is_role = len(parts) > 1 and "Role" in parts[1]
            badge_text = "ROL" if is_role else "CAR"
            badge_color = tokens["accent"] if is_role else tokens["secondary"]

            card = ctk.CTkFrame(
                scroll_frame,
                fg_color=tokens["card"],
                border_width=1,
                border_color=tokens["border"],
                corner_radius=8,
            )
            card.grid(row=count, column=0, sticky="ew", padx=2, pady=(0, 6))
            card.grid_columnconfigure(1, weight=1)

            badge = ctk.CTkFrame(card, width=48, height=28, fg_color=badge_color, corner_radius=8)
            badge.grid(row=0, column=0, sticky="w", padx=12, pady=10)
            badge.grid_propagate(False)
            ctk.CTkLabel(
                badge,
                text=badge_text,
                font=("Segoe UI", 10, "bold"),
                text_color="white",
            ).pack(fill="both", expand=True)

            ctk.CTkLabel(
                card, 
                text=name,
                font=("Consolas", 13), 
                anchor="w",
                text_color=tokens["text"],
            ).grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)
            
            count += 1

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.pack(fill="x", padx=22, pady=(0, 18))
        ctk.CTkLabel(
            footer,
            text=f"Total instalados: {count}",
            text_color=tokens["muted"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).pack(side="left")
        ctk.CTkButton(
            footer,
            text="Cerrar",
            command=win.destroy,
            width=130,
            height=38,
            fg_color=tokens["secondary"],
            hover_color=tokens["secondary_hover"],
            font=("Segoe UI", 12, "bold"),
        ).pack(side="right")
