from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from ..constants import APP_NAME, APP_VERSION
from ..core.license_guard import LicenseGuard
from ..core.sysutils import SysUtils
from ..tasks.ad_users import task_ad_create_users
from ..tasks.replication import task_dfsr_action, task_repadmin_syncall
from ..tasks.skype import (
    pre_task_skype_dns,
    pre_task_skype_install,
    pre_task_skype_permissions,
    pre_task_skype_prereqs,
)


DEFAULT_UPDATE_URL = (
    "https://www.dropbox.com/scl/fi/p8qbe0fzn17nk7qdah75x/update.json"
    "?rlkey=7yb1odpc9aptdrek0mk7iafgk&st=3yg87fc3&dl=1"
)


def compare_versions(remote_version: str, local_version: str = APP_VERSION) -> int:
    def parts(value):
        nums = [int(item) for item in re.findall(r"\d+", str(value or ""))]
        return nums or [0]

    left = parts(remote_version)
    right = parts(local_version)
    size = max(len(left), len(right))
    left.extend([0] * (size - len(left)))
    right.extend([0] * (size - len(right)))
    return (left > right) - (left < right)


def normalize_dropbox_download_url(url: str) -> str:
    parsed = urllib.parse.urlparse(str(url or "").strip())
    if "dropbox.com" not in parsed.netloc.lower():
        return str(url or "").strip()
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, value) for key, value in query if key.lower() not in {"dl", "raw"}]
    query.append(("dl", "1"))
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


def is_http_url(url: str) -> bool:
    return urllib.parse.urlparse(str(url or "").strip()).scheme.lower() in {"http", "https"}


def app_data_path(*parts: str) -> Path:
    base = Path(SysUtils.app_data_dir())
    return base.joinpath(*parts)


def update_settings_path() -> Path:
    return app_data_path("update_settings.json")


def updates_dir() -> Path:
    path = app_data_path("updates")
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_update_settings() -> dict:
    path = update_settings_path()
    if not path.exists():
        return {"url": DEFAULT_UPDATE_URL}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"url": DEFAULT_UPDATE_URL}
    if not isinstance(data, dict):
        return {"url": DEFAULT_UPDATE_URL}
    data.setdefault("url", DEFAULT_UPDATE_URL)
    return data


def save_update_settings(url: str) -> dict:
    path = update_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"url": str(url or "").strip() or DEFAULT_UPDATE_URL}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def fetch_update_json(url: str) -> dict:
    url = normalize_dropbox_download_url(url)
    if not is_http_url(url):
        raise ValueError("La URL de actualización debe empezar por http:// o https://.")
    request = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(1024 * 1024)
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("El update.json no contiene un objeto JSON válido.")
    return data


def safe_update_filename(filename: str, version: str) -> str:
    filename = os.path.basename(str(filename or "").strip())
    if not filename.lower().endswith(".exe"):
        clean_version = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(version or "update")).strip("_")
        filename = f"EasyDeploy_Setup_v{clean_version or 'update'}.exe"
    return re.sub(r"[^0-9A-Za-z_. -]+", "_", filename).strip() or "EasyDeploy_Setup.exe"


class ActionRegistry:
    def __init__(self, host):
        self.host = host
        self.actions = {
            "app.info": self.app_info,
            "dashboard.check_admin": self.dashboard_check_admin,
            "dashboard.check_resources": self.dashboard_check_resources,
            "dashboard.open_logs": self.open_logs,
            "dashboard.keyboard_es": self.keyboard_es,
            "dashboard.firewall_status": self.firewall_status,
            "dashboard.system_info": self.system_info,
            "dashboard.roles_installed": self.roles_installed,
            "dashboard.top_processes": self.top_processes,
            "dashboard.ping": self.ping_once,
            "dashboard.disk_management": lambda payload: self.host._accion_abrir_disk_management(),
            "system.time_sync": lambda payload: self.host.iniciar_tarea(self.host.task_time_sync),
            "system.kms": lambda payload: self.host.iniciar_tarea(self.host.task_kms),
            "kms.run": lambda payload: self.host.iniciar_tarea(self.host.task_kms),
            "system.sql": lambda payload: self.host.iniciar_tarea(self.host.task_install_sql),
            "sql.install_2022": lambda payload: self.host.iniciar_tarea(self.host.task_install_sql),
            "system.jchat": lambda payload: self.host.iniciar_tarea(self.host.task_jchat),
            "jchat.openfire": lambda payload: self.host.iniciar_tarea(self.host.task_jchat),
            "system.jchat_cli": lambda payload: self.host.iniciar_tarea(self.host.task_jchat_cli),
            "jchat.cli": lambda payload: self.host.iniciar_tarea(self.host.task_jchat_cli),
            "sharepoint.roles": lambda payload: self.host.iniciar_tarea(self.host.task_sp_roles),
            "sharepoint.install": lambda payload: self.host.iniciar_tarea(self.host.task_sp_prereqs),
            "ad.dc1": lambda payload: self.host.pre_task_dc1(),
            "ad.dc2": lambda payload: self.host.pre_task_dc2(),
            "ad.join_domain": lambda payload: self.host.pre_task_join_domain(),
            "ad.gpo": lambda payload: self.host.iniciar_tarea(self.host.task_gpupdate_force),
            "tools.gpo_force": lambda payload: self.host.iniciar_tarea(self.host.task_gpupdate_force),
            "ad.create_users": self.ad_create_users,
            "ad.netfx35": lambda payload: self.host.iniciar_tarea(self.host.task_netfx35),
            "programs.netfx35": lambda payload: self.host.iniciar_tarea(self.host.task_netfx35),
            "ad.repadmin": lambda payload: self.host.iniciar_tarea(task_repadmin_syncall, self.host),
            "ad.d2d4": self.d2d4_action,
            "exchange.prereqs": lambda payload: self.host.pre_task_exchange_prereqs(),
            "exchange.prepare_schema": lambda payload: self.host.pre_task_exchange_schema(),
            "exchange.install": lambda payload: self.host.pre_task_exchange_install(),
            "exchange.create_users": self.exchange_create_users,
            "exchange.recover_server": lambda payload: self.host.pre_task_exchange_recover_server(),
            "skype.prereqs": lambda payload: pre_task_skype_prereqs(self.host),
            "skype.install": lambda payload: pre_task_skype_install(self.host),
            "skype.permissions": lambda payload: pre_task_skype_permissions(self.host),
            "skype.dns": lambda payload: pre_task_skype_dns(self.host),
            "programs.firefox": lambda payload: self.host.iniciar_tarea(self.host.task_install_firefox),
            "programs.winrar": lambda payload: self.host.iniciar_tarea(self.host.task_install_winrar),
            "programs.adobe_reader": lambda payload: self.host.iniciar_tarea(self.host.task_install_adobe_reader),
            "programs.office_skype": lambda payload: self.host.pre_task_install_office_skype(),
            "programs.install_all": self.programs_install_all,
            "security.firewall_status": self.firewall_status,
            "security.firewall_disable": lambda payload: self.host.pre_task_disable_windows_firewall(),
            "security.firewall_enable": lambda payload: self.host.iniciar_tarea(self.host.task_enable_windows_firewall),
            "security.audit": self.pending_action,
            "tools.cmd": lambda payload: self.host._open_admin_cmd(),
            "tools.powershell": lambda payload: self.host._open_admin_powershell(),
            "tools.dns_manager": lambda payload: self.host._open_dns_manager(),
            "tools.aduc": lambda payload: self.host._open_ad_users_and_computers(),
            "tools.gpmc": lambda payload: self.host._open_group_policy_management(),
            "tools.open_resources": self.open_resources,
            "tools.open_logs": self.open_logs,
            "tools.versions": self.versions,
            "tools.credits": self.credits,
            "tools.ping": self.ping_once,
            "ping.favorites": self.ping_favorites,
            "ping.add_favorite": self.ping_add_favorite,
            "ping.delete_favorite": self.ping_delete_favorite,
            "networks.switch_allied": lambda payload: self.host.open_switch_allied_tool(),
            "networks.switch_cisco": lambda payload: self.host.open_switch_cisco_tool(),
            "networks.router": lambda payload: self.host.open_router_tool(),
            "networks.asa": self.pending_action,
            "networks.checkpoint": self.pending_action,
            "networks.topology": self.pending_action,
            "networks.ip_addressing": self.pending_action,
            "updates.load_settings": self.updates_load_settings,
            "updates.save_endpoint": self.updates_save_endpoint,
            "updates.check": self.updates_check,
            "updates.download": self.updates_download,
            "updates.launch_installer": self.updates_launch_installer,
            "activation.status": self.activation_status,
            "activation.activate": self.activation_activate,
            "activation.trial_status": self.activation_status,
        }
        for guide_name, action_id in {
            "Guía DC1": "guides.open_dc1",
            "Guía DC2": "guides.open_dc2",
            "Guía Exchange": "guides.open_exchange",
            "Guía Skype": "guides.open_skype",
            "Guía Jchat": "guides.open_jchat",
            "Guía Sharepoint": "guides.open_sharepoint",
            "Guía D2 D4": "guides.open_d2d4",
            "Guía Certificados": "guides.open_certificates",
            "Guía DHCP": "guides.open_dhcp",
            "Guía WDS": "guides.open_wds",
            "Guía WSUS": "guides.open_wsus",
        }.items():
            self.actions[action_id] = lambda payload, name=guide_name: self.host.open_guide_pdf(name)
        self.dangerous_actions = {
            "ad.dc1",
            "ad.dc2",
            "ad.join_domain",
            "ad.gpo",
            "tools.gpo_force",
            "ad.netfx35",
            "programs.netfx35",
            "ad.repadmin",
            "ad.d2d4",
            "ad.create_users",
            "system.time_sync",
            "system.kms",
            "kms.run",
            "system.sql",
            "sql.install_2022",
            "system.jchat",
            "jchat.openfire",
            "system.jchat_cli",
            "jchat.cli",
            "sharepoint.roles",
            "sharepoint.install",
            "exchange.prereqs",
            "exchange.prepare_schema",
            "exchange.install",
            "exchange.recover_server",
            "exchange.create_users",
            "skype.prereqs",
            "skype.install",
            "skype.permissions",
            "skype.dns",
            "programs.firefox",
            "programs.winrar",
            "programs.adobe_reader",
            "programs.office_skype",
            "programs.install_all",
            "security.firewall_disable",
            "security.firewall_enable",
            "networks.switch_allied",
            "networks.switch_cisco",
            "networks.router",
        }

    def _mask_payload_for_log(self, payload):
        if not isinstance(payload, dict):
            return payload
        masked = {}
        for key, value in payload.items():
            if any(token in str(key).lower() for token in ("password", "clave", "code", "token", "secret")):
                masked[key] = "***"
            else:
                masked[key] = value
        return masked

    def _write_action_audit(self, action_id: str, payload=None, status="inicio", result=None):
        try:
            logs_dir = Path(self.host.log_manager.logs_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)
            safe_action = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(action_id or "accion")).strip("_")[:80] or "accion"
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            audit_path = logs_dir / f"{stamp}_{safe_action}_audit.log"
            with audit_path.open("a", encoding="utf-8") as handle:
                handle.write(f"Acción: {action_id}\n")
                handle.write(f"Estado: {status}\n")
                handle.write(f"Fecha local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                handle.write(f"Payload: {json.dumps(self._mask_payload_for_log(payload or {}), ensure_ascii=False)}\n")
                if result is not None:
                    handle.write(f"Resultado: {json.dumps(result, ensure_ascii=False, default=str)}\n")
        except Exception:
            pass

    def run(self, action_id: str, payload=None):
        payload = payload or {}
        self._write_action_audit(action_id, payload, "inicio")
        handler = self.actions.get(action_id)
        if not handler:
            raise KeyError(f"Acción no permitida: {action_id}")
        self.host.sink.emit("log", source="PYTHON", level="info", message=f"[PYTHON] Acción encontrada: {action_id}")
        if payload.get("dryRun") and action_id in self.dangerous_actions:
            message = f"[PYTHON] Dry-run activo. Acción real mapeada y no ejecutada por seguridad: {action_id}"
            self.host.sink.emit("log", source="PYTHON", level="warning", message=message)
            return {
                "ok": True,
                "dryRun": True,
                "action": action_id,
                "mapped": True,
                "message": message,
            }
        self.host.sink.emit("status", level="info", message=f"[PYTHON] Ejecutando acción: {action_id}")
        result = handler(payload)
        final_result = result if isinstance(result, dict) else {"ok": True}
        self._write_action_audit(action_id, payload, "finalizada", final_result)
        return final_result

    def app_info(self, payload):
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "payload_root": self.host.payload_root,
            "base_path": self.host.base_path,
            "admin": SysUtils.is_admin(),
        }

    def pending_action(self, payload):
        message = "Esta acción queda pendiente de adaptación al nuevo front-end."
        self.host.sink.emit("log", source="BRIDGE", level="warning", message=message)
        return {"ok": False, "pending": True, "message": message}

    def pending_complex_form(self, payload):
        message = (
            "Formulario complejo pendiente de migración visual. "
            "La lógica antigua se conserva en easy_deploy_app y no se ha duplicado."
        )
        self.host.sink.emit("log", source="BRIDGE", level="warning", message=message)
        return {"ok": False, "pending": True, "message": message}

    def ad_create_users(self, payload):
        users = (payload or {}).get("users")
        if not users:
            name = self.host.input_dialog("Crear usuarios AD", "Nombre de usuario / nombre visible:")
            if not name:
                return {"ok": False, "cancelled": True}
            password = self.host.input_dialog("Crear usuarios AD", "Contraseña:", is_password=True)
            if not password:
                return {"ok": False, "cancelled": True}
            ou = self.host.input_dialog(
                "Crear usuarios AD",
                "Destino en AD (opcional / avanzado). Deja vacío para usar Users:",
                default="",
            ) or "Users"
            sam = re.sub(r"[^A-Za-z0-9._-]+", ".", str(name).strip()).strip(".").lower()[:20]
            users = [{
                "Name": str(name).strip(),
                "SamAccountName": sam,
                "OrganizationalUnit": str(ou).strip() or "Users",
                "Password": str(password),
                "MustChangePassword": False,
                "CannotChangePassword": True,
                "PasswordNeverExpires": True,
                "AccountDisabled": False,
            }]
        self.host.iniciar_tarea(task_ad_create_users, self.host, users)
        return {"ok": True, "users": len(users)}

    def exchange_create_users(self, payload):
        users = (payload or {}).get("users")
        if not users:
            email = self.host.input_dialog("Crear usuarios Exchange", "Correo o alias:")
            if not email:
                return {"ok": False, "cancelled": True}
            first_name = self.host.input_dialog("Crear usuarios Exchange", "Nombre visible:")
            if not first_name:
                return {"ok": False, "cancelled": True}
            password = self.host.input_dialog("Crear usuarios Exchange", "Contraseña:", is_password=True)
            if not password:
                return {"ok": False, "cancelled": True}
            ou = self.host.input_dialog(
                "Crear usuarios Exchange",
                "Destino en AD (opcional / avanzado). Deja vacío para usar Users:",
                default="",
            ) or ""
            email = str(email).strip().lower()
            domain = email.split("@", 1)[1] if "@" in email else ""
            users = [{
                "Email": email,
                "FirstName": str(first_name).strip(),
                "OrganizationalUnit": str(ou).strip(),
                "Password": str(password),
                "Domain": domain,
            }]
        self.host.iniciar_tarea(self.host.task_exchange_create_users, users)
        return {"ok": True, "users": len(users)}

    def dashboard_check_admin(self, payload):
        admin = SysUtils.is_admin()
        self.host.sink.emit(
            "log",
            source="SYSTEM",
            level="success" if admin else "warning",
            message="Permisos de administrador detectados." if admin else "Easy Deploy no está ejecutándose como administrador.",
        )
        return {"admin": admin}

    def dashboard_check_resources(self, payload):
        report = SysUtils.payload_resource_report(self.host.payload_root)
        missing = report.get("missing", [])
        self.host.sink.emit(
            "log",
            source="SYSTEM",
            level="success" if report.get("complete") else "warning",
            message="Recursos OK." if report.get("complete") else f"Recursos incompletos: {len(missing)} elementos pendientes.",
        )
        return report

    def open_logs(self, payload=None):
        path = self.host.log_manager.logs_dir
        os.makedirs(path, exist_ok=True)
        subprocess.Popen(["explorer.exe", str(path)], creationflags=subprocess.CREATE_NO_WINDOW)
        return {"path": path}

    def open_resources(self, payload=None):
        if not os.path.isdir(self.host.payload_root):
            raise FileNotFoundError(f"No se encontró la carpeta de recursos: {self.host.payload_root}")
        os.startfile(self.host.payload_root)
        return {"path": self.host.payload_root}

    def keyboard_es(self, payload):
        ok, detail = SysUtils.set_spanish_spain_keyboard()
        self.host.sink.emit(
            "log",
            source="SYSTEM",
            level="success" if ok else "warning",
            message=detail or ("Teclado español aplicado." if ok else "No se pudo aplicar teclado español."),
        )
        return {"ok": ok, "detail": detail}

    def firewall_status(self, payload=None):
        status = SysUtils.firewall_all_profiles_enabled()
        if status is None:
            status = SysUtils.firewall_all_profiles_enabled_quick()
        enabled = bool(status)
        self.host.sink.emit(
            "log",
            source="FIREWALL",
            level="success" if enabled else "warning",
            message="Firewall activo en todos los perfiles." if enabled else "Algún perfil de Firewall está desactivado.",
        )
        return {"enabled": enabled}

    def system_info(self, payload):
        commands = [
            ["cmd.exe", "/c", "hostname"],
            ["cmd.exe", "/c", "ver"],
        ]
        output = []
        for cmd in commands:
            code, text = SysUtils.run_native_command(cmd, timeout=20)
            if text.strip():
                output.append(text.strip())
        for line in output:
            self.host.sink.emit("log", source="SYSTEM", level="info", message=line)
        return {"output": output}

    def roles_installed(self, payload):
        command = "Get-WindowsFeature | Where-Object Installed | Select-Object -ExpandProperty Name"
        ok, output = SysUtils.run_powershell(command, capture=True, timeout=60)
        level = "success" if ok else "error"
        for line in output.splitlines()[:120]:
            if line.strip():
                self.host.sink.emit("log", source="SYSTEM", level=level, message=line.strip())
        return {"ok": ok, "output": output}

    def top_processes(self, payload):
        command = (
            "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 "
            "ProcessName,Id,CPU,WorkingSet64 | Format-Table -AutoSize"
        )
        ok, output = SysUtils.run_powershell(command, capture=True, timeout=30)
        for line in output.splitlines():
            if line.strip():
                self.host.sink.emit("log", source="SYSTEM", level="info", message=line)
        return {"ok": ok, "output": output}

    def ping_once(self, payload):
        target = str((payload or {}).get("target") or "").strip()
        if not target:
            target = self.host.input_dialog("Ping", "Introduce IP o nombre DNS:")
        if not target:
            return {"ok": False, "cancelled": True}
        ok, output = SysUtils.ping_host(target, count=4, timeout_ms=3000)
        for line in str(output).splitlines():
            if line.strip():
                self.host.sink.emit("log", source="NETWORK", level="success" if ok else "warning", message=line)
        self.host.sink.emit(
            "data",
            name="ping.result",
            value={"target": target, "ok": ok, "output": output},
        )
        return {"ok": ok, "target": target, "output": output}

    def ping_favorites(self, payload=None):
        favorites = self.host._load_ping_favorites()
        self.host.sink.emit("data", name="ping.favorites", value=favorites)
        return {"favorites": favorites}

    def ping_add_favorite(self, payload):
        host = str((payload or {}).get("host") or "").strip()
        name = str((payload or {}).get("name") or "").strip()
        if not host:
            raise ValueError("No se ha indicado IP o nombre DNS para Favoritos.")

        def notify(title, level="info", message=""):
            self.host.sink.emit("log", source="PING", level=level, message=message or title)

        saved = self.host._add_ping_favorite(host, name, notify=notify)
        favorites = self.host._load_ping_favorites()
        self.host.sink.emit("data", name="ping.favorites", value=favorites)
        return {"ok": bool(saved), "favorites": favorites}

    def ping_delete_favorite(self, payload):
        host = str((payload or {}).get("host") or "").strip()
        if not host:
            raise ValueError("No se ha indicado favorito para borrar.")
        deleted = self.host._delete_ping_favorite(host)
        favorites = self.host._load_ping_favorites()
        self.host.sink.emit("data", name="ping.favorites", value=favorites)
        return {"ok": bool(deleted), "favorites": favorites}

    def programs_install_all(self, payload):
        """Ejecuta el arsenal offline en el mismo orden visual del front-end."""
        self.host.sink.emit("log", source="INSTALLER", level="info", message="Iniciando Instalar todo el arsenal: .NET 3.5, Firefox, WinRAR, Adobe Reader y Office + Skype.")
        tasks = (
            ("Net Framework 3.5", self.host.task_netfx35),
            ("Firefox", self.host.task_install_firefox),
            ("WinRAR", self.host.task_install_winrar),
            ("Adobe Reader", self.host.task_install_adobe_reader),
        )
        for label, task in tasks:
            self.host.sink.emit("log", source="INSTALLER", level="info", message=f"Instalando {label}...")
            self.host.iniciar_tarea(task)
        self.host.sink.emit("log", source="INSTALLER", level="info", message="Lanzando Office + Skype...")
        self.host.pre_task_install_office_skype()
        return {"ok": True, "components": 5}

    def d2d4_action(self, payload):
        action_key = str((payload or {}).get("mode") or "").strip().lower()
        if action_key not in {"d2", "d4"}:
            action_key = self.host.input_dialog("D2/D4", "Escribe D2 o D4 para ejecutar la acción DFSR:")
        action_key = str(action_key or "").strip().lower()
        if action_key not in {"d2", "d4"}:
            return {"ok": False, "cancelled": True}
        self.host.iniciar_tarea(task_dfsr_action, self.host, action_key)
        return {"ok": True, "mode": action_key}

    def versions(self, payload):
        from ..changelog import CHANGELOG

        self.host.sink.emit("data", name="versions", value=CHANGELOG[:8])
        return {"versions": CHANGELOG[:8]}

    def credits(self, payload):
        message = (
            "Easy Deploy\n"
            "Autoría y créditos disponibles en la aplicación antigua. "
            "La ventana visual completa queda pendiente de migración al front-end nuevo."
        )
        self.host.sink.emit("notification", level="info", title="Créditos", message=message)
        return {"message": message}

    def activation_status(self, payload=None):
        guard = LicenseGuard()
        status = guard.status
        data = {
            "usable": status.usable,
            "blocked": status.blocked,
            "expired": status.expired,
            "days_used": status.days_used,
            "days_remaining": status.days_remaining,
            "message": status.message,
            "detail": status.detail,
        }
        self.host.sink.emit("data", name="activation.status", value=data)
        return data

    def activation_activate(self, payload):
        code = str((payload or {}).get("code") or "").strip()
        if not code:
            code = self.host.input_dialog("Activación", "Introduce el código de licencia:", is_password=True)
        ok = SysUtils.validar_licencia(code)
        self.host.sink.emit(
            "log",
            source="SECURITY",
            level="success" if ok else "error",
            message="Código de licencia válido." if ok else "Código de licencia incorrecto.",
        )
        return {"ok": ok}

    def updates_load_settings(self, payload=None):
        data = load_update_settings()
        self.host.sink.emit("data", name="updates.settings", value=data)
        return data

    def updates_save_endpoint(self, payload):
        url = str((payload or {}).get("url") or "").strip()
        if not is_http_url(url):
            raise ValueError("La URL debe empezar por http:// o https://.")
        data = save_update_settings(url)
        self.host.sink.emit("log", source="UPDATES", level="success", message="Ruta de actualización guardada.")
        return data

    def updates_check(self, payload):
        url = str((payload or {}).get("url") or "").strip() or load_update_settings().get("url", DEFAULT_UPDATE_URL)
        data = fetch_update_json(url)
        remote_version = str(data.get("version") or "").strip()
        installer_url = str(data.get("url") or data.get("downloadUrl") or data.get("download_url") or "").strip()
        filename = str(data.get("filename") or "").strip()
        sha256 = str(data.get("sha256") or "").strip()
        mandatory = bool(data.get("mandatory", False))
        if not remote_version:
            raise ValueError("El update.json no contiene version.")
        comparison = compare_versions(remote_version)
        notes = data.get("notes") or data.get("cambios") or []
        self.host.sink.emit(
            "data",
            name="updates.check",
            value={
                "local_version": APP_VERSION,
                "remote_version": remote_version,
                "available": comparison > 0,
                "notes": notes,
                "url": url,
                "installer_url": installer_url,
                "filename": filename,
                "sha256": sha256,
                "mandatory": mandatory,
            },
        )
        self.host.sink.emit(
            "log",
            source="UPDATES",
            level="success" if comparison <= 0 else "warning",
            message=(
                "Easy Deploy está actualizado."
                if comparison <= 0
                else f"Hay una versión nueva disponible: {remote_version}."
            ),
        )
        return {
            "local_version": APP_VERSION,
            "remote_version": remote_version,
            "available": comparison > 0,
            "notes": notes,
            "url": url,
            "installer_url": installer_url,
            "filename": filename,
            "sha256": sha256,
            "mandatory": mandatory,
            "raw": data,
        }

    def updates_download(self, payload):
        installer_url = normalize_dropbox_download_url(str((payload or {}).get("url") or "").strip())
        remote_version = str((payload or {}).get("version") or "update")
        sha256 = str((payload or {}).get("sha256") or "").strip().lower()
        filename = safe_update_filename((payload or {}).get("filename") or os.path.basename(urllib.parse.urlparse(installer_url).path), remote_version)
        if not is_http_url(installer_url):
            raise ValueError("La URL del instalador debe empezar por http:// o https://.")
        if not filename.lower().endswith(".exe"):
            raise ValueError("El instalador de actualización debe ser un archivo .exe.")
        target = updates_dir() / filename
        request = urllib.request.Request(installer_url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        self.host.sink.emit("status", level="info", message=f"Descargando instalador: {filename}")
        with urllib.request.urlopen(request, timeout=60) as response, open(target, "wb") as handle:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    self.host.update_progress(downloaded / total)
        if sha256:
            digest = hashlib.sha256(target.read_bytes()).hexdigest().lower()
            if digest != sha256:
                target.unlink(missing_ok=True)
                raise ValueError("El SHA256 del instalador descargado no coincide.")
        self.host.sink.emit("data", name="updates.downloaded", value={"path": str(target)})
        return {"path": str(target)}

    def updates_launch_installer(self, payload):
        installer = Path(str((payload or {}).get("path") or ""))
        base = updates_dir().resolve()
        if not installer.exists() or installer.suffix.lower() != ".exe":
            raise FileNotFoundError("No se encontró un instalador .exe válido.")
        if base not in installer.resolve().parents:
            raise ValueError("El instalador debe estar dentro de la carpeta controlada de actualizaciones.")
        helper = base / f"easydeploy_update_{os.getpid()}.cmd"
        helper.write_text(
            "@echo off\r\n"
            "setlocal\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            f'start "" /wait "{installer}"\r\n'
            f'for /l %%i in (1,1,20) do (del /f /q "{installer}" >nul 2>nul & if not exist "{installer}" goto done & timeout /t 1 /nobreak >nul)\r\n'
            ":done\r\n"
            'del "%~f0" >nul 2>nul\r\n',
            encoding="utf-8",
        )
        subprocess.Popen(["cmd.exe", "/c", str(helper)], creationflags=subprocess.CREATE_NO_WINDOW)
        self.host.sink.emit("restart_required", installer=str(installer))
        return {"launched": True, "installer": str(installer)}
