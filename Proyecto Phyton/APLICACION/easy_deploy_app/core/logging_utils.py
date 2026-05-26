import os
import re
import tempfile
import threading
from datetime import datetime


class LogManager:
    """Escribe logs persistentes por ejecucion de tarea."""

    def __init__(self, app_folder="EasyDeploy"):
        base_dir = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        self.logs_dir = os.path.join(base_dir, app_folder, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.current_log_path = None
        self._lock = threading.Lock()

    def start_run(self, task_name):
        safe_task = self._safe_name(task_name or "tarea")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.current_log_path = os.path.join(self.logs_dir, f"{timestamp}_{safe_task}.log")
        self.write("=" * 72)
        self.write(f"Inicio de tarea: {task_name}")
        self.write(f"Fecha local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.write("=" * 72)
        return self.current_log_path

    def write(self, message):
        if not self.current_log_path:
            return
        lines = [line.rstrip() for line in str(message).splitlines() if line.strip()]
        if not lines:
            return
        with self._lock:
            with open(self.current_log_path, "a", encoding="utf-8") as fh:
                for line in lines:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    fh.write(f"[{timestamp}] {line}\n")

    def finish_run(self, status="finalizada"):
        self.write("-" * 72)
        self.write(f"Tarea {status}")
        self.write(f"Fin local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    @staticmethod
    def _safe_name(value):
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_")
        return safe[:80] or "tarea"
