import os
import subprocess
import time

from ..core.sysutils import SysUtils


class SharePointTasksMixin:
    APPFABRIC_INSTALLER = "11-WindowsServerAppFabricSetup_x64.exe"
    APPFABRIC_CU7_INSTALLER = "AppFabric-KB3092423-x64-ENU.exe"
    LEGACY_APPFABRIC_CU1_INSTALLER = "12-AppFabric1.1-RTM-KB2671763-x64-ENU.exe"

    WCFDATASERVICES56_INSTALLER = "2-WcfDataServices.exe"
    WCFDATASERVICES56_FALLBACK_INSTALLER = "3-WcfDataServices 5 ov3.exe"

    SHAREPOINT_2019_REQUIRED_INSTALLERS = [
        "1-sqlncli 2012 sp4.msi",
        "5-Synchronization.msi",
        APPFABRIC_INSTALLER,
        "6-MicrosoftIdentityExtensions-64.msi",
        "4-setup_msipc_x64.exe",
        WCFDATASERVICES56_INSTALLER,
        "7-NDP472-KB4054530-x86-x64-AllOS-ENU.exe",
        APPFABRIC_CU7_INSTALLER,
        "8-vcredist_x64_2012.exe",
        "9-vcredist_x64_2015.exe",
    ]

    SHAREPOINT_2019_UNUSED_INSTALLERS = [
        WCFDATASERVICES56_FALLBACK_INSTALLER,
        "10-WIN-SRVR-APPFabric.txt",
        LEGACY_APPFABRIC_CU1_INSTALLER,
        "13-sqlncli.msi",
    ]

    def _prepare_sharepoint_prereq_environment(self, folder):
        print("[PRE-CHECK] Desbloqueando instaladores locales de SharePoint...")
        unblock_script = f"""
        $folder = {SysUtils.ps_quote(folder)}
        if (Test-Path -LiteralPath $folder) {{
            Get-ChildItem -LiteralPath $folder -File -Recurse -ErrorAction SilentlyContinue |
                ForEach-Object {{
                    Unblock-File -LiteralPath $_.FullName -ErrorAction SilentlyContinue
                }}
        }}
        'OK'
        """
        ok, output = SysUtils.run_powershell(unblock_script, capture=True, timeout=60)
        if ok:
            print("[OK] Recursos locales desbloqueados para evitar marca Zone.Identifier.")
        else:
            print(f"[AVISO] No se pudieron desbloquear todos los recursos: {output.strip()}")

        print("[PRE-CHECK] Habilitando Windows Script Host para instaladores AppFabric...")
        wsh_script = r"""
        $paths = @(
            'HKCU:\Software\Microsoft\Windows Script Host\Settings',
            'HKLM:\Software\Microsoft\Windows Script Host\Settings'
        )
        foreach ($path in $paths) {
            if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
            New-ItemProperty -Path $path -Name Enabled -PropertyType DWord -Value 1 -Force | Out-Null
        }
        'OK'
        """
        ok, output = SysUtils.run_powershell(wsh_script, capture=True, timeout=20)
        if ok:
            print("[OK] Windows Script Host habilitado en HKCU/HKLM.")
        else:
            print(f"[AVISO] No se pudo confirmar Windows Script Host: {output.strip()}")

    def _find_sharepoint_file(self, folder, exact_name, contains=None):
        exact_path = os.path.join(folder, exact_name)
        if os.path.exists(exact_path):
            return exact_path

        tokens = [str(token).lower() for token in (contains or []) if str(token).strip()]
        if not tokens:
            return ""

        try:
            for name in os.listdir(folder):
                lower = name.lower()
                if lower.endswith((".exe", ".msi")) and all(token in lower for token in tokens):
                    return os.path.join(folder, name)
        except Exception:
            return ""

        return ""

    def _warn_unused_sharepoint_files(self, folder):
        found = [
            name for name in self.SHAREPOINT_2019_UNUSED_INSTALLERS
            if os.path.exists(os.path.join(folder, name))
        ]

        if not found:
            return

        print("[AVISO] Se han detectado archivos que Easy Deploy no usara como prerrequisitos principales:")
        for name in found:
            print(f"  - {name}")

        if self.LEGACY_APPFABRIC_CU1_INSTALLER in found:
            print("[AVISO] KB2671763 es AppFabric CU1 antiguo. Para SharePoint 2019 se usa KB3092423 CU7.")

    def _remove_sharepoint_prereq_startup_loop(self):
        script = r"""
        $paths = @(
            "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\SharePointServerPreparationToolStartup_0FF1CE14-0000-0000-0000-000000000000.cmd",
            "$env:AppData\Microsoft\Windows\Start Menu\Programs\Startup\SharePointServerPreparationToolStartup_0FF1CE14-0000-0000-0000-000000000000.cmd"
        )

        foreach ($path in $paths) {
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
                "REMOVED: $path"
            }
        }

        'OK'
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=20)
        if ok and output.strip():
            print(output.strip())

    def _appfabric_cu7_path(self, folder):
        return self._find_sharepoint_file(
            folder,
            self.APPFABRIC_CU7_INSTALLER,
            ["kb3092423", "x64"],
        )

    def _wcf_data_services56_path(self, folder):
        primary = self._find_sharepoint_file(
            folder,
            self.WCFDATASERVICES56_INSTALLER,
            ["wcf", "data", "services"],
        )
        if primary:
            return primary

        return self._find_sharepoint_file(
            folder,
            self.WCFDATASERVICES56_FALLBACK_INSTALLER,
            ["wcf", "data", "services"],
        )

    def _is_appfabric_sharepoint_ready(self):
        script = r"""
        $product = $false

        $paths = @(
            'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
        )

        foreach ($path in $paths) {
            Get-ItemProperty $path -ErrorAction SilentlyContinue | ForEach-Object {
                if ([string]$_.DisplayName -like '*Windows Server AppFabric*') {
                    $product = $true
                }
            }
        }

        $service = Get-Service -Name AppFabricCachingService -ErrorAction SilentlyContinue

        $moduleCandidates = @(
            (Join-Path $env:ProgramFiles 'AppFabric 1.1 for Windows Server\PowershellModules\DistributedCacheAdministration'),
            (Join-Path $env:ProgramFiles 'AppFabric 1.1 for Windows Server\PowershellModules\DistributedCacheAdministration\DistributedCacheAdministration.psd1'),
            (Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\Modules\DistributedCacheAdministration')
        )

        $module = $moduleCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

        $clientCandidates = @(
            (Join-Path $env:ProgramFiles 'AppFabric 1.1 for Windows Server\Microsoft.ApplicationServer.Caching.Client.dll'),
            (Join-Path $env:WINDIR 'Microsoft.NET\assembly\GAC_MSIL\Microsoft.ApplicationServer.Caching.Client')
        )

        $client = $clientCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

        if ($product -and $service -and $module -and $client) {
            'True'
        } else {
            'False'
        }
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=20)
        return ok and output.strip().splitlines()[-1:] == ["True"]

    def _is_appfabric_base_present(self):
        if SysUtils.is_program_installed(["*Windows Server AppFabric*"]):
            return True

        if SysUtils.is_service_installed("AppFabricCachingService"):
            return True

        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        appfabric_dir = os.path.join(program_files, "AppFabric 1.1 for Windows Server")
        if os.path.exists(appfabric_dir):
            return True

        script = r"""
        $checks = @()
        $checks += Test-Path 'HKLM:\SOFTWARE\Microsoft\AppFabric\V1.0'
        $checks += Test-Path 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\AppFabric\V1.0'

        if ($checks -contains $true) {
            'True'
        } else {
            'False'
        }
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=15)
        return ok and output.strip().splitlines()[-1:] == ["True"]

    def _is_appfabric_installed_but_not_ready(self):
        return self._is_appfabric_base_present() and not self._is_appfabric_sharepoint_ready()

    def _is_appfabric_cu7_installed(self):
        if SysUtils.is_hotfix_installed("KB3092423") or SysUtils.is_program_installed(["*KB3092423*"]):
            return True

        script = r"""
        $paths = @(
            'HKLM:\SOFTWARE\Microsoft\Updates\AppFabric 1.1 for Windows Server\KB3092423',
            'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Updates\AppFabric 1.1 for Windows Server\KB3092423'
        )

        foreach ($path in $paths) {
            if (Test-Path $path) {
                'True'
                exit 0
            }
        }

        'False'
        """
        ok, output = SysUtils.run_powershell(script, capture=True, timeout=15)
        return ok and output.strip().splitlines()[-1:] == ["True"]

    def _warn_missing_appfabric_cu7_file(self, folder):
        if self._appfabric_cu7_path(folder):
            return False

        legacy_path = os.path.join(folder, self.LEGACY_APPFABRIC_CU1_INSTALLER)
        legacy_note = ""

        if os.path.exists(legacy_path):
            legacy_note = (
                "\n\nSe ha detectado el archivo antiguo "
                f"'{self.LEGACY_APPFABRIC_CU1_INSTALLER}', pero ese es CU1/KB2671763. "
                "Para SharePoint 2019 se requiere CU7/KB3092423."
            )
            print(f"[ERROR] {self.LEGACY_APPFABRIC_CU1_INSTALLER} no sirve para SharePoint 2019. Falta KB3092423.")

        message = (
            "Falta el prerrequisito correcto de AppFabric para SharePoint 2019:\n\n"
            f"{self.APPFABRIC_CU7_INSTALLER}\n\n"
            "Coloca el paquete CU7 de AppFabric 1.1, KB3092423 x64, en la carpeta SHAPRE."
            f"{legacy_note}\n\n"
            "Easy Deploy no lanzara el instalador final de SharePoint hasta que AppFabric y CU7 esten instalados."
        )

        print("[ERROR] Falta AppFabric CU7 KB3092423 en la carpeta SHAPRE.")
        self.ui_showwarning("AppFabric CU7 requerido", message)
        return True

    def _sharepoint_prerequisite_installer_args(self, folder):
        exe_path = os.path.join(folder, "PrerequisiteInstaller.exe")

        required = [
            ("SQLNCli", "1-sqlncli 2012 sp4.msi", None),
            ("Sync", "5-Synchronization.msi", None),
            ("AppFabric", self.APPFABRIC_INSTALLER, None),
            ("IDFX11", "6-MicrosoftIdentityExtensions-64.msi", None),
            ("MSIPCClient", "4-setup_msipc_x64.exe", None),
            ("WCFDataServices56", self.WCFDATASERVICES56_INSTALLER, ["wcf", "data", "services"]),
            ("DotNet472", "7-NDP472-KB4054530-x86-x64-AllOS-ENU.exe", None),
            ("KB3092423", self.APPFABRIC_CU7_INSTALLER, ["kb3092423", "x64"]),
            ("MSVCRT11", "8-vcredist_x64_2012.exe", None),
            ("MSVCRT141", "9-vcredist_x64_2015.exe", None),
        ]

        args = [exe_path]
        missing = []

        for option, filename, tokens in required:
            if option == "WCFDataServices56":
                path = self._wcf_data_services56_path(folder)
            elif option == "KB3092423":
                path = self._appfabric_cu7_path(folder)
            else:
                path = self._find_sharepoint_file(folder, filename, tokens)

            if not path:
                missing.append(filename)
                continue

            args.append(f"/{option}:{path}")

        return args, missing

    def _install_sqlncli2012(self, full_path):
        if SysUtils.is_program_installed([
            "*SQL Server 2012 Native Client*",
            "*Microsoft SQL Server 2012 Native Client*",
        ]):
            print("   [OMITIDO] SQL Server 2012 Native Client ya esta instalado.")
            return 0

        log_path = os.path.join(
            os.environ.get("TEMP", os.path.dirname(full_path)),
            "EasyDeploy_sqlncli2012.log",
        )

        print("   Instalando SQL Server 2012 Native Client SP4 con aceptacion de licencia...")
        print(f"   Log MSI: {log_path}")

        result = subprocess.run(
            [
                "msiexec",
                "/i",
                full_path,
                "/qn",
                "/norestart",
                "IACCEPTSQLNCLILICENSETERMS=YES",
                "/L*v",
                log_path,
            ],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode not in (0, 3010) and SysUtils.is_program_installed([
            "*SQL Server 2012 Native Client*",
            "*Microsoft SQL Server 2012 Native Client*",
        ]):
            print("   [AVISO] SQL Native Client devolvio error, pero aparece instalado. Se continua.")
            return 0

        return result.returncode

    def _install_wcf_data_services56(self, full_path):
        if SysUtils.is_program_installed([
            "*WCF Data Services 5.6*",
            "*WCF Data Services 5.6.0 Runtime*",
            "*Microsoft WCF Data Services*",
        ]):
            print("   [OMITIDO] WCF Data Services 5.6 ya esta instalado.")
            return 0

        print("   Instalando Microsoft WCF Data Services 5.6...")
        result = subprocess.run(
            [full_path, "/quiet", "/norestart"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        return result.returncode

    def _install_appfabric_for_sharepoint(self, full_path):
        if self._is_appfabric_sharepoint_ready():
            print("   [OMITIDO] Windows Server AppFabric ya esta instalado con los componentes requeridos.")
            return 0

        if self._is_appfabric_base_present():
            print("   [OMITIDO] Windows Server AppFabric base ya aparece instalado.")
            print("            No se repite el instalador para evitar bucle 2359302/reinicio.")
            print("            Se continuara con AppFabric CU7 y PrerequisiteInstaller hara la validacion final.")
            return 0

        args = [
            full_path,
            "/i",
            "CacheClient,CachingService,CacheAdmin",
            "/gac",
        ]

        print("   Instalando AppFabric con los parametros requeridos por SharePoint...")
        print("   Comando: 11-WindowsServerAppFabricSetup_x64.exe /i CacheClient,CachingService,CacheAdmin /gac")

        process = subprocess.Popen(args, creationflags=0)

        if not self._wait_for_installer_process(process, "Windows Server AppFabric"):
            return process.returncode if process.returncode is not None else 1

        result_code = process.returncode

        if result_code == 2359302:
            if self._is_appfabric_base_present():
                print("   [OK] AppFabric ya aparece registrado en el sistema. Se continua sin repetir el instalador.")
                return 0

            if SysUtils.is_reboot_pending():
                print("   [INFO] AppFabric devuelve 2359302 y Windows indica reinicio pendiente.")
                return 3010

        if result_code in (0, 3010):
            if result_code == 3010:
                print("   [INFO] AppFabric requiere reinicio.")
                return 3010

            if SysUtils.is_reboot_pending() and not self._is_appfabric_base_present():
                print("   [INFO] AppFabric requiere reinicio antes de continuar.")
                return 3010

            if not self._is_appfabric_sharepoint_ready():
                if self._is_appfabric_base_present():
                    print("   [AVISO] AppFabric base aparece instalado, pero la comprobacion estricta no lo confirma.")
                    print("           Se continua para evitar reinstalacion/bucle.")
                    return 0

                print("   [AVISO] AppFabric termino, pero no se han confirmado sus componentes.")
                return 3010

            return result_code

        print(f"   [ERROR] AppFabric finalizo con codigo: {result_code}")
        return result_code

    def _install_appfabric_cu7(self, full_path):
        if self._is_appfabric_cu7_installed():
            print("   [OMITIDO] AppFabric CU7 KB3092423 ya esta instalado.")
            return 0

        if not self._is_appfabric_base_present():
            print("   [ERROR] No se instala CU7 porque AppFabric base no aparece instalado.")
            return 1603

        if not self._is_appfabric_sharepoint_ready():
            print("   [AVISO] AppFabric base aparece instalado, pero la comprobacion estricta no lo confirma.")
            print("           Se intentara instalar CU7 de todas formas; el instalador oficial validara el estado real.")

        print("   Instalando AppFabric CU7 KB3092423...")
        result = subprocess.run(
            [full_path, "/quiet", "/norestart"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode == 2359302:
            print("   [OK] AppFabric CU7 indica que ya estaba instalado.")
            return 0

        return result.returncode

    def _sharepoint_needs_restart(self, output=""):
        text = str(output or "").lower()

        markers = (
            "restart needed",
            "you must restart",
            "restart is pending",
            "pending restart",
            "reinicio pendiente",
            "requiere reiniciar",
        )

        return any(marker in text for marker in markers) or SysUtils.is_reboot_pending()

    def _notify_sharepoint_restart(self, title="Reinicio requerido"):
        self.console_finish_state = "restart"
        print("[AVISO] SharePoint/AppFabric requiere reiniciar el servidor antes de continuar.")

        self.ui_showwarning(
            title,
            "Windows ha indicado que hay un reinicio pendiente.\n\n"
            "Reinicia el servidor antes de continuar con SharePoint para evitar instalaciones incompletas. "
            "El boton Reiniciar sistema aparece abajo en Easy Deploy.",
        )

    def _is_sharepoint_installed(self):
        return (
            SysUtils.is_service_installed("SPTimerV4")
            or SysUtils.is_program_installed([
                "*Microsoft SharePoint Server*",
                "*SharePoint Server*",
            ])
        )

    def _sharepoint_prereq_checks(self):
        return {
            "1-sqlncli 2012 sp4.msi": (
                "SQL Server 2012 Native Client SP4",
                lambda: SysUtils.is_program_installed([
                    "*SQL Server 2012 Native Client*",
                    "*Microsoft SQL Server 2012 Native Client*",
                ]),
            ),
            "5-Synchronization.msi": (
                "Microsoft Sync Framework Runtime",
                lambda: SysUtils.is_program_installed([
                    "*Sync Framework*Runtime*",
                    "*Microsoft Sync Framework*",
                ]),
            ),
            self.APPFABRIC_INSTALLER: (
                "Windows Server AppFabric 1.1 base",
                self._is_appfabric_base_present,
            ),
            "6-MicrosoftIdentityExtensions-64.msi": (
                "Microsoft Identity Extensions",
                lambda: SysUtils.is_program_installed([
                    "*Microsoft Identity Extensions*",
                ]),
            ),
            "4-setup_msipc_x64.exe": (
                "Microsoft Information Protection/RMS Client",
                lambda: SysUtils.is_program_installed([
                    "*Microsoft Information Protection*",
                    "*Rights Management Services Client*",
                    "*MSIPC*",
                ]),
            ),
            self.WCFDATASERVICES56_INSTALLER: (
                "WCF Data Services 5.6.0 Runtime",
                lambda: SysUtils.is_program_installed([
                    "*WCF Data Services 5.6*",
                    "*WCF Data Services 5.6.0 Runtime*",
                    "*Microsoft WCF Data Services*",
                ]),
            ),
            "7-NDP472-KB4054530-x86-x64-AllOS-ENU.exe": (
                ".NET Framework 4.7.2 o superior",
                lambda: SysUtils.is_dotnet_release_at_least(461808),
            ),
            self.APPFABRIC_CU7_INSTALLER: (
                "Actualizacion AppFabric 1.1 CU7 KB3092423",
                self._is_appfabric_cu7_installed,
            ),
            "8-vcredist_x64_2012.exe": (
                "Microsoft Visual C++ 2012 Redistributable x64",
                lambda: SysUtils.is_program_installed([
                    "*Microsoft Visual C++ 2012*Redistributable*x64*",
                    "*Microsoft Visual C++ 2012*x64*",
                ]),
            ),
            "9-vcredist_x64_2015.exe": (
                "Microsoft Visual C++ 2017/2015-2022 Redistributable x64",
                lambda: SysUtils.is_program_installed([
                    "*Microsoft Visual C++ 2017*Redistributable*x64*",
                    "*Microsoft Visual C++ 2015-2022*Redistributable*x64*",
                    "*Microsoft Visual C++ 2015-2019*Redistributable*x64*",
                    "*Microsoft Visual C++ 2015*Redistributable*x64*",
                ]),
            ),
        }

    def task_sp_roles(self):
        if not self._require_windows_server(
            "SharePoint roles",
            "Los roles de IIS, MSMQ, WIF y caracteristicas de servidor no existen en Windows cliente.",
        ):
            return

        all_feats = [
            "Web-Server",
            "Web-Mgmt-Console",
            "NET-Framework-45-Features",
            "NET-Framework-45-ASPNET",
            "NET-WCF-Services45",
            "NET-WCF-HTTP-Activation45",
            "NET-WCF-MSMQ-Activation45",
            "NET-WCF-Pipe-Activation45",
            "NET-WCF-TCP-Activation45",
            "MSMQ-Server",
            "Web-Mgmt-Compat",
            "Web-Metabase",
            "Web-Lgcy-Scripting",
            "Web-Lgcy-Mgmt-Console",
            "Windows-Identity-Foundation",
            "Web-ASP",
            "Web-IP-Security",
            "Web-Url-Auth",
            "Web-Windows-Auth",
            "Web-Scripting-Tools",
            "Wireless-Networking",
            "Xps-Viewer",
        ]

        print("=== ROLES SHAREPOINT ===")
        print("Comprobando caracteristicas pendientes...")

        missing_feats = SysUtils.missing_windows_features(all_feats)

        for feature in all_feats:
            if feature in missing_feats:
                print(f" [FALTA] {feature}")
            else:
                print(f" [OMITIDO] Ya instalado: {feature}")

        if self.stop_event.is_set():
            return

        if not missing_feats:
            self.update_progress(1.0)
            print("\n[OK] Todos los roles ya estaban instalados.")
            self.ui_showinfo(
                "Roles SharePoint",
                "Todos los roles y caracteristicas necesarios para SharePoint ya estaban instalados.",
            )
            return

        source_path = SysUtils.find_sxs_source()
        source_arg = f" -Source {SysUtils.ps_quote(source_path)}" if source_path else ""

        if source_path:
            print(f"Origen SxS detectado: {source_path}")
        else:
            print("[AVISO] No se encontro Sources\\SxS. Windows usara Windows Update u origen configurado.")

        print(f"\nInstalando {len(missing_feats)} roles pendientes...")

        cmd = (
            f"Install-WindowsFeature -Name {','.join(missing_feats)}"
            f"{source_arg} -IncludeManagementTools -Restart:$false"
        )

        ok, output = SysUtils.run_powershell(cmd, capture=True)

        if ok:
            print("\n[OK] Roles instalados correctamente.")
            if output.strip():
                print(output.strip())

            if self._sharepoint_needs_restart(output):
                self._notify_sharepoint_restart("Roles SharePoint")
        else:
            print("\n[ERROR] Hubo un problema instalando roles SharePoint.")
            print(output.strip())
            self._notify_task_error(
                "Roles SharePoint",
                "No se han podido instalar todos los roles y caracteristicas de SharePoint.\n\n"
                "Revisa si Windows puede instalar Features, si hay origen SxS disponible y si hay reinicio pendiente. "
                "El detalle queda en el log.",
            )

        self.update_progress(1.0)
        print("\nPROCESO DE ROLES FINALIZADO.")

    def task_sp_prereqs(self):
        if not self._require_windows_server(
            "SharePoint prerrequisitos",
            "Los prerrequisitos de SharePoint 2019 deben ejecutarse sobre Windows Server.",
        ):
            return

        if self._is_sharepoint_installed():
            print("[OK] SharePoint ya parece instalado. Se omiten prerrequisitos e imagen final.")
            self.update_progress(1.0)
            self.ui_showinfo(
                "SharePoint",
                "SharePoint ya parece instalado.\n\n"
                "No se reinstalan prerrequisitos ni se monta de nuevo la imagen.",
            )
            return

        SysUtils.ensure_windows_update_running()

        carpeta = self.payload_path("SHAPRE")
        instaladores = list(self.SHAREPOINT_2019_REQUIRED_INSTALLERS)
        img_office = "officeserver.img"

        print("=== PRERREQUISITOS SHAREPOINT 2019 ===")

        if not os.path.exists(carpeta):
            self._notify_task_error(
                "SharePoint",
                f"No se encuentra la carpeta de recursos de SharePoint:\n\n{carpeta}\n\n"
                "Comprueba que la carpeta SHAPRE exista dentro de los recursos de Easy Deploy.",
            )
            return

        self._prepare_sharepoint_prereq_environment(carpeta)
        self._remove_sharepoint_prereq_startup_loop()
        self._warn_unused_sharepoint_files(carpeta)

        self._warn_missing_files(
            carpeta,
            instaladores + ["PrerequisiteInstaller.exe", img_office],
            abort=False,
        )

        self._warn_missing_appfabric_cu7_file(carpeta)

        inicio = int(self.db.cargar("sp_step", 0))
        total = len(instaladores)

        if inicio < 0 or inicio >= total:
            inicio = 0
            self.db.guardar("sp_step", 0)

        print(f"Recuperando progreso desde paso: {inicio}")

        prereq_checks = self._sharepoint_prereq_checks()

        if inicio > 0:
            for check_idx, check_file in enumerate(instaladores[:inicio]):
                check_label, check_func = prereq_checks.get(check_file, (check_file, lambda: False))

                try:
                    still_missing = not bool(check_func())
                except Exception:
                    still_missing = False

                if still_missing:
                    print(
                        f"[INFO] El progreso guardado apuntaba al paso {inicio}, "
                        f"pero '{check_label}' aun no esta confirmado. Se reanuda desde el paso {check_idx}."
                    )
                    inicio = check_idx
                    self.db.guardar("sp_step", inicio)
                    break

        prereqs_changed = False
        restart_required = False

        for idx, archivo in enumerate(instaladores):
            if idx < inicio:
                continue

            if self.stop_event.is_set():
                self.db.guardar("sp_step", idx)
                print("Cancelado. Progreso guardado.")
                return

            full_path = os.path.join(carpeta, archivo)
            prereq_label, prereq_check = prereq_checks.get(archivo, (archivo, lambda: False))
            retry_current_after_restart = False

            print(f"\n>>> Procesando {archivo}...")

            try:
                already_installed = bool(prereq_check())
            except Exception:
                already_installed = False

            if already_installed:
                print(f"   [OMITIDO] {prereq_label} ya esta instalado.")
                self.db.guardar("sp_step", idx + 1)
                self.update_progress(0.9 * ((idx + 1) / total))
                continue

            if archivo == self.WCFDATASERVICES56_INSTALLER:
                detected = self._wcf_data_services56_path(carpeta)
                if detected:
                    full_path = detected

            if archivo == self.APPFABRIC_CU7_INSTALLER:
                detected = self._appfabric_cu7_path(carpeta)
                if detected:
                    full_path = detected

            if not os.path.exists(full_path):
                self._notify_task_warning(
                    "Prerequisito SharePoint",
                    f"No se encuentra este prerrequisito:\n\n{full_path}\n\n"
                    "Easy Deploy saltara este paso, pero SharePoint podria bloquear la instalacion final si el componente es obligatorio.",
                )
                self.db.guardar("sp_step", idx + 1)
                self.update_progress(0.9 * ((idx + 1) / total))
                continue

            try:
                if archivo == "1-sqlncli 2012 sp4.msi":
                    result_code = self._install_sqlncli2012(full_path)

                elif archivo == self.APPFABRIC_INSTALLER:
                    result_code = self._install_appfabric_for_sharepoint(full_path)

                elif archivo == self.APPFABRIC_CU7_INSTALLER:
                    result_code = self._install_appfabric_cu7(full_path)

                elif archivo == self.WCFDATASERVICES56_INSTALLER:
                    result_code = self._install_wcf_data_services56(full_path)

                elif archivo.endswith(".msi"):
                    print("   Ejecucion silenciosa MSI...")
                    result = subprocess.run(
                        ["msiexec", "/i", full_path, "/qn", "/norestart"],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    result_code = result.returncode

                elif archivo.endswith(".exe"):
                    print("   Ejecucion silenciosa EXE...")
                    result = subprocess.run(
                        [full_path, "/quiet", "/norestart"],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    result_code = result.returncode

                else:
                    print(f"   [AVISO] Tipo de archivo desconocido. Saltando: {archivo}")
                    result_code = 0

                if result_code in (0, 3010, 2359302):
                    prereqs_changed = True

                    if result_code == 3010:
                        restart_required = True

                    if result_code == 2359302:
                        print("   [OK] El instalador indica que el componente/update ya estaba instalado. Se continua.")
                    else:
                        print("   [OK] Instalacion finalizada.")

                else:
                    display_code = "4294967295 (0xFFFFFFFF / -1)" if result_code == 4294967295 else result_code
                    print(f"   [AVISO] Instalador finalizo con codigo: {display_code}")

                    if SysUtils.is_reboot_pending() and result_code != 2359302:
                        restart_required = True
                        retry_current_after_restart = True
                        print("   [INFO] Hay reinicio pendiente. Este prerrequisito se repetira despues de reiniciar.")

            except Exception as exc:
                print(f"   [ERROR] Error ejecutando instalador: {exc}")
                self._notify_task_error(
                    "Prerequisito SharePoint",
                    f"No se pudo ejecutar el instalador:\n\n{archivo}\n\nDetalle: {exc}",
                )

            time.sleep(1)

            if restart_required:
                self.db.guardar("sp_step", idx if retry_current_after_restart else idx + 1)
                self.update_progress(1.0)
                self._notify_sharepoint_restart("Prerrequisitos SharePoint")
                return

            self.db.guardar("sp_step", idx + 1)
            self.update_progress(0.9 * ((idx + 1) / total))

        self.db.guardar("sp_step", 0)

        print("\n=== PRERREQUISITOS SHAREPOINT REVISADOS ===")

        critical_missing = []

        if not self._is_appfabric_base_present():
            critical_missing.append("Windows Server AppFabric 1.1 base")

        if not self._is_appfabric_cu7_installed():
            critical_missing.append("Cumulative Update 7 de AppFabric 1.1, KB3092423")

        if critical_missing:
            print("[AVISO] Faltan prerrequisitos criticos o Easy Deploy no puede confirmarlos:")
            for missing_name in critical_missing:
                print(f"  - {missing_name}")

            print("[INFO] Se permitira ejecutar PrerequisiteInstaller.exe con rutas locales para validacion oficial.")

        prereq_installer_path = os.path.join(carpeta, "PrerequisiteInstaller.exe")

        if os.path.exists(prereq_installer_path):
            if self.ui_askyesno(
                "PrerequisiteInstaller",
                "Los prerrequisitos locales ya han sido revisados.\n\n"
                "Quieres arrancar PrerequisiteInstaller.exe con rutas locales para que SharePoint valide el estado?",
            ):
                args, missing_local = self._sharepoint_prerequisite_installer_args(carpeta)

                if missing_local:
                    print("[AVISO] No se arranca PrerequisiteInstaller.exe porque faltan recursos locales:")
                    for missing_name in missing_local:
                        print(f"  - {missing_name}")

                    self.ui_showwarning(
                        "PrerequisiteInstaller",
                        "No se arranca PrerequisiteInstaller.exe para evitar descargas fallidas.\n\n"
                        "Faltan estos recursos locales:\n\n"
                        + "\n".join(f"- {name}" for name in missing_local),
                    )
                else:
                    self._remove_sharepoint_prereq_startup_loop()

                    print("Iniciando PrerequisiteInstaller.exe con rutas locales...")
                    print("Comando: " + " ".join(f'"{arg}"' if " " in arg else arg for arg in args))

                    try:
                        process = subprocess.Popen(args, creationflags=0)

                        if not self._wait_for_installer_process(process, "PrerequisiteInstaller"):
                            print("[AVISO] PrerequisiteInstaller cancelado desde Easy Deploy.")
                            return

                        print("[OK] PrerequisiteInstaller finalizado.")
                        self._remove_sharepoint_prereq_startup_loop()

                        if process.returncode == 3010:
                            restart_required = True

                    except Exception as exc:
                        print(f"[ERROR] Error al iniciar PrerequisiteInstaller.exe: {exc}")
                        self._notify_task_error(
                            "PrerequisiteInstaller",
                            f"No se pudo iniciar PrerequisiteInstaller.exe.\n\nDetalle: {exc}",
                        )
            else:
                print("Omision de PrerequisiteInstaller.exe por parte del usuario.")
        else:
            print(f"[AVISO] PrerequisiteInstaller.exe no encontrado en {carpeta}.")

        if self.stop_event.is_set():
            return

        if restart_required:
            self.update_progress(1.0)
            self._notify_sharepoint_restart("Prerrequisitos SharePoint")
            return

        if not self._is_appfabric_cu7_installed():
            print("[ERROR] No se lanzara SharePoint porque falta AppFabric CU7 KB3092423.")
            self.update_progress(1.0)
            self.ui_showwarning(
                "SharePoint bloqueado",
                "No se lanzara el instalador final de SharePoint porque falta:\n\n"
                "- AppFabric CU7 KB3092423\n\n"
                "Comprueba que AppFabric-KB3092423-x64-ENU.exe esta en SHAPRE y vuelve a ejecutar los prerrequisitos.",
            )
            return

        if self._is_sharepoint_installed():
            print("[OK] SharePoint ya esta instalado. No se monta de nuevo la imagen final.")
            self.update_progress(1.0)
            self.ui_showinfo(
                "SharePoint",
                "SharePoint ya esta instalado.\n\n"
                "No se monta de nuevo la imagen de instalacion.",
            )
            return

        print(f"\n>>> Paso final: Procesando imagen {img_office}")

        img_path = os.path.join(carpeta, img_office)
        mounted_image = ""

        if not os.path.exists(img_path):
            self._notify_task_error(
                "SharePoint",
                f"No se encuentra la imagen de SharePoint:\n\n{img_path}\n\n"
                "Coloca officeserver.img en la carpeta SHAPRE y vuelve a intentarlo.",
            )
            self.update_progress(1.0)
            return

        try:
            print("   Montando imagen IMG/ISO en Windows...")
            mounted, drive_or_error = SysUtils.mount_disk_image(img_path)

            if not mounted:
                self._notify_task_error(
                    "SharePoint",
                    "No se pudo montar la imagen de SharePoint automaticamente.\n\n"
                    f"Detalle: {drive_or_error}",
                )
                return

            mounted_image = img_path
            print(f"   [OK] Imagen montada en unidad [{drive_or_error}:]")

            setup_path = f"{drive_or_error}:\\setup.exe"

            if not os.path.exists(setup_path):
                self._notify_task_error(
                    "SharePoint",
                    f"La imagen se ha montado en {drive_or_error}: pero no se encuentra setup.exe.\n\n"
                    "Comprueba que la imagen corresponde a SharePoint Server.",
                )
                return

            print("   Lanzando instalador principal de SharePoint...")
            print("   Completa la instalacion. Easy Deploy NO extraera el CD/ISO hasta que pulses Aceptar.")

            process = subprocess.Popen([setup_path], creationflags=0)

            if not self._wait_for_media_installer_confirmation(process, "SharePoint Setup"):
                print("   [AVISO] Instalacion de SharePoint cancelada desde Easy Deploy.")
                return

            print("   [OK] Usuario confirmo fin/cancelacion del instalador de SharePoint.")

        except Exception as exc:
            print(f"   [ERROR] Fallo al gestionar la imagen: {exc}")
            self._notify_task_error(
                "SharePoint",
                f"Fallo al gestionar la imagen o lanzar el instalador.\n\nDetalle: {exc}",
            )

        finally:
            if mounted_image:
                reason = "cancelada" if self.stop_event.is_set() else "finalizada"
                self._dismount_task_media(mounted_image, reason, ask_user=False)

        self.update_progress(1.0)
        print("\nPROCESO DE PRERREQUISITOS FINALIZADO.")
        print("Es recomendable reiniciar el servidor si algun prerrequisito lo ha solicitado.")
