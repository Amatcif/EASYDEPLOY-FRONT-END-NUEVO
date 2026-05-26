import re
import subprocess

from ..core.sysutils import SysUtils


class KmsTasksMixin:
    KMS_CLIENT_KEYS = {
        "2022": {
            "ServerDatacenter": "WX4NM-KYWYW-QJJR4-XV3QB-6VM33",
            "ServerStandard": "VDYBN-27WPP-V4HQT-9VMD4-VMK7H",
        },
        "2019": {
            "ServerDatacenter": "WMDGN-G9PQG-XVVXX-R3X43-63DFG",
            "ServerStandard": "N69G4-B89J2-4G8F4-WWYCC-J464C",
            "ServerEssentials": "WVDHN-86M7X-466P6-VHXV7-YY726",
        },
        "2016": {
            "ServerDatacenter": "CB7KF-BWN84-R7R2Y-793K2-8XDDG",
            "ServerStandard": "WC2BQ-8NRM3-FDDYY-2BFGV-KHKQY",
            "ServerEssentials": "JCKRF-N37P4-C2D82-9YXRT-4M63B",
        },
        "2012 R2": {
            "ServerDatacenter": "W3GGN-FT8W3-Y4M27-J84CP-Q3VJ9",
            "ServerStandard": "D2N9P-3P6X9-2R39C-7RTCD-MDVJX",
            "ServerEssentials": "KNC87-3J2TX-XB4WP-VCPJV-M4FWM",
        },
        "2012": {
            "ServerDatacenter": "48HP8-DN98B-MYWDG-T2DCC-8W83P",
            "ServerStandard": "XC9B7-NBPP2-83J2H-RHMBY-92BT4",
        },
        "2008 R2": {
            "ServerDatacenter": "74YFP-3QFB3-KQT8W-PMXWJ-7M648",
            "ServerEnterprise": "489J6-VHDMP-X63PK-3K798-CPX3Y",
            "ServerStandard": "YC6KT-GKW9T-YTKYR-T4X34-R7VHC",
        },
        "2008": {
            "ServerDatacenter": "7M67G-PC374-GR742-YH8V4-TCBY3",
            "ServerEnterprise": "YQGMW-MPWTJ-34KDK-48M3W-X4Q6V",
            "ServerStandard": "TM24T-X9RMF-VWXK6-X8JC9-BFGM2",
        },
    }

    _SERVER_EDITION_RE = re.compile(r"\b(Server[A-Za-z0-9]+)\b", re.IGNORECASE)

    def task_kms(self):
        print("Analizando sistema operativo...")
        full_name = SysUtils.get_os_caption()
        edition_state = self._get_windows_edition_state(full_name)
        current_edition = edition_state["current_edition"]
        target_editions = edition_state["target_editions"]
        release = edition_state["release"]
        display_name = self._display_os_name(full_name, current_edition)

        print(f"Sistema detectado: {display_name}")
        if current_edition:
            print(f"Edicion DISM actual: {current_edition}")
        if target_editions:
            print("Ediciones destino permitidas por DISM: " + ", ".join(target_editions))

        is_eval = self._is_eval_installation(full_name, current_edition)
        if is_eval:
            self._convert_evaluation_server(display_name, current_edition, target_editions, release)
            return

        self._activate_kms_client(display_name, current_edition, release)

    def _get_windows_edition_state(self, full_name):
        current_ok, current_output = self._capture_process(["dism.exe", "/online", "/Get-CurrentEdition"])
        current_edition = self._parse_current_edition(current_output) if current_ok else ""
        if not current_ok:
            print("[AVISO] No se pudo leer la edicion actual con DISM.")
            if current_output.strip():
                print(current_output.strip())

        target_ok, target_output = self._capture_process(["dism.exe", "/online", "/Get-TargetEditions"])
        target_editions = self._parse_target_editions(target_output) if target_ok else []
        if not target_ok:
            print("[AVISO] No se pudieron leer las ediciones destino con DISM.")
            if target_output.strip():
                print(target_output.strip())

        if not current_edition:
            caption_edition = self._edition_from_caption(full_name)
            if caption_edition and self._caption_mentions_eval(full_name):
                current_edition = caption_edition + "Eval"
            else:
                current_edition = caption_edition

        return {
            "current_edition": current_edition,
            "target_editions": target_editions,
            "release": self._detect_server_release(full_name),
        }

    def _convert_evaluation_server(self, full_name, current_edition, target_editions, release):
        print("[INFO] Version Evaluation detectada. Se hara conversion de edicion antes de activar KMS.")

        if self._is_domain_controller():
            self._notify_task_error(
                "KMS / Conversion Evaluation",
                "Microsoft no permite convertir un controlador de dominio desde Evaluation a retail/volumen.\n\n"
                "Instala otro DC con una version completa, migra roles FSMO y retira este DC Evaluation.",
            )
            return

        target_edition = self._select_eval_target_edition(current_edition, target_editions, full_name)
        if not target_edition:
            self._notify_task_error(
                "KMS / Conversion Evaluation",
                "No se pudo determinar una edicion destino segura para DISM.\n\n"
                "Revisa la edicion detectada y las ediciones destino que muestra DISM antes de repetir.",
            )
            return

        print(f"Objetivo: convertir a {target_edition}")
        gvlk_key = self._key_for(release, target_edition)
        if gvlk_key:
            print(f"[INFO] Clave generica de Microsoft para esta edicion: {self._mask_key(gvlk_key)}")
        print("[INFO] Si introduces una clave generica de Microsoft, Easy Deploy intentara convertir Windows Server Trial/Evaluation a una edicion normal usando esa clave generica.")

        conversion_key = self._ask_eval_conversion_key(full_name, target_edition, release)
        if not conversion_key:
            print("Operacion cancelada: no se ha iniciado la conversion Evaluation.")
            return

        print(f"Clave de conversion introducida: {self._mask_key(conversion_key)}")
        print("Preparando servicio de licencias...")
        self.update_progress(0.05)
        self._capture_process(["sc.exe", "start", "sppsvc"])

        cmd_dism = [
            "dism.exe",
            "/online",
            f"/Set-Edition:{target_edition}",
            f"/ProductKey:{conversion_key}",
            "/AcceptEula",
        ]

        print(f"Iniciando conversion DISM a {target_edition}...")
        return_code = self._run_streamed_process(
            cmd_dism,
            key_to_mask=conversion_key,
            hide_progress_lines=True,
            hidden_output_phrases=(
                "1168",
                "error:",
                "an error occurred while applying target edition",
                "the upgrade cannot proceed",
                "for more information",
                "the dism log file can be found",
            ),
        )

        if return_code in (0, 3010, 1168):
            self.update_progress(1.0)
            if return_code == 1168:
                print("[OK] Cambios de edicion aplicados. Windows necesita reiniciarse para finalizar la conversion.")
            elif return_code == 3010:
                print("[OK] Conversion completada. Windows informa que debe reiniciarse.")
            else:
                print("[OK] Conversion completada.")
            print("IMPORTANTE: reinicia el servidor antes de volver a ejecutar KMS.")
            print("Despues del reinicio, ejecuta KMS otra vez para configurar el servidor KMS y activar Windows.")
            if self._is_reboot_pending():
                print("[INFO] Windows tiene un reinicio pendiente.")
            if self.ui_ask_reboot("Reinicio requerido", "La conversion necesita reiniciar el servidor para completarse.\n\nDespues del reinicio, vuelve a ejecutar KMS para activar Windows."):
                subprocess.run(["shutdown", "/r", "/t", "0"], creationflags=subprocess.CREATE_NO_WINDOW)
            return

        print("[ERROR] DISM no ha completado la conversion.")
        print(r"Revisa el registro de Windows en C:\Windows\Logs\DISM\dism.log si necesitas mas detalle.")
        print("No se ha continuado con activacion KMS para no dejar el servidor a medias.")
        self._notify_task_error(
            "KMS / Conversion Evaluation",
            "DISM no ha completado la conversion de edicion.\n\n"
            "No se continua con la activacion KMS para no dejar el servidor a medias.\n\n"
            r"Revisa C:\Windows\Logs\DISM\dism.log y vuelve a intentarlo.",
        )

    def _ask_eval_conversion_key(self, full_name, target_edition, release):
        prompt = (
            f"Sistema: {full_name}\n"
            f"Objetivo DISM: {target_edition}\n\n"
            "Introduce una clave para convertir Windows Server Trial/Evaluation.\n"
            "Puedes escribirla con guiones o sin guiones.\n\n"
            "Ejemplo con guiones:\n"
            "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX\n\n"
            "Ejemplo sin guiones:\n"
            "XXXXXXXXXXXXXXXXXXXXXXXXX\n\n"
            "Si introduces una clave generica de Microsoft, se intentara convertir la version Trial a una version normal usando esa clave generica."
        )

        raw_key = self.ui_input_dialog("Clave de conversion", prompt, max_chars=29, auto_dash=False)
        if not raw_key:
            return ""

        conversion_key = self._normalize_product_key(raw_key)
        if not self._validate_or_show(
            conversion_key,
            SysUtils.is_valid_product_key,
            "Clave de conversion no valida",
            "La clave debe tener el formato XXXXX-XXXXX-XXXXX-XXXXX-XXXXX.",
        ):
            return ""

        if self._is_known_gvlk(conversion_key):
            expected_gvlk = self._key_for(release, target_edition)
            detail = (
                f"\n\nClave generica detectada para esta edicion: {self._mask_key(expected_gvlk)}"
                if expected_gvlk and conversion_key == expected_gvlk
                else ""
            )
            use_gvlk = self.ui_askyesno(
                "Clave generica de Microsoft",
                "Has introducido una clave generica de Microsoft.\n\n"
                "Easy Deploy intentara convertir Windows Server Trial/Evaluation a una version normal usando esa clave generica. "
                "Si Windows necesita reiniciar para finalizar la conversion, Easy Deploy te lo pedira al terminar.\n\n"
                "Quieres continuar?" + detail,
            )
            if not use_gvlk:
                print("[INFO] Conversion cancelada por el usuario al detectar una clave generica de Microsoft.")
                return ""
            print("[INFO] Se continuara con una clave generica de Microsoft.")

        return conversion_key

    def _activate_kms_client(self, full_name, current_edition, release):
        print("[OK] Version no Evaluation detectada. Se configurara activacion KMS.")

        kms_server = self.ui_input_dialog("Configuracion KMS", "Introduce IP/Hostname del servidor KMS:")
        if not kms_server:
            print("Operacion cancelada.")
            return

        kms_server = kms_server.strip()
        if not self._validate_or_show(
            kms_server,
            SysUtils.is_valid_host,
            "Servidor KMS no valido",
            "Introduce una IP o nombre DNS valido para el servidor KMS.",
        ):
            print("Operacion cancelada: servidor KMS no valido.")
            return

        print(f"Comprobando conectividad con {kms_server}...")
        ping_ok, ping_output = SysUtils.ping_host(kms_server, count=1, timeout_ms=2000)
        if ping_output.strip():
            print(ping_output.strip())
        if not ping_ok:
            print(f"[ERROR] No se puede conectar con {kms_server}.")
            print("El servidor no responde al ping. Verifica IP, DNS, firewall o VPN.")
            print("--- PROCESO CANCELADO ---")
            self._notify_task_error(
                "Servidor KMS no accesible",
                f"No se puede conectar con el servidor KMS:\n\n{kms_server}\n\n"
                "Verifica IP, DNS, firewall, VPN o que el servidor KMS este encendido.",
            )
            return

        target_edition = self._edition_without_eval(current_edition) or self._edition_from_caption(full_name)
        kms_key = self._key_for(release, target_edition)
        if kms_key:
            print(f"Clave GVLK oficial detectada para Windows Server {release} / {target_edition}: {self._mask_key(kms_key)}")
        else:
            print("[AVISO] No se pudo elegir una GVLK automaticamente para este sistema.")
            raw_key = self.ui_input_dialog(
                "Licencia Windows",
                f"Sistema: {full_name}\n\n"
                "Introduce tu licencia GVLK.\n"
                "Puedes escribirla con guiones o sin guiones.\n\n"
                "Ejemplo con guiones:\n"
                "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX\n\n"
                "Ejemplo sin guiones:\n"
                "XXXXXXXXXXXXXXXXXXXXXXXXX",
                max_chars=29,
                auto_dash=False,
            )
            if not raw_key:
                print("Operacion cancelada.")
                return

            kms_key = self._normalize_product_key(raw_key)
            if not self._validate_or_show(
                kms_key,
                SysUtils.is_valid_product_key,
                "Clave GVLK no valida",
                "La clave debe tener el formato XXXXX-XXXXX-XXXXX-XXXXX-XXXXX.",
            ):
                print("Operacion cancelada: clave GVLK no valida.")
                return

        cmds = [
            ("Instalando clave GVLK", ["cscript", "//NoLogo", r"C:\Windows\System32\slmgr.vbs", "/ipk", kms_key]),
            ("Configurando servidor KMS", ["cscript", "//NoLogo", r"C:\Windows\System32\slmgr.vbs", "/skms", kms_server]),
            ("Solicitando activacion", ["cscript", "//NoLogo", r"C:\Windows\System32\slmgr.vbs", "/ato"]),
        ]

        for index, (label, cmd) in enumerate(cmds, start=1):
            if self.stop_event.is_set():
                print("Operacion cancelada por el usuario.")
                return
            print(f"{label} ({index}/{len(cmds)})...")
            ok, output = self._capture_process(cmd, key_to_mask=kms_key)
            if output.strip():
                print(output.strip())
            if not ok:
                print("[ERROR] El paso anterior fallo. Se detiene la activacion KMS.")
                self._notify_task_error(
                    "Activacion KMS",
                    f"El paso '{label}' no se ha completado correctamente.\n\n"
                    "Se detiene la activacion para que revises el log y el estado del servidor KMS.",
                )
                return
            self.update_progress(index / len(cmds))

        print("[OK] Proceso de activacion KMS finalizado.")

    def _capture_process(self, cmd, key_to_mask=None):
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=SysUtils.oem_encoding(),
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output = res.stdout or ""
            if key_to_mask:
                output = output.replace(key_to_mask, self._mask_key(key_to_mask))
            return res.returncode == 0, output
        except Exception as exc:
            return False, f"Excepcion ejecutando {' '.join(cmd)}: {exc}"

    def _run_streamed_process(self, cmd, key_to_mask=None, hidden_output_phrases=None, hide_progress_lines=False):
        try:
            printable_cmd = " ".join(cmd)
            if key_to_mask:
                printable_cmd = printable_cmd.replace(key_to_mask, self._mask_key(key_to_mask))
            print(f"> {printable_cmd}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=SysUtils.oem_encoding(),
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            for line in process.stdout:
                if self.stop_event.is_set():
                    process.terminate()
                    print("Operacion cancelada por el usuario.")
                    return -1

                text = line.rstrip()
                if key_to_mask:
                    text = text.replace(key_to_mask, self._mask_key(key_to_mask))
                progress_match = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s*%", line)
                hidden_text = bool(hide_progress_lines and progress_match)
                if hidden_output_phrases:
                    lowered = text.lower()
                    hidden_text = hidden_text or any(phrase.lower() in lowered for phrase in hidden_output_phrases)
                if text and not hidden_text:
                    print(text)

                if progress_match:
                    percent = float(progress_match.group(1).replace(",", "."))
                    self.update_progress(max(0.05, min(percent / 100.0, 0.98)))

            return process.wait()
        except Exception as exc:
            print(f"[ERROR] Excepcion ejecutando proceso: {exc}")
            return -1

    def _parse_current_edition(self, output):
        for line in output.splitlines():
            if ":" not in line:
                continue
            edition = self._first_server_edition(line.split(":", 1)[1])
            if edition:
                return edition
        return self._first_server_edition(output)

    def _parse_target_editions(self, output):
        editions = []
        for match in self._SERVER_EDITION_RE.finditer(output or ""):
            edition = self._canonical_edition(match.group(1), keep_eval=False)
            if edition and edition not in editions:
                editions.append(edition)
        return editions

    def _first_server_edition(self, text):
        match = self._SERVER_EDITION_RE.search(text or "")
        return self._canonical_edition(match.group(1), keep_eval=True) if match else ""

    def _canonical_edition(self, value, keep_eval=False):
        text = str(value or "").strip()
        lower = text.lower()
        if "datacenter" in lower:
            base = "ServerDatacenter"
        elif "standard" in lower:
            base = "ServerStandard"
        elif "essential" in lower or "solution" in lower:
            base = "ServerEssentials"
        elif "enterprise" in lower:
            base = "ServerEnterprise"
        else:
            return ""
        return base + "Eval" if keep_eval and "eval" in lower else base

    def _detect_server_release(self, caption):
        text = str(caption or "").upper()
        for release in ("2022", "2019", "2016", "2012 R2", "2012", "2008 R2", "2008"):
            if release in text:
                return release
        return ""

    def _edition_from_caption(self, caption):
        return self._canonical_edition(caption, keep_eval=False)

    def _caption_mentions_eval(self, caption):
        text = str(caption or "").upper()
        return "EVALUATION" in text or "EVALUACION" in text or "EVALUACIÓN" in text

    def _is_eval_installation(self, caption, current_edition):
        if current_edition:
            return "eval" in str(current_edition or "").lower()
        return self._caption_mentions_eval(caption)

    def _display_os_name(self, caption, current_edition):
        text = str(caption or "").strip()
        if current_edition and "eval" not in str(current_edition).lower() and self._caption_mentions_eval(text):
            text = re.sub(r"\s+Evaluation\b", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s+Evaluaci[oó]n\b", "", text, flags=re.IGNORECASE)
        return text or "Windows Server"

    def _edition_without_eval(self, edition):
        return self._canonical_edition(edition, keep_eval=False)

    def _select_eval_target_edition(self, current_edition, target_editions, full_name):
        base_edition = self._edition_without_eval(current_edition) or self._edition_from_caption(full_name)
        if not base_edition:
            return ""

        if not target_editions:
            print("[AVISO] DISM no devolvio ediciones destino. Se usara la misma familia detectada por seguridad.")
            return base_edition

        if base_edition in target_editions:
            return base_edition

        print(f"[ERROR] La edicion detectada ({base_edition}) no aparece como destino valido de DISM.")
        print("Destinos permitidos: " + ", ".join(target_editions))
        return ""

    def _key_for(self, release, edition):
        return self.KMS_CLIENT_KEYS.get(release or "", {}).get(edition or "", "")

    def _known_gvlk_values(self):
        values = set()
        for editions in self.KMS_CLIENT_KEYS.values():
            values.update(key.upper() for key in editions.values())
        return values

    def _is_known_gvlk(self, product_key):
        return str(product_key or "").upper().strip() in self._known_gvlk_values()

    def _normalize_product_key(self, product_key):
        """
        Normaliza claves escritas con guiones, sin guiones, espacios o minúsculas.

        Entrada válida:
            XXXXX-XXXXX-XXXXX-XXXXX-XXXXX

        También acepta:
            XXXXXXXXXXXXXXXXXXXXXXXXX

        Devuelve:
            XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
        """
        chars = re.sub(r"[^A-Za-z0-9]", "", str(product_key or "")).upper()
        chars = chars[:25]

        groups = []
        for index in range(0, len(chars), 5):
            groups.append(chars[index:index + 5])

        return "-".join(groups)

    def _mask_key(self, key):
        key = self._normalize_product_key(key)
        if not key or len(key) < 11:
            return "*****"
        return f"{key[:5]}-*****-*****-*****-{key[-5:]}"

    def _is_domain_controller(self):
        ok, output = SysUtils.run_powershell("(Get-CimInstance Win32_OperatingSystem).ProductType", capture=True, timeout=10)
        return ok and output.strip().splitlines()[0:1] == ["2"]

    def _is_reboot_pending(self):
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
