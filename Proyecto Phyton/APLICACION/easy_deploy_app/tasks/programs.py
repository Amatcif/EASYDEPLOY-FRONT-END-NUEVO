import glob
import ctypes
import os
import re
import subprocess
from xml.sax.saxutils import escape

from ..core.sysutils import SysUtils


class ProgramsTasksMixin:
    """Instaladores auxiliares lanzados desde la carpeta OTROS."""

    FIREFOX_PATTERNS = ("Firefox Setup*.exe", "Firefox*.exe", "*firefox*.exe")
    WINRAR_PATTERNS = ("winrar-x64*.exe", "WinRAR*.exe", "*winrar*.exe")
    ADOBE_READER_PATTERNS = ("AcroRdrDC2600121529_es_ES.exe", "AcroRdrDC*.exe", "*AcroRdr*.exe")
    OFFICE_OFFLINE_FOLDER = "officeoffline"
    OFFICE_OFFLINE_VBS_PATTERNS = ("Instalar_Office_Oculto.vbs", "*.vbs")
    OFFICE_OFFLINE_BAT_PATTERNS = ("Instalar_office_offline.bat", "*.bat")
    OFFICE_IMAGE_PATTERNS = ("O365ProPlusRetail*.img", "*.img", "*.iso", "Setup.exe")
    SKYPE_STANDALONE_PATTERNS = ("lyncentry*.exe", "*Skype*.exe", "*lync*.exe")

    OFFICE_PRODUCTS = (
        ("O365ProPlusRetail", "", "Microsoft 365 Apps/Office ProPlus Retail"),
        ("ProPlus2021Volume", "PerpetualVL2021", "Office LTSC Professional Plus 2021 Volume"),
        ("ProPlus2021Retail", "PerpetualVL2021", "Office Professional Plus 2021 Retail"),
        ("ProPlusRetail", "", "Office Professional Plus Retail"),
        ("Professional2021Retail", "PerpetualVL2021", "Office Professional 2021 Retail"),
    )
    SKYPE_PRODUCTS = (
        ("SkypeforBusinessRetail", "Skype for Business Retail"),
        ("SkypeforBusiness2021Volume", "Skype for Business LTSC 2021 Volume"),
        ("SkypeforBusiness2021Retail", "Skype for Business 2021 Retail"),
        ("SkypeforBusinessEntryRetail", "Skype for Business Basic Retail"),
    )

    def task_install_firefox(self):
        self._run_other_installer("Firefox", self.FIREFOX_PATTERNS)

    def task_install_winrar(self):
        self._run_other_installer("WinRAR", self.WINRAR_PATTERNS)

    def task_install_adobe_reader(self):
        self._run_other_installer("Adobe Reader", self.ADOBE_READER_PATTERNS)

    def _confirm_office_skype_launch(self):
        return self.modal_dialog(
            "Office + Skype",
            "Se va a abrir el instalador de Office + Skype.\n\n"
            "Cuando termine, vuelve a Easy Deploy para revisar el resultado.",
            "question",
            [("Continuar", True, "primary"), ("Cancelar", False, "secondary")],
        )

    def pre_task_install_office_skype(self):
        if not SysUtils.is_admin():
            self.ui_showerror(
                "Office + Skype",
                "Office + Skype debe ejecutarse como administrador.\n\n"
                "Cierra Easy Deploy y abrelo con 'Ejecutar como administrador'.",
            )
            return

        offline_launcher, offline_root = self._find_office_offline_launcher()
        if not offline_launcher:
            if not self._confirm_office_skype_launch():
                return
            self.iniciar_tarea(self.task_install_office_skype)
            return

        office_platform, installed_products = self._existing_office_click_to_run_state()
        if office_platform.lower() in {"x86", "32", "32bit"}:
            self.ui_showerror(
                "Office + Skype",
                "Ya existe Office Click-to-Run de 32 bits instalado.\n\n"
                "La instalacion offline de Easy Deploy usa Office de 64 bits. Microsoft no permite mezclar Office de 32 y 64 bits.\n\n"
                "Desinstala Office de 32 bits y vuelve a ejecutar Office + Skype.",
            )
            return

        missing = self._office_offline_missing(offline_root, offline_launcher)
        if missing:
            self.ui_showerror(
                "Office + Skype",
                "La carpeta officeoffline esta incompleta.\n\n"
                "Faltan estos elementos:\n- "
                + "\n- ".join(missing),
            )
            return

        if not self._confirm_office_skype_launch():
            return

        ok, detail = self._launch_office_offline_shell(offline_launcher, offline_root)
        if not ok:
            self.ui_showerror(
                "Office + Skype",
                "No se pudo lanzar el .bat de instalacion mediante Windows.\n\n"
                f"Detalle: {detail}",
            )
            return

        print("[OK] Office + Skype se ha lanzado desde Windows ShellExecute.")

    def task_install_office_skype(self):
        if not SysUtils.is_admin():
            self._notify_task_error(
                "Office + Skype",
                "Office + Skype debe ejecutarse como administrador.\n\n"
                "Cierra Easy Deploy y abrelo con 'Ejecutar como administrador'.",
            )
            return

        self.update_progress(5)
        mounted_image = ""
        setup_path = ""
        source_path = ""

        try:
            office_platform, installed_products = self._existing_office_click_to_run_state()
            if office_platform:
                print(f"Office Click-to-Run detectado: plataforma={office_platform}, productos={installed_products or 'no detectado'}")
            if office_platform.lower() in {"x86", "32", "32bit"}:
                self._notify_task_error(
                    "Office + Skype",
                    "Ya existe Office Click-to-Run de 32 bits instalado.\n\n"
                    "La instalacion offline de Easy Deploy usa Office de 64 bits. Microsoft no permite mezclar Office de 32 y 64 bits.\n\n"
                    "Desinstala Office de 32 bits y vuelve a ejecutar Office + Skype.",
                )
                return

            offline_launcher, offline_root = self._find_office_offline_launcher()
            if offline_launcher:
                self._run_office_offline_launcher(offline_launcher, offline_root)
                return

            print("Buscando medio offline de Office...")
            office_media = self._find_payload_file("OFFICE", self.OFFICE_IMAGE_PATTERNS)
            if not office_media:
                self._notify_task_error(
                    "Office + Skype",
                    "No se ha encontrado el medio offline de Office.\n\n"
                    "Coloca la carpeta OFFICE\\officeoffline con setup.exe, configuration.xml, Office e Instalar_Office_Oculto.vbs.",
                )
                return

            print(f"[OK] Medio Office encontrado: {office_media}")
            extension = os.path.splitext(office_media)[1].lower()
            if extension in {".img", ".iso"}:
                print("Montando medio Office...")
                mounted, drive_or_error = SysUtils.mount_disk_image(office_media)
                if not mounted:
                    self._notify_task_error(
                        "Office + Skype",
                        "No se pudo montar el medio offline de Office.\n\n"
                        f"Detalle: {drive_or_error}",
                    )
                    return
                mounted_image = office_media
                source_path = f"{drive_or_error}:\\"
                setup_path = os.path.join(source_path, "Setup.exe")
            elif os.path.basename(office_media).lower() == "setup.exe":
                setup_path = office_media
                source_path = os.path.dirname(office_media)

            self.update_progress(20)
            if not os.path.isfile(setup_path):
                self._notify_task_error(
                    "Office + Skype",
                    "El medio de Office no contiene Setup.exe en la raiz.\n\n"
                    f"Ruta esperada: {setup_path}",
                )
                return

            data_dir = os.path.join(source_path, "Office", "Data")
            if not os.path.isdir(data_dir):
                self._notify_task_error(
                    "Office + Skype",
                    "El origen offline no contiene Office\\Data.\n\n"
                    "Easy Deploy no descargara archivos de Internet. Usa un medio offline completo de Office Click-to-Run.",
                )
                return

            product_ids = self._read_office_source_product_ids(source_path)
            if product_ids:
                print("Productos detectados en el origen Office:")
                print(", ".join(sorted(product_ids)))
            else:
                print("[AVISO] No se pudo leer C2RFireFlyData.xml. Se intentara con IDs habituales.")

            office_product, channel, office_label = self._select_office_product(product_ids)
            skype_product, skype_label = self._select_skype_product(product_ids)
            if not office_product or not skype_product:
                self._notify_task_error(
                    "Office + Skype",
                    "El origen offline no contiene una combinacion compatible de Office y Skype for Business.\n\n"
                    "No se puede mezclar el instalador independiente de Skype con Office Click-to-Run.\n\n"
                    "Solucion: prepara un origen ODT offline que incluya Office y Skype for Business en el mismo Office\\Data.",
                )
                return

            standalone_skype = self._find_payload_file("SKYPE", self.SKYPE_STANDALONE_PATTERNS)
            if standalone_skype:
                print(f"[INFO] Instalador Skype independiente detectado pero no se usara: {standalone_skype}")
                print("[INFO] Para evitar conflicto MSI/Click-to-Run, Skype se instala desde el mismo origen Office.")

            print(f"[OK] Office seleccionado: {office_label} ({office_product})")
            print(f"[OK] Skype seleccionado: {skype_label} ({skype_product})")
            self.update_progress(35)

            config_path = self._write_office_skype_configuration(
                source_path,
                office_product,
                skype_product,
                channel,
            )
            print(f"Configuration.xml generado: {config_path}")
            print("Ejecutando instalacion offline: setup.exe /configure configuration.xml")
            self.update_progress(45)

            process = subprocess.Popen(
                [setup_path, "/configure", config_path],
                cwd=source_path,
                creationflags=0,
            )

            if self._wait_for_installer_process(process, "Office + Skype"):
                self.update_progress(100)
                self._notify_task_info(
                    "Office + Skype",
                    "La instalacion de Office + Skype ha finalizado o se ha cerrado correctamente.\n\n"
                    "Si Office solicita activacion, usa una licencia compatible con el producto instalado.",
                )
            else:
                self.update_progress(100)
                self._notify_task_warning(
                    "Office + Skype",
                    "La instalacion de Office + Skype se ha cancelado o no ha finalizado correctamente.\n\n"
                    "Revisa el log de Easy Deploy y los logs de Office en la carpeta TEMP del usuario.",
                )
        except Exception as exc:
            self._notify_task_error(
                "Office + Skype",
                f"No se pudo ejecutar la instalacion conjunta.\n\nDetalle: {exc}",
            )
        finally:
            if mounted_image:
                self._dismount_task_media(mounted_image, "finalizada")

    def _other_installers_roots(self):
        return self._payload_subfolder_roots("OTROS")

    def _payload_subfolder_roots(self, folder_name):
        roots = []

        payload_root = getattr(self, "payload_root", "")
        if payload_root:
            roots.append(os.path.join(payload_root, folder_name))

        base_path = getattr(self, "base_path", "")
        if base_path:
            current = os.path.abspath(base_path)
            for _ in range(6):
                roots.append(os.path.join(current, folder_name))
                roots.append(os.path.join(current, "EASY DEPLOY", folder_name))
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent

        roots.append(os.path.join(r"C:\Users\amatc\Desktop\PROYECTOS\EASYDEPLOY\EASY DEPLOY", folder_name))

        unique = []
        seen = set()
        for root in roots:
            norm = os.path.normcase(os.path.abspath(root))
            if norm in seen:
                continue
            seen.add(norm)
            unique.append(root)
        return unique

    def _find_payload_file(self, folder_name, patterns):
        for root in self._payload_subfolder_roots(folder_name):
            if not os.path.isdir(root):
                continue
            matches = []
            for pattern in patterns:
                matches.extend(glob.glob(os.path.join(root, pattern)))
            matches = [path for path in matches if os.path.isfile(path)]
            if matches:
                return max(matches, key=os.path.getmtime)
        return None

    def _find_other_installer(self, patterns):
        return self._find_payload_file("OTROS", patterns)

    def _find_payload_dir(self, folder_name, dir_name):
        for root in self._payload_subfolder_roots(folder_name):
            candidate = os.path.join(root, dir_name)
            if os.path.isdir(candidate):
                return candidate
        return ""

    def _find_office_offline_launcher(self):
        offline_root = self._find_payload_dir("OFFICE", self.OFFICE_OFFLINE_FOLDER)
        if not offline_root:
            return "", ""

        vbs_matches = []
        for pattern in self.OFFICE_OFFLINE_VBS_PATTERNS:
            vbs_matches.extend(glob.glob(os.path.join(offline_root, pattern)))
        vbs_matches = [path for path in vbs_matches if os.path.isfile(path)]
        if vbs_matches:
            return max(vbs_matches, key=os.path.getmtime), offline_root

        matches = []
        for pattern in self.OFFICE_OFFLINE_BAT_PATTERNS:
            matches.extend(glob.glob(os.path.join(offline_root, pattern)))
        matches = [path for path in matches if os.path.isfile(path)]
        if not matches:
            return "", offline_root
        return max(matches, key=os.path.getmtime), offline_root

    def _run_office_offline_launcher(self, launcher_path, offline_root):
        missing = self._office_offline_missing(offline_root, launcher_path)
        if missing:
            self._notify_task_error(
                "Office + Skype",
                "La carpeta officeoffline esta incompleta.\n\n"
                "Faltan estos elementos:\n- "
                + "\n- ".join(missing),
            )
            return

        print(f"[OK] Instalador offline Office encontrado: {launcher_path}")
        print(f"[OK] Carpeta offline: {offline_root}")
        print("Lanzando instalador offline mediante Windows ShellExecute.")
        self.update_progress(25)

        ok, detail = self._launch_office_offline_shell(launcher_path, offline_root)
        if not ok:
            self._notify_task_error(
                "Office + Skype",
                "No se pudo lanzar el .bat de instalacion mediante Windows.\n\n"
                f"Detalle: {detail}",
            )
            return

        self.update_progress(100)
        print("[OK] Office + Skype se ha lanzado desde Windows ShellExecute.")

    def _office_offline_missing(self, offline_root, launcher_path=""):
        missing = []
        has_vbs = os.path.isfile(os.path.join(offline_root, "Instalar_Office_Oculto.vbs"))
        has_bat = os.path.isfile(os.path.join(offline_root, "Instalar_office_offline.bat"))
        checks = (
            ("setup.exe", os.path.isfile(os.path.join(offline_root, "setup.exe"))),
            ("configuration.xml", os.path.isfile(os.path.join(offline_root, "configuration.xml"))),
            ("Instalar_Office_Oculto.vbs o Instalar_office_offline.bat", has_vbs or has_bat or os.path.isfile(launcher_path)),
            ("Office", os.path.isdir(os.path.join(offline_root, "Office"))),
        )
        for label, present in checks:
            if not present:
                missing.append(label)
        return missing

    def _launch_office_offline_shell(self, launcher_path, offline_root):
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                launcher_path,
                None,
                offline_root,
                1,
            )
        except Exception as exc:
            return False, str(exc)
        try:
            code = int(result)
        except Exception:
            code = 0
        if code <= 32:
            return False, f"ShellExecuteW devolvio codigo {code}"
        return True, f"ShellExecuteW devolvio codigo {code}"

    def _read_office_source_product_ids(self, source_path):
        metadata_path = os.path.join(source_path, "Office", "Data", "C2RFireFlyData.xml")
        if not os.path.isfile(metadata_path):
            return set()
        try:
            with open(metadata_path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
        except Exception:
            return set()
        return {match.lower() for match in re.findall(r'<PRId\s+name="([^"]+)"', content, flags=re.IGNORECASE)}

    def _select_office_product(self, product_ids):
        for product_id, channel, label in self.OFFICE_PRODUCTS:
            if not product_ids or product_id.lower() in product_ids:
                return product_id, channel, label
        return "", "", ""

    def _select_skype_product(self, product_ids):
        for product_id, label in self.SKYPE_PRODUCTS:
            if not product_ids or product_id.lower() in product_ids:
                return product_id, label
        return "", ""

    def _write_office_skype_configuration(self, source_path, office_product, skype_product, channel):
        config_dir = os.path.join(SysUtils.app_data_dir(), "office_skype")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "configuration_office_skype.xml")
        source = escape(os.path.abspath(source_path))
        channel_attr = f' Channel="{escape(channel)}"' if channel else ""
        xml = (
            '<Configuration>\n'
            f'  <Add OfficeClientEdition="64"{channel_attr} SourcePath="{source}" AllowCdnFallback="FALSE">\n'
            f'    <Product ID="{escape(office_product)}">\n'
            '      <Language ID="es-es" />\n'
            '    </Product>\n'
            f'    <Product ID="{escape(skype_product)}">\n'
            '      <Language ID="es-es" />\n'
            '    </Product>\n'
            '  </Add>\n'
            '  <RemoveMSI />\n'
            '  <Updates Enabled="FALSE" />\n'
            '  <Display Level="Full" AcceptEULA="TRUE" />\n'
            '</Configuration>\n'
        )
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write(xml)
        return config_path

    def _existing_office_click_to_run_state(self):
        script = r"""
        $paths = @(
            'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Office\ClickToRun\Configuration'
        )
        foreach ($path in $paths) {
            if (Test-Path $path) {
                $item = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue
                if ($item) {
                    "PLATFORM=$($item.Platform)"
                    "PRODUCTS=$($item.ProductReleaseIds)"
                    exit 0
                }
            }
        }
        "PLATFORM="
        "PRODUCTS="
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=10)
        if not ok:
            return "", ""
        data = {}
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip().upper()] = value.strip()
        return data.get("PLATFORM", ""), data.get("PRODUCTS", "")

    def _run_other_installer(self, program_name, patterns):
        print(f"Buscando instalador de {program_name} en la carpeta OTROS...")
        installer_path = self._find_other_installer(patterns)
        if not installer_path:
            checked = "\n".join(f"- {path}" for path in self._other_installers_roots())
            self._notify_task_error(
                program_name,
                "No se ha encontrado el instalador.\n\n"
                "Rutas comprobadas:\n"
                f"{checked}",
            )
            return

        print(f"[OK] Instalador encontrado: {installer_path}")
        self.update_progress(25)
        print(f"Lanzando instalador de {program_name}...")

        try:
            process = subprocess.Popen(
                [installer_path],
                cwd=os.path.dirname(installer_path),
                creationflags=0,
            )
        except Exception as exc:
            self._notify_task_error(
                program_name,
                f"No se pudo abrir el instalador.\n\nDetalle: {exc}",
            )
            return

        self.update_progress(60)
        print("Completa el instalador. Easy Deploy esperara a que se cierre.")
        if self._wait_for_installer_process(process, program_name):
            self.update_progress(100)
            self._notify_task_info(
                program_name,
                f"El instalador de {program_name} ha finalizado o se ha cerrado correctamente.",
            )
        else:
            self.update_progress(100)
            self._notify_task_warning(
                program_name,
                f"El instalador de {program_name} se ha cancelado o no ha finalizado correctamente.",
            )
