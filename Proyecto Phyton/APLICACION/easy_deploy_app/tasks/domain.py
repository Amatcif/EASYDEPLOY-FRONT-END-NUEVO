import os
import re
import subprocess
import time

from ..core.sysutils import SysUtils


class DomainTasksMixin:
    _DC_STORAGE_DRIVE_SCAN_ORDER = "DEFGHIJKLMNOPQRSTUVWXYZC"

    def _normalize_dc_storage_path(self, path):
        if not isinstance(path, str):
            return ""
        path = path.strip().strip('"').strip("'").replace("/", "\\")
        while len(path) > 3 and path.endswith("\\"):
            path = path[:-1]
        return path

    def _is_valid_local_dc_path(self, path):
        path = self._normalize_dc_storage_path(path)
        if not path or "\n" in path or "\r" in path:
            return False
        if not re.match(r"^[A-Za-z]:\\.+", path):
            return False
        # Caracteres no validos en la parte de carpeta. El ':' de la unidad ya esta validado.
        return not any(ch in path[3:] for ch in '<>"|?*')

    def _dc_storage_drive(self, path):
        path = self._normalize_dc_storage_path(path)
        if re.match(r"^[A-Za-z]:\\", path):
            return path[:2].upper()
        return ""

    def _get_existing_drive_letters(self):
        letters = []
        for letter in self._DC_STORAGE_DRIVE_SCAN_ORDER:
            if os.path.isdir(f"{letter}:\\"):
                letters.append(letter)
        return letters

    def _folder_key(self, value):
        return re.sub(r"[^a-z0-9]", "", str(value).casefold())

    def _find_dc_storage_folder(self, folder_name):
        """Busca NTDS/SYSVOL en cualquier unidad fija disponible, sin depender de D:/E: ni de mayusculas."""
        wanted = self._folder_key(folder_name)
        aliases = {
            "ntds": ("ntds", "addsntds", "adntds", "addatabase", "basedatosad"),
            "sysvol": ("sysvol", "sysvolume", "sysvolumen", "adsysvol"),
        }.get(wanted, (wanted,))

        exact_matches = []
        fuzzy_matches = []
        for letter in self._get_existing_drive_letters():
            root = f"{letter}:\\"
            try:
                for entry in os.scandir(root):
                    try:
                        if not entry.is_dir():
                            continue
                    except OSError:
                        continue
                    key = self._folder_key(entry.name)
                    if key in aliases:
                        exact_matches.append(entry.path)
                    elif any(alias in key for alias in aliases):
                        fuzzy_matches.append(entry.path)
            except OSError:
                continue

        if exact_matches:
            return exact_matches[0]
        if fuzzy_matches:
            return fuzzy_matches[0]
        return ""

    def _suggest_dc_storage_path(self, folder_name, preferred_index=0):
        found = self._find_dc_storage_folder(folder_name)
        if found:
            return found
        drives = [letter for letter in self._get_existing_drive_letters() if letter.upper() != "C"]
        if not drives:
            drives = self._get_existing_drive_letters()
        if drives:
            letter = drives[min(preferred_index, len(drives) - 1)]
        else:
            letter = "D" if preferred_index == 0 else "E"
        folder = "NTDS" if self._folder_key(folder_name) == "ntds" else "SYSVOL"
        return f"{letter}:\\{folder}"

    def _expand_dc_storage_input(self, value, folder_name, suggested_path):
        value = self._normalize_dc_storage_path(value)
        if not value:
            return ""
        if value.upper() in ("AUTO", "AUTOMATICO", "AUTOMÁTICO"):
            return suggested_path
        # Permite escribir solo la letra de unidad: F, F: o F:\ .
        if re.match(r"^[A-Za-z]:?\\?$", value):
            folder = "NTDS" if self._folder_key(folder_name) == "ntds" else "SYSVOL"
            return f"{value[0].upper()}:\\{folder}"
        return value

    def _prompt_dc_storage_paths(self, role_name):
        """Obtiene rutas NTDS/SYSVOL antes de lanzar el hilo de trabajo.

        Si ya existen carpetas reconocibles, se usan automaticamente. Si no, se piden al usuario.
        El usuario puede escribir solo la letra de unidad o una ruta completa.
        """
        detected_ntds = self._find_dc_storage_folder("NTDS")
        detected_sysvol = self._find_dc_storage_folder("SYSVOL")
        if detected_ntds and detected_sysvol:
            return detected_ntds, detected_sysvol

        ntds_suggestion = detected_ntds or self._suggest_dc_storage_path("NTDS", 0)
        sysvol_suggestion = detected_sysvol or self._suggest_dc_storage_path("SYSVOL", 1)

        ntds_value = self.input_dialog(
            f"{role_name} - Ruta NTDS",
            "Introduce la ruta local para NTDS.\n"
            "Puedes escribir solo la letra de unidad, por ejemplo F, o una ruta completa.\n\n"
            f"Sugerencia: {ntds_suggestion}\n"
            "Escribe AUTO para usar la sugerencia.",
        )
        if not ntds_value:
            return None
        ntds_path = self._expand_dc_storage_input(ntds_value, "NTDS", ntds_suggestion)

        sysvol_value = self.input_dialog(
            f"{role_name} - Ruta SYSVOL",
            "Introduce la ruta local para SYSVOL.\n"
            "Puedes escribir solo la letra de unidad, por ejemplo G, o una ruta completa.\n\n"
            f"Sugerencia: {sysvol_suggestion}\n"
            "Escribe AUTO para usar la sugerencia.",
        )
        if not sysvol_value:
            return None
        sysvol_path = self._expand_dc_storage_input(sysvol_value, "SYSVOL", sysvol_suggestion)

        if not self._is_valid_local_dc_path(ntds_path):
            self.ui_showerror(
                f"{role_name} - NTDS",
                "La ruta NTDS no es valida. Usa una ruta local absoluta, por ejemplo F:\\NTDS.",
            )
            return None
        if not self._is_valid_local_dc_path(sysvol_path):
            self.ui_showerror(
                f"{role_name} - SYSVOL",
                "La ruta SYSVOL no es valida. Usa una ruta local absoluta, por ejemplo G:\\SYSVOL.",
            )
            return None
        if ntds_path.casefold() == sysvol_path.casefold():
            self.ui_showerror(
                f"{role_name} - Almacenamiento",
                "NTDS y SYSVOL no pueden apuntar exactamente a la misma carpeta.",
            )
            return None

        return ntds_path, sysvol_path

    def _prepare_dc_storage_paths(self, ntds_path=None, sysvol_path=None):
        print("Comprobando carpetas NTDS y SYSVOL en particiones disponibles...")
        ntds_path = self._normalize_dc_storage_path(
            ntds_path or getattr(self, "_dc_ntds_path", "") or self._find_dc_storage_folder("NTDS") or self._suggest_dc_storage_path("NTDS", 0)
        )
        sysvol_path = self._normalize_dc_storage_path(
            sysvol_path or getattr(self, "_dc_sysvol_path", "") or self._find_dc_storage_folder("SYSVOL") or self._suggest_dc_storage_path("SYSVOL", 1)
        )

        if not self._is_valid_local_dc_path(ntds_path):
            print(f"[ERROR] Ruta NTDS no valida: {ntds_path}")
            return False
        if not self._is_valid_local_dc_path(sysvol_path):
            print(f"[ERROR] Ruta SYSVOL no valida: {sysvol_path}")
            return False
        if ntds_path.casefold() == sysvol_path.casefold():
            print("[ERROR] NTDS y SYSVOL no pueden usar exactamente la misma carpeta.")
            return False

        for path in (ntds_path, sysvol_path):
            drive_root = path[:3]
            if not os.path.isdir(drive_root):
                print(f"[ERROR] La unidad {drive_root} no existe o no esta accesible.")
                return False

        if not SysUtils.ensure_dirs(ntds_path, sysvol_path):
            return False

        self._dc_ntds_path = ntds_path
        self._dc_sysvol_path = sysvol_path
        print(f"[OK] NTDS preparado en: {ntds_path}")
        print(f"[OK] SYSVOL preparado en: {sysvol_path}")
        if self._dc_storage_drive(ntds_path) == self._dc_storage_drive(sysvol_path):
            print("[AVISO] NTDS y SYSVOL estan en la misma unidad. Se permite, pero lo recomendado es usar particiones dedicadas.")
        return True

    def _get_current_domain_membership(self):
        cmd = (
            "$cs = Get-CimInstance -ClassName Win32_ComputerSystem; "
            "if ($cs.PartOfDomain) { 'DOMAIN=' + $cs.Domain } else { 'WORKGROUP=' + $cs.Workgroup }"
        )
        try:
            ok, output = SysUtils.run_powershell(cmd, capture=True, timeout=60)
        except TypeError:
            ok, output = SysUtils.run_powershell(cmd, capture=True)
        except Exception as exc:
            print(f"[AVISO] No se pudo comprobar si el servidor esta unido a dominio: {exc}")
            return None, ""

        if not ok:
            print("[AVISO] No se pudo comprobar si el servidor esta unido a dominio.")
            if output and output.strip():
                print(output.strip())
            return None, ""

        for line in output.splitlines():
            line = line.strip()
            if line.upper().startswith("DOMAIN="):
                return True, line.split("=", 1)[1].strip()
            if line.upper().startswith("WORKGROUP="):
                return False, line.split("=", 1)[1].strip()
        return None, ""

    def _domain_names_match(self, current_domain, expected_domain):
        current = str(current_domain or "").strip().casefold().rstrip(".")
        expected = str(expected_domain or "").strip().casefold().rstrip(".")
        if not current or not expected:
            return False
        return current == expected or current.endswith("." + expected) or expected.endswith("." + current)

    def _prevalidate_dc2_domain_membership(self, dom):
        joined, current_domain = self._get_current_domain_membership()
        if joined is None:
            # No bloqueamos si no se ha podido consultar; la tarea lo volvera a validar y mostrara log.
            return True
        if not joined:
            self.ui_showwarning(
                "DC2 - Prerrequisito",
                "Antes de promocionar este servidor como DC2 debe estar unido al dominio existente y reiniciado tras la union.\n\n"
                f"Estado actual detectado: grupo de trabajo {current_domain or '(desconocido)'}\n\n"
                "Usa primero la funcion Unir a dominio, reinicia, inicia sesion con una cuenta de dominio y vuelve a ejecutar DC2.",
            )
            return False
        if current_domain and "." in current_domain and not self._domain_names_match(current_domain, dom):
            self.ui_showwarning(
                "DC2 - Dominio incorrecto",
                f"Este servidor esta unido a {current_domain}, pero has indicado {dom}.\n\n"
                "Corrige el dominio indicado o une el servidor al dominio correcto antes de promocionarlo como DC2.",
            )
            return False
        return True

    def _ensure_dc2_domain_membership(self, dom):
        joined, current_domain = self._get_current_domain_membership()
        if joined is None:
            print("[AVISO] No se pudo validar la pertenencia a dominio. Se continua con la promocion.")
            return True
        if not joined:
            print("[ERROR] El servidor no esta unido al dominio. Cancelo la promocion de DC2.")
            self._notify_task_error(
                "DC2 - Prerrequisito",
                "Este servidor aun no esta unido al dominio existente.\n\n"
                "Une el servidor al dominio, reinicia, inicia sesion con una cuenta de dominio y vuelve a ejecutar DC2.",
            )
            return False
        if current_domain and "." in current_domain and not self._domain_names_match(current_domain, dom):
            print(f"[ERROR] Dominio unido actual: {current_domain}. Dominio indicado: {dom}.")
            self._notify_task_error(
                "DC2 - Dominio incorrecto",
                f"Este servidor esta unido a {current_domain}, pero has indicado {dom}.\n\n"
                "No se continua para evitar promocionar contra el dominio equivocado.",
            )
            return False
        print(f"[OK] Servidor unido a dominio: {current_domain or dom}")
        return True

    def _check_domain_ping(self, dom, notify=True):
        print(f"Comprobando conectividad DNS/ICMP con el dominio: {dom}")
        ok, output = SysUtils.ping_host(dom, count=1, timeout_ms=2500)
        if output.strip():
            print(output.strip())
        if not ok:
            print("[ERROR] No se pudo resolver o alcanzar el dominio. Revisa DNS/red antes de continuar.")
            if notify:
                self._notify_task_error(
                    "Dominio no accesible",
                    f"No se pudo resolver o alcanzar el dominio:\n\n{dom}\n\n"
                    "Revisa DNS, IP, puerta de enlace y conectividad con el controlador de dominio antes de continuar.",
                )
        return ok

    def _ensure_ad_dns_roles(self):
        features = ["AD-Domain-Services", "DNS"]
        print("Comprobando roles AD DS y DNS...")
        missing = SysUtils.missing_windows_features(features)
        missing_lookup = {feature.casefold() for feature in missing}

        for feature in features:
            if feature.casefold() in missing_lookup:
                print(f"[FALTA] {feature}")
            else:
                print(f"[OMITIDO] Ya instalado: {feature}")

        if not missing:
            print("[OMITIDO] AD-Domain-Services y DNS ya estan instalados.")
            return True

        print(f"Instalando roles pendientes: {', '.join(missing)}")
        res = SysUtils.run_powershell(
            "Install-WindowsFeature -Name "
            + ",".join(missing)
            + " -IncludeManagementTools -Restart:$false"
        )
        if not res:
            print("ERROR al instalar los roles ADDS/DNS.")
            self._notify_task_error(
                "Dominio y Active Directory",
                "No se han podido instalar los roles AD DS/DNS.\n\n"
                "Revisa permisos de administrador, origen de Windows Features y si hay un reinicio pendiente.",
            )
            return False

        print("[OK] Roles ADDS/DNS instalados correctamente.")
        return True

    def _notify_netfx35_success_and_dismount(self, sxs_detail):
        """Avisa del éxito y desmonta solo la ISO de NetFX montada por Easy Deploy."""
        iso_path = ""
        mounted_by_easydeploy = False
        if isinstance(sxs_detail, dict):
            iso_path = sxs_detail.get("iso_path", "")
            mounted_by_easydeploy = bool(sxs_detail.get("mounted_by_easydeploy"))

        if not iso_path or not mounted_by_easydeploy:
            self._notify_task_info(
                "Net Framework 3.5",
                ".NET Framework 3.5 se ha instalado correctamente desde el medio local.",
            )
            return

        self._notify_task_info(
            "Net Framework 3.5",
            ".NET Framework 3.5 se ha instalado correctamente desde el medio local.\n\n"
            "Al pulsar Aceptar, Easy Deploy desmontara la ISO de recursos usada para la instalacion.",
        )
        print("[INFO] Desmontando ISO de recursos de .NET Framework 3.5...")
        ok, output = SysUtils.dismount_disk_image(iso_path)
        if ok:
            print("[OK] ISO de .NET Framework 3.5 desmontada.")
            detail = str(output or "").strip()
            if detail:
                print(f"[INFO] Resultado desmontaje: {detail}")
        else:
            print("[AVISO] No se pudo desmontar automaticamente la ISO de .NET Framework 3.5.")
            detail = str(output or "").strip()
            if detail:
                print(f"[INFO] Detalle desmontaje: {detail}")


    def task_netfx35(self):
        print("=== .NET FRAMEWORK 3.5 ===")
        if not self._require_windows_server("Net Framework 3.5"):
            return

        self.update_progress(0.1)
        print("Comprobando si Net-Framework-Core ya esta instalado...")
        if SysUtils.is_feature_installed("Net-Framework-Core"):
            self.update_progress(1.0)
            print("[OK] Net-Framework-Core ya instalado.")
            print("[OK] .NET Framework 3.5 ya estaba instalado.")
            self._notify_task_info(
                "Net Framework 3.5",
                ".NET Framework 3.5 ya esta instalado en este servidor.",
            )
            return
        print("[INFO] Net-Framework-Core no instalado; se instalara desde el medio local.")

        source_path, sxs_detail = SysUtils.find_sxs_source(
            getattr(self, "payload_root", ""),
            getattr(self, "base_path", ""),
            auto_mount_netfx_iso=True,
            return_detail=True,
        )
        if not source_path:
            self.update_progress(1.0)
            expected_iso = sxs_detail.get("expected_iso_path", "")
            iso_path = sxs_detail.get("iso_path", "")
            mount_error = sxs_detail.get("mount_error", "")
            if not iso_path:
                message = (
                    "No se encuentra la ISO de recursos para .NET Framework 3.5.\n\n"
                    f"Ruta esperada:\n{expected_iso}\n\n"
                    "Comprueba que exista OTROS\\NetFramework3.5.iso dentro de la carpeta de recursos de Easy Deploy."
                )
            elif mount_error:
                message = (
                    "No se pudo montar automaticamente la ISO de .NET Framework 3.5.\n\n"
                    f"ISO:\n{iso_path}\n\n"
                    f"Detalle: {mount_error}"
                )
            else:
                message = (
                    "La ISO de .NET Framework 3.5 se ha montado, pero no se ha encontrado Sources\\SxS.\n\n"
                    f"ISO:\n{iso_path}\n\n"
                    "Comprueba que la imagen corresponde a un medio de Windows Server."
                )
            self._notify_task_error(
                "Net Framework 3.5",
                message,
            )
            return

        self.update_progress(0.35)
        print(f"Origen SxS detectado: {source_path}")
        print("[INFO] .NET Framework 3.5 puede tardar varios minutos en instalarse. No cierres Easy Deploy.")
        print("Instalando Net-Framework-Core desde el medio local...")

        cmd = (
            "Install-WindowsFeature -Name Net-Framework-Core "
            f"-Source {SysUtils.ps_quote(source_path)} "
            "-Restart:$false"
        )
        ok, output = SysUtils.run_powershell(cmd, capture=True, timeout=1800)
        if output.strip():
            print(output.strip())

        self.update_progress(0.85)
        installed = SysUtils.is_feature_installed("Net-Framework-Core")
        if not installed:
            print("Install-WindowsFeature no confirmo la instalacion. Reintentando con DISM...")
            dism_code, dism_output = SysUtils.run_native_command(
                [
                    "dism.exe",
                    "/online",
                    "/enable-feature",
                    "/featurename:NetFX3",
                    "/All",
                    f"/Source:{source_path}",
                    "/LimitAccess",
                ],
                timeout=1800,
            )
            if dism_output.strip():
                print(dism_output.strip())
            if dism_code == 3010:
                self.console_finish_state = "restart"
            ok = ok or dism_code in (0, 3010)
            installed = SysUtils.is_feature_installed("Net-Framework-Core")
        self.update_progress(1.0)

        if ok and installed:
            print("[OK] Net-Framework-Core instalado.")
            print("[OK] .NET Framework 3.5 instalado correctamente.")
            self._notify_netfx35_success_and_dismount(sxs_detail)
            return

        self._notify_task_error(
            "Net Framework 3.5",
            ".NET Framework 3.5 no se ha podido instalar.\n\n"
            "Revisa que el ISO/CD corresponda a Windows Server y que la carpeta Sources\\SxS sea accesible. "
            "El detalle queda en el log.",
        )

    def pre_task_dc1(self):
        # 1. Comprobación unificada de requisitos previos
        mensaje_aviso = (
            "Antes de continuar, confirma que se cumplen TODOS estos requisitos:\n\n"
            "1. DISCOS: ¿Existen las carpetas NTDS y SYSVOL en particiones dedicadas?\n"
            "   (Se aceptan letras distintas, por ejemplo D/E o E/F)\n\n"
            "2. RED: ¿Está configurada la IP estática y DNS correctamente?\n\n"
            "3. FIREWALL: ¿Está deshabilitado o configurado?\n\n"
            "4. SOFTWARE: ¿Está instalado .NET Framework 3.5?\n\n"
            "¿Se cumplen TODOS los requisitos?"
        )

        confirmacion = self.ui_askyesno("Confirmar Requisitos Previos", mensaje_aviso)

        if not confirmacion:
            print("Operación cancelada por el usuario.")
            return  # Cancelamos si dice que No

        storage_paths = self._prompt_dc_storage_paths("DC1")
        if not storage_paths:
            return
        ntds_path, sysvol_path = storage_paths

        # 2. Pedir Dominio
        # ATENCIÓN: Si self.input_dialog te da error en DC1 pero va en DC2,
        # asegúrate de que estás llamando al MISMO método.
        # Si usas la nueva función input_dialog que te di:
        dom = self.input_dialog("Dominio", "Nombre de Dominio Ej: (ET.MS.ESP):")
        if not dom: return
        dom = dom.strip()
        if not self._validate_or_show(
            dom,
            SysUtils.is_valid_domain,
            "Dominio no válido",
            "Introduce un dominio DNS válido. Ejemplo: et.ms.esp"
        ):
            return

        # 3. Pedir NetBIOS
        net = self.input_dialog("NetBIOS", "Nombre NetBIOS Ej: (ET):")
        if not net: return
        net = net.strip().upper()
        if not self._validate_or_show(
            net,
            SysUtils.is_valid_netbios,
            "NetBIOS no válido",
            "Introduce un nombre NetBIOS de 1 a 15 caracteres, sin espacios."
        ):
            return

        # 4. Pedir Contraseña SafeMode
        pwd = self.input_dialog("Pass", "Contraseña del modo seguro (SAFEMODE):", is_password=True)
        if not pwd: return
        if not self._validate_or_show(
            pwd,
            lambda value: SysUtils.is_plain_value(value, max_len=127),
            "Contraseña no válida",
            "La contraseña no puede estar vacía ni contener saltos de línea."
        ):
            return
        
        # Iniciar tarea
        self.iniciar_tarea(self.task_dc1_logic, dom, net, pwd, ntds_path, sysvol_path)

    def task_dc1_logic(self, dom, net, pwd, ntds_path=None, sysvol_path=None):
        print("Verificando prerrequisitos...")
        if not self._require_windows_server("DC1 - Nuevo bosque"):
            return
        if not self._prepare_dc_storage_paths(ntds_path, sysvol_path):
            self._notify_task_error(
                "DC1 - Almacenamiento",
                "No se pudieron crear o validar las carpetas NTDS y SYSVOL.\n\n"
                "Revisa que existan particiones dedicadas y que tengas permisos de escritura.",
            )
            return
        if not SysUtils.is_feature_installed("Net-Framework-Core"):
            self._notify_task_error(
                "DC1 - .NET Framework 3.5",
                ".NET Framework 3.5 no esta instalado.\n\n"
                "Instalalo antes de promocionar el servidor a controlador de dominio.",
            )
            return

        if self.stop_event.is_set(): return
        if not self._ensure_ad_dns_roles():
            return
        self.update_progress(0.5)

        print("Promocionando a Controlador de Dominio (Bosque Nuevo). NO CANCELE ESTE PASO.")
        ntds_path = getattr(self, "_dc_ntds_path", r"D:\NTDS")
        sysvol_path = getattr(self, "_dc_sysvol_path", r"E:\Sysvol")
        cmd = (
            f"Install-ADDSForest -DomainName {SysUtils.ps_quote(dom)} "
            f"-DomainNetBiosName {SysUtils.ps_quote(net)} -InstallDns "
            f"-DatabasePath {SysUtils.ps_quote(ntds_path)} -LogPath {SysUtils.ps_quote(ntds_path)} -SysvolPath {SysUtils.ps_quote(sysvol_path)} "
            f"-SafeModeAdministratorPassword (ConvertTo-SecureString {SysUtils.ps_quote(pwd)} -AsPlainText -Force) -Force"
        )
        
        res, out = SysUtils.run_powershell(cmd, capture=True)
        print(out)
        self.update_progress(1)
        if res:
            print("\nPromoción exitosa. El servidor se REINICIARÁ automáticamente.")
        else:
            print("\nERROR en la promoción. Revise el log.")
            self._notify_task_error(
                "DC1 - Promocion",
                "La promocion a controlador de dominio no se ha completado.\n\n"
                "Revisa el log para ver si fallan DNS, credenciales, rutas NTDS/SYSVOL o prerrequisitos.",
            )

    def pre_task_dc2(self):
        # 1. Aviso de prerrequisitos
        if not self.ui_askyesno(
            "Confirmar DC2",
            "Antes de continuar, confirma que se cumplen TODOS estos requisitos:\n\n"
            "1. DOMINIO: este servidor YA esta unido al dominio existente y se ha reiniciado tras la union.\n"
            "   Si aun esta en grupo de trabajo, usa primero Unir a dominio y reinicia.\n\n"
            "2. DISCOS: existen o se indicaran rutas locales para NTDS y SYSVOL.\n"
            "   Se aceptan letras distintas y rutas personalizadas, por ejemplo F:\\NTDS y G:\\SYSVOL.\n\n"
            "3. SOFTWARE: esta instalado .NET Framework 3.5.\n\n"
            "4. FIREWALL: esta deshabilitado o configurado para AD DS/DNS.\n\n"
            "5. RED/DNS: el DNS principal apunta al DC/DNS del dominio existente.\n\n"
            "6. CONECTIVIDAD: el dominio resuelve por DNS y responde correctamente.\n\n"
            "Easy Deploy promocionara automaticamente este servidor como controlador adicional; "
            "no tendras que usar el asistente de Administrador del servidor.\n\n"
            "¿Se cumplen TODOS los requisitos?"
        ):
            return  # Cancelado por el usuario

        # 2. Dominio existente
        dom = self.input_dialog("Dominio", "Dominio existente Ej: (ET.MS.ESP):")
        if not dom:
            return
        dom = dom.strip()
        if not self._validate_or_show(
            dom,
            SysUtils.is_valid_domain,
            "Dominio no válido",
            "Introduce un dominio DNS válido. Ejemplo: et.ms.esp"
        ):
            return

        if not self._prevalidate_dc2_domain_membership(dom):
            return

        storage_paths = self._prompt_dc_storage_paths("DC2")
        if not storage_paths:
            return
        ntds_path, sysvol_path = storage_paths

        # 3. Usuario administrador del dominio
        user = self.input_dialog(
            "User",
            "Usuario Admin del Dominio\nEj: administrador, ET\\administrador o administrador@et.ms.esp:"
        )
        if not user:
            return
        user = user.strip()
        if not self._validate_or_show(
            user,
            SysUtils.is_plain_value,
            "Usuario no válido",
            "El usuario no puede estar vacío ni contener saltos de línea."
        ):
            return

        # 4. Contraseña del usuario administrador
        pwd_u = self.input_dialog("Pass", "Contraseña Admin:", True)
        if not pwd_u:
            return
        if not self._validate_or_show(
            pwd_u,
            lambda value: SysUtils.is_plain_value(value, max_len=127),
            "Contraseña no válida",
            "La contraseña no puede estar vacía ni contener saltos de línea."
        ):
            return

        # 5. Contraseña del modo seguro (DSRM / SafeMode)
        pwd_s = self.input_dialog("Safe", "Contraseña del modo seguro (SAFEMODE):", True)
        if not pwd_s:
            return
        if not self._validate_or_show(
            pwd_s,
            lambda value: SysUtils.is_plain_value(value, max_len=127),
            "Contraseña no válida",
            "La contraseña no puede estar vacía ni contener saltos de línea."
        ):
            return

        # 6. Iniciar tarea
        self.iniciar_tarea(self.task_dc2_logic, dom, user, pwd_u, pwd_s, ntds_path, sysvol_path)

    def task_dc2_logic(self, dom, user, pwd_u, pwd_s, ntds_path=None, sysvol_path=None):
        if not self._require_windows_server("DC2 - Controlador adicional"):
            return
        if not self._ensure_dc2_domain_membership(dom):
            return
        if not self._prepare_dc_storage_paths(ntds_path, sysvol_path):
            self._notify_task_error(
                "DC2 - Almacenamiento",
                "No se pudieron crear o validar las carpetas NTDS y SYSVOL.\n\n"
                "Revisa que existan particiones dedicadas y que tengas permisos de escritura.",
            )
            return
        if not self._check_domain_ping(dom):
            return

        if not self._ensure_ad_dns_roles():
            return
        self.update_progress(0.5)

        print("Promocionando a Controlador de Dominio Adicional. NO CANCELE ESTE PASO.")

        # Si el usuario no indica formato dominio\\usuario ni UPN, usamos UPN: usuario@dominio.
        user_with_dom = user if ('\\' in user or '@' in user) else f'{user}@{dom}'
        ntds_path = getattr(self, "_dc_ntds_path", r"D:\NTDS")
        sysvol_path = getattr(self, "_dc_sysvol_path", r"E:\Sysvol")

        cmd = f'''
        $p = ConvertTo-SecureString {SysUtils.ps_quote(pwd_u)} -AsPlainText -Force;
        $c = New-Object System.Management.Automation.PSCredential ({SysUtils.ps_quote(user_with_dom)}, $p);
        Install-ADDSDomainController -DomainName {SysUtils.ps_quote(dom)} -Credential $c `
            -InstallDns `
            -DatabasePath {SysUtils.ps_quote(ntds_path)} -LogPath {SysUtils.ps_quote(ntds_path)} -SysvolPath {SysUtils.ps_quote(sysvol_path)} `
            -SafeModeAdministratorPassword (ConvertTo-SecureString {SysUtils.ps_quote(pwd_s)} -AsPlainText -Force) `
            -NoGlobalCatalog:$false `
            -NoRebootOnCompletion:$false `
            -Force
        '''
        res, out = SysUtils.run_powershell(cmd, capture=True)
        print(out)
        self.update_progress(1)
        if res:
            self.console_finish_state = "restart"
            print("\nPromocion DC2 completada automaticamente. El servidor se reiniciara para finalizar AD DS.")
            self._notify_task_info(
                "DC2 - Promocion completada",
                "La promocion automatica como controlador de dominio adicional se ha completado.\n\n"
                "El servidor se reiniciara o quedara pendiente de reinicio para terminar la instalacion de AD DS.\n"
                "No hace falta abrir el asistente de Administrador del servidor para promocionarlo manualmente.",
            )
        else:
            print("\nERROR en la promoción. Revise el log.")
            self._notify_task_error(
                "DC2 - Promocion",
                "La promocion como controlador adicional no se ha completado.\n\n"
                "Revisa credenciales, DNS, conectividad con el dominio y prerrequisitos.",
            )

    def pre_task_join_domain(self):
        """Preparación para la tarea de unir a dominio."""
        
        # 1. DOMINIO
        dom = self.input_dialog("Dominio", "Dominio al que unirse\nEj: (midominio.local)")
        if not dom: return # Si cancela o cierra, sale.
        dom = dom.strip()
        if not self._validate_or_show(
            dom,
            SysUtils.is_valid_domain,
            "Dominio no válido",
            "Introduce un dominio DNS válido. Ejemplo: midominio.local"
        ):
            return

        # 2. NUEVO NOMBRE (Opcional)
        # Usamos "NO" como palabra clave para no cambiar el nombre.
        new_name = self.input_dialog("Nombre", "Nuevo Nombre Equipo\n(Escribe 'NO' para dejar el actual)")
        if not new_name: return
        
        # Normalizamos: si escribe "NO", "no", "No", lo tratamos como vacío (no cambiar)
        if new_name.strip().upper() == "NO": 
            new_name = "" 
        else:
            new_name = new_name.strip().upper()
            if not self._validate_or_show(
                new_name,
                SysUtils.is_valid_netbios,
                "Nombre de equipo no válido",
                "El nombre del equipo debe tener 1 a 15 caracteres, sin espacios."
            ):
                return

        # 3. USUARIO
        user = self.input_dialog("User", "Usuario Administrador del Dominio\nEj: (et.ms.esp\\administrador)")
        if not user: return
        user = user.strip()
        if not self._validate_or_show(
            user,
            SysUtils.is_plain_value,
            "Usuario no válido",
            "El usuario no puede estar vacío ni contener saltos de línea."
        ):
            return

        # 4. CONTRASEÑA
        pwd = self.input_dialog("Pass", "Contraseña del Administrador:", is_password=True)
        if not pwd: return
        if not self._validate_or_show(
            pwd,
            lambda value: SysUtils.is_plain_value(value, max_len=127),
            "Contraseña no válida",
            "La contraseña no puede estar vacía ni contener saltos de línea."
        ):
            return
        
        # Confirmación final
        # Mensaje personalizado según si va a cambiar nombre o no
        accion_nombre = f"cambiando nombre a '{new_name}'" if new_name else "manteniendo nombre actual"
        
        if self.ui_askyesno("Confirmar Dominio", f"¿Unir a '{dom}' {accion_nombre} con usuario '{user}'?"):
            self.iniciar_tarea(self.task_join_domain, dom, new_name, user, pwd)

    def task_join_domain(self, dom, new_name, user, pwd):
        """Lógica de unión a dominio."""
        ping_ok = self._check_domain_ping(dom, notify=False)
        if not ping_ok:
            self.update_progress(1)
            self.ui_showerror(
                "Unir a dominio",
                "No se pudo contactar con el dominio.\n\n"
                "Revisa la configuracion de red, DNS, puerta de enlace y conectividad antes de repetir la union.",
            )
            return
        
        # 1. Determinar comando
        if new_name:
            print(f"Se intentará CAMBIAR el nombre a '{new_name}' y unir a '{dom}'.")
            join_cmd = f"Add-Computer -DomainName {SysUtils.ps_quote(dom)} -Credential $c -Force -NewName {SysUtils.ps_quote(new_name)}"
        else:
            print(f"Uniendo a dominio '{dom}' manteniendo nombre actual.")
            join_cmd = f"Add-Computer -DomainName {SysUtils.ps_quote(dom)} -Credential $c -Force"
            
        # 2. Construir credencial
        user_with_dom = user if ('\\' in user or '@' in user) else f'{user}@{dom}'
        
        cmd = f'''
        $p = ConvertTo-SecureString {SysUtils.ps_quote(pwd)} -AsPlainText -Force;
        $c = New-Object System.Management.Automation.PSCredential ({SysUtils.ps_quote(user_with_dom)}, $p);
        {join_cmd}
        '''
        
        # 3. Ejecutar
        print("Ejecutando script de Powershell...")
        res, out = SysUtils.run_powershell(cmd, capture=True)
        print(out) 
        
        # 4. Resultado
        if res:
            print("\n[OK] Unido correctamente. REINICIA el equipo para aplicar cambios.")
            self.console_finish_state = "restart"
        else:
            # Si quieres mantener el aviso del SID como información pero sin decir "Ejecuta CAMBIAR SID":
            if "SID" in out:
                 print("\n[ERROR] Posible SID Duplicado detectado.")
            
            print("\n[ERROR] Falló la unión. Revisa credenciales/red.")
            self.ui_showwarning(
                "Unir a dominio",
                "Conexion con el dominio correcta.\n\n"
                "Revisa los DNS y Active Directory por posible duplicidad del nombre de equipo. "
                "Si el equipo ya estuvo unido antes con el mismo nombre, elimina o corrige el registro duplicado y repite la union.",
            )

        self.update_progress(1)
