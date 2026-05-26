import os
import threading
import time

from ..core.sysutils import SysUtils


class EnvironmentMixin:
    def _widget_exists(self, widget):
        try:
            return widget is not None and widget.winfo_exists()
        except Exception:
            return False

    def _configure_if_alive(self, widget, **kwargs):
        if self._widget_exists(widget):
            try:
                widget.configure(**kwargs)
            except Exception:
                pass

    def payload_path(self, *parts):
        """Construye rutas dentro de la carpeta de recursos de Easy Deploy."""
        return os.path.join(self.payload_root, *parts)

    def _update_environment_status(self):
        """Actualiza la barra superior con el estado real del entorno."""
        if not self._widget_exists(getattr(self, "lbl_env_status", None)):
            return

        admin_text = "Admin OK" if SysUtils.is_admin() else "Sin admin"
        admin_color = "#16803C" if SysUtils.is_admin() else "#D97706"
        payload_report = SysUtils.payload_resource_report(self.payload_root)
        payload_ok = bool(payload_report["complete"])
        payload_partial = bool(payload_report["looks_like_payload_root"])
        if payload_ok:
            payload_text = "Recursos OK"
            payload_color = "#16803C"
        elif payload_partial:
            payload_text = "Recursos incompletos"
            payload_color = "#D97706"
        else:
            payload_text = "Recursos no encontrados"
            payload_color = "#D97706"
        sidebar_admin_color = "#6EE7B7" if SysUtils.is_admin() else "#F59E0B"
        sidebar_payload_color = "#6EE7B7" if payload_ok else "#F59E0B"
        self._configure_if_alive(getattr(self, "lbl_env_admin_status", None), text=admin_text, text_color=sidebar_admin_color)
        self._configure_if_alive(getattr(self, "lbl_env_payload_status", None), text=payload_text, text_color=sidebar_payload_color)
        self._configure_if_alive(getattr(self, "lbl_payload_path", None), text=f"Recursos: {self.payload_root}")
        self._set_tile_status(getattr(self, "admin_tile", None), admin_text, admin_color)
        self._set_tile_status(getattr(self, "payload_tile", None), payload_text, payload_color)
        self._update_keyboard_tile_status()
        self._update_firewall_tile_status()
        if hasattr(self, "_update_disk_status_panel"):
            self._update_disk_status_panel()

    def _update_keyboard_tile_status(self):
        if getattr(self, "_keyboard_status", None) is None:
            self._set_tile_status(getattr(self, "keyboard_tile", None), "Comprobando", "#D97706")
            self._refresh_keyboard_status_async()
            return

        keyboard_ok = bool(getattr(self, "_keyboard_status", False))
        text = "ESP OK" if keyboard_ok else "Cambiar a ESP"
        color = "#16803C" if keyboard_ok else "#D97706"
        self._set_tile_status(getattr(self, "keyboard_tile", None), text, color)

    def _refresh_keyboard_status_async(self):
        if getattr(self, "_keyboard_check_running", False):
            return
        self._keyboard_check_running = True

        watchdog = getattr(self, "_keyboard_check_watchdog", None)
        if watchdog:
            try:
                self.after_cancel(watchdog)
            except Exception:
                pass
        self._keyboard_check_watchdog = self.after(5000, self._keyboard_status_watchdog)

        def worker():
            try:
                status = SysUtils.is_spanish_spain_keyboard()
            except Exception:
                status = False

            def apply_status():
                self._keyboard_status = status
                self._keyboard_check_running = False
                watchdog_id = getattr(self, "_keyboard_check_watchdog", None)
                if watchdog_id:
                    try:
                        self.after_cancel(watchdog_id)
                    except Exception:
                        pass
                    self._keyboard_check_watchdog = None
                self._update_keyboard_tile_status()

            self.after(0, apply_status)

        threading.Thread(target=worker, daemon=True).start()

    def _keyboard_status_watchdog(self):
        self._keyboard_check_watchdog = None
        if getattr(self, "_keyboard_status", None) is not None:
            return
        self._keyboard_check_running = False
        quick_status = SysUtils.is_spanish_spain_keyboard_quick()
        self._keyboard_status = bool(quick_status) if quick_status is not None else False
        self._update_keyboard_tile_status()

    def _update_firewall_tile_status(self):
        status = getattr(self, "_firewall_status", None)
        if status is None:
            self._set_tile_status(getattr(self, "firewall_tile", None), "Comprobando", "#D97706")
            self._refresh_firewall_status_async()
            return

        if status == "unknown":
            status = SysUtils.firewall_all_profiles_enabled_quick()
            if status is None:
                status = False

        firewall_ok = bool(status)
        text = "Firewall OK" if firewall_ok else "Firewall OFF"
        color = "#16803C" if firewall_ok else "#B42318"
        self._set_tile_status(getattr(self, "firewall_tile", None), text, color)

    def _refresh_firewall_status_async(self, force=False):
        if getattr(self, "_firewall_check_running", False):
            return
        if force:
            self._firewall_status = None
        self._firewall_check_running = True

        watchdog = getattr(self, "_firewall_check_watchdog", None)
        if watchdog:
            try:
                self.after_cancel(watchdog)
            except Exception:
                pass
        self._firewall_check_watchdog = self.after(6000, self._firewall_status_watchdog)

        def worker():
            try:
                status = SysUtils.firewall_all_profiles_enabled()
            except Exception:
                status = SysUtils.firewall_all_profiles_enabled_quick()
            if status is None:
                status = SysUtils.firewall_all_profiles_enabled_quick()

            def apply_status():
                self._firewall_status = bool(status) if status is not None else False
                self._firewall_check_running = False
                watchdog_id = getattr(self, "_firewall_check_watchdog", None)
                if watchdog_id:
                    try:
                        self.after_cancel(watchdog_id)
                    except Exception:
                        pass
                    self._firewall_check_watchdog = None
                self._update_firewall_tile_status()

            self.after(0, apply_status)

        threading.Thread(target=worker, daemon=True).start()

    def _firewall_status_watchdog(self):
        self._firewall_check_watchdog = None
        if getattr(self, "_firewall_status", None) is not None:
            return
        self._firewall_check_running = False
        quick_status = SysUtils.firewall_all_profiles_enabled_quick()
        self._firewall_status = bool(quick_status) if quick_status is not None else False
        self._update_firewall_tile_status()

    def _set_tile_status(self, tile, text, color):
        if not self._widget_exists(tile):
            return
        status_label = getattr(tile, "status_label", None)
        if status_label is not None:
            self._configure_if_alive(status_label, text=text, text_color=color)
            return
        try:
            labels = tile.winfo_children()
        except Exception:
            return
        if len(labels) > 1:
            self._configure_if_alive(labels[1], text=text, text_color=color)

    def _show_startup_warnings(self):
        """Muestra avisos iniciales útiles sin bloquear la apertura de la UI."""
        if self.startup_warning_shown:
            return
        self.startup_warning_shown = True
        self._update_environment_status()

        warnings = []
        if not SysUtils.is_admin():
            warnings.append(
                "La app no se ha abierto como Administrador. Las tareas de despliegue se bloquearán hasta que la ejecutes con permisos elevados."
            )

        payload_report = SysUtils.payload_resource_report(self.payload_root)
        if not payload_report["looks_like_payload_root"]:
            warnings.append(
                "No encuentro la carpeta de recursos con EXCHANGE, SHAPRE, SQL o JCHAT. "
                f"Ruta buscada: {self.payload_root}"
            )
        elif not payload_report["complete"]:
            warnings.append(
                "La carpeta de recursos se ha detectado, pero faltan archivos. "
                "Pulsa Recursos en Inicio para ver la lista de recursos faltantes."
            )


    def _warn_missing_files(self, folder, filenames, abort=False):
        """Lista archivos ausentes antes de iniciar un despliegue."""
        missing = [name for name in filenames if not os.path.exists(os.path.join(folder, name))]
        if not missing:
            return []

        print("\n[AVISO] Faltan recursos en:")
        print(f"  {folder}")
        for name in missing:
            print(f"  - {name}")

        if abort:
            print("\n[ERROR] Tarea cancelada para evitar una instalación incompleta.")
        else:
            print("\n[INFO] La tarea continuará y omitirá lo que no exista.")
        if hasattr(self, "ui_showwarning"):
            action = (
                "La tarea se ha cancelado para evitar una instalacion incompleta."
                if abort
                else "La tarea continuara, pero los pasos que dependan de esos archivos podrian omitirse o fallar."
            )
            self.ui_showwarning(
                "Recursos no encontrados",
                "Faltan archivos en la carpeta de recursos:\n\n"
                f"{folder}\n\n"
                + "\n".join(f"- {name}" for name in missing)
                + "\n\n"
                + action,
            )
        return missing

    def _notify_task_error(self, title, message):
        """Muestra un error de tarea en UI y deja rastro claro en consola."""
        print(f"[ERROR] {title}: {message.replace(chr(10), ' ')}")
        if hasattr(self, "ui_showerror"):
            self.ui_showerror(title, message)

    def _notify_task_warning(self, title, message):
        """Muestra una advertencia de tarea en UI y deja rastro claro en consola."""
        print(f"[AVISO] {title}: {message.replace(chr(10), ' ')}")
        if hasattr(self, "ui_showwarning"):
            self.ui_showwarning(title, message)

    def _notify_task_info(self, title, message):
        """Muestra informacion de tarea en UI y deja rastro claro en consola."""
        print(f"[INFO] {title}: {message.replace(chr(10), ' ')}")
        if hasattr(self, "ui_showinfo"):
            self.ui_showinfo(title, message)

    def _require_windows_server(self, task_name, detail=""):
        """Bloquea tareas de servidor cuando se ejecutan en Windows cliente."""
        if SysUtils.is_windows_server():
            return True
        message = (
            f"{task_name} requiere Windows Server para instalar roles, caracteristicas o productos de servidor.\n\n"
            "Ejecuta esta funcion en Windows Server y vuelve a intentarlo."
        )
        if detail:
            message += f"\n\n{detail}"
        self._notify_task_error(task_name, message)
        return False

    def _validate_or_show(self, value, validator, title, message):
        """Valida entradas antes de construir comandos del sistema."""
        if validator(value):
            return True
        if hasattr(self, "ui_showerror"):
            self.ui_showerror(title, message)
        else:
            print(f"[ERROR] {title}: {message}")
        return False

    def _wait_for_installer_process(self, process, label):
        """Espera un instalador GUI y permite cancelar desde Easy Deploy."""
        while process.poll() is None:
            if self.stop_event.is_set():
                print(f"[AVISO] Cancelacion solicitada. Cerrando instalador: {label}")
                try:
                    process.terminate()
                    process.wait(timeout=12)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
                return False
            time.sleep(0.5)
        return process.returncode in (0, None, 3010)

    def _wait_for_media_installer_confirmation(self, process, label):
        """Para instaladores lanzados desde ISO/IMG: espera confirmacion humana."""
        confirm_event = threading.Event()

        def enable_media_confirm_button():
            if not self._widget_exists(getattr(self, "console_input", None)):
                return
            self.console_input_var.set("")
            self.console_input.configure(
                state="disabled",
                show="",
                placeholder_text=f"{label} en curso. Vuelve aqui al terminar y pulsa Extraer CD/ISO.",
            )
            self.console_send_button.configure(
                text="Extraer CD/ISO",
                state="normal",
                command=confirm_event.set,
                fg_color=self.colors.get("warning", "#D97706"),
                hover_color="#B45309",
            )
            self.console_cancel_button.configure(state="normal")

        def restore_console_buttons():
            if not self._widget_exists(getattr(self, "console_input", None)):
                return
            self.console_send_button.configure(
                text="Enviar",
                command=self._send_console_input,
                fg_color=self.colors.get("accent", "#2F9E8F"),
                hover_color=self.colors.get("accent_hover", "#258176"),
            )
            self._set_console_input_enabled(
                False,
                "Proceso en curso. Pulsa Cancelar para detenerlo.",
                cancel_enabled=True,
            )

        print(
            f"[INFO] {label} se ha abierto. Easy Deploy mantendra el CD/ISO montado "
            "hasta que confirmes manualmente."
        )
        print(
            "[INFO] No se mostrara una ventana encima del instalador. "
            "Cuando termines, vuelve a Easy Deploy y pulsa 'Extraer CD/ISO'."
        )
        self._call_ui_thread(enable_media_confirm_button)

        try:
            while not confirm_event.is_set():
                if self.stop_event.is_set():
                    print("[AVISO] Cancelacion solicitada desde Easy Deploy.")
                    return False
                time.sleep(0.25)

            if process.poll() is None:
                print(f"[INFO] El proceso inicial de {label} sigue abierto. No se cerrara desde Easy Deploy.")
            else:
                print(f"[INFO] El proceso inicial de {label} finalizo con codigo: {process.returncode}")
            return True
        finally:
            self._call_ui_thread(restore_console_buttons)

    def _dismount_task_media(self, image_path, reason="finalizada", ask_user=True):
        """Avisa y desmonta una imagen montada por Easy Deploy."""
        if not image_path:
            return

        print(f"\n[INFO] La tarea ha sido {reason}. Easy Deploy va a extraer el CD/ISO de instalacion.")
        if ask_user:
            self.ui_showinfo(
                "Extraer medio",
                f"La tarea ha sido {reason}.\n\n"
                "Pulsa Aceptar para extraer el CD/ISO de instalacion."
            )
        ok, detail = SysUtils.dismount_disk_image(image_path)
        if ok:
            print("[OK] CD/ISO de instalacion extraido correctamente.")
        else:
            print(f"[AVISO] No se pudo extraer el CD/ISO automaticamente: {detail}")
            self.ui_showwarning(
                "Extraer medio",
                "No se pudo extraer el CD/ISO automaticamente.\n\n"
                "Si el instalador sigue abierto, cierralo y expulsa la unidad desde Windows.\n\n"
                f"Detalle: {detail}"
            )
