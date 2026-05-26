import os
import shutil
import subprocess

from ..core.sysutils import SysUtils


class JchatTasksMixin:
    JCHAT_CLI_INSTALLER = "jchat-dist-package-windows-bundled-2.7.1.0.msi"

    def _is_java_installed(self):
        return (
            shutil.which("java") is not None
            or SysUtils.is_program_installed([
                "*Java 8*",
                "*Java(TM) SE Runtime*",
                "*Java SE Development Kit*",
                "*OpenJDK*",
                "*Eclipse Temurin*",
                "*Microsoft Build of OpenJDK*",
            ])
        )

    def _is_openfire_installed(self):
        return (
            SysUtils.is_service_installed("Openfire")
            or SysUtils.is_program_installed(["*Openfire*"])
        )

    def task_jchat(self):
        carpeta = self.payload_path("JCHAT")
        jre_installer = "jre-8u371-windows-x64.exe"
        openfire_installer = "openfire_4_7_5_x64.exe"

        print("=== INSTALADOR JCHAT / OPENFIRE ===")
        print(f"Buscando instaladores en {carpeta}...")

        if not os.path.exists(carpeta):
            self._notify_task_error(
                "JCHAT / Openfire",
                f"No se encuentra la carpeta de recursos JCHAT:\n\n{carpeta}\n\n"
                "Comprueba que la carpeta JCHAT exista dentro de los recursos de Easy Deploy.",
            )
            return

        self._warn_missing_files(carpeta, [jre_installer, openfire_installer], abort=False)

        java_installed = self._is_java_installed()
        openfire_installed = self._is_openfire_installed()

        if java_installed and openfire_installed:
            print("\n[OMITIDO] Java ya esta instalado. No se reinstala JRE.")
            print("[OMITIDO] Openfire ya esta instalado. No se reinstala.")
            self.update_progress(1.0)
            self.ui_showinfo(
                "JCHAT / Openfire",
                "Java y Openfire ya estan instalados.\n\n"
                "No se reinstalara ningun componente. Puedes continuar con otra tarea.",
            )
            print("\nInstalacion de JCHAT finalizada.")
            return

        if java_installed:
            print("\n[OMITIDO] Java ya esta instalado. No se reinstala JRE.")
            self.update_progress(0.5)
        else:
            jre_path = os.path.join(carpeta, jre_installer)
            if not os.path.exists(jre_path):
                print(f"[ERROR] No encuentro el instalador JRE en: {jre_path}")
                self._notify_task_warning(
                    "JCHAT / Openfire",
                    "No se encuentra el instalador de Java JRE.\n\n"
                    "Openfire puede fallar si Java no esta instalado. Easy Deploy te preguntara si quieres continuar de todas formas.",
                )
                if not self.ui_askyesno(
                    "Falta instalador",
                    "No encuentro el instalador de Java.\n\n"
                    "Quieres intentar instalar Openfire de todas formas?"
                ):
                    return
            else:
                print("\n>>> Iniciando instalador JRE puede tardar hasta 3 min")
                try:
                    process = subprocess.Popen([jre_path], creationflags=0)
                    if not self._wait_for_installer_process(process, "Java JRE"):
                        print("[AVISO] Instalacion de Java cancelada desde Easy Deploy.")
                        return
                    print("[OK] Instalador Java finalizado.")
                except Exception as exc:
                    print(f"[ERROR] No se pudo lanzar el instalador Java: {exc}")
                    self._notify_task_error(
                        "Java JRE",
                        f"No se pudo lanzar el instalador de Java.\n\nDetalle: {exc}",
                    )
                    return

            self.update_progress(0.5)

        if self.stop_event.is_set():
            return

        if self._is_openfire_installed():
            print("\n[OMITIDO] Openfire ya esta instalado. No se reinstala.")
            self.update_progress(1.0)
            self.ui_showinfo(
                "JCHAT / Openfire",
                "Openfire ya parece instalado.\n\n"
                "No se reinstala Openfire. Si Java tambien estaba presente, no se ha instalado ningun componente.",
            )
            print("\nInstalacion de JCHAT finalizada.")
            return

        openfire_path = os.path.join(carpeta, openfire_installer)
        if not os.path.exists(openfire_path):
            print(f"[ERROR] No encuentro el instalador Openfire en: {openfire_path}")
            self._notify_task_error(
                "Openfire",
                f"No se encuentra el instalador de Openfire:\n\n{openfire_path}\n\n"
                "Coloca openfire_4_7_5_x64.exe en la carpeta JCHAT y vuelve a intentarlo.",
            )
            self.update_progress(1.0)
            return

        print("\n>>> Iniciando instalador Openfire...")
        print("Completa la instalacion. Easy Deploy esperara a que se cierre el instalador.")
        try:
            process = subprocess.Popen([openfire_path], creationflags=0)
            if not self._wait_for_installer_process(process, "Openfire"):
                print("[AVISO] Instalacion de Openfire cancelada desde Easy Deploy.")
                return
            print("[OK] Instalador Openfire finalizado.")
        except Exception as exc:
            print(f"[ERROR] Error lanzando Openfire: {exc}")
            self._notify_task_error(
                "Openfire",
                f"No se pudo lanzar el instalador de Openfire.\n\nDetalle: {exc}",
            )
            return

        self.update_progress(1.0)
        print("\nInstalacion de JCHAT finalizada.")

    def task_jchat_cli(self):
        carpeta = self.payload_path("JCHAT")
        installer_path = os.path.join(carpeta, self.JCHAT_CLI_INSTALLER)

        print("=== INSTALADOR JCHAT CLI ===")
        print(f"Buscando instalador en {carpeta}...")
        print(f"Ruta esperada: {installer_path}")

        if not os.path.isdir(carpeta):
            print(f"[ERROR] No se encuentra la carpeta de recursos JCHAT: {carpeta}")
            self._notify_task_error(
                "JCHAT CLI",
                f"No se encuentra la carpeta de recursos JCHAT:\n\n{carpeta}\n\n"
                "Comprueba que la carpeta JCHAT exista dentro de los recursos de Easy Deploy.",
            )
            self.update_progress(1.0)
            return

        if not os.path.isfile(installer_path):
            print(f"[ERROR] No se encuentra el instalador JCHAT CLI en: {installer_path}")
            self._notify_task_error(
                "JCHAT CLI",
                f"No se encuentra el instalador JCHAT CLI:\n\n{installer_path}\n\n"
                f"Coloca {self.JCHAT_CLI_INSTALLER} en la carpeta JCHAT y vuelve a intentarlo.",
            )
            self.update_progress(1.0)
            return

        print(f"[OK] Instalador detectado: {installer_path}")
        print(f'Comando: msiexec.exe /i "{installer_path}"')
        self.update_progress(0.25)

        try:
            process = subprocess.Popen(
                ["msiexec.exe", "/i", installer_path],
                creationflags=0,
            )
            exit_code = process.wait()
        except Exception as exc:
            print(f"[ERROR] No se pudo lanzar el instalador JCHAT CLI: {exc}")
            self._notify_task_error(
                "JCHAT CLI",
                f"No se pudo lanzar el instalador JCHAT CLI.\n\nDetalle: {exc}",
            )
            self.update_progress(1.0)
            return

        print(f"Codigo de salida MSI: {exit_code}")
        self.update_progress(1.0)

        if exit_code == 0:
            print("[OK] JCHAT CLI instalado correctamente.")
            self.ui_showinfo(
                "JCHAT CLI",
                "JCHAT CLI se ha instalado correctamente.",
            )
        elif exit_code == 3010:
            print("[OK] JCHAT CLI instalado correctamente. Reinicio recomendado.")
            self.ui_showwarning(
                "JCHAT CLI",
                "JCHAT CLI se ha instalado correctamente.\n\n"
                "El instalador recomienda reiniciar el equipo.",
            )
        else:
            print(f"[ERROR] Instalacion cancelada o fallida. Codigo MSI: {exit_code}")
            self._notify_task_error(
                "JCHAT CLI",
                "La instalacion de JCHAT CLI no se ha completado.\n\n"
                f"Codigo MSI: {exit_code}",
            )
