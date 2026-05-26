import ctypes
import fnmatch
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import winreg

from ..constants import (
    DEFAULT_LICENSE_SHA256,
    DOMAIN_RE,
    HOST_RE,
    IPV4_RE,
    LICENSE_HASH_ENV,
    NETBIOS_RE,
    PAYLOAD_DIR_NAMES,
    PRODUCT_KEY_RE,
)


class SysUtils:
    """Utilidades del sistema estáticas (Registry, PowerShell, etc)."""
    SPANISH_SPAIN_INPUT_TIPS = ("040A:0000040A", "0C0A:0000040A")
    NETFX35_ISO_NAME = "NetFramework3.5.iso"
    NETFX35_ISO_RELATIVE_PATH = os.path.join("OTROS", NETFX35_ISO_NAME)
    PAYLOAD_RESOURCE_SPEC = (
        (
            "EXCHANGE",
            (
                "Net Framework 4.8.exe",
                "rewrite_amd64_es-ES.msi",
                "UcmaRuntimeSetup.exe",
                "vcredist_x64 2012.exe",
                "vcredist_x64 2013.exe",
                "ExchangeServer2019-x64-cu15.iso",
            ),
        ),
        (
            "SHAPRE",
            (
                "1-sqlncli 2012 sp4.msi",
                "5-Synchronization.msi",
                "11-WindowsServerAppFabricSetup_x64.exe",
                "6-MicrosoftIdentityExtensions-64.msi",
                "4-setup_msipc_x64.exe",
                "2-WcfDataServices.exe",
                "7-NDP472-KB4054530-x86-x64-AllOS-ENU.exe",
                "AppFabric-KB3092423-x64-ENU.exe",
                "8-vcredist_x64_2012.exe",
                "9-vcredist_x64_2015.exe",
                "PrerequisiteInstaller.exe",
                "officeserver.img",
            ),
        ),
        (
            "SQL",
            (
                "msodbcsql.msi",
                "msoledbsql.msi",
                "SSMS-Setup-ESN.exe",
                "SQLServer2022-x64-ENU.iso",
            ),
        ),
        (
            "JCHAT",
            (
                "jre-8u371-windows-x64.exe",
                "openfire_4_7_5_x64.exe",
                "jchat-dist-package-windows-bundled-2.7.1.0.msi",
            ),
        ),
        (
            "OTROS",
            (
                "Firefox Setup*.exe",
                "winrar-x64*.exe",
                "AcroRdrDC*.exe",
                "NetFramework3.5.iso",
            ),
        ),
        (
            "OFFICE",
            (
                "officeoffline\\setup.exe",
                "officeoffline\\configuration.xml",
                "officeoffline\\Instalar_Office_Oculto.vbs",
                "officeoffline\\Instalar_office_offline.bat",
                "officeoffline\\Office",
            ),
        ),
        (
            "SKYPE",
            (
                "SW_DVD5_SfB_Server_2019_64Bit_Spanish_MLF_X21-89208.ISO",
                "Preskype\\Silverlight_x64.exe",
                "Preskype\\UcmaRuntimeSetup.exe",
            ),
        ),
        (
            "GUIAS",
            (
                "GUIA DC1.pdf",
                "GUIA DC2.pdf",
                "GUIA INTERCAMBIO ROLES.pdf",
                "GUIA RELACION DE CONFIANZA.pdf",
                "GUIA JCHAT.pdf",
                "GUIA EXCHANGE.pdf",
                "GUIA SKYPE.pdf",
                "GUIA D2 D4.pdf",
                "GUIA SHAREPOINT.pdf",
                "GUIA CERTIFICADOS.pdf",
                "GUIA DHCP.pdf",
                "GUIA WDS.pdf",
                "GUIA WSUS.pdf",
            ),
        ),
    )

    @staticmethod
    def oem_encoding():
        """Devuelve la pagina OEM de Windows para leer comandos nativos."""
        try:
            code_page = ctypes.windll.kernel32.GetOEMCP()
            if code_page:
                return f"cp{code_page}"
        except Exception:
            pass
        return "cp850"

    @staticmethod
    def _repair_mojibake(text):
        """Repara casos típicos UTF-8 leído como OEM, por ejemplo ra├¡z o a├▒adir."""
        if not isinstance(text, str) or not text:
            return text or ""
        if not any(marker in text for marker in ("├", "┬", "Â", "Ã")):
            return text
        for source_encoding in (SysUtils.oem_encoding(), "cp850", "cp437", "cp1252"):
            try:
                repaired = text.encode(source_encoding, errors="strict").decode("utf-8", errors="strict")
            except Exception:
                continue
            if repaired and repaired.count("�") <= text.count("�"):
                return repaired
        return text

    @staticmethod
    def decode_process_bytes(data, prefer_utf8=False):
        """Decodifica salida de procesos evitando textos tipo 'm?s' o 'ra├¡z'."""
        if not data:
            return ""
        if isinstance(data, str):
            return SysUtils._repair_mojibake(data)

        encodings = []
        if prefer_utf8:
            encodings.extend(("utf-8-sig", "utf-8"))
        encodings.extend((SysUtils.oem_encoding(), "cp1252", "utf-8"))

        seen = set()
        for encoding in encodings:
            if encoding in seen:
                continue
            seen.add(encoding)
            try:
                return SysUtils._repair_mojibake(data.decode(encoding))
            except UnicodeDecodeError:
                continue
            except LookupError:
                continue
        return SysUtils._repair_mojibake(data.decode(SysUtils.oem_encoding(), errors="replace"))

    @staticmethod
    def run_native_command(cmd, timeout=None):
        """Ejecuta comandos clasicos de Windows y decodifica stdout/stderr con OEM."""
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=timeout,
            )
            stdout = SysUtils.decode_process_bytes(res.stdout)
            stderr = SysUtils.decode_process_bytes(res.stderr)
            output = "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())
            return res.returncode, output
        except subprocess.TimeoutExpired as exc:
            stdout = SysUtils.decode_process_bytes(exc.stdout)
            stderr = SysUtils.decode_process_bytes(exc.stderr)
            output = "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())
            return -1, (output + f"\nTimeout ejecutando {' '.join(cmd)}.").strip()
        except Exception as exc:
            return -1, f"Error ejecutando {' '.join(cmd)}: {exc}"

    @staticmethod
    def is_admin():
        """Comprueba si el proceso actual tiene privilegios de administrador."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def is_windows_server():
        """Detecta si el sistema operativo actual es Windows Server."""
        cmd = "(Get-CimInstance Win32_OperatingSystem).ProductType"
        ok, output = SysUtils.run_powershell(cmd, capture=True)
        if not ok:
            return False
        return output.strip() in {"2", "3"}

    @staticmethod
    def firewall_all_profiles_enabled():
        """Devuelve True si Domain, Private y Public tienen Windows Firewall activo."""
        cmd = """
        $profiles = @(Get-NetFirewallProfile -Profile Domain,Private,Public -ErrorAction Stop)
        if ($profiles.Count -lt 3) {
            'Unknown'
            exit 0
        }
        $disabled = @($profiles | Where-Object { [string]$_.Enabled -ne 'True' })
        if ($disabled.Count -eq 0) { 'True' } else { 'False' }
        """
        ok, output = SysUtils.run_powershell(cmd, capture=True, timeout=12)
        if not ok:
            return SysUtils.firewall_all_profiles_enabled_quick()
        for line in reversed([item.strip().lower() for item in output.splitlines() if item.strip()]):
            if line == "true":
                return True
            if line == "false":
                return False
            if line == "unknown":
                return SysUtils.firewall_all_profiles_enabled_quick()
        return SysUtils.firewall_all_profiles_enabled_quick()

    @staticmethod
    def firewall_all_profiles_enabled_quick():
        """Lee el estado de Firewall desde el registro como respaldo rapido."""
        base = r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy"
        profiles = ("DomainProfile", "StandardProfile", "PublicProfile")
        states = []
        try:
            for profile in profiles:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, fr"{base}\{profile}") as key:
                    value, _ = winreg.QueryValueEx(key, "EnableFirewall")
                    states.append(int(value) != 0)
        except Exception:
            return None
        return all(states) if len(states) == 3 else None

    @staticmethod
    def get_os_caption():
        """Devuelve el nombre del sistema operativo sin depender de WMIC."""
        cmd = "(Get-CimInstance Win32_OperatingSystem).Caption"
        ok, output = SysUtils.run_powershell(cmd, capture=True)
        if ok and output.strip():
            return output.strip().splitlines()[0]
        return "Desconocido"

    @staticmethod
    def desktop_path():
        """Devuelve la ruta del escritorio del usuario actual."""
        return os.path.join(os.path.expanduser("~"), "Desktop")

    @staticmethod
    def app_data_dir():
        base_dir = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        path = os.path.join(base_dir, "EasyDeploy")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def get_easydeploy_temp_scripts_dir():
        """Carpeta controlada para scripts/datos temporales de tareas internas."""
        base_dir = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        path = os.path.join(base_dir, "EasyDeploy", "temp_scripts")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def make_temp_script_path(prefix, suffix):
        """Crea una ruta temporal controlada y bloquea fuentes Python temporales."""
        clean_prefix = re.sub(r"[^A-Za-z0-9_-]+", "_", str(prefix or "easydeploy")).strip("_")
        if not clean_prefix:
            clean_prefix = "easydeploy"

        clean_suffix = str(suffix or "").strip()
        if not clean_suffix.startswith("."):
            clean_suffix = "." + clean_suffix
        if clean_suffix.casefold() == ".py":
            raise ValueError("No se permite crear archivos .py temporales.")

        stamp = time.strftime("%Y%m%d-%H%M%S")
        unique = f"{os.getpid()}-{time.time_ns()}"
        return os.path.join(
            SysUtils.get_easydeploy_temp_scripts_dir(),
            f"{clean_prefix}_{stamp}_{unique}{clean_suffix}",
        )

    @staticmethod
    def cleanup_temp_file(path):
        """Elimina un temporal si existe, sin propagar errores de limpieza."""
        if not path:
            return False
        try:
            if os.path.isfile(path):
                os.remove(path)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def settings_path():
        return os.path.join(SysUtils.app_data_dir(), "settings.json")

    @staticmethod
    def read_configured_payload_root():
        try:
            with open(SysUtils.settings_path(), "r", encoding="utf-8") as handle:
                data = json.load(handle)
            value = data.get("payload_root")
            if value and os.path.isdir(value):
                return os.path.abspath(value)
        except Exception:
            pass
        return ""

    @staticmethod
    def save_configured_payload_root(path):
        try:
            settings_path = SysUtils.settings_path()
            data = {}
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r", encoding="utf-8") as handle:
                        data = json.load(handle)
                except Exception:
                    data = {}
            data["payload_root"] = os.path.abspath(path)
            with open(settings_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def resolve_payload_root(app_base_path=None):
        """Localiza la carpeta que contiene EXCHANGE, SHAPRE, SQL y JCHAT."""
        candidates = []

        configured_path = SysUtils.read_configured_payload_root()
        if configured_path:
            candidates.append(configured_path)

        env_path = os.environ.get("EASYDEPLOY_PAYLOAD_DIR")
        if env_path:
            candidates.append(env_path)

        if app_base_path:
            app_dir = os.path.abspath(app_base_path)
            search_roots = [app_dir]
            parent_dir = app_dir
            for _ in range(4):
                parent_dir = os.path.dirname(parent_dir)
                if parent_dir and parent_dir not in search_roots:
                    search_roots.append(parent_dir)

            for root in search_roots:
                for folder_name in PAYLOAD_DIR_NAMES:
                    candidates.append(os.path.join(root, folder_name))

        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        for folder_name in PAYLOAD_DIR_NAMES:
            candidates.append(os.path.join(exe_dir, folder_name))
            candidates.append(os.path.join(SysUtils.desktop_path(), folder_name))

        seen = set()
        unique_candidates = []
        for path in candidates:
            norm = os.path.normcase(os.path.abspath(path))
            if norm not in seen:
                seen.add(norm)
                unique_candidates.append(path)

        for path in unique_candidates:
            if SysUtils.has_payload_structure(path):
                return os.path.abspath(path)

        for path in unique_candidates:
            if os.path.isdir(path):
                return os.path.abspath(path)

        return os.path.abspath(unique_candidates[0]) if unique_candidates else SysUtils.desktop_path()

    @staticmethod
    def has_payload_structure(path):
        """Comprueba si la carpeta parece ser el paquete de recursos de Easy Deploy."""
        return bool(SysUtils.payload_resource_report(path)["looks_like_payload_root"])

    @staticmethod
    def normalize_payload_root(path):
        """Acepta la carpeta de recursos o su carpeta padre si contiene EASY DEPLOY/EASYDEPLOY."""
        if not path:
            return ""

        selected = os.path.abspath(path)
        if SysUtils._path_has_payload_markers(selected):
            return selected

        for folder_name in PAYLOAD_DIR_NAMES:
            candidate = os.path.join(selected, folder_name)
            if SysUtils._path_has_payload_markers(candidate):
                return os.path.abspath(candidate)

        return selected

    @staticmethod
    def _path_has_payload_markers(path):
        if not path or not os.path.isdir(path):
            return False
        expected_folders = [folder for folder, _items in SysUtils.PAYLOAD_RESOURCE_SPEC]
        return any(os.path.isdir(os.path.join(path, folder)) for folder in expected_folders)

    @staticmethod
    def _find_payload_item(folder_path, pattern):
        exact_path = os.path.join(folder_path, pattern)
        if os.path.isfile(exact_path) or os.path.isdir(exact_path):
            return exact_path

        if os.sep in pattern or "/" in pattern or "\\" in pattern:
            return ""

        try:
            names = os.listdir(folder_path)
        except Exception:
            return ""

        pattern_lower = pattern.casefold()
        for name in names:
            candidate = os.path.join(folder_path, name)
            if not os.path.isfile(candidate) and not os.path.isdir(candidate):
                continue
            if fnmatch.fnmatch(name.casefold(), pattern_lower):
                return candidate
        return ""

    @staticmethod
    def payload_resource_report(path):
        """Valida recursos esperados y devuelve un informe estructurado."""
        normalized = SysUtils.normalize_payload_root(path)
        report = {
            "root": normalized,
            "root_exists": bool(normalized and os.path.isdir(normalized)),
            "looks_like_payload_root": False,
            "complete": False,
            "total": 0,
            "present_count": 0,
            "missing_count": 0,
            "groups": [],
            "missing": [],
        }

        if not report["root_exists"]:
            return report

        report["looks_like_payload_root"] = SysUtils._path_has_payload_markers(normalized)

        for folder, items in SysUtils.PAYLOAD_RESOURCE_SPEC:
            folder_path = os.path.join(normalized, folder)
            folder_exists = os.path.isdir(folder_path)
            group = {
                "folder": folder,
                "folder_exists": folder_exists,
                "present": [],
                "missing": [],
            }
            for item in items:
                report["total"] += 1
                found_path = SysUtils._find_payload_item(folder_path, item) if folder_exists else ""
                if found_path:
                    report["present_count"] += 1
                    group["present"].append((item, found_path))
                else:
                    report["missing_count"] += 1
                    group["missing"].append(item)
                    report["missing"].append(f"{folder}\\{item}")
            report["groups"].append(group)

        report["complete"] = report["looks_like_payload_root"] and report["missing_count"] == 0
        return report

    @staticmethod
    def format_payload_report(report):
        root = report.get("root") or "Sin ruta"
        lines = [f"Carpeta de recursos:", root, ""]

        if not report.get("root_exists"):
            lines.append("ERROR: la ruta seleccionada no existe.")
            return "\n".join(lines)

        if not report.get("looks_like_payload_root"):
            lines.append("ERROR: la carpeta seleccionada no parece contener los recursos de Easy Deploy.")
            lines.append("Debe contener carpetas como EXCHANGE, SHAPRE, SQL, JCHAT, OTROS o GUIAS.")
            return "\n".join(lines)

        total = report.get("total", 0)
        present = report.get("present_count", 0)
        missing_count = report.get("missing_count", 0)
        lines.append(f"Resultado: {present}/{total} recursos encontrados.")
        lines.append("")

        if missing_count:
            lines.append("Recursos que faltan:")
            lines.append("")

        for group in report.get("groups", []):
            folder = group["folder"]
            if not group["folder_exists"]:
                lines.append(f"Carpeta: {os.path.join(root, folder)}")
                lines.append("Faltan:")
                lines.append(f"- Carpeta completa no encontrada: {folder}")
                lines.append("")
                continue
            if not group["missing"]:
                continue
            else:
                lines.append(f"Carpeta: {os.path.join(root, folder)}")
                lines.append("Faltan:")
                for item in group["missing"]:
                    lines.append(f"- {item}")
                lines.append("")

        if missing_count == 0:
            lines.append("Todos los recursos necesarios estan presentes.")
        return "\n".join(lines)

    @staticmethod
    def ps_quote(value):
        """Escapa un valor como literal seguro de PowerShell con comillas simples."""
        text = "" if value is None else str(value)
        return "'" + text.replace("'", "''") + "'"

    @staticmethod
    def is_plain_value(value, max_len=255):
        """Evita entradas vacías o multilinea en campos que acaban en comandos."""
        if value is None:
            return False
        text = str(value).strip()
        return bool(text) and len(text) <= max_len and "\n" not in text and "\r" not in text

    @staticmethod
    def is_valid_domain(value):
        return SysUtils.is_plain_value(value) and bool(DOMAIN_RE.match(str(value).strip()))

    @staticmethod
    def is_valid_netbios(value):
        return SysUtils.is_plain_value(value, max_len=15) and bool(NETBIOS_RE.match(str(value).strip()))

    @staticmethod
    def is_valid_host(value):
        if not SysUtils.is_plain_value(value):
            return False
        text = str(value).strip()
        return bool(IPV4_RE.match(text) or HOST_RE.match(text))

    @staticmethod
    def is_valid_product_key(value):
        return SysUtils.is_plain_value(value, max_len=29) and bool(PRODUCT_KEY_RE.match(str(value).strip()))

    @staticmethod
    def validar_licencia(code):
        """Valida la licencia sin guardar la clave en texto plano dentro del código."""
        if not code:
            return False
        env_hash = os.environ.get(LICENSE_HASH_ENV, "").strip().lower()
        if getattr(sys, "frozen", False):
            expected_hash = DEFAULT_LICENSE_SHA256.strip().lower()
        else:
            expected_hash = env_hash or DEFAULT_LICENSE_SHA256.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", expected_hash):
            expected_hash = DEFAULT_LICENSE_SHA256.strip().lower()
        given_hash = hashlib.sha256(str(code).strip().encode("utf-8")).hexdigest()
        return hmac.compare_digest(given_hash, expected_hash)

    @staticmethod
    def detectar_modo_windows():
        """Detecta el modo de color de Windows (Dark/Light)."""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                # 0 es Dark, 1 es Light
                return "Light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 1 else "Dark"
        except: return "Dark"

    @staticmethod
    def is_spanish_spain_keyboard():
        """Comprueba si el metodo de entrada predeterminado es Español/España."""
        quick_status = SysUtils.is_spanish_spain_keyboard_quick()
        if quick_status is not None:
            return quick_status

        return SysUtils._is_spanish_spain_primary_input()

    @staticmethod
    def is_spanish_spain_keyboard_quick():
        """Lectura rapida del layout activo para evitar dejar la UI en 'Comprobando'."""
        active_layout = SysUtils._active_keyboard_language_id()
        if active_layout is None:
            return None
        return active_layout in {0x040A, 0x0C0A}

    @staticmethod
    def _active_keyboard_language_id():
        try:
            layout_id = ctypes.windll.user32.GetKeyboardLayout(0) & 0xFFFF
            return layout_id
        except Exception:
            return None

    @staticmethod
    def _is_spanish_spain_primary_input():
        tips = "@(" + ",".join(SysUtils.ps_quote(tip) for tip in SysUtils.SPANISH_SPAIN_INPUT_TIPS) + ")"
        cmd = f"""
        $acceptedTips = {tips}
        $override = Get-WinDefaultInputMethodOverride -ErrorAction SilentlyContinue
        if ($override -and $override.InputTip) {{
            if ($acceptedTips -contains $override.InputTip.ToUpperInvariant()) {{ 'True' }} else {{ 'False' }}
            exit 0
        }}

        $langs = Get-WinUserLanguageList
        $first = $langs | Select-Object -First 1
        if ($first -and $first.LanguageTag -eq 'es-ES' -and $first.InputMethodTips.Count -gt 0 -and ($acceptedTips -contains $first.InputMethodTips[0].ToUpperInvariant())) {{
            'True'
            exit 0
        }}
        'False'
        """
        ok, output = SysUtils.run_powershell(cmd, capture=True, timeout=12)
        if not ok:
            return False
        result = output.strip().splitlines()
        return bool(result and result[-1].strip().lower() == "true")

    @staticmethod
    def _activate_spanish_spain_layout():
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.LoadKeyboardLayoutW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
            user32.LoadKeyboardLayoutW.restype = ctypes.c_void_p
            hkl = user32.LoadKeyboardLayoutW("0000040A", 0x00000001 | 0x00000008 | 0x00000100)
            if not hkl:
                return False

            user32.ActivateKeyboardLayout.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            user32.ActivateKeyboardLayout.restype = ctypes.c_void_p
            user32.ActivateKeyboardLayout(ctypes.c_void_p(hkl), 0x00000008 | 0x00000100)

            hkl_param = ctypes.c_void_p(hkl)
            user32.SystemParametersInfoW(0x005A, 0, ctypes.byref(hkl_param), 0x0002)

            user32.PostMessageW(ctypes.c_void_p(0xFFFF), 0x0050, ctypes.c_void_p(0), ctypes.c_void_p(hkl))
            foreground = user32.GetForegroundWindow()
            if foreground:
                user32.PostMessageW(ctypes.c_void_p(foreground), 0x0050, ctypes.c_void_p(0), ctypes.c_void_p(hkl))
            return True
        except Exception:
            return False

    @staticmethod
    def set_spanish_spain_keyboard():
        """Establece Español/España como metodo de entrada predeterminado."""
        input_tip = SysUtils.SPANISH_SPAIN_INPUT_TIPS[0]
        cmd = f"""
        $inputTip = {SysUtils.ps_quote(input_tip)}
        $langs = Get-WinUserLanguageList
        $ordered = New-WinUserLanguageList -Language 'es-ES'
        $ordered[0].InputMethodTips.Clear()
        $ordered[0].InputMethodTips.Add($inputTip) | Out-Null

        foreach ($lang in $langs) {{
            if ($lang.LanguageTag -ne 'es-ES' -and -not ($ordered.LanguageTag -contains $lang.LanguageTag)) {{
                try {{ $ordered.Add($lang.LanguageTag) | Out-Null }} catch {{ }}
            }}
        }}

        Set-WinUserLanguageList $ordered -Force
        Set-WinDefaultInputMethodOverride -InputTip $inputTip

        $preload = 'HKCU:\\Keyboard Layout\\Preload'
        if (-not (Test-Path $preload)) {{ New-Item -Path $preload -Force | Out-Null }}
        Set-ItemProperty -Path $preload -Name '1' -Value '0000040A'

        'OK primary es-ES'
        """
        ok, output = SysUtils.run_powershell(cmd, capture=True, timeout=25)
        if not ok:
            return False, output.strip()
        for _ in range(4):
            SysUtils._activate_spanish_spain_layout()
            time.sleep(0.15)
            active_layout = SysUtils._active_keyboard_language_id()
            if active_layout in {0x040A, 0x0C0A}:
                break
        return True, output.strip()

    @staticmethod
    def run_powershell(cmd, capture=False, timeout=None):
        """Ejecuta comando PS. Si capture=True retorna (exito, salida). Si False retorna exito boolean."""
        try:
            # Se usa -NoProfile y -ExecutionPolicy Bypass para un entorno más predecible
            # El script se entrega por stdin para no dejar comandos completos en la línea de proceso.
            full_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "-"]
            script = (
                "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
                "$OutputEncoding = [Console]::OutputEncoding\n"
                "$ErrorActionPreference = 'Stop'\n"
                + str(cmd)
            )
            
            if capture:
                res = subprocess.run(
                    full_cmd, 
                    input=script.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True, 
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=timeout,
                )
                # stdout y stderr son separados por PowerShell, los unimos
                output = (
                    SysUtils.decode_process_bytes(res.stdout, prefer_utf8=True)
                    + "\n"
                    + SysUtils.decode_process_bytes(res.stderr, prefer_utf8=True)
                )
                return (True, output)
            else:
                # Si no captura, solo comprueba si la ejecución fue exitosa
                subprocess.run(
                    full_cmd,
                    input=script.encode("utf-8"),
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=timeout,
                )
                return True
        except subprocess.TimeoutExpired as e:
            err_text = f"Timeout ejecutando PowerShell tras {timeout} segundos."
            if capture:
                output = ""
                if e.stdout:
                    output += SysUtils.decode_process_bytes(e.stdout, prefer_utf8=True)
                if e.stderr:
                    output += "\n" + SysUtils.decode_process_bytes(e.stderr, prefer_utf8=True)
                return (False, (output + "\n" + err_text).strip())
            return False
        except subprocess.CalledProcessError as e:
            # Esto captura errores dentro del script PS o si Check=True falla.
            # Se conserva stdout + stderr porque algunos errores de PowerShell aparecen en stdout.
            stdout_text = SysUtils.decode_process_bytes(e.stdout, prefer_utf8=True) if e.stdout else ""
            stderr_text = SysUtils.decode_process_bytes(e.stderr, prefer_utf8=True) if e.stderr else ""
            err_text = "\n".join(part.strip() for part in (stdout_text, stderr_text) if part and part.strip())
            if not err_text:
                err_text = str(e)
            if capture: return (False, f"Error (Code {e.returncode}): {err_text}")
            else: return False
        except Exception as e:
            if capture: return (False, f"Excepción desconocida en run_powershell: {e}")
            else: return False

    @staticmethod
    def ping_host(host, count=1, timeout_ms=2000):
        """Comprueba conectividad ICMP y devuelve (ok, salida)."""
        return_code, output = SysUtils.run_native_command(
            ["ping", "-n", str(count), "-w", str(timeout_ms), str(host)]
        )
        return return_code == 0, output

    @staticmethod
    def netfx35_iso_candidates(payload_root=None, app_base_path=None):
        """Devuelve rutas esperadas para la ISO local de .NET Framework 3.5."""
        candidates = []

        def add_payload_root(root):
            if not root:
                return
            normalized = SysUtils.normalize_payload_root(root)
            if normalized:
                candidates.append(os.path.join(normalized, SysUtils.NETFX35_ISO_RELATIVE_PATH))

        add_payload_root(payload_root)
        add_payload_root(SysUtils.read_configured_payload_root())
        add_payload_root(os.environ.get("EASYDEPLOY_PAYLOAD_DIR"))

        if app_base_path:
            add_payload_root(SysUtils.resolve_payload_root(app_base_path))

        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        for folder_name in PAYLOAD_DIR_NAMES:
            candidates.append(os.path.join(exe_dir, folder_name, SysUtils.NETFX35_ISO_RELATIVE_PATH))
            candidates.append(os.path.join(SysUtils.desktop_path(), folder_name, SysUtils.NETFX35_ISO_RELATIVE_PATH))

        candidates.append(os.path.join(r"C:\EASY DEPLOY", SysUtils.NETFX35_ISO_RELATIVE_PATH))
        candidates.append(os.path.join(r"C:\EASYDEPLOY", SysUtils.NETFX35_ISO_RELATIVE_PATH))

        seen = set()
        unique_candidates = []
        for path in candidates:
            if not path:
                continue
            norm = os.path.normcase(os.path.abspath(path))
            if norm in seen:
                continue
            seen.add(norm)
            unique_candidates.append(os.path.abspath(path))
        return unique_candidates

    @staticmethod
    def expected_netfx35_iso_path(payload_root=None, app_base_path=None):
        candidates = SysUtils.netfx35_iso_candidates(payload_root, app_base_path)
        return candidates[0] if candidates else os.path.join("EASY DEPLOY", SysUtils.NETFX35_ISO_RELATIVE_PATH)

    @staticmethod
    def find_netfx35_iso(payload_root=None, app_base_path=None):
        for candidate in SysUtils.netfx35_iso_candidates(payload_root, app_base_path):
            if os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def find_sxs_source(payload_root=None, app_base_path=None, auto_mount_netfx_iso=False, return_detail=False):
        """Localiza una carpeta Sources\\SxS para roles que necesitan origen."""
        detail = {
            "expected_iso_path": SysUtils.expected_netfx35_iso_path(payload_root, app_base_path),
            "iso_path": "",
            "mount_drive": "",
            "mount_error": "",
            "image_was_attached": None,
            "mounted_by_easydeploy": False,
        }

        def done(source):
            return (source, detail) if return_detail else source

        env_path = os.environ.get("EASYDEPLOY_SXS_SOURCE")
        if env_path and os.path.isdir(env_path):
            return done(os.path.abspath(env_path))

        if auto_mount_netfx_iso:
            iso_path = SysUtils.find_netfx35_iso(payload_root, app_base_path)
            detail["iso_path"] = iso_path
            if not iso_path:
                return done("")

            image_was_attached = SysUtils.is_disk_image_attached(iso_path)
            detail["image_was_attached"] = image_was_attached

            ok, drive_or_error = SysUtils.mount_disk_image(iso_path)
            if not ok:
                detail["mount_error"] = drive_or_error
                return done("")

            detail["mount_drive"] = drive_or_error
            detail["mounted_by_easydeploy"] = image_was_attached is False
            drive = f"{drive_or_error}:\\"
            for relative in (r"Sources\SxS", r"sources\sxs"):
                candidate = os.path.join(drive, relative)
                if os.path.isdir(candidate):
                    return done(candidate)
            return done("")

        for letter in "DEFGHIJKLMNOPQRSTUVWXYZC":
            drive = f"{letter}:\\"
            for relative in (r"Sources\SxS", r"sources\sxs"):
                candidate = os.path.join(drive, relative)
                if os.path.isdir(candidate):
                    return done(candidate)

        return done("")

    @staticmethod
    def is_disk_image_attached(image_path):
        """Devuelve si una ISO/IMG ya estaba montada antes de tocarla.

        Si no se puede determinar con seguridad, devuelve None para evitar
        desmontar después una imagen que pudiera haber montado el usuario.
        """
        if not image_path or not os.path.exists(image_path):
            return None

        script = f"""
        $imagePath = {SysUtils.ps_quote(image_path)}
        $image = Get-DiskImage -ImagePath $imagePath -ErrorAction SilentlyContinue
        if ($null -ne $image -and $image.Attached) {{
            'True'
        }} else {{
            'False'
        }}
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=30)
        if not ok:
            return None
        lines = [line.strip().casefold() for line in output.splitlines() if line.strip()]
        if not lines:
            return None
        if lines[-1] == "true":
            return True
        if lines[-1] == "false":
            return False
        return None


    @staticmethod
    def mount_disk_image(image_path):
        """Monta una ISO/IMG y devuelve (ok, letra_o_error)."""
        if not image_path or not os.path.exists(image_path):
            return False, f"No existe la imagen: {image_path}"

        script = f"""
        $imagePath = {SysUtils.ps_quote(image_path)}
        $image = Get-DiskImage -ImagePath $imagePath -ErrorAction SilentlyContinue
        if ($null -eq $image -or -not $image.Attached) {{
            $image = Mount-DiskImage -ImagePath $imagePath -PassThru
        }} else {{
            $image = Get-DiskImage -ImagePath $imagePath
        }}
        Start-Sleep -Seconds 1
        $volume = $image | Get-Volume | Where-Object DriveLetter | Select-Object -First 1
        if ($null -eq $volume -or -not $volume.DriveLetter) {{
            throw "La imagen se monto, pero no tiene letra de unidad."
        }}
        $volume.DriveLetter
        """
        ok, output = SysUtils.run_powershell(script, capture=True)
        if not ok:
            return False, output.strip()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return (True, lines[-1]) if lines else (False, "No se obtuvo letra de unidad.")

    @staticmethod
    def dismount_disk_image(image_path):
        """Desmonta una ISO/IMG si esta adjunta."""
        if not image_path or not os.path.exists(image_path):
            return False, f"No existe la imagen: {image_path}"

        script = f"""
        $imagePath = {SysUtils.ps_quote(image_path)}
        $image = Get-DiskImage -ImagePath $imagePath -ErrorAction SilentlyContinue
        if ($null -eq $image -or -not $image.Attached) {{
            'NO_ATTACHED'
            exit 0
        }}
        Dismount-DiskImage -ImagePath $imagePath -ErrorAction Stop | Out-Null
        'DISMOUNTED'
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=30)
        if not ok:
            return False, output.strip()
        return True, output.strip()

    @staticmethod
    def is_program_installed(patterns):
        """Busca DisplayName en uninstall registry de 32/64 bits y HKCU."""
        if isinstance(patterns, str):
            patterns = [patterns]
        normalized = []
        for pattern in patterns or []:
            text = str(pattern or "").strip()
            if not text:
                continue
            if "*" not in text:
                text = f"*{text}*"
            normalized.append(text)
        if not normalized:
            return False

        ps_patterns = "@(" + ",".join(SysUtils.ps_quote(pattern) for pattern in normalized) + ")"
        script = f"""
        $patterns = {ps_patterns}
        $paths = @(
            'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
            'HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
            'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'
        )
        foreach ($path in $paths) {{
            Get-ItemProperty $path -ErrorAction SilentlyContinue | ForEach-Object {{
                $display = [string]$_.DisplayName
                if ([string]::IsNullOrWhiteSpace($display)) {{ return }}
                foreach ($pattern in $patterns) {{
                    if ($display -like $pattern) {{
                        'True'
                        exit 0
                    }}
                }}
            }}
        }}
        'False'
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=20)
        if not ok:
            return False
        return output.strip().splitlines()[-1:] == ["True"]

    @staticmethod
    def is_service_installed(service_name):
        if not service_name:
            return False
        script = f"if (Get-Service -Name {SysUtils.ps_quote(service_name)} -ErrorAction SilentlyContinue) {{ 'True' }} else {{ 'False' }}"
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=10)
        return ok and output.strip().splitlines()[-1:] == ["True"]

    @staticmethod
    def is_hotfix_installed(hotfix_id):
        if not hotfix_id:
            return False
        script = f"if (Get-HotFix -Id {SysUtils.ps_quote(hotfix_id)} -ErrorAction SilentlyContinue) {{ 'True' }} else {{ 'False' }}"
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=15)
        return ok and output.strip().splitlines()[-1:] == ["True"]

    @staticmethod
    def is_reboot_pending():
        script = r"""
        $paths = @(
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending',
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired',
            'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager'
        )
        $pending = $false
        foreach ($path in $paths) {
            if (Test-Path $path) {
                if ($path -like '*Session Manager') {
                    $value = (Get-ItemProperty -Path $path -Name PendingFileRenameOperations -ErrorAction SilentlyContinue).PendingFileRenameOperations
                    if ($null -ne $value) { $pending = $true }
                } else {
                    $pending = $true
                }
            }
        }
        $pending
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=10)
        return ok and output.strip().splitlines()[-1:] == ["True"]

    @staticmethod
    def is_dotnet_release_at_least(min_release):
        script = r"""
        $release = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -Name Release -ErrorAction SilentlyContinue).Release
        if ($null -eq $release) { '0' } else { [string]$release }
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=10)
        if not ok:
            return False
        try:
            release = int(output.strip().splitlines()[-1])
        except Exception:
            return False
        return release >= int(min_release)

    @staticmethod
    def missing_windows_features(feature_names):
        features = [str(name).strip() for name in feature_names or [] if str(name).strip()]
        if not features:
            return []
        feature_list = "@(" + ",".join(SysUtils.ps_quote(name) for name in features) + ")"
        script = f"""
        $features = {feature_list}
        Get-WindowsFeature -Name $features -ErrorAction SilentlyContinue |
            Where-Object {{ -not $_.Installed }} |
            Select-Object -ExpandProperty Name
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=30)
        if not ok:
            return features
        found_missing = {line.strip().casefold() for line in output.splitlines() if line.strip()}
        return [name for name in features if name.casefold() in found_missing]

    @staticmethod
    def ensure_dirs(*paths):
        """Crea carpetas necesarias y devuelve False si alguna unidad no existe."""
        for path in paths:
            drive = os.path.splitdrive(path)[0] + "\\"
            if drive and not os.path.exists(drive):
                print(f"[ERROR] No existe la unidad requerida: {drive}")
                return False
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as exc:
                print(f"[ERROR] No se pudo preparar la carpeta {path}: {exc}")
                return False
        return True


    @staticmethod
    def is_feature_installed(feature):
        """Comprueba si una característica de Windows está instalada."""
        feature_name = str(feature or "").strip()
        if not feature_name:
            return False

        script = f"""
        $feature = Get-WindowsFeature -Name {SysUtils.ps_quote(feature_name)} -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -ne $feature -and $feature.Installed) {{
            'True'
        }} else {{
            'False'
        }}
        """
        res, output = SysUtils.run_powershell(script, capture=True, timeout=30)
        if res:
            lines = [line.strip().casefold() for line in output.splitlines() if line.strip()]
            if lines and lines[-1] == "true":
                return True

        if feature_name.casefold() in {"net-framework-core", "netfx3"}:
            code, dism_output = SysUtils.run_native_command(
                [
                    "dism.exe",
                    "/online",
                    "/Get-FeatureInfo",
                    "/FeatureName:NetFx3",
                ],
                timeout=60,
            )
            if code == 0:
                normalized = SysUtils._repair_mojibake(dism_output).casefold()
                enabled_markers = (
                    "state : enabled",
                    "state: enabled",
                    "estado : habilitado",
                    "estado: habilitado",
                )
                if any(marker in normalized for marker in enabled_markers):
                    return True

        return False

    @staticmethod
    def cargar_icono(path):
        """Carga y redimensiona un icono para CustomTkinter."""
        try:
            if os.path.exists(path):
                import customtkinter as ctk
                from PIL import Image

                img = Image.open(path)
                img = img.resize((24, 24), Image.LANCZOS)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
        except: pass
        return None
    
    @staticmethod
    def ensure_windows_update_running():
        """Asegura que el servicio wuauserv esté en Automatic/Running."""
        service_name = "wuauserv"
        print(f"\n[PRE-CHECK] Asegurando que el servicio '{service_name}' esté activo para los prerrequisitos...")

        # 1. Comprobar estado actual
        cmd_check = f'(Get-Service -Name {service_name}).Status'
        success, status = SysUtils.run_powershell(cmd_check, capture=True)
        status = status.strip().lower() if success else "error"

        if status == "running":
            print(f"   [OK] El servicio '{service_name}' ya está 'Running'.")
            return

        # 2. Establecer tipo de inicio a Automático
        print("   [SETUP] Configurando tipo de inicio a 'Automatic'...")
        cmd_set_auto = f'Set-Service -Name {service_name} -StartupType Automatic'
        SysUtils.run_powershell(cmd_set_auto)

        # 3. Iniciar el servicio
        print("   [ACCIÓN] Iniciando servicio...")
        cmd_start = f'Start-Service -Name {service_name}'
        success_start = SysUtils.run_powershell(cmd_start)
        
        if success_start:
            time.sleep(2) # Esperar un momento para que el servicio inicie
            success_confirm, new_status = SysUtils.run_powershell(cmd_check, capture=True)
            new_status = new_status.strip().lower() if success_confirm else "unknown"
            
            if new_status == "running":
                print(f"   [OK] Servicio '{service_name}' activado y ahora está 'Running'.")
            else:
                print(f"   [WARNING] Servicio inició pero su estado actual es: {new_status}")
        else:
            print(f"   [ERROR] No se pudo iniciar el servicio '{service_name}'.")
