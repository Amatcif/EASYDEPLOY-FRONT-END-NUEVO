import builtins
import importlib.util
import os
import queue
import runpy
import sys
import tempfile
import threading
import traceback


class NetworkTasksMixin:
    """Ejecuta herramientas de red de consola dentro de la UI."""

    NETWORK_TOOL_MODULES = {
        "switchconf.py": "easy_deploy_app.network_tools.switchCONF",
        "switchcisco.py": "easy_deploy_app.network_tools.switchCisco",
        "r3.py": "easy_deploy_app.network_tools.r3",
    }

    def open_switch_tool(self):
        self.open_switch_allied_tool()

    def open_switch_allied_tool(self):
        self.iniciar_script_interactivo("Switch_Allied", "switchCONF.py")

    def open_switch_cisco_tool(self):
        self.iniciar_script_interactivo("Switch_Cisco", "switchCisco.py")

    def open_router_tool(self):
        self.iniciar_script_interactivo("Router", "r3.py")

    def iniciar_script_interactivo(self, task_name, script_name):
        if self.active_thread and self.active_thread.is_alive():
            self.ui_showwarning(
                "Proceso en curso",
                "Ya hay una tarea ejecutandose. Cancela o espera a que termine antes de iniciar otra.",
            )
            return

        module_name = self._resolve_network_module(script_name)
        if not module_name:
            self.ui_showerror(
                task_name,
                "No encuentro la herramienta de red integrada.",
            )
            return

        self.return_frame_after_console = "Network"
        self.show_frame("Console")
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", "end")
        self.console_text.configure(state="disabled")
        self.update_progress(0)
        self.stop_event.clear()
        self.console_input_queue = queue.Queue()
        self._set_console_input_enabled(True, f"Entrada para {task_name}: escribe y pulsa Enter")
        self.update_control_bar("interactive")

        if hasattr(self, "log_manager"):
            log_path = self.log_manager.start_run(f"redes_{task_name}")
            self.lbl_log_path.configure(text=f"Log actual: {log_path}")
            self.log(f"[LOG] Guardando registro en: {log_path}")

        self.log(f"[REDES] Iniciando herramienta {task_name}")
        self.log("[REDES] Herramienta cargada correctamente.")
        self.active_thread = threading.Thread(
            target=self._interactive_script_wrapper,
            args=(task_name, module_name),
            daemon=True,
        )
        self.active_thread.start()

    def _resolve_network_module(self, script_name):
        script_name = os.path.basename(script_name)
        module_name = self.NETWORK_TOOL_MODULES.get(script_name.lower())
        if not module_name:
            return ""
        return module_name if importlib.util.find_spec(module_name) else ""

    def _network_runtime_dir(self):
        if hasattr(self, "log_manager") and getattr(self.log_manager, "logs_dir", None):
            root = os.path.dirname(self.log_manager.logs_dir)
        else:
            root = os.path.join(tempfile.gettempdir(), "EasyDeploy")
        runtime_dir = os.path.join(root, "network")
        os.makedirs(runtime_dir, exist_ok=True)
        return runtime_dir

    def _interactive_script_wrapper(self, task_name, module_name):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        old_input = builtins.input
        old_cwd = os.getcwd()
        runtime_dir = self._network_runtime_dir()

        def input_bridge(prompt=""):
            if self.stop_event.is_set():
                raise KeyboardInterrupt("Proceso cancelado")

            prompt_text = str(prompt or "")
            sensitive = self._is_sensitive_console_prompt(prompt_text)
            if prompt_text:
                self._call_ui_thread(self.log_raw, prompt_text)
            self._call_ui_thread(self._set_console_waiting_for_input, prompt_text, sensitive)

            value = self.console_input_queue.get()
            self._call_ui_thread(self._set_console_waiting_for_input, "", False)

            if value is None or self.stop_event.is_set():
                raise KeyboardInterrupt("Proceso cancelado")
            return value

        try:
            os.chdir(runtime_dir)
            sys.stdout = self
            sys.stderr = self
            builtins.input = input_bridge
            self.log(f"[INFO] Carpeta de trabajo: {runtime_dir}")
            runpy.run_module(module_name, run_name="__main__", alter_sys=True)
        except SystemExit as exc:
            if exc.code not in (None, 0):
                self.log(f"[AVISO] La herramienta {task_name} finalizo con codigo: {exc.code}")
                if str(exc.code).strip() == "1":
                    self.ui_showwarning(
                        task_name,
                        "La herramienta ha terminado con codigo 1.\n\n"
                        "Normalmente esto significa que Easy Deploy no detecta el puerto de consola, "
                        "el cable USB/Serial no esta conectado, el driver no esta cargado o el puerto COM "
                        "esta abierto en otra aplicacion como PuTTY o MobaXterm.\n\n"
                        "Conecta el cable de consola, revisa el Administrador de dispositivos y vuelve a intentarlo.",
                    )
        except KeyboardInterrupt:
            self.log("[AVISO] Proceso cancelado por el usuario.")
        except Exception:
            self.log(f"[ERROR] Error ejecutando {task_name}:\n{traceback.format_exc()}")
        finally:
            builtins.input = old_input
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            os.chdir(old_cwd)
            self._call_ui_thread(self._finish_interactive_console_run)

    @staticmethod
    def _is_sensitive_console_prompt(prompt):
        prompt = (prompt or "").lower()
        sensitive_tokens = ("password", "contrase", "clave", "secret")
        return any(token in prompt for token in sensitive_tokens)
