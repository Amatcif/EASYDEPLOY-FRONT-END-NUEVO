import os
import subprocess

from ..core.sysutils import SysUtils


class SqlTasksMixin:
    def _is_sql_server_installed(self):
        return (
            SysUtils.is_service_installed("MSSQLSERVER")
            or SysUtils.is_program_installed([
                "*Microsoft SQL Server 2022*",
                "*Microsoft SQL Server 2019*",
                "*Microsoft SQL Server 2017*",
                "*Microsoft SQL Server*Database Engine*",
            ])
        )

    def task_install_sql(self):
        carpeta = self.payload_path("SQL")
        instaladores = [
            ("msodbcsql.msi", "Microsoft ODBC Driver 17 for SQL Server", ["*Microsoft ODBC Driver*SQL Server*"]),
            ("msoledbsql.msi", "Microsoft OLE DB Driver for SQL Server", ["*Microsoft OLE DB Driver*SQL Server*"]),
            ("SSMS-Setup-ESN.exe", "Microsoft SQL Server Management Studio", ["*SQL Server Management Studio*"]),
        ]
        iso_sql = "SQLServer2022-x64-ENU.iso"

        print("=== INSTALADOR SQL SERVER ===")
        print(f"Ruta de trabajo: {carpeta}")

        if not os.path.exists(carpeta):
            self._notify_task_error(
                "SQL Server",
                f"No se encuentra la carpeta de recursos de SQL:\n\n{carpeta}\n\n"
                "Comprueba que la carpeta SQL exista dentro de los recursos de Easy Deploy.",
            )
            return
        self._warn_missing_files(carpeta, [archivo for archivo, _nombre, _patterns in instaladores] + [iso_sql], abort=False)

        total = len(instaladores) + 1

        for idx, (archivo, nombre_programa, patterns) in enumerate(instaladores):
            if self.stop_event.is_set():
                return

            print(f"\n>>> Paso {idx + 1}/{len(instaladores)}: Verificando {nombre_programa}...")

            if SysUtils.is_program_installed(patterns):
                print(f"   [OMITIDO] {nombre_programa} ya esta instalado.")
                self.update_progress((idx + 1) / total)
                continue

            full_path = os.path.join(carpeta, archivo)
            if not os.path.exists(full_path):
                self._notify_task_warning(
                    "Prerequisito SQL",
                    f"No se encuentra este instalador:\n\n{archivo}\n\n"
                    "Easy Deploy saltara este paso, pero SQL podria necesitarlo.",
                )
                self.update_progress((idx + 1) / total)
                continue

            print(f"   Iniciando instalador de {archivo}...")
            print("   Esperando a que completes la instalacion manual...")

            try:
                process = subprocess.Popen(["msiexec", "/i", full_path] if archivo.endswith(".msi") else [full_path], creationflags=0)
                if self._wait_for_installer_process(process, nombre_programa):
                    print("   [OK] Instalacion finalizada/cerrada.")
                else:
                    print("   [AVISO] Instalacion cancelada desde Easy Deploy.")
                    return
            except Exception as exc:
                print(f"   [ERROR] Fallo al ejecutar: {exc}")
                self._notify_task_error(
                    "SQL Server",
                    f"No se pudo ejecutar el instalador de {nombre_programa}.\n\nDetalle: {exc}",
                )

            self.update_progress((idx + 1) / total)

        if self.stop_event.is_set():
            return
        if self._is_sql_server_installed():
            print("[OK] SQL Server ya esta instalado. No se monta de nuevo la ISO principal.")
            self.update_progress(1)
            self.ui_showinfo(
                "SQL Server",
                "SQL Server ya parece instalado.\n\n"
                "No se monta de nuevo la ISO principal.",
            )
            return

        print(f"\n>>> Procesando ISO final: {iso_sql}")
        iso_path = os.path.join(carpeta, iso_sql)
        mounted_image = ""
        if not os.path.exists(iso_path):
            self._notify_task_error(
                "SQL Server",
                f"No se encuentra la ISO de SQL Server:\n\n{iso_path}\n\n"
                "Coloca SQLServer2022-x64-ENU.iso en la carpeta SQL y vuelve a intentarlo.",
            )
            return

        try:
            print("   Montando imagen ISO en Windows...")
            mounted, drive_or_error = SysUtils.mount_disk_image(iso_path)
            if not mounted:
                self._notify_task_error(
                    "SQL Server",
                    "No se pudo montar la ISO de SQL Server automaticamente.\n\n"
                    f"Detalle: {drive_or_error}",
                )
                return

            mounted_image = iso_path
            print(f"   [OK] ISO montada en unidad [{drive_or_error}:]")
            setup_path = f"{drive_or_error}:\\setup.exe"

            if not os.path.exists(setup_path):
                self._notify_task_error(
                    "SQL Server",
                    f"La ISO se ha montado en {drive_or_error}: pero no se encuentra setup.exe.\n\n"
                    "Comprueba que la ISO corresponde a SQL Server.",
                )
                return

            print(f"   Lanzando {setup_path}...")
            print("   Completa la instalacion. Easy Deploy NO extraera el CD/ISO hasta que pulses Aceptar.")
            process = subprocess.Popen([setup_path], creationflags=0)
            if not self._wait_for_media_installer_confirmation(process, "SQL Server Setup"):
                print("   [AVISO] Instalacion de SQL Server cancelada desde Easy Deploy.")
                return
            print("   [OK] Usuario confirmo fin/cancelacion del instalador de SQL Server.")
        except Exception as exc:
            print(f"   [ERROR] Fallo al gestionar la ISO: {exc}")
            self._notify_task_error(
                "SQL Server",
                f"Fallo al gestionar la ISO o lanzar el instalador.\n\nDetalle: {exc}",
            )
        finally:
            if mounted_image:
                reason = "cancelada" if self.stop_event.is_set() else "finalizada"
                self._dismount_task_media(mounted_image, reason, ask_user=False)

        self.update_progress(1)
        print("\n--- TAREA FINALIZADA ---")
