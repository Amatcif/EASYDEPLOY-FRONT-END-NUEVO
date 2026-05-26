from __future__ import annotations

import json
import sys
import threading
import traceback

from .action_registry import ActionRegistry
from .event_protocol import EventSink
from .headless_host import HeadlessEasyDeployHost


class BridgeServer:
    def __init__(self):
        self.sink = EventSink(sys.__stdout__)
        self.host = HeadlessEasyDeployHost(self.sink)
        self.registry = ActionRegistry(self.host)
        self._actions_lock = threading.Lock()
        self._running_actions: dict[str, threading.Thread] = {}

    def run(self):
        self.sink.emit("ready", app="Easy Deploy Bridge")
        for raw_line in sys.stdin:
            line = raw_line.strip().lstrip("\ufeff")
            if not line:
                continue
            try:
                message = json.loads(line)
                self._handle_message(message)
            except Exception as exc:
                self.sink.emit(
                    "error",
                    title="Bridge",
                    message=f"No se pudo procesar el mensaje: {exc}",
                    traceback=traceback.format_exc(),
                )
        self._wait_for_running_actions()

    def _wait_for_running_actions(self):
        while True:
            with self._actions_lock:
                threads = list(self._running_actions.values())
            if not threads:
                return
            for thread in threads:
                thread.join(timeout=0.2)

    def _handle_message(self, message: dict):
        msg_type = message.get("type")
        request_id = str(message.get("id") or "")
        if msg_type == "run_action":
            action = str(message.get("action") or "")
            payload = message.get("payload") or {}
            self.sink.emit("log", source="BACKEND", level="info", message=f"[BACKEND] JSON recibido: {action}")
            self._start_action(request_id, action, payload)
            return
        if msg_type == "prompt_response":
            self.host.respond_prompt(message.get("prompt_id"), message.get("value"))
            return
        if msg_type == "cancel":
            self.host.cancelar_proceso()
            self.sink.emit("finished", id=request_id, action="cancel", success=True)
            return
        if msg_type == "shutdown":
            self.host.cancelar_proceso()
            self.sink.emit("finished", id=request_id, action="shutdown", success=True)
            sys.exit(0)
        raise ValueError(f"Tipo de mensaje no permitido: {msg_type}")

    def _has_background_task(self) -> bool:
        thread = getattr(self.host, "active_thread", None)
        return bool(thread and thread.is_alive())

    def _start_action(self, request_id: str, action: str, payload: dict):
        non_blocking = {
            "app.info",
            "dashboard.open_logs",
            "tools.open_logs",
            "updates.load_settings",
            "ping.favorites",
            "ping.add_favorite",
            "ping.delete_favorite",
            "dashboard.ping",
        }
        with self._actions_lock:
            busy = bool(self._running_actions) or self._has_background_task()
        if busy and action not in non_blocking:
            message = "Ya hay una tarea en ejecución. Cancela la tarea actual o espera a que termine antes de iniciar otra."
            self.sink.emit("error", id=request_id, action=action, source="BACKEND", level="warning", title="Proceso en curso", message=message)
            self.sink.emit("finished", id=request_id, action=action, success=False, result={"busy": True, "message": message})
            return

        def worker():
            success = True
            result = {}
            try:
                result = self.registry.run(action, payload)
            except Exception as exc:
                success = False
                result = {"error": str(exc)}
                self.sink.emit(
                    "error",
                    id=request_id,
                    action=action,
                    title=action or "Acción",
                    message=str(exc),
                    traceback=traceback.format_exc(),
                )
            finally:
                self.sink.emit("finished", id=request_id, action=action, success=success, result=result)
                with self._actions_lock:
                    self._running_actions.pop(request_id, None)

        thread = threading.Thread(target=worker, daemon=True)
        with self._actions_lock:
            self._running_actions[request_id] = thread
        thread.start()
        self.sink.emit("accepted", id=request_id, action=action)


def self_test() -> int:
    server = BridgeServer()
    actions = sorted(server.registry.actions.keys())
    server.sink.emit("log", source="SELFTEST", level="info", message=f"Acciones registradas: {len(actions)}")
    checks = {
        "app.info": {},
        "dashboard.check_admin": {},
        "security.firewall_status": {},
    }
    results = {}
    ok = True
    for action, payload in checks.items():
        try:
            results[action] = server.registry.run(action, payload)
            server.sink.emit("log", source="SELFTEST", level="success", message=f"{action}: OK")
        except Exception as exc:
            ok = False
            results[action] = {"error": str(exc)}
            server.sink.emit("error", source="SELFTEST", level="error", title=action, message=str(exc))
    server.sink.emit("data", name="self_test", value={"ok": ok, "actions": actions, "results": results})
    return 0 if ok else 1


def main():
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    BridgeServer().run()


if __name__ == "__main__":
    main()
