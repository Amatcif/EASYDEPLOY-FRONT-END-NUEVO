import os
import re
import subprocess
import time

from ..core.sysutils import SysUtils


class SystemTasksMixin:
    def pre_task_disable_windows_firewall(self):
        if not self.ui_askyesno(
            "Desactivar firewall",
            "Vas a desactivar Windows Firewall en los perfiles Domain, Private y Public.\n\n"
            "Esto puede dejar el equipo expuesto si esta conectado a una red no controlada.\n\n"
            "Quieres continuar?",
        ):
            return
        self.iniciar_tarea(self.task_disable_windows_firewall)

    def _set_windows_firewall_enabled(self, enabled):
        state_text = "activar" if enabled else "desactivar"
        final_text = "activado" if enabled else "desactivado"
        ps_value = "True" if enabled else "False"

        def refresh_firewall_tile():
            self._firewall_status = None
            if hasattr(self, "_update_firewall_tile_status"):
                self._update_firewall_tile_status()

        print(f"Iniciando tarea para {state_text} Windows Firewall en todos los perfiles...")
        self.update_progress(0.10)

        command = f"Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled {ps_value}"
        print(f"> Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled {ps_value}")
        ok, output = SysUtils.run_powershell(command, capture=True, timeout=60)
        if output.strip():
            print(output.strip())

        self.update_progress(0.55)
        if not ok:
            try:
                self.after(0, refresh_firewall_tile)
            except Exception:
                pass
            self._notify_task_error(
                "Windows Firewall",
                "No se pudo cambiar el estado de Windows Firewall.\n\n"
                "Revisa permisos de administrador, politicas de dominio o si el servicio Firewall esta disponible.",
            )
            self.update_progress(1)
            return

        status_command = "Get-NetFirewallProfile | Select-Object Name, Enabled"
        print("\nComprobando estado:")
        print("> " + status_command)
        status_ok, status_output = SysUtils.run_powershell(status_command, capture=True, timeout=30)
        if status_output.strip():
            print(status_output.strip())

        try:
            self.after(0, refresh_firewall_tile)
        except Exception:
            pass

        self.update_progress(1)
        if status_ok:
            self.ui_showinfo(
                "Windows Firewall",
                f"Windows Firewall ha quedado {final_text} en los perfiles Domain, Private y Public.\n\n"
                "El estado tambien queda registrado en la consola y en el log.",
            )
        else:
            self._notify_task_warning(
                "Windows Firewall",
                f"Se ha intentado dejar Windows Firewall {final_text}, pero no se pudo comprobar el estado final.\n\n"
                "Revisa la salida de la consola.",
            )

    def task_disable_windows_firewall(self):
        self._set_windows_firewall_enabled(False)

    def task_enable_windows_firewall(self):
        self._set_windows_firewall_enabled(True)

    def task_gpupdate_force(self):
        """Fuerza la actualización de políticas de grupo desde consola integrada."""
        print("Forzando actualización de políticas de grupo...")
        print("> gpupdate /force")
        self.update_progress(0.15)

        try:
            return_code, output = SysUtils.run_native_command(["cmd.exe", "/c", "gpupdate", "/force"], timeout=180)
            if output:
                print(output)
            self.update_progress(1)
            if return_code == 0:
                print("[OK] Políticas actualizadas correctamente.")
            else:
                print(f"[ERROR] gpupdate /force terminó con código {return_code}.")
        except subprocess.TimeoutExpired:
            self.update_progress(1)
            print("[ERROR] gpupdate /force agotó el tiempo de espera. Revisa conectividad con el controlador de dominio.")
        except Exception as exc:
            self.update_progress(1)
            print(f"[ERROR] No se pudo ejecutar gpupdate /force: {exc}")

    def task_time_sync(self):
        # --- AVISO NUEVO ---
        if not self.ui_askyesno(
            "Cambio de Zona Horaria", 
            "ATENCIÓN: Este proceso cambiará la configuración horaria a UTC (Coordinated Universal Time), "
            "establecerá España como región y aplicará formato de reloj 24 horas.\n\n"
            "¿Deseas continuar?"
        ):
            print("Sincronización cancelada por el usuario.")
            return
        # -------------------

        print("Iniciando sincronización de hora robusta...")

        # 1. Aseguramos primero la zona horaria (UTC)
        print("Ajustando zona a UTC...")
        subprocess.run(["tzutil", "/s", "UTC"], creationflags=subprocess.CREATE_NO_WINDOW)
        self.update_progress(0.15)

        print("Aplicando región España y formato horario de 24 horas...")
        regional_cmd = r"""
        Set-WinHomeLocation -GeoId 217
        Set-Culture es-ES
        $intl = 'HKCU:\Control Panel\International'
        Set-ItemProperty -Path $intl -Name sShortTime -Value 'HH:mm'
        Set-ItemProperty -Path $intl -Name sTimeFormat -Value 'HH:mm:ss'
        Set-ItemProperty -Path $intl -Name iTime -Value '1'
        Set-ItemProperty -Path $intl -Name sCountry -Value 'Spain'
        Set-ItemProperty -Path $intl -Name sShortDate -Value 'dd/MM/yyyy'
        Set-ItemProperty -Path $intl -Name sLongDate -Value 'dddd, d MMMM, yyyy'
        'OK region Spain / es-ES / 24h'
        """
        region_ok, region_out = SysUtils.run_powershell(regional_cmd, capture=True, timeout=20)
        if region_out.strip():
            print(region_out.strip())
        if not region_ok:
            print("[AVISO] No se pudo aplicar toda la configuración regional. Revisa Region en Windows.")
        self.update_progress(0.30)

        # 2. Método PRINCIPAL: W32TM (El estándar moderno para Active Directory)
        cmds = [
            ["net", "start", "w32time"],                         # 1. Asegurar servicio encendido
            ["w32tm", "/config", "/syncfromflags:DOMHIER", "/update"], # 2. Obligar a leer del Dominio
            ["w32tm", "/resync", "/rediscover"]                  # 3. Forzar sincronización AHORA
        ]

        w32tm_ok = True
        for cmd in cmds:
            return_code, output = SysUtils.run_native_command(cmd)
            cmd_text = " ".join(cmd)
            if return_code != 0:
                print(f"Aviso en paso w32tm: {cmd_text} -> {output.strip()}")
                if "/resync" in cmd: w32tm_ok = False
            else:
                if output.strip():
                    print(output.strip())
                print(f"OK: {cmd_text}")
            self.update_progress(min(0.9, 0.30 + (cmds.index(cmd) + 1) * 0.18))

        # 3. Método RESPALDO: NET TIME (Solo si W32TM falló)
        if not w32tm_ok:
            print("W32TM falló. Intentando método 'fuerza bruta' (NET TIME)...")
            res, output = SysUtils.run_powershell("net time /domain /set /Y", capture=True)
            print(output)
        
        self.update_progress(1)
        print("Proceso finalizado. La hora debería ser exacta ahora.")
