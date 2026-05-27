from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from ..core.logging_utils import LogManager
from ..core.progress import ProgresoManager
from ..core.sysutils import SysUtils
from ..tasks.domain import DomainTasksMixin
from ..tasks.exchange import ExchangeTasksMixin
from ..tasks.guides import GuidesTasksMixin
from ..tasks.jchat import JchatTasksMixin
from ..tasks.kms import KmsTasksMixin
from ..tasks.network import NetworkTasksMixin
from ..tasks.programs import ProgramsTasksMixin
from ..tasks.sharepoint import SharePointTasksMixin
from ..tasks.sql import SqlTasksMixin
from ..tasks.system import SystemTasksMixin
from ..ui.actions import ActionsMixin
from ..ui.environment import EnvironmentMixin
from .event_protocol import EventSink, new_id


class HeadlessEasyDeployHost(
    EnvironmentMixin,
    ActionsMixin,
    SharePointTasksMixin,
    KmsTasksMixin,
    SystemTasksMixin,
    JchatTasksMixin,
    SqlTasksMixin,
    ExchangeTasksMixin,
    DomainTasksMixin,
    NetworkTasksMixin,
    ProgramsTasksMixin,
    GuidesTasksMixin,
):
    """Adaptador mínimo para reutilizar tareas internas sin arrancar Tkinter."""

    def __init__(self, sink: EventSink):
        self.sink = sink
        self.ui_thread_id = threading.get_ident()
        if getattr(sys, "frozen", False):
            self.base_path = str(Path(sys.executable).resolve().parent)
        else:
            self.base_path = str(Path(__file__).resolve().parents[2])
        self.payload_root = SysUtils.resolve_payload_root(self.base_path)
        self.stop_event = threading.Event()
        self.active_thread = None
        self.active_process = None
        self.console_finish_state = "finished"
        self.console_input_queue = None
        self.log_manager = LogManager()
        self.db = ProgresoManager()
        self.colors = {
            "accent": "#2F9E8F",
            "accent_hover": "#258176",
            "danger": "#B42318",
            "warning": "#D97706",
        }
        self._prompt_lock = threading.Lock()
        self._prompt_responses: dict[str, dict] = {}
        self._timers = set()

    def emit_status(self, message: str, level: str = "info"):
        self.sink.emit("status", level=level, message=str(message))

    def emit_error(self, title: str, message: str):
        self.sink.emit("error", title=str(title), message=str(message))

    def log(self, text):
        message = str(text).rstrip()
        if not message:
            return
        if hasattr(self, "log_manager"):
            self.log_manager.write(message)
        self.sink.emit("log", source="PYTHON", level=self._classify_log_level(message), message=message)

    def log_raw(self, text):
        self.log(text)

    def write(self, text):
        message = str(text).rstrip()
        if message:
            self.log(message)

    def flush(self):
        return None

    def update_progress(self, value):
        try:
            progress = float(value)
        except Exception:
            progress = 0.0
        if progress > 1:
            progress = progress / 100.0
        progress = max(0.0, min(1.0, progress))
        self.sink.emit("progress", value=progress)

    def _classify_log_level(self, message: str) -> str:
        text = message.casefold()
        if "[error]" in text or " error" in text or text.startswith("error"):
            return "error"
        if "[aviso]" in text or "warning" in text or "advertencia" in text:
            return "warning"
        if "[ok]" in text or "correctamente" in text or "exito" in text or "?xito" in text:
            return "success"
        return "info"

    def _call_ui_thread(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def after(self, delay_ms, callback=None, *args):
        if callback is None:
            return None
        if delay_ms <= 0:
            return callback(*args)

        timer = threading.Timer(delay_ms / 1000.0, callback, args=args)
        timer.daemon = True
        self._timers.add(timer)

        def run_and_forget():
            try:
                callback(*args)
            finally:
                self._timers.discard(timer)

        timer.function = run_and_forget
        timer.args = ()
        timer.start()
        return timer

    def after_cancel(self, timer):
        try:
            timer.cancel()
            self._timers.discard(timer)
        except Exception:
            pass

    def _widget_exists(self, widget):
        return False

    def _configure_if_alive(self, widget, **kwargs):
        return None

    def _set_tile_status(self, tile, text, color):
        self.sink.emit("status", level="info", message=f"{text}")

    def _update_environment_status(self):
        self.sink.emit(
            "status",
            level="info",
            message=f"Admin={'OK' if SysUtils.is_admin() else 'NO'} | Recursos={self.payload_root}",
        )

    def _set_console_input_enabled(self, enabled, placeholder=None, cancel_enabled=None, sensitive=False):
        self.sink.emit(
            "console_input",
            enabled=bool(enabled),
            placeholder=placeholder or "",
            cancel_enabled=bool(cancel_enabled) if cancel_enabled is not None else False,
            sensitive=bool(sensitive),
        )

    def _set_console_waiting_for_input(self, prompt_text="", sensitive=False):
        placeholder = prompt_text or "Introduce el dato solicitado por la tarea y pulsa Enter."
        self._set_console_input_enabled(True, placeholder, cancel_enabled=True, sensitive=bool(sensitive))

    def submit_console_input(self, value):
        if self.console_input_queue is None:
            self.sink.emit(
                "status",
                level="warning",
                message="No hay ninguna sesión interactiva esperando entrada.",
            )
            return False
        self.console_input_queue.put(value)
        return True

    def _finish_interactive_console_run(self):
        self._set_console_input_enabled(False, "Proceso finalizado.", cancel_enabled=False)
        if hasattr(self, "log_manager"):
            self.log_manager.finish_run(self.console_finish_state)
        self.update_progress(1)
        self.sink.emit("finished", action="interactive_console", success=self.console_finish_state != "error")

    def iniciar_script_interactivo(self, task_name, script_name):
        if self.active_thread and self.active_thread.is_alive():
            self.ui_showwarning(
                "Proceso en curso",
                "Ya hay una tarea ejecutándose. Cancela o espera a que termine antes de iniciar otra.",
            )
            return

        module_name = self._resolve_network_module(script_name)
        if not module_name:
            self.ui_showerror(task_name, "No encuentro la herramienta de red integrada.")
            return

        self.update_progress(0)
        self.stop_event.clear()
        self.console_finish_state = "finished"
        self.console_input_queue = queue.Queue()
        self._set_console_input_enabled(True, f"Entrada para {task_name}: responde al prompt cuando aparezca.")
        if hasattr(self, "log_manager"):
            log_path = self.log_manager.start_run(f"redes_{task_name}")
            self.sink.emit("status", level="info", message=f"Log actual: {log_path}")
            self.log(f"[LOG] Guardando registro en: {log_path}")

        self.log(f"[REDES] Iniciando herramienta {task_name}")
        self.active_thread = threading.Thread(
            target=self._interactive_script_wrapper,
            args=(task_name, module_name),
            daemon=True,
        )
        self.active_thread.start()

    def _request_prompt(self, title, message, kind="input", is_password=False, default="", buttons=None):
        prompt_id = new_id()
        event = threading.Event()
        with self._prompt_lock:
            self._prompt_responses[prompt_id] = {"event": event, "value": None}
        self.sink.emit(
            "prompt",
            prompt_id=prompt_id,
            kind=kind,
            title=str(title),
            message=str(message),
            is_password=bool(is_password),
            default=str(default or ""),
            buttons=buttons or [],
        )
        event.wait()
        with self._prompt_lock:
            response = self._prompt_responses.pop(prompt_id, {})
        return response.get("value")

    def respond_prompt(self, prompt_id, value):
        with self._prompt_lock:
            response = self._prompt_responses.get(str(prompt_id))
            if not response:
                return False
            response["value"] = value
            response["event"].set()
            return True

    def input_dialog(self, title, prompt, is_password=False, max_chars=None, auto_dash=False, initial_error="", default=""):
        message = str(prompt or "")
        if initial_error:
            message = f"{initial_error}\n\n{message}"
        value = self._request_prompt(title, message, kind="input", is_password=is_password, default=default)
        if value is None:
            return None
        value = str(value)
        if max_chars:
            value = value[: int(max_chars)]
        return value

    def ui_input_dialog(self, *args, **kwargs):
        return self.input_dialog(*args, **kwargs)

    def modal_dialog(self, title, message, kind="info", buttons=None, topmost=False):
        buttons = buttons or [("Aceptar", True, "primary")]
        if len(buttons) <= 1 and kind in {"info", "warning", "error"}:
            level = "error" if kind == "error" else "warning" if kind == "warning" else "info"
            self.sink.emit("notification", level=level, title=str(title), message=str(message))
            return buttons[0][1]
        prompt_buttons = [{"text": text, "value": value, "style": style} for text, value, style in buttons]
        value = self._request_prompt(title, message, kind="confirm", buttons=prompt_buttons)
        if value is None:
            return buttons[-1][1]
        return value

    def ui_askyesno(self, title, message):
        return bool(
            self.modal_dialog(
                title,
                message,
                "question",
                [("Sí", True, "primary"), ("No", False, "secondary")],
            )
        )

    def ui_ask_reboot(self, title, message):
        return bool(
            self.modal_dialog(
                title,
                message,
                "warning",
                [("Reiniciar", True, "warning"), ("Más tarde", False, "secondary")],
            )
        )

    def ui_showinfo(self, title, message):
        return self.modal_dialog(title, message, "info", [("Aceptar", True, "primary")])

    def ui_showinfo_topmost(self, title, message):
        return self.ui_showinfo(title, message)

    def ui_showwarning(self, title, message):
        return self.modal_dialog(title, message, "warning", [("Aceptar", True, "warning")])

    def ui_showerror(self, title, message):
        return self.modal_dialog(title, message, "error", [("Aceptar", True, "danger")])

    def _wait_for_media_installer_confirmation(self, process, label):
        self.log(
            f"[INFO] {label} se ha abierto. Easy Deploy mantendrá el medio montado hasta que confirmes el final."
        )
        confirmed = self.ui_askyesno(
            label,
            f"{label} está en curso.\n\n"
            "Cuando termines o cierres el instalador externo, confirma para que Easy Deploy pueda continuar.",
        )
        if not confirmed:
            return False
        if process and process.poll() is None:
            self.log(f"[INFO] El proceso inicial de {label} sigue abierto. No se cerrará desde Easy Deploy.")
        elif process:
            self.log(f"[INFO] El proceso inicial de {label} finalizó con código: {process.returncode}")
        return True

    def iniciar_tarea(self, target_func, *args):
        if self.active_thread and self.active_thread.is_alive():
            self.ui_showwarning("Proceso en curso", "Ya hay una tarea ejecutándose.")
            return
        if not SysUtils.is_admin():
            self.ui_showerror(
                "Permisos de administrador",
                "Esta tarea necesita permisos de Administrador.\n\n"
                "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
            )
            return

        self.stop_event.clear()
        self.console_finish_state = "finished"
        self.update_progress(0)
        task_name = getattr(target_func, "__name__", "tarea")
        log_path = self.log_manager.start_run(task_name)
        self.sink.emit("status", level="info", message=f"Log actual: {log_path}")
        self.log(f"[LOG] Guardando registro en: {log_path}")

        old_stdout = sys.stdout
        sys.stdout = self
        try:
            target_func(*args)
        except Exception as exc:
            self.console_finish_state = "error"
            self.log(f"[ERROR] Tarea detenida: {exc}")
            self.emit_error("Error inesperado", str(exc))
        finally:
            sys.stdout = old_stdout
            self.log_manager.finish_run(self.console_finish_state)
            self.log("--- PROCESO FINALIZADO ---")
            self.update_progress(1)

    def cancelar_proceso(self):
        self.stop_event.set()
        try:
            if self.console_input_queue is not None:
                self.console_input_queue.put_nowait(None)
        except Exception:
            pass
        try:
            process = getattr(self, "active_process", None)
            if process and process.poll() is None:
                process.terminate()
        except Exception:
            pass
        self.sink.emit("status", level="warning", message="Cancelación solicitada.")

    def destroy(self):
        self.cancelar_proceso()

    def show_frame(self, name):
        self.sink.emit("status", level="info", message=f"Vista solicitada por tarea interna: {name}")

    def update_control_bar(self, state="finished"):
        self.sink.emit("status", level="info", message=f"Estado de tarea: {state}")

    def _open_control_applet(self, applet_name):
        subprocess.Popen(["control", applet_name], creationflags=subprocess.CREATE_NO_WINDOW)

    def run_shell_tool(self, title, executable, parameters="", elevated=False):
        self._shell_execute(title, executable, parameters=parameters, elevated=elevated)
        self.sink.emit("finished", action=title, success=True)

    def sleep_with_cancel(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            if self.stop_event.is_set():
                return False
            time.sleep(0.2)
        return True

