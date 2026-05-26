import ctypes
import os
import sys
import threading

import customtkinter as ctk

from .core.sysutils import SysUtils
from .core.license_guard import LicenseGuard, SESSION_CHECK_MS
from .ui.environment import EnvironmentMixin
from .ui.actions import ActionsMixin
from .ui.layout import LayoutMixin
from .tasks.sharepoint import SharePointTasksMixin
from .tasks.kms import KmsTasksMixin
from .tasks.system import SystemTasksMixin
from .tasks.jchat import JchatTasksMixin
from .tasks.sql import SqlTasksMixin
from .tasks.exchange import ExchangeTasksMixin
from .tasks.domain import DomainTasksMixin
from .tasks.network import NetworkTasksMixin
from .tasks.programs import ProgramsTasksMixin
from .tasks.guides import GuidesTasksMixin
from .constants import APP_DISPLAY_TITLE

ctk.set_default_color_theme("blue")


class EASYDEPLOY(
    EnvironmentMixin,
    ActionsMixin,
    LayoutMixin,
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
    ctk.CTk,
):
    def __init__(self):
        super().__init__()
        self._init_single_instance_guard()
        self.ui_thread_id = threading.get_ident()
        self.withdraw() # Ocultar carga inicial
        
        # ---   ---
        # Usamos update_idletasks para asegurar que tenemos datos de pantalla
        self.update_idletasks()
        try:
            ctk.set_appearance_mode(SysUtils.detectar_modo_windows())
        except Exception:
            pass

        self.license_guard = LicenseGuard()
        self.license_status = self.license_guard.status
        if not self.license_status.usable:
            self.modal_dialog(
                "Licencia bloqueada",
                f"{self.license_status.message}\n\n{self.license_status.detail}",
                "error",
                [("Cerrar", True, "danger")],
            )
            sys.exit()
        
        # Verificacion de contrasena de acceso
        licencia_valida = False
        intentos = 0
        license_error = ""
        while intentos < 3:
            # LLAMADA CORREGIDA: Usamos directamente self.input_dialog
            code = self.input_dialog(
                APP_DISPLAY_TITLE,
                "INTRODUCE EL CÓDIGO DE LICENCIA:",
                is_password=True,
                initial_error=license_error,
            )
            
            # input_dialog devuelve el texto o None si se cancela/cierra
            
            if SysUtils.validar_licencia(code):
                licencia_valida = True
                break
            else:
                if code is None: # Si cierra la ventana o pulsa Cancelar
                    sys.exit()
                intentos += 1
                remaining = max(0, 3 - intentos)
                license_error = (
                    "Licencia incorrecta. Acceso denegado."
                    if remaining == 0
                    else f"Licencia incorrecta. Intentos restantes: {remaining}."
                )
        
        if not licencia_valida:
            sys.exit()

        
        # --- FIN LICENCIA ---

        self.title(APP_DISPLAY_TITLE)

        # Centrar la ventana principal al iniciar con altura suficiente para Inicio.
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = 1180
        h = min(820, max(720, screen_h - 45))
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.minsize(1020, 660)
        ctk.set_appearance_mode(SysUtils.detectar_modo_windows())
        
        # -- Estado y Utils --
        from .core.logging_utils import LogManager
        from .core.progress import ProgresoManager

        self.db = ProgresoManager()
        self.log_manager = LogManager()
        self.stop_event = threading.Event()
        self.active_thread = None
        
        # Rutas base
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.payload_root = SysUtils.resolve_payload_root(self.base_path)
        self.startup_warning_shown = False

        # -- UI Layout --
        self._init_ui()
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.license_guard.start_session()
        self.after(SESSION_CHECK_MS, self._license_guard_tick)
        
        # -- Mostrar Splash --
        self.after(0, self.mostrar_splash)

    def _init_single_instance_guard(self):
        """Evita que otra instancia muestre la licencia encima de la app abierta."""
        self._single_instance_mutex = None
        allow_restart = os.environ.pop("EASYDEPLOY_ALLOW_RESTART_INSTANCE", "") == "1"
        if os.name != "nt":
            return
        try:
            mutex_name = "Local\\EASY_DEPLOY_RT21_SINGLE_INSTANCE"
            kernel32 = ctypes.windll.kernel32
            mutex = kernel32.CreateMutexW(None, False, mutex_name)
            self._single_instance_mutex = mutex
            already_running = kernel32.GetLastError() == 183
            if already_running and not allow_restart:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "Easy Deploy ya esta abierto.\n\nCierra la instancia actual antes de abrir otra.",
                    "Easy Deploy",
                    0x40,
                )
                sys.exit(0)
        except Exception:
            self._single_instance_mutex = None

    def _license_guard_tick(self):
        status = self.license_guard.check_session_clock()
        self.license_status = status
        if not status.usable:
            self.modal_dialog(
                "Licencia bloqueada",
                f"{status.message}\n\n{status.detail}",
                "error",
                [("Cerrar", True, "danger")],
            )
            self.destroy()
            return
        self.after(SESSION_CHECK_MS, self._license_guard_tick)
