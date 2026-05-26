# -*- coding: utf-8 -*-
"""Tareas de Skype for Business Server para Easy Deploy.

Objetivo:
- Instalar prerrequisitos locales de Windows/Skype.
- Montar la ISO de Skype for Business Server 2019.
- Abrir el instalador oficial/Deployment Wizard para continuar la parte guiada.

No se automatiza la topología completa porque depende del diseño del dominio,
nombres FQDN, certificados, file share y decisiones del operador.
"""

import ipaddress
import os
import subprocess
import threading
import time

from ..core.sysutils import SysUtils


SKYPE_FOLDER_NAME = "SKYPE"
SKYPE_ISO_NAME = "SW_DVD5_SfB_Server_2019_64Bit_Spanish_MLF_X21-89208.ISO"
PRESKYPE_FOLDER_NAME = "Preskype"
SILVERLIGHT_EXE = "Silverlight_x64.exe"
UCMA_EXE = "UcmaRuntimeSetup.exe"

SKYPE_WINDOWS_FEATURES = [
    "RSAT-ADDS",
    "Web-Server",
    "Web-Static-Content",
    "Web-Default-Doc",
    "Web-Http-Errors",
    "Web-Asp-Net",
    "Web-Net-Ext",
    "Web-ISAPI-Ext",
    "Web-ISAPI-Filter",
    "Web-Http-Logging",
    "Web-Log-Libraries",
    "Web-Request-Monitor",
    "Web-Http-Tracing",
    "Web-Basic-Auth",
    "Web-Windows-Auth",
    "Web-Client-Auth",
    "Web-Filtering",
    "Web-Stat-Compression",
    "Web-Dyn-Compression",
    "NET-WCF-HTTP-Activation45",
    "Web-Asp-Net45",
    "Web-Mgmt-Tools",
    "Web-Scripting-Tools",
    "Web-Mgmt-Compat",
    "Server-Media-Foundation",
    "Telnet-Client",
]

PREREQ_INSTALL_CHECKS = {
    "Silverlight": ["*Microsoft Silverlight*"],
    "UCMA Runtime": [
        "*Unified Communications Managed API*",
        "*UCMA*Runtime*",
        "*Microsoft UCMA*",
    ],
}


def pre_task_skype_prereqs(app):
    """Confirma y lanza la instalación de prerrequisitos de Skype."""
    if not SysUtils.is_admin():
        app.ui_showerror(
            "Skype for Business",
            "Esta tarea necesita permisos de Administrador.\n\n"
            "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
        )
        return

    message = (
        "Esta tarea instalará los prerrequisitos locales de Skype for Business Server:\n\n"
        "- Roles y características de Windows Server.\n"
        "- IIS y herramientas de administración.\n"
        "- RSAT-ADDS.\n"
        "- Server Media Foundation.\n"
        "- Telnet Client.\n"
        "- Silverlight y UCMA desde la carpeta SKYPE\\Preskype.\n\n"
        "Ejecuta esto en la MV donde instalarás Skype for Business Server, ya unida al dominio y con DNS correcto.\n\n"
        "Easy Deploy montara automaticamente OTROS\\NetFramework3.5.iso para usar Sources\\SxS si Windows lo necesita.\n"
        "La instalación de .NET Framework 3.5 y características de Windows puede tardar varios minutos. No cierres Easy Deploy mientras finaliza.\n\n"
    )
    if not app.ui_askyesno("Prerrequisitos Skype", message + "\n\n¿Continuar?"):
        return

    app.iniciar_tarea(task_skype_prereqs, app)


def pre_task_skype_install(app):
    """Confirma y lanza el montaje de ISO/Setup de Skype."""
    if not SysUtils.is_admin():
        app.ui_showerror(
            "Skype for Business",
            "Esta tarea necesita permisos de Administrador.\n\n"
            "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
        )
        return

    message = (
        "Esta tarea montará la ISO de Skype for Business Server 2019 y abrirá el Setup oficial.\n\n"
        "Antes de continuar, revisa este checklist:\n\n"
        "1. Ejecuta primero Prerrequisitos Skype y reinicia si Windows lo pide.\n"
        "2. Ejecuta Permisos a usuario Skype con la cuenta que usará el Deployment Wizard.\n"
        "3. Ejecuta Puntero DNS Skype y valida que la resolución DNS responde correctamente.\n"
        "4. La MV Skype debe estar unida al dominio y tener ping/DNS correcto contra el dominio.\n"
        "5. Deben estar instalados Silverlight, UCMA y las características Windows requeridas.\n"
        "6. Debe existir la carpeta compartida C:\\share con permisos adecuados.\n"
        "7. Debe estar instalado Exchange antes de hacer este paso.\n\n"
        "Al pulsar Continuar se cerrará este aviso y después se abrirá el instalador oficial."
    )
    if not app.ui_askyesno("Instalar Skype", message + "\n\n¿Continuar?"):
        return

    app.iniciar_tarea(task_skype_install, app)

def _skype_ad_environment_report():
    """Comprobación suave de entorno AD, reutilizando la idea de ad_users.py.

    No bloquea la herramienta porque en algunos DC la detección previa puede devolver
    una salida incompleta aunque el script real de Active Directory funcione.
    """
    script = r"""
$ErrorActionPreference = 'Continue'
try {
    $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    "COMPUTER=$env:COMPUTERNAME"
    "PART_OF_DOMAIN=$($cs.PartOfDomain)"
    "DOMAIN_ROLE=$($cs.DomainRole)"
    "IS_DC=$([int]$cs.DomainRole -ge 4)"
    try {
        Import-Module ActiveDirectory -ErrorAction Stop
        $domain = Get-ADDomain -ErrorAction Stop
        "DOMAIN=$($domain.DNSRoot)"
        "DOMAIN_DN=$($domain.DistinguishedName)"
        "PDC=$($domain.PDCEmulator)"
        "AD_MODULE=True"
    } catch {
        "AD_MODULE=False"
        "AD_ERROR=$($_.Exception.Message)"
    }
    exit 0
} catch {
    "ERROR=$($_.Exception.Message)"
    exit 1
}
"""
    ok, output = SysUtils.run_powershell(script, capture=True, timeout=30)
    output = SysUtils.decode_process_bytes(output or "", prefer_utf8=True)
    data = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if key == "COMPUTER":
            data["computer"] = value
        elif key == "DOMAIN":
            data["domain"] = value
        elif key == "DOMAIN_DN":
            data["domain_dn"] = value
        elif key == "PDC":
            data["pdc"] = value
        elif key == "PART_OF_DOMAIN":
            data["part_of_domain"] = value.lower() == "true"
        elif key == "DOMAIN_ROLE":
            try:
                data["domain_role"] = int(value)
            except Exception:
                data["domain_role"] = -1
        elif key == "IS_DC":
            data["is_dc"] = value.lower() == "true"
        elif key == "AD_MODULE":
            data["ad_module"] = value.lower() == "true"
        elif key == "AD_ERROR":
            data["ad_error"] = value
        elif key == "ERROR":
            data["error"] = value

    messages = []
    if data.get("computer"):
        messages.append(f"Equipo: {data['computer']}")
    if data.get("domain"):
        messages.append(f"Dominio AD: {data['domain']}")
    if data.get("pdc"):
        messages.append(f"PDC Emulator: {data['pdc']}")
    if "is_dc" in data:
        messages.append("Es DC: " + ("Sí" if data.get("is_dc") else "No"))
    if data.get("ad_error"):
        messages.append("Aviso módulo AD: " + data["ad_error"])
    if data.get("error"):
        messages.append("Aviso: " + data["error"])

    env_ok = bool(ok and data.get("part_of_domain") and data.get("ad_module") and data.get("domain"))
    if not data.get("part_of_domain", False):
        env_ok = False
        messages.append("El equipo no parece estar unido a un dominio.")
    if not data.get("ad_module", False):
        env_ok = False
        messages.append("No se pudo confirmar el módulo ActiveDirectory en la comprobación previa.")

    return env_ok, "\n".join(messages), data


def pre_task_skype_permissions(app):
    """Comprueba y añade un usuario a grupos necesarios para Skype for Business."""
    if not SysUtils.is_admin():
        app.ui_showerror(
            "Permisos Skype",
            "Esta tarea necesita permisos de Administrador.\n\n"
            "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
        )
        return

    # Misma filosofía que Crear usuarios AD: la comprobación previa es informativa.
    # No debe bloquear el formulario porque en algunos DC puede dar falso negativo.
    try:
        env_ok, env_message, _env_data = _skype_ad_environment_report()
    except Exception as exc:
        env_ok = False
        env_message = f"No se pudo realizar la comprobación previa: {exc}"

    env_status = env_message.strip() if env_message else "No se obtuvo información previa del entorno."
    if env_ok:
        env_intro = "Comprobación previa AD correcta."
    else:
        env_intro = (
            "Aviso: la comprobación previa no ha podido confirmar completamente el entorno AD.\n"
            "Esto no bloqueará la herramienta; la validación real se hará en consola al ejecutar."
        )

    message = (
        f"{env_intro}\n\n"
        f"{env_status}\n\n"
        "Ejecuta esta opción preferiblemente desde un Controlador de Dominio. También puede funcionar desde "
        "un servidor/equipo unido al dominio con RSAT-ADDS / módulo ActiveDirectory instalado y permisos para modificar grupos.\n\n"
        "Qué puede hacer Easy Deploy:\n\n"
        "1. Instalación / preparación de Active Directory:\n"
        "   - Schema Admins\n"
        "   - Enterprise Admins\n"
        "   - Domain Admins\n\n"
        "2. Administración y control de acceso Skype:\n"
        "   - CsAdministrator\n"
        "   - CsUserAdministrator\n"
        "   - CsVoiceAdministrator\n"
        "   - CsHelpDesk\n\n"
        "Aviso: los grupos de instalación dan permisos muy altos. Úsalos solo para la cuenta que realizará "
        "la preparación inicial de Skype. Después de añadir permisos, el usuario debe cerrar sesión y volver "
        "a entrar para actualizar su token de seguridad.\n\n"
        "¿Quieres continuar?"
    )
    if not app.ui_askyesno("Permisos a usuario Skype", message):
        return

    username = app.ui_input_dialog(
        "Usuario AD",
        "Introduce el usuario de Active Directory que quieres comprobar o preparar.\n\n"
        "Puedes escribir sAMAccountName, UPN o nombre visible.\n"
        "Ejemplos: s01adm, administrador@et.ms.esp, ET\\s01adm",
    )
    if not username:
        return
    username = username.strip()
    if "\\" in username:
        username = username.rsplit("\\", 1)[-1].strip()
    if not SysUtils.is_plain_value(username, max_len=128):
        app.ui_showerror(
            "Usuario no válido",
            "Introduce un usuario válido sin saltos de línea ni caracteres extraños.",
        )
        return

    mode = app.modal_dialog(
        "Tipo de permisos",
        "Selecciona qué grupo de permisos quieres comprobar y aplicar al usuario:\n\n"
        "Instalación AD: permisos altos para preparar esquema, bosque y dominio.\n"
        "Administración RBAC: grupos Cs* para administrar Skype una vez preparado Active Directory.\n"
        "Ambos: aplica los dos bloques.",
        "question",
        [
            ("Instalación AD", "install", "warning"),
            ("Administración RBAC", "admin", "primary"),
            ("Ambos", "both", "primary"),
            ("Cancelar", "", "secondary"),
        ],
    )
    if not mode:
        return

    confirm_text = (
        f"Usuario seleccionado: {username}\n\n"
        f"Bloque seleccionado: {mode}\n\n"
        "Easy Deploy buscará el usuario en Active Directory, comprobará pertenencia a grupos "
        "y añadirá únicamente los grupos que falten.\n\n"
        "La validación real se ejecutará ahora mediante PowerShell, igual que en Crear usuarios AD.\n\n"
        "Recuerda cerrar sesión y volver a entrar después para que Windows cargue los nuevos permisos.\n\n"
        "¿Ejecutar ahora?"
    )
    if not app.ui_askyesno("Confirmar permisos Skype", confirm_text):
        return

    app.iniciar_tarea(task_skype_permissions, app, username, mode)


def pre_task_skype_dns(app):
    """Crea registros DNS internos mínimos para Skype for Business Server."""
    if not SysUtils.is_admin():
        app.ui_showerror(
            "Puntero DNS Skype",
            "Esta tarea necesita permisos de Administrador.\n\n"
            "Cierra Easy Deploy y ejecútalo con 'Ejecutar como administrador'.",
        )
        return

    try:
        env_ok, env_message, env_data = _skype_ad_environment_report()
    except Exception as exc:
        env_ok = False
        env_message = f"No se pudo realizar la comprobación previa: {exc}"
        env_data = {}

    message = (
        "Esta opción creará o actualizará los punteros DNS correspondientes a la instalación del servidor Skype.\n\n"
        "Debes ejecutarlo desde un Controlador de Dominio/DNS Server o desde un equipo con RSAT-DNS "
        "y permisos para modificar la zona DNS.\n\n"
        "¿Quieres continuar?"
    )
    if not app.ui_askyesno("Puntero DNS Skype", message):
        return

    fqdn = app.ui_input_dialog(
        "FQDN servidor/pool Skype",
        "Introduce el FQDN completo del servidor o pool Skype.\n\n"
        "Ejemplo: s01skype.et.ms.esp",
    )
    if not fqdn:
        return
    fqdn = _normalize_dns_name(fqdn)
    if not _is_valid_fqdn(fqdn):
        app.ui_showerror(
            "FQDN no válido",
            "Introduce un FQDN válido, por ejemplo:\n\n"
            "s01sfb1.et.ms.esp",
        )
        return

    zone_name = _zone_from_fqdn(fqdn)
    if not zone_name:
        app.ui_showerror(
            "Zona DNS no válida",
            "No se pudo deducir la zona DNS desde el FQDN indicado.\n\n"
            "Ejemplo correcto: s01sfb1.et.ms.esp",
        )
        return

    suggested_ip = ""
    if env_data.get("computer") and fqdn.split(".", 1)[0].lower() == str(env_data.get("computer", "")).lower():
        suggested_ip = "\n\nSi estás ejecutando Easy Deploy en el servidor Skype, usa la IP principal de este servidor."

    server_ip = app.ui_input_dialog(
        "IP servidor Skype",
        "Introduce la IPv4 interna del servidor Skype.\n\n"
        "Ejemplo: 192.168.248.11"
        + suggested_ip,
    )
    if not server_ip:
        return
    server_ip = server_ip.strip()
    try:
        ip_obj = ipaddress.ip_address(server_ip)
        if ip_obj.version != 4:
            raise ValueError("Solo IPv4")
    except Exception:
        app.ui_showerror(
            "IP no válida",
            "Introduce una dirección IPv4 válida, por ejemplo:\n\n192.168.248.11",
        )
        return

    sip_tls_fqdn = fqdn
    if app.ui_askyesno(
        "FQDN adicional",
        "Easy Deploy puede usar el mismo FQDN para todos los punteros DNS de Skype.\n\n"
        f"FQDN actual: {fqdn}\n\n"
        "¿Quieres indicar un FQDN diferente para el puntero adicional?",
    ):
        custom_sip_tls_fqdn = app.ui_input_dialog(
            "FQDN adicional",
            "Introduce el FQDN adicional que quieres usar.\n\n"
            "Ejemplo: s01skype.et.ms.esp",
        )
        if not custom_sip_tls_fqdn:
            return
        custom_sip_tls_fqdn = _normalize_dns_name(custom_sip_tls_fqdn)
        if not _is_valid_fqdn(custom_sip_tls_fqdn):
            app.ui_showerror(
                "FQDN no válido",
                "Introduce un FQDN válido, por ejemplo:\n\n"
                "s01skype.et.ms.esp",
            )
            return
        sip_tls_fqdn = custom_sip_tls_fqdn

    host_short = fqdn.split(".", 1)[0]
    records_preview = ", ".join(_skype_dns_a_record_names(host_short))
    confirm_text = (
        f"Servidor/pool Skype: {fqdn}\n"
        f"FQDN adicional: {sip_tls_fqdn}\n"
        f"Zona DNS: {zone_name}\n"
        f"IPv4 destino: {server_ip}\n\n"
        "Se crearán o actualizarán los punteros DNS necesarios para la instalación del servidor Skype.\n\n"
        "¿Ejecutar ahora?"
    )
    if not app.ui_askyesno("Confirmar DNS Skype", confirm_text):
        return

    app.iniciar_tarea(task_skype_dns, app, fqdn, server_ip, zone_name, sip_tls_fqdn)


def task_skype_dns(app, server_fqdn, server_ip, zone_name, sip_tls_fqdn=None):
    """Crea registros DNS internos mínimos para Skype for Business Server."""
    print("Preparando punteros DNS internos para Skype for Business Server...")
    _safe_progress(app, 0.05)
    _print_environment_summary()
    _safe_progress(app, 0.12)

    server_fqdn = _normalize_dns_name(server_fqdn)
    sip_tls_fqdn = _normalize_dns_name(sip_tls_fqdn or server_fqdn)
    zone_name = _normalize_dns_name(zone_name)
    host_short = server_fqdn.split(".", 1)[0]
    a_records = _skype_dns_a_record_names(host_short)

    print(f"[INFO] Zona DNS: {zone_name}")
    print(f"[INFO] FQDN servidor/pool Skype: {server_fqdn}")
    print(f"[INFO] FQDN destino _sip._tls: {sip_tls_fqdn}")
    print(f"[INFO] IPv4 destino: {server_ip}")
    print("[INFO] Registros A previstos: " + ", ".join(a_records))
    print("[INFO] Registro SRV previsto: _sipinternaltls._tcp -> puerto 5061 -> " + server_fqdn)
    print("[INFO] Registro SRV previsto: _sip._tls -> puerto 443 -> " + sip_tls_fqdn)
    _safe_progress(app, 0.20)

    script = _skype_dns_script(server_fqdn, sip_tls_fqdn, server_ip, zone_name, a_records)
    ok, output = SysUtils.run_powershell(script, capture=True, timeout=120)
    output = SysUtils.decode_process_bytes(output or "", prefer_utf8=True)

    added = 0
    updated = 0
    existing = 0
    warnings = []
    failures = []

    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        print(line)
        if line.startswith("ADDED|"):
            added += 1
        elif line.startswith("UPDATED|"):
            updated += 1
        elif line.startswith("OKDNS|"):
            existing += 1
        elif line.startswith("WARN|"):
            warnings.append(line.split("|", 1)[1])
        elif line.startswith("FAIL|"):
            failures.append(line.split("|", 1)[1])

    _safe_progress(app, 1.0)

    if not ok or failures:
        details = "\n".join(f"- {item}" for item in failures[:10])
        if not details:
            details = "PowerShell no pudo completar la creación de DNS. Revisa la consola y el log."
        app._notify_task_error(
            "Puntero DNS Skype",
            "No se pudieron completar los registros DNS de Skype.\n\n"
            f"{details}\n\n"
            "Comprueba que estás ejecutando desde un DC/DNS Server o desde un equipo con RSAT-DNS, "
            "y que la cuenta actual puede modificar la zona DNS.",
        )
        return

    print("[OK] Punteros DNS Skype finalizados.")
    print(f"[INFO] Registros creados: {added}")
    print(f"[INFO] Registros actualizados: {updated}")
    print(f"[INFO] Registros ya correctos: {existing}")
    if warnings:
        print("[AVISO] Avisos:")
        for item in warnings[:10]:
            print(f" - {item}")

    app._notify_task_info(
        "Puntero DNS Skype",
        "Registros DNS de Skype finalizados correctamente.\n\n"
        f"Creados: {added}\n"
        f"Actualizados: {updated}\n"
        f"Ya correctos: {existing}\n\n"
        "Siguiente paso recomendado: valida Resolve-DnsName de los SRV, ejecuta Permisos Skype si falta, "
        "replica entre DCs si has preparado AD y continúa con Instalar Skype.",
    )


def _normalize_dns_name(value):
    return str(value or "").strip().strip(".").lower()


def _is_valid_fqdn(value):
    text = _normalize_dns_name(value)
    if not text or "." not in text or len(text) > 253:
        return False
    labels = text.split(".")
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not all(ch.isalnum() or ch == "-" for ch in label):
            return False
    return True


def _zone_from_fqdn(fqdn):
    text = _normalize_dns_name(fqdn)
    parts = text.split(".")
    if len(parts) < 2:
        return ""
    return ".".join(parts[1:])


def _skype_dns_a_record_names(server_host):
    names = [
        server_host,
        "meet",
        "dialin",
        "pool",
        "admin",
        "lyncdiscoverinternal",
        "lyncdiscover",
    ]
    result = []
    seen = set()
    for item in names:
        clean = _normalize_dns_name(item)
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def _skype_dns_script(server_fqdn, sip_tls_fqdn, server_ip, zone_name, a_records):
    fqdn_literal = SysUtils.ps_quote(server_fqdn)
    sip_tls_literal = SysUtils.ps_quote(sip_tls_fqdn)
    ip_literal = SysUtils.ps_quote(server_ip)
    zone_literal = SysUtils.ps_quote(zone_name)
    records_literal = _ps_array(a_records)
    return r"""
$ErrorActionPreference = 'Stop'
$serverFqdn = __SERVER_FQDN__
$sipTlsFqdn = __SIP_TLS_FQDN__
$serverIp = __SERVER_IP__
$zoneName = __ZONE_NAME__
$aRecords = __A_RECORDS__

function Write-Info([string]$Message) { Write-Output "[INFO] $Message" }
function Write-Fail([string]$Message) { Write-Output "FAIL|$Message" }
function Write-Warn([string]$Message) { Write-Output "WARN|$Message" }

try {
    Import-Module DnsServer -ErrorAction Stop
} catch {
    Write-Fail "No se pudo cargar el módulo DnsServer. Ejecuta desde un DC/DNS Server o instala RSAT-DNS-Server. Detalle: $($_.Exception.Message)"
    exit 10
}

try {
    $null = Get-DnsServerZone -Name $zoneName -ErrorAction Stop
    Write-Info "Zona DNS encontrada: $zoneName"
} catch {
    Write-Fail "No se encontró la zona DNS '$zoneName'. Crea la zona o revisa el FQDN indicado. Detalle: $($_.Exception.Message)"
    exit 11
}

function Ensure-ARecord {
    param(
        [string]$Name,
        [string]$IPv4
    )
    try {
        $existing = @(Get-DnsServerResourceRecord -ZoneName $zoneName -Name $Name -RRType A -ErrorAction SilentlyContinue)
        $matching = @($existing | Where-Object { $_.RecordData.IPv4Address.IPAddressToString -eq $IPv4 })
        $recordFqdn = "$Name.$zoneName"
        if ($matching.Count -gt 0) {
            Write-Output "OKDNS|A|$recordFqdn|$IPv4"
            Write-Output "[OK] A $recordFqdn ya apunta a $IPv4."
            return
        }
        if ($existing.Count -gt 0) {
            $oldValues = ($existing | ForEach-Object { $_.RecordData.IPv4Address.IPAddressToString }) -join ', '
            foreach ($old in $existing) {
                Remove-DnsServerResourceRecord -ZoneName $zoneName -InputObject $old -Force -ErrorAction Stop
            }
            Add-DnsServerResourceRecordA -ZoneName $zoneName -Name $Name -IPv4Address $IPv4 -AllowUpdateAny -TimeToLive 01:00:00 -ErrorAction Stop | Out-Null
            Write-Output "UPDATED|A|$recordFqdn|$IPv4"
            Write-Output "[OK] A $recordFqdn actualizado de [$oldValues] a $IPv4."
            return
        }
        Add-DnsServerResourceRecordA -ZoneName $zoneName -Name $Name -IPv4Address $IPv4 -AllowUpdateAny -TimeToLive 01:00:00 -ErrorAction Stop | Out-Null
        Write-Output "ADDED|A|$recordFqdn|$IPv4"
        Write-Output "[OK] A $recordFqdn creado apuntando a $IPv4."
    } catch {
        Write-Fail "No se pudo crear/actualizar A $($Name).$($zoneName): $($_.Exception.Message)"
    }
}

function Ensure-SrvRecord {
    param(
        [string]$Name,
        [string]$TargetFqdn,
        [int]$Port
    )
    try {
        $existing = @(Get-DnsServerResourceRecord -ZoneName $zoneName -Name $Name -RRType SRV -ErrorAction SilentlyContinue)
        $targetNorm = $TargetFqdn.TrimEnd('.').ToLowerInvariant()
        $matching = @($existing | Where-Object {
            ($_.RecordData.DomainName.TrimEnd('.').ToLowerInvariant() -eq $targetNorm) -and
            ([int]$_.RecordData.Port -eq $Port) -and
            ([int]$_.RecordData.Priority -eq 0) -and
            ([int]$_.RecordData.Weight -eq 0)
        })
        $recordFqdn = "$Name.$zoneName"
        if ($matching.Count -gt 0) {
            Write-Output "OKDNS|SRV|$recordFqdn|$TargetFqdn`:$Port"
            Write-Output "[OK] SRV $recordFqdn ya apunta a $TargetFqdn puerto $Port."
            return
        }
        if ($existing.Count -gt 0) {
            foreach ($old in $existing) {
                Remove-DnsServerResourceRecord -ZoneName $zoneName -InputObject $old -Force -ErrorAction Stop
            }
            Add-DnsServerResourceRecord -ZoneName $zoneName -Name $Name -Srv -DomainName $TargetFqdn -Priority 0 -Weight 0 -Port $Port -TimeToLive 01:00:00 -ErrorAction Stop | Out-Null
            Write-Output "UPDATED|SRV|$recordFqdn|$TargetFqdn`:$Port"
            Write-Output "[OK] SRV $recordFqdn actualizado a $TargetFqdn puerto $Port."
            return
        }
        Add-DnsServerResourceRecord -ZoneName $zoneName -Name $Name -Srv -DomainName $TargetFqdn -Priority 0 -Weight 0 -Port $Port -TimeToLive 01:00:00 -ErrorAction Stop | Out-Null
        Write-Output "ADDED|SRV|$recordFqdn|$TargetFqdn`:$Port"
        Write-Output "[OK] SRV $recordFqdn creado apuntando a $TargetFqdn puerto $Port."
    } catch {
        Write-Fail "No se pudo crear/actualizar SRV $($Name).$($zoneName) puerto $($Port): $($_.Exception.Message)"
    }
}

Write-Info "Creando registros A mínimos de Skype..."
foreach ($name in $aRecords) {
    Ensure-ARecord -Name $name -IPv4 $serverIp
}

Write-Info "Creando registro SRV interno _sipinternaltls._tcp..."
Ensure-SrvRecord -Name '_sipinternaltls._tcp' -TargetFqdn $serverFqdn -Port 5061

Write-Info "Creando registro SRV adicional _sip._tls..."
Ensure-SrvRecord -Name '_sip._tls' -TargetFqdn $sipTlsFqdn -Port 443

Write-Info "Validación de resolución DNS posterior:"
foreach ($name in $aRecords) {
    try {
        $resolved = @(Resolve-DnsName -Name "$name.$zoneName" -Type A -ErrorAction Stop | Where-Object { $_.IPAddress })
        $ips = ($resolved | ForEach-Object { $_.IPAddress }) -join ', '
        Write-Output "[OK] Resolve $name.$zoneName -> $ips"
    } catch {
        Write-Warn "No se pudo resolver $name.$zoneName tras crear el registro: $($_.Exception.Message)"
    }
}
foreach ($srvName in @('_sipinternaltls._tcp', '_sip._tls')) {
    try {
        $srv = @(Resolve-DnsName -Name "$srvName.$zoneName" -Type SRV -ErrorAction Stop | Where-Object { $_.NameTarget })
        $targets = ($srv | ForEach-Object { "$($_.NameTarget):$($_.Port)" }) -join ', '
        Write-Output "[OK] Resolve $srvName.$zoneName -> $targets"
    } catch {
        Write-Warn "No se pudo resolver $srvName.$zoneName tras crear el registro: $($_.Exception.Message)"
    }
}

if ($false) { Write-Output '' }
""".replace("__SERVER_FQDN__", fqdn_literal).replace("__SIP_TLS_FQDN__", sip_tls_literal).replace("__SERVER_IP__", ip_literal).replace("__ZONE_NAME__", zone_literal).replace("__A_RECORDS__", records_literal)


def task_skype_prereqs(app):
    """Instala prerrequisitos locales para Skype for Business Server."""
    print("Preparando prerrequisitos de Skype for Business Server...")
    _safe_progress(app, 0.03)
    _print_environment_summary()
    _safe_progress(app, 0.08)

    resources = _find_skype_resources(app)
    skype_root = resources.get("root", "")
    print(f"[INFO] Carpeta SKYPE detectada: {skype_root or 'No detectada'}")
    _safe_progress(app, 0.10)

    silverlight = resources.get("silverlight", "")
    ucma = resources.get("ucma", "")

    issues = []

    print(">>> Instalando características de Windows requeridas...")
    print("[INFO] Instalacion offline: Easy Deploy montara OTROS\\NetFramework3.5.iso para usar Sources\\SxS.")
    print("[INFO] Este paso puede tardar varios minutos, sobre todo si instala .NET Framework 3.5. No cierres Easy Deploy.")
    try:
        app._last_netfx35_sxs_detail = {}
    except Exception:
        pass
    feature_pulse = _ProgressPulse(app, start=0.12, end=0.62, seconds=300)
    feature_pulse.start()
    try:
        features_ok = _install_windows_features(
            SKYPE_WINDOWS_FEATURES,
            getattr(app, "payload_root", ""),
            getattr(app, "base_path", ""),
            app=app,
        )
    finally:
        feature_pulse.stop()
    if not features_ok:
        issues.append(
            "No se han podido instalar todas las características de Windows. "
            "Revisa que exista OTROS\\NetFramework3.5.iso en la carpeta de recursos y repite Prerrequisitos Skype."
        )
    _safe_progress(app, 0.68)

    if silverlight:
        print(">>> Instalando Silverlight...")
        _safe_progress(app, 0.72)
        if not _install_exe_silent(silverlight, ["/q"], "Silverlight"):
            issues.append("Silverlight no se ha podido confirmar como instalado.")
    else:
        print("[AVISO] No se encontró Silverlight_x64.exe en SKYPE\\Preskype. Se omite este instalador.")
        issues.append("Falta Silverlight_x64.exe en SKYPE\\Preskype.")
    _safe_progress(app, 0.78)

    if ucma:
        print(">>> Instalando UCMA Runtime...")
        _safe_progress(app, 0.82)
        if not _install_exe_silent(ucma, ["/quiet", "/norestart"], "UCMA Runtime"):
            issues.append("UCMA Runtime no se ha podido confirmar como instalado.")
    else:
        print("[AVISO] No se encontró UcmaRuntimeSetup.exe en SKYPE\\Preskype. Se omite este instalador.")
        issues.append("Falta UcmaRuntimeSetup.exe en SKYPE\\Preskype.")
    _safe_progress(app, 0.88)

    print(">>> Comprobando si hay reinicio pendiente...")
    reboot_pending = SysUtils.is_reboot_pending()
    if reboot_pending:
        print("[AVISO] Windows indica reinicio pendiente. Reinicia antes de lanzar la instalación de Skype.")
        try:
            app.console_finish_state = "restart"
        except Exception:
            pass
    else:
        print("[OK] No se detecta reinicio pendiente.")
    _safe_progress(app, 0.95)

    if issues:
        print("")
        print("[ERROR] Prerrequisitos de Skype finalizados con incidencias.")
        print("[INFO] No ejecutes todavía 'Instalar Skype' hasta corregir lo siguiente:")
        for issue in issues:
            print(f" - {issue}")
        print("")
        print("[INFO] Acción recomendada:")
        print("1. Reinicia la MV si hay reinicio pendiente.")
        print("2. Revisa OTROS\\NetFramework3.5.iso si Windows Features falla.")
        print("3. Repite el botón 'Prerrequisitos Skype'.")
        _safe_progress(app, 1.0)
        if reboot_pending:
            _force_restart_controls(app)
        return

    print("[OK] Prerrequisitos de Skype finalizados correctamente.")
    _safe_progress(app, 1.0)
    _notify_netfx_iso_dismount(app, getattr(app, "_last_netfx35_sxs_detail", {}), "Prerrequisitos Skype")
    if reboot_pending:
        print("[INFO] Reinicia antes de pulsar 'Instalar Skype'.")
        _notify_reboot_required(app)
        _force_restart_controls(app)
    else:
        print("[INFO] Siguiente paso recomendado: botón 'Instalar Skype' y seguir la Guía Skype.")

def task_skype_permissions(app, username, mode):
    """Añade el usuario indicado a los grupos AD/Skype necesarios."""
    print("Preparando comprobación de permisos para Skype for Business Server...")
    _safe_progress(app, 0.03)
    _print_environment_summary()
    _safe_progress(app, 0.08)

    mode_label = {
        "install": "Instalación / preparación de Active Directory",
        "admin": "Administración y control de acceso Skype",
        "both": "Instalación AD + Administración Skype",
    }.get(mode, str(mode))
    print(f"[INFO] Usuario indicado: {username}")
    print(f"[INFO] Bloque seleccionado: {mode_label}")
    print("[INFO] Esta tarea usa la misma filosofía que Crear usuarios AD: la comprobación fuerte se hace dentro del script PowerShell.")
    print("[INFO] Recomendado: ejecutar desde un DC o desde un equipo con RSAT-ADDS / módulo ActiveDirectory y permisos suficientes.")
    _safe_progress(app, 0.12)

    ps1_path = ""
    process = None
    added = 0
    already = 0
    missing_groups = []
    failed_lines = []

    try:
        ps1_path = _write_skype_permissions_script(app, username, mode)
        print(f"Script temporal: {ps1_path}")
        print("[INFO] No se guardan contraseñas. Solo se usa el usuario indicado para modificar pertenencia a grupos.")
        _safe_progress(app, 0.18)

        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            ps1_path,
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        pulse = _ProgressPulse(app, start=0.20, end=0.80, seconds=120, interval=1.5)
        pulse.start()
        try:
            while True:
                if app.stop_event.is_set():
                    print("[AVISO] Cancelación solicitada. Deteniendo comprobación de permisos Skype...")
                    try:
                        process.terminate()
                        process.wait(timeout=10)
                    except Exception:
                        try:
                            process.kill()
                        except Exception:
                            pass
                    return

                raw = process.stdout.readline() if process.stdout else b""
                if raw:
                    line = _decode_permissions_process_line(raw)
                    clean = line.strip()
                    if clean:
                        print(clean)
                        if clean.startswith("ADDED|"):
                            added += 1
                        elif clean.startswith("OKMEMBER|"):
                            already += 1
                        elif clean.startswith("MISSINGGROUP|"):
                            missing_groups.append(clean.split("|", 1)[1])
                        elif clean.startswith("FAIL|"):
                            failed_lines.append(clean.split("|", 1)[1])
                        elif any(marker in clean for marker in (
                            "ParserError",
                            "FullyQualifiedErrorId",
                            "InvalidVariableReferenceWithDrive",
                            "La referencia de variable no es válida",
                            "La referencia de variable no es valida",
                            "CategoryInfo",
                        )):
                            failed_lines.append(clean)

                if process.poll() is not None:
                    if process.stdout:
                        for remaining in process.stdout:
                            line = _decode_permissions_process_line(remaining)
                            clean = line.strip()
                            if not clean:
                                continue
                            print(clean)
                            if clean.startswith("ADDED|"):
                                added += 1
                            elif clean.startswith("OKMEMBER|"):
                                already += 1
                            elif clean.startswith("MISSINGGROUP|"):
                                missing_groups.append(clean.split("|", 1)[1])
                            elif clean.startswith("FAIL|"):
                                failed_lines.append(clean.split("|", 1)[1])
                    break

                if not raw:
                    time.sleep(0.2)
        finally:
            pulse.stop()

        _safe_progress(app, 1.0)
        return_code = process.returncode if process is not None else -1

        if return_code != 0 or failed_lines:
            details = "\n".join(f"- {item}" for item in failed_lines[:10])
            if not details:
                details = f"PowerShell devolvió código {return_code}. Revisa el log para ver el detalle."
            app._notify_task_error(
                "Permisos Skype",
                "No se pudo completar la comprobación/asignación de permisos.\n\n"
                f"{details}\n\n"
                "Comprueba que estás ejecutando desde un DC o desde un equipo con RSAT-ADDS / módulo ActiveDirectory, "
                "y que la cuenta actual tiene permisos para modificar los grupos seleccionados.",
            )
            return

        if missing_groups:
            app._notify_task_warning(
                "Permisos Skype",
                "La tarea terminó, pero algunos grupos de Skype no existen todavía en Active Directory.\n\n"
                "Normalmente esto ocurre si aún no se ha ejecutado 'Prepare Active Directory' desde el Deployment Wizard de Skype.\n\n"
                "Grupos no encontrados:\n- " + "\n- ".join(missing_groups[:12]),
            )
            return

        print("[OK] Comprobación de permisos Skype finalizada.")
        print(f"[INFO] Grupos añadidos: {added}")
        print(f"[INFO] Grupos ya presentes: {already}")
        print("[INFO] Si se añadieron grupos, cierra sesión y vuelve a entrar antes de continuar con el Deployment Wizard.")
        app._notify_task_info(
            "Permisos Skype",
            f"Comprobación finalizada correctamente.\n\n"
            f"Grupos añadidos: {added}\n"
            f"Grupos ya presentes: {already}\n\n"
            "Si se añadió algún grupo, cierra sesión y vuelve a entrar en Windows antes de continuar con Skype.",
        )
    except Exception as exc:
        _safe_progress(app, 1.0)
        app._notify_task_error(
            "Permisos Skype",
            f"No se pudo crear o ejecutar el script de permisos Skype.\n\nDetalle: {exc}",
        )
    finally:
        if ps1_path and os.path.exists(ps1_path):
            try:
                os.remove(ps1_path)
            except Exception:
                pass


def _skype_permissions_script_dir(app):
    """Carpeta temporal para scripts PowerShell de permisos Skype, sin dejar .py fuera del programa."""
    return SysUtils.get_easydeploy_temp_scripts_dir()


def _write_skype_permissions_script(app, username, mode):
    """Escribe un .ps1 temporal en UTF-8 BOM y lo elimina task_skype_permissions al finalizar."""
    script_dir = _skype_permissions_script_dir(app)
    os.makedirs(script_dir, exist_ok=True)
    ps1_path = SysUtils.make_temp_script_path("easydeploy_skype_permissions", ".ps1")
    with open(ps1_path, "w", encoding="utf-8-sig") as handle:
        handle.write(_skype_permissions_script(username, mode))
    return ps1_path


def _decode_permissions_process_line(raw_line):
    """Decodifica líneas de PowerShell evitando ra├¡z/a├▒adir y manteniendo tildes."""
    if isinstance(raw_line, str):
        return SysUtils.decode_process_bytes(raw_line.rstrip("\r\n"), prefer_utf8=True)
    if not raw_line:
        return ""
    return SysUtils.decode_process_bytes(raw_line.rstrip(b"\r\n"), prefer_utf8=True)


def _skype_permissions_script(username, mode):
    """Genera el script PowerShell que comprueba y añade grupos AD para Skype."""
    username_literal = SysUtils.ps_quote(username)
    mode_literal = SysUtils.ps_quote(mode)
    script = r"""
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$ErrorActionPreference = 'Stop'
$identity = __USERNAME__
$mode = __MODE__

function Write-Info([string]$Message) { Write-Output "[INFO] $Message" }
$script:HadFailure = $false
$script:ProcessedGroups = 0
function Write-Fail([string]$Message) {
    $script:HadFailure = $true
    Write-Output "FAIL|$Message"
}

function Escape-LdapFilterValue {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    $text = [string]$Value
    $text = $text.Replace('\', '\5c')
    $text = $text.Replace('*', '\2a')
    $text = $text.Replace('(', '\28')
    $text = $text.Replace(')', '\29')
    $text = $text.Replace(([string][char]0), '\00')
    return $text
}

try {
    Import-Module ActiveDirectory -ErrorAction Stop
} catch {
    Write-Fail "No se pudo cargar el módulo ActiveDirectory. Ejecuta desde un DC o instala RSAT-ADDS."
    exit 10
}

try {
    $currentDomain = Get-ADDomain -ErrorAction Stop
    $forest = Get-ADForest -ErrorAction Stop
    $rootDomain = Get-ADDomain -Identity $forest.RootDomain -ErrorAction Stop
    Write-Info "Dominio actual: $($currentDomain.DNSRoot)"
    Write-Info "Dominio raíz del bosque: $($rootDomain.DNSRoot)"
} catch {
    Write-Fail "No se pudo consultar Active Directory: $($_.Exception.Message)"
    exit 11
}

function Resolve-User {
    param([string]$RawIdentity)
    $clean = ([string]$RawIdentity).Trim()
    if ([string]::IsNullOrWhiteSpace($clean)) { throw "Usuario vacío." }
    if ($clean.Contains('\')) { $clean = $clean.Split('\')[-1] }

    try {
        $direct = @(Get-ADUser -Identity $clean -Properties MemberOf,DistinguishedName,SamAccountName,UserPrincipalName,DisplayName -ErrorAction Stop)
        if ($direct.Count -ge 1) { return @($direct | Select-Object -First 1)[0] }
    } catch { }

    $escaped = Escape-LdapFilterValue $clean
    $matches = @(Get-ADUser -LDAPFilter "(|(sAMAccountName=$escaped)(userPrincipalName=$escaped)(name=$escaped)(displayName=$escaped))" -Properties MemberOf,DistinguishedName,SamAccountName,UserPrincipalName,DisplayName -ErrorAction SilentlyContinue)
    if ($matches.Count -eq 1) { return @($matches | Select-Object -First 1)[0] }
    if ($matches.Count -gt 1) {
        $names = ($matches | Select-Object -First 8 | ForEach-Object { "$($_.SamAccountName) <$($_.UserPrincipalName)>" }) -join ', '
        throw "La búsqueda es ambigua. Coincidencias: $names"
    }
    throw "No se encontró el usuario '$RawIdentity' en Active Directory."
}

function Get-FirstSafeObject {
    param($Value)
    $items = @($Value | Where-Object { $null -ne $_ })
    if ($items.Count -lt 1) { return $null }
    return $items[0]
}

function Get-SafeADIdentity {
    param(
        $Object,
        [string]$Kind,
        [string]$Label
    )
    $item = Get-FirstSafeObject $Object
    if ($null -eq $item) { return '' }

    if ($item -is [string]) {
        $text = ([string]$item).Trim()
        if (-not [string]::IsNullOrWhiteSpace($text)) { return $text }
    }

    foreach ($prop in @('DistinguishedName','SID','SamAccountName','ObjectGUID','Name')) {
        try {
            $value = $item.$prop
            if ($null -eq $value) { continue }
            if ($prop -eq 'SID' -and $value.Value) { $value = $value.Value }
            if ($prop -eq 'ObjectGUID' -and $value.Guid) { $value = $value.Guid }
            $text = ([string]$value).Trim()
            if (-not [string]::IsNullOrWhiteSpace($text)) { return $text }
        } catch { }
    }

    Write-Fail "No se pudo obtener identidad AD valida para $Kind $Label. El objeto devuelto por PowerShell no contiene DistinguishedName/SID/SamAccountName utilizable."
    return ''
}

function Resolve-WellKnownDomainGroup {
    param(
        [Microsoft.ActiveDirectory.Management.ADDomain]$Domain,
        [int]$Rid,
        [string]$FriendlyName
    )
    $domainSid = ''
    try {
        if ($Domain -and $Domain.DomainSID -and $Domain.DomainSID.Value) {
            $domainSid = ([string]$Domain.DomainSID.Value).Trim()
        }
    } catch { }

    if ([string]::IsNullOrWhiteSpace($domainSid)) {
        Write-Fail "No se pudo leer el SID del dominio para resolver $FriendlyName. Dominio recibido: $($Domain.DNSRoot)"
        return $null
    }

    $sid = "$domainSid-$Rid"
    try {
        $group = @(Get-ADGroup -Identity $sid -Properties DistinguishedName,SamAccountName,SID,Name -ErrorAction Stop | Select-Object -First 1)[0]
        if ($null -eq $group) {
            Write-Fail "No se pudo localizar $FriendlyName por SID $($sid): Active Directory no devolvio ningun grupo."
            return $null
        }
        return $group
    } catch {
        Write-Fail "No se pudo localizar $FriendlyName por SID $($sid): $($_.Exception.Message)"
        return $null
    }
}

function Resolve-NamedGroup {
    param([string]$Name)
    try {
        $direct = @(Get-ADGroup -Identity $Name -Properties DistinguishedName,SamAccountName,SID,Name -ErrorAction Stop | Select-Object -First 1)[0]
        if ($direct) { return $direct }
    } catch { }

    $escaped = Escape-LdapFilterValue $Name
    $matches = @(Get-ADGroup -LDAPFilter "(|(sAMAccountName=$escaped)(name=$escaped)(cn=$escaped))" -Properties DistinguishedName,SamAccountName,SID,Name -ErrorAction SilentlyContinue)
    if ($matches.Count -ge 1) { return $matches[0] }
    Write-Output "MISSINGGROUP|$Name"
    return $null
}

function Add-UserToGroupIfMissing {
    param(
        [string]$UserIdentity,
        $Group,
        [string]$Label
    )
    $singleGroup = Get-FirstSafeObject $Group
    if ([string]::IsNullOrWhiteSpace($UserIdentity)) {
        Write-Fail "Usuario no valido al procesar el grupo $($Label): identidad vacia."
        return
    }
    if ($null -eq $singleGroup) { return }

    $groupIdentity = Get-SafeADIdentity -Object $singleGroup -Kind 'grupo' -Label $Label
    if ([string]::IsNullOrWhiteSpace($groupIdentity)) { return }

    try {
        $freshUser = Get-ADUser -Identity $UserIdentity -Properties MemberOf,DistinguishedName,SamAccountName,UserPrincipalName,DisplayName -ErrorAction Stop
    } catch {
        Write-Fail "No se pudo refrescar el usuario al procesar $($Label) con identidad '$UserIdentity': $($_.Exception.Message)"
        return
    }

    try {
        $freshGroup = Get-ADGroup -Identity $groupIdentity -Properties DistinguishedName,SamAccountName,SID,Name -ErrorAction Stop
    } catch {
        Write-Fail "No se pudo refrescar el grupo $($Label) con identidad '$groupIdentity': $($_.Exception.Message)"
        return
    }

    $freshUserDn = Get-SafeADIdentity -Object $freshUser -Kind 'usuario' -Label $Label
    $freshGroupDn = Get-SafeADIdentity -Object $freshGroup -Kind 'grupo' -Label $Label
    if ([string]::IsNullOrWhiteSpace($freshUserDn) -or [string]::IsNullOrWhiteSpace($freshGroupDn)) { return }

    $script:ProcessedGroups += 1
    $memberOf = @($freshUser.MemberOf)
    if ($memberOf -contains $freshGroup.DistinguishedName) {
        Write-Output "OKMEMBER|$($freshUser.SamAccountName)|$Label"
        Write-Output "[OK] $($freshUser.SamAccountName) ya pertenece a $Label."
        return
    }

    try {
        Add-ADGroupMember -Identity $freshGroupDn -Members $freshUserDn -ErrorAction Stop
        Write-Output "ADDED|$($freshUser.SamAccountName)|$Label"
        Write-Output "[OK] Añadido $($freshUser.SamAccountName) a $Label."
        return
    } catch {
        Write-Fail "No se pudo añadir $($freshUser.SamAccountName) a $($Label): $($_.Exception.Message)"
        return
    }
}

try {
    $user = @(Resolve-User -RawIdentity $identity | Select-Object -First 1)[0]
    if ($null -eq $user) { throw "No se pudo resolver el usuario indicado." }
    Write-Info "Usuario encontrado: $($user.SamAccountName) | $($user.UserPrincipalName) | $($user.DistinguishedName)"

    $targetGroups = @()

    if ($mode -eq 'install' -or $mode -eq 'both') {
        Write-Info "Bloque Instalación AD: Schema Admins, Enterprise Admins y Domain Admins."
        $schemaAdmins = Resolve-WellKnownDomainGroup -Domain $rootDomain -Rid 518 -FriendlyName 'Schema Admins'
        $enterpriseAdmins = Resolve-WellKnownDomainGroup -Domain $rootDomain -Rid 519 -FriendlyName 'Enterprise Admins'
        $domainAdmins = Resolve-WellKnownDomainGroup -Domain $currentDomain -Rid 512 -FriendlyName 'Domain Admins'
        if ($schemaAdmins) { $targetGroups += [pscustomobject]@{ Label = 'Schema Admins'; Group = $schemaAdmins } }
        if ($enterpriseAdmins) { $targetGroups += [pscustomobject]@{ Label = 'Enterprise Admins'; Group = $enterpriseAdmins } }
        if ($domainAdmins) { $targetGroups += [pscustomobject]@{ Label = 'Domain Admins'; Group = $domainAdmins } }
    }

    if ($mode -eq 'admin' -or $mode -eq 'both') {
        Write-Info "Bloque Administración Skype RBAC: CsAdministrator, CsUserAdministrator, CsVoiceAdministrator y CsHelpDesk."
        foreach ($groupName in @('CsAdministrator','CsUserAdministrator','CsVoiceAdministrator','CsHelpDesk')) {
            $group = Resolve-NamedGroup -Name $groupName
            if ($group) { $targetGroups += [pscustomobject]@{ Label = $groupName; Group = $group } }
        }
    }

    if ($targetGroups.Count -eq 0) {
        Write-Fail "No se pudo resolver ningún grupo para el bloque seleccionado."
        exit 12
    }

    $userIdentityForMembership = Get-SafeADIdentity -Object $user -Kind 'usuario' -Label 'permisos Skype'
    if ([string]::IsNullOrWhiteSpace($userIdentityForMembership)) {
        Write-Fail "No se pudo obtener una identidad valida del usuario para modificar grupos."
        exit 13
    }

    foreach ($item in @($targetGroups)) {
        Add-UserToGroupIfMissing -UserIdentity $userIdentityForMembership -Group $item.Group -Label $item.Label
    }

    if ($script:ProcessedGroups -lt 1) {
        Write-Fail "No se procesó ningún grupo. Revisa resolución de Schema Admins, Enterprise Admins, Domain Admins o grupos RBAC."
        exit 14
    }

    if ($script:HadFailure) {
        exit 15
    }

    Write-Output "[OK] Proceso de permisos completado."
    Write-Output "[INFO] Cierra sesión y vuelve a entrar para que el token de seguridad cargue los grupos nuevos."
    exit 0
} catch {
    Write-Fail $_.Exception.Message
    exit 20
}
"""
    return script.replace("__USERNAME__", username_literal).replace("__MODE__", mode_literal)


def task_skype_install(app):
    """Monta la ISO de Skype for Business Server 2019 y abre Setup."""
    print("Preparando instalación de Skype for Business Server 2019...")
    _print_environment_summary()

    resources = _find_skype_resources(app)
    iso_path = resources.get("iso", "")
    if not iso_path:
        print("[ERROR] No se encontró la ISO de Skype for Business Server 2019.")
        print("[INFO] Ruta esperada principal:")
        print(r"C:\EASY DEPLOY\SKYPE\\" + SKYPE_ISO_NAME)
        print("[INFO] También se busca dentro de la carpeta de recursos configurada en Easy Deploy.")
        return

    print(f"[INFO] ISO detectada: {iso_path}")
    print(">>> Montando imagen ISO...")
    ok, mount_result = SysUtils.mount_disk_image(iso_path)
    if not ok:
        print(f"[ERROR] No se pudo montar la ISO: {mount_result}")
        return

    drive_letter = str(mount_result).strip().rstrip(":")
    drive_root = drive_letter + ":\\"
    print(f"[OK] ISO montada en {drive_root}")

    setup_path = _find_skype_setup(drive_root)
    if not setup_path:
        print("[ERROR] ISO montada, pero no se encontró Setup.exe.")
        print("[INFO] Revisa manualmente la unidad montada y abre Setup\\amd64\\Setup.exe si existe.")
        try:
            os.startfile(drive_root)
        except Exception:
            pass
        return

    print(f"[INFO] Setup detectado: {setup_path}")
    print(">>> Abriendo instalador oficial de Skype for Business Server...")
    try:
        subprocess.Popen([setup_path], cwd=os.path.dirname(setup_path), close_fds=True)
        print("[OK] Setup lanzado correctamente.")
    except Exception as exc:
        print(f"[ERROR] No se pudo abrir Setup.exe: {exc}")
        return

    print("")
    print("PASO  Sigue estos pasos en el asistente oficial:")
    print("1. Instala los Core Components si el asistente lo solicita.")
    print("2. Abre Skype for Business Server Deployment Wizard.")
    print("3. Instala Administrative Tools si todavía no están instaladas.")
    print("4. Si es la primera instalación del dominio, ejecuta Prepare Active Directory con permisos correctos.")
    print("5. Crea/publica la topología con Topology Builder.")
    print("6. Ejecuta Install or Update Skype for Business Server System.")
    print("7. Solicita/asigna certificados.")
    print("8. Inicia servicios y valida el estado.")
    print("")
    print("[INFO] Recuerda: la Guía Skype está en el apartado Guías de Easy Deploy.")



def _safe_progress(app, value):
    """Actualiza la barra de progreso sin romper si la UI no está disponible."""
    try:
        app.update_progress(value)
    except Exception:
        pass


class _ProgressPulse:
    """Mueve suavemente la barra durante pasos largos que no emiten salida en directo."""

    def __init__(self, app, start=0.0, end=0.9, seconds=300, interval=2.0):
        self.app = app
        self.start_value = float(start)
        self.end_value = float(end)
        self.seconds = max(float(seconds), 1.0)
        self.interval = max(float(interval), 0.5)
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        _safe_progress(self.app, self.start_value)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self):
        started = time.monotonic()
        last_value = self.start_value
        while not self._stop.wait(self.interval):
            elapsed = time.monotonic() - started
            ratio = min(0.98, elapsed / self.seconds)
            value = self.start_value + ((self.end_value - self.start_value) * ratio)
            if value > last_value:
                last_value = value
                _safe_progress(self.app, value)


def _notify_netfx_iso_dismount(app, sxs_detail, title):
    """Desmonta la ISO de NetFX solo si Easy Deploy la monto en esta tarea."""
    if not isinstance(sxs_detail, dict):
        return
    iso_path = sxs_detail.get("iso_path", "")
    if not iso_path or not sxs_detail.get("mounted_by_easydeploy"):
        return

    try:
        app._notify_task_info(
            title,
            "La instalacion ha finalizado correctamente.\n\n"
            "Al pulsar Aceptar, Easy Deploy desmontara la ISO de recursos usada para .NET Framework 3.5.",
        )
    except Exception:
        pass

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


def _notify_reboot_required(app):
    """Muestra aviso claro cuando Windows exige reinicio tras los prerrequisitos."""
    try:
        app.ui_showwarning(
            "Reinicio pendiente",
            "Windows indica que hay un reinicio pendiente.\n\n"
            "Reinicia la MV antes de pulsar 'Instalar Skype'.\n\n"
            "Después del reinicio, vuelve a abrir Easy Deploy como administrador y continúa con la instalación de Skype.",
        )
    except Exception:
        pass


def _force_restart_controls(app):
    """Refuerza que la consola muestre el estado de reinicio aunque el wrapper tarde en refrescar."""
    try:
        app.console_finish_state = "restart"
        app.update_control_bar("restart")
    except Exception:
        pass

def _find_skype_resources(app):
    """Localiza la carpeta SKYPE y sus recursos principales."""
    candidates = []

    payload_root = getattr(app, "payload_root", "") or ""
    if payload_root:
        candidates.append(os.path.join(payload_root, SKYPE_FOLDER_NAME))
        normalized = SysUtils.normalize_payload_root(payload_root)
        if normalized:
            candidates.append(os.path.join(normalized, SKYPE_FOLDER_NAME))

    base_path = getattr(app, "base_path", "") or ""
    if base_path:
        resolved = SysUtils.resolve_payload_root(base_path)
        candidates.append(os.path.join(resolved, SKYPE_FOLDER_NAME))

    candidates.extend([
        r"C:\EASY DEPLOY\SKYPE",
        r"C:\EASYDEPLOY\SKYPE",
        os.path.join(SysUtils.desktop_path(), "EASY DEPLOY", "SKYPE"),
        os.path.join(SysUtils.desktop_path(), "EASYDEPLOY", "SKYPE"),
    ])

    seen = set()
    roots = []
    for path in candidates:
        if not path:
            continue
        norm = os.path.normcase(os.path.abspath(path))
        if norm in seen:
            continue
        seen.add(norm)
        roots.append(os.path.abspath(path))

    result = {"root": "", "iso": "", "silverlight": "", "ucma": ""}
    for root in roots:
        if not os.path.isdir(root):
            continue
        result["root"] = root
        iso = os.path.join(root, SKYPE_ISO_NAME)
        silverlight = os.path.join(root, PRESKYPE_FOLDER_NAME, SILVERLIGHT_EXE)
        ucma = os.path.join(root, PRESKYPE_FOLDER_NAME, UCMA_EXE)
        if os.path.isfile(iso):
            result["iso"] = iso
        if os.path.isfile(silverlight):
            result["silverlight"] = silverlight
        if os.path.isfile(ucma):
            result["ucma"] = ucma
        if result["iso"] or result["silverlight"] or result["ucma"]:
            return result

    return result


def _print_environment_summary():
    """Muestra comprobaciones básicas sin bloquear la tarea."""
    script = r"""
$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
"HOST=$env:COMPUTERNAME"
"DOMAIN=$($cs.Domain)"
"PART_OF_DOMAIN=$($cs.PartOfDomain)"
"OS=$($os.Caption)"
try {
    $domain = Get-ADDomain -ErrorAction Stop
    "AD_DOMAIN=$($domain.DNSRoot)"
} catch {
    "AD_DOMAIN=No disponible"
}
"""
    ok, output = SysUtils.run_powershell(script, capture=True, timeout=20)
    if output:
        for line in output.splitlines():
            clean = line.strip()
            if clean:
                print(clean)
    if not ok:
        print("[AVISO] No se pudo validar completamente el dominio desde PowerShell.")
    if "PART_OF_DOMAIN=True" not in output:
        print("[AVISO] Este equipo no parece estar unido al dominio. Skype for Business Server normalmente debe instalarse en servidor unido al dominio.")


def _install_windows_features(features, payload_root=None, app_base_path=None, app=None):
    """Instala características Windows Server que falten y verifica el resultado real."""
    features = [str(item).strip() for item in features or [] if str(item).strip()]
    if not features:
        print("[AVISO] No hay características definidas para instalar.")
        return True

    missing_before = SysUtils.missing_windows_features(features)
    if not missing_before:
        print("[OK] Todas las características de Windows necesarias ya estaban instaladas.")
        return True

    print(f"[INFO] Características pendientes: {len(missing_before)}")
    for feature in missing_before:
        print(f" - {feature}")

    sxs_source, sxs_detail = SysUtils.find_sxs_source(
        payload_root,
        app_base_path,
        auto_mount_netfx_iso=True,
        return_detail=True,
    )
    if app is not None:
        try:
            app._last_netfx35_sxs_detail = sxs_detail
        except Exception:
            pass
    if sxs_source:
        print(f"[INFO] Origen local Sources\\SxS detectado: {sxs_source}")
        print("[INFO] Instalacion offline: se usara el origen local, no Windows Update/WSUS.")
    else:
        expected_iso = sxs_detail.get("expected_iso_path", "")
        iso_path = sxs_detail.get("iso_path", "")
        mount_error = sxs_detail.get("mount_error", "")
        if not iso_path:
            print("[ERROR] No se encuentra la ISO de recursos para .NET Framework 3.5.")
            print(f"[INFO] Ruta esperada: {expected_iso}")
            print("[INFO] Debe existir OTROS\\NetFramework3.5.iso dentro de la carpeta de recursos de Easy Deploy.")
        elif mount_error:
            print("[ERROR] No se pudo montar automaticamente la ISO de .NET Framework 3.5.")
            print(f"[INFO] ISO detectada: {iso_path}")
            print(f"[INFO] Detalle: {mount_error}")
        else:
            print("[ERROR] La ISO de .NET Framework 3.5 no contiene Sources\\SxS accesible.")
            print(f"[INFO] ISO detectada: {iso_path}")
        print("[INFO] Instalacion offline: no se intentara usar Windows Update ni WSUS.")
        print("[INFO] Corrige la ISO de recursos y repite 'Prerrequisitos Skype'.")
        return False

    feature_array = _ps_array(features)
    missing_array = _ps_array(missing_before)
    source_literal = SysUtils.ps_quote(sxs_source)

    script = f"""
$ErrorActionPreference = 'Stop'
$features = {feature_array}
$missingNames = {missing_array}
$source = {source_literal}

if ($missingNames.Count -eq 0) {{
    Write-Output "[OK] Todas las caracteristicas ya estaban instaladas."
    exit 0
}}

try {{
    $params = @{{
        Name = $missingNames
        IncludeManagementTools = $true
        ErrorAction = 'Stop'
    }}

    if (-not ($source -and (Test-Path -LiteralPath $source))) {{
        Write-Output "[FAIL] No existe el origen local Sources\\SxS indicado: $source"
        exit 21
    }}

    $params.Source = $source
    Write-Output "[INFO] Usando origen local offline: $source"

    $result = Install-WindowsFeature @params
    $result | Format-Table -AutoSize | Out-String | Write-Output
}} catch {{
    Write-Output "[FAIL] Install-WindowsFeature fallo: $($_.Exception.Message)"
    exit 20
}}

$remaining = @(Get-WindowsFeature -Name $features -ErrorAction SilentlyContinue | Where-Object {{ -not $_.Installed }} | Select-Object -ExpandProperty Name)
if ($remaining.Count -gt 0) {{
    Write-Output "[FAIL] Siguen faltando caracteristicas:"
    $remaining | ForEach-Object {{ Write-Output " - $_" }}
    exit 30
}}

Write-Output "[OK] Caracteristicas de Windows instaladas correctamente."
"""
    ok, output = SysUtils.run_powershell(script, capture=True, timeout=1800)
    if output:
        for line in output.splitlines():
            if line.strip():
                print(line.rstrip())

    remaining = SysUtils.missing_windows_features(features)
    if remaining:
        print("[ERROR] Siguen faltando características de Windows:")
        for feature in remaining:
            print(f" - {feature}")
        if output and "0x8024402c" in output:
            print("[INFO] El código 0x8024402c suele aparecer cuando Windows no puede consultar Windows Update/WSUS o el origen de características.")
        print("[INFO] Solucion recomendada: reinicia si procede, revisa OTROS\\NetFramework3.5.iso y repite esta tarea para usar Sources\\SxS.")
        print("[INFO] Easy Deploy no usara Internet/Windows Update para completar estos prerrequisitos.")
        return False

    if not ok:
        print("[AVISO] PowerShell devolvió error, pero la verificación final indica que las características ya están instaladas.")
    return True


def _install_exe_silent(exe_path, args, label):
    """Ejecuta un instalador EXE en modo silencioso si existe y verifica instalación cuando es posible."""
    if not exe_path or not os.path.isfile(exe_path):
        print(f"[AVISO] No se encontró instalador para {label}.")
        return False

    if _is_prereq_installed(label):
        print(f"[OK] {label} ya estaba instalado.")
        return True

    quoted_args = ", ".join(SysUtils.ps_quote(arg) for arg in (args or []))
    script = f"""
$ErrorActionPreference = 'Stop'
$exe = {SysUtils.ps_quote(exe_path)}
$argsList = @({quoted_args})
try {{
    $p = Start-Process -FilePath $exe -ArgumentList $argsList -Wait -PassThru
    "EXITCODE=$($p.ExitCode)"
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {{
        throw "{label} devolvio codigo $($p.ExitCode)"
    }}
}} catch {{
    Write-Output "[FAIL] {label}: $($_.Exception.Message)"
    exit 40
}}
"""
    ok, output = SysUtils.run_powershell(script, capture=True, timeout=900)
    if output:
        for line in output.splitlines():
            if line.strip():
                print(line.rstrip())

    if ok:
        print(f"[OK] {label} instalado o ya presente.")
        return True

    if _is_prereq_installed(label):
        print(f"[OK] {label} aparece instalado tras el intento.")
        return True

    print(f"[AVISO] Instalación silenciosa de {label} no confirmada.")
    print(f"[INFO] Puedes ejecutarlo manualmente desde: {exe_path}")
    return False


def _is_prereq_installed(label):
    """Comprueba por registro si un prerequisito conocido ya está instalado."""
    patterns = PREREQ_INSTALL_CHECKS.get(label)
    if not patterns:
        return False
    try:
        return bool(SysUtils.is_program_installed(patterns))
    except Exception:
        return False


def _ps_array(values):
    """Convierte una lista de strings en un array literal seguro de PowerShell."""
    return "@(" + ",".join(SysUtils.ps_quote(value) for value in values) + ")"


def _find_skype_setup(drive_root):
    candidates = [
        os.path.join(drive_root, "Setup", "amd64", "Setup.exe"),
        os.path.join(drive_root, "setup", "amd64", "Setup.exe"),
        os.path.join(drive_root, "Setup.exe"),
        os.path.join(drive_root, "setup.exe"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    for root, _dirs, files in os.walk(drive_root):
        for name in files:
            if name.casefold() == "setup.exe":
                return os.path.join(root, name)
    return ""
