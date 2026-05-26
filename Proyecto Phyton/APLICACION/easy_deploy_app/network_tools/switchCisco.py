#IMPORTACIONES DE MÓDULOS
import serial                  #PERMITE USAR EL PUERTO COM
import serial.tools.list_ports #DETECTA PUERTOS DISPONIBLES
import ipaddress
import sys
import time                    #PERMITE MANEJAR PAUSAS Y MEDICIONES DE TIEMPO
import re                      #NOS SIRVE PARA INTERPRETAR RESPUESTAS DEL SWITCH
import os                      #PERMITE INTERACTUAR CON EL SISTEMA OPERATIVO
from datetime import datetime  #FECHA Y HORA ACTUAL
from pathlib import Path

gestion_ip = None  #AQUI GUARDAREMOS LA IP CONFIGURADA PARA HACER PING O SSH
SWITCH_VENDOR = "cisco"

PROMPT_RE = re.compile(r"(?m)(?:^|[\r\n])[^\r\n]*(?:\([^\r\n]*\))?[>#]\s*$")
CONTROL_CHARS_RE = re.compile(r"[\r\n\x00-\x1f\x7f]")
CLI_ERROR_PATTERNS = (
    "% Invalid input",
    "% Incomplete command",
    "% Ambiguous command",
    "% Bad IP address",
    "% Unknown command",
    "% Unrecognized command",
    "Invalid input",
    "Incomplete command",
)
MORE_MARKERS = ("--More--", "---- More ----", "More: <space>")


def _decode_serial(data):
    return data.decode("utf-8", errors="ignore") if data else ""


def _has_prompt(text):
    return bool(PROMPT_RE.search(text or ""))


def _has_expected(text, expected):
    if isinstance(expected, (tuple, list, set)):
        return any(_has_expected(text, item) for item in expected)
    if expected is None:
        return _has_prompt(text)
    expected = str(expected)
    if expected in {">", "#"}:
        return _has_prompt(text)
    return expected in text


def _write_line(con, value):
    line = "" if value is None else str(value)
    if CONTROL_CHARS_RE.search(line):
        raise ValueError("Entrada bloqueada: no se permiten saltos de linea ni caracteres de control.")
    con.write((line.strip() + "\r\n").encode("utf-8"))
    try:
        con.flush()
    except Exception:
        pass


def _read_until(con, expected="#", timeout=8, mostrar=True, hard_timeout=None):
    buffer = ""
    start = time.monotonic()
    idle_deadline = start + max(timeout, 1)
    hard_deadline = start + (hard_timeout or max(timeout * 4, timeout + 15))

    while time.monotonic() < hard_deadline:
        try:
            data = con.read_all()
        except serial.SerialException as exc:
            print(f"Error leyendo del puerto serie: {exc}")
            break

        if data:
            text = _decode_serial(data)
            buffer += text
            for marker in MORE_MARKERS:
                if marker in buffer:
                    try:
                        con.write(b" ")
                    except serial.SerialException as exc:
                        print(f"Error respondiendo a paginacion: {exc}")
                        break
                    buffer = buffer.replace(marker, "")
            if _has_expected(buffer, expected):
                break
            idle_deadline = time.monotonic() + max(timeout, 1)
        elif time.monotonic() >= idle_deadline:
            print(f"Aviso: tiempo de espera agotado esperando '{expected}'.")
            break

        time.sleep(0.15)

    if mostrar and buffer:
        print(buffer)
    if any(pattern in buffer for pattern in CLI_ERROR_PATTERNS):
        print("Aviso: el switch devolvio un error de CLI. Revisa el comando anterior.")
    return buffer


def enviar(con, comando, espera_prompt="#", timeout=8, mostrar=True):
    try:
        _write_line(con, comando)
    except (ValueError, serial.SerialException) as exc:
        print(f"No se pudo enviar el comando de forma segura: {exc}")
        return ""
    return _read_until(con, espera_prompt, timeout=timeout, mostrar=mostrar)


def enviar_interactivo(con, comando, respuestas, timeout=60, mostrar=True):
    try:
        _write_line(con, comando)
    except (ValueError, serial.SerialException) as exc:
        print(f"No se pudo enviar el comando interactivo: {exc}")
        return ""

    buffer = ""
    usados = set()
    deadline = time.monotonic() + timeout
    respuestas = [(re.compile(patron, re.IGNORECASE), respuesta) for patron, respuesta in respuestas]

    while time.monotonic() < deadline:
        try:
            data = con.read_all()
        except serial.SerialException as exc:
            print(f"Error leyendo del puerto serie: {exc}")
            break

        if data:
            buffer += _decode_serial(data)
            respondio = False
            for idx, (patron, respuesta) in enumerate(respuestas):
                if idx not in usados and patron.search(buffer):
                    try:
                        con.write((respuesta + "\r\n").encode("utf-8"))
                    except serial.SerialException as exc:
                        print(f"Error respondiendo a confirmacion: {exc}")
                        return buffer
                    usados.add(idx)
                    deadline = time.monotonic() + timeout
                    buffer = ""
                    respondio = True
                    break
            if respondio:
                continue
            if _has_prompt(buffer):
                break
        time.sleep(0.2)

    if mostrar and buffer:
        print(buffer)
    return buffer


def pedir_texto(prompt, campo="valor", max_len=128, patron=None, requerido=True):
    while True:
        valor = input(prompt).strip()
        if not valor and not requerido:
            return ""
        if not valor:
            print(f"{campo} no puede estar vacio.")
            continue
        if len(valor) > max_len:
            print(f"{campo} es demasiado largo (maximo {max_len} caracteres).")
            continue
        if CONTROL_CHARS_RE.search(valor):
            print(f"{campo} contiene caracteres no permitidos.")
            continue
        if patron and not re.fullmatch(patron, valor):
            print(f"{campo} tiene un formato no valido.")
            continue
        return valor


def pedir_numero(prompt, minimo, maximo, campo="numero"):
    while True:
        valor = input(prompt).strip()
        try:
            numero = int(valor)
        except ValueError:
            print(f"{campo} debe ser numerico.")
            continue
        if minimo <= numero <= maximo:
            return str(numero)
        print(f"{campo} debe estar entre {minimo} y {maximo}.")


def pedir_ipv4(prompt, campo="IP"):
    while True:
        valor = input(prompt).strip()
        try:
            return str(ipaddress.IPv4Address(valor))
        except ValueError:
            print(f"{campo} no es una IPv4 valida.")


def pedir_prefijo(prompt):
    while True:
        valor = input(prompt).strip().lstrip("/")
        try:
            numero = int(valor)
        except ValueError:
            print("Prefijo no valido. Ejemplo: /24")
            continue
        if 0 <= numero <= 32:
            return f"/{numero}"
        print("Prefijo no valido. Debe estar entre /0 y /32.")


def pedir_interfaz(prompt):
    return pedir_texto(prompt, "interfaz", 64, r"[A-Za-z][A-Za-z0-9/._:-]*")


def parece_interfaz_allied(interfaz):
    texto = (interfaz or "").strip().lower()
    return texto.startswith("port") and not texto.startswith("port-channel")


def validar_interfaz_cisco(interfaz):
    if parece_interfaz_allied(interfaz):
        print(
            f"Interfaz no valida para Cisco IOS: {interfaz}\n"
            "El formato port1.0.1 es de Allied Telesis. En Cisco usa el nombre real del puerto, "
            "por ejemplo Gi0/1, GigabitEthernet0/1, FastEthernet0/1 o Ethernet1/1."
        )
        return False
    return True


def pedir_hostname(prompt):
    return pedir_texto(prompt, "hostname", 63, r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


def pedir_nombre_ios(prompt, campo="nombre"):
    return pedir_texto(prompt, campo, 64, r"[A-Za-z0-9_.:-]+")


def pedir_secreto(prompt):
    while True:
        valor = pedir_texto(prompt, "contrasena", 128)
        if any(c.isspace() for c in valor):
            print("La contrasena no debe contener espacios para evitar errores de CLI.")
            continue
        return valor


def confirmar(prompt):
    return input(prompt).strip().lower() in {"s", "si", "y", "yes"}


def carpeta_ejecutable():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def ruta_backup_segura(nombre):
    nombre = Path(nombre).name if nombre else f"backup_switch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    if not re.fullmatch(r"[A-Za-z0-9_. -]{1,80}", nombre):
        nombre = f"backup_switch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    if not Path(nombre).suffix:
        nombre += ".txt"
    return carpeta_ejecutable() / nombre


def es_cisco():
    return SWITCH_VENDOR == "cisco"


def es_allied():
    return SWITCH_VENDOR == "allied"


def prefijo_a_mascara(prefijo):
    return str(ipaddress.IPv4Network(f"0.0.0.0/{prefijo.lstrip('/')}").netmask)


def salida_tiene_error(salida):
    salida = salida or ""
    return any(pattern.lower() in salida.lower() for pattern in CLI_ERROR_PATTERNS)

# ==========================================================
# FUNCIONES BASE DE COMUNICACIÓN
# ==========================================================

# ==========================================================
# LOGIN Y DETECCIÓN DE PUERTOS
# ==========================================================
def test_port_available(device, baudrate=9600, timeout=1):
    """
    Intenta abrir el puerto y lo cierra inmediatamente para comprobar disponibilidad.
    Devuelve True si está libre, False si está en uso o no se puede abrir.
    """
    try:
        with serial.Serial(device, baudrate, timeout=timeout):
            return True
    except (serial.SerialException, OSError):
        return False
    
def seleccionar_puerto():
    """
    Lista puertos serie y permite seleccionar uno. Si el puerto está en uso (p. ej. por MobaXterm)
    ofrece opciones para cerrar la conexión externa, elegir otro puerto o salir.
    """
    while True:
        puertos = list(serial.tools.list_ports.comports())
        if not puertos:
            print("No se detectaron puertos serie.")
            raise SystemExit(1)

        print("\nPuertos serie disponibles:")
        for i, p in enumerate(puertos):
            print(f"{i+1}: {p.device} - {p.description}")

        eleccion = input("\nSelecciona el puerto COM (numero o nombre, ej. COM3): ").strip()
        if eleccion.upper().startswith("COM"):
            seleccion = next((p for p in puertos if p.device.upper() == eleccion.upper()), None)
            if seleccion is None:
                print("Puerto COM no encontrado. Intenta de nuevo.")
                continue
            device = seleccion.device
        else:
            try:
                indice = int(eleccion)
                if not (1 <= indice <= len(puertos)):
                    print("Numero fuera de rango. Intenta de nuevo.")
                    continue
            except ValueError:
                print("Entrada no valida. Introduce el numero o el nombre del puerto COM.")
                continue
            device = puertos[indice - 1].device

        # Test de disponibilidad
        if test_port_available(device):
            return device

        # Si está en uso, ofrecer opciones al usuario
        print(f"\nEl puerto {device} parece estar en uso (p. ej. MobaXterm u otra aplicación).")
        print("Opciones:")
        print("  1) Cerrar la conexión en MobaXterm y presionar Enter para reintentar")
        print("  2) Elegir otro puerto")
        print("  3) Salir")

        opcion = input("Selecciona opción (1/2/3) [1]: ").strip() or "1"
        if opcion == "1":
            input("Cierra la sesión en MobaXterm en ese puerto y pulsa Enter cuando esté cerrado...")
            # Se reitera el bucle y se refresca la lista de puertos
            continue
        elif opcion == "2":
            # Repetir bucle para elegir otro puerto
            continue
        else:
            print("Saliendo.")
            raise SystemExit(1)


def login(con):
    print("Verificando estado de sesion...")

    try:
        con.reset_input_buffer()
        con.write(b"\r\n")
        time.sleep(0.4)
        con.write(b"\r\n")
    except serial.SerialException as exc:
        print(f"No se pudo comunicar con el switch: {exc}")
        return False

    salida = _read_until(con, ("Username", "login:", "Password:", ">", "#"), timeout=3, mostrar=False)

    if _has_prompt(salida):
        print("Sesion detectada en el switch.")
        enviar(con, "terminal length 0", espera_prompt=("#", ">"), timeout=5, mostrar=False)
        if ">" in salida:
            salida_enable = enviar(con, "enable", espera_prompt=("#", "Password:", ">"), timeout=8, mostrar=False)
            if "#" in salida_enable:
                enviar(con, "terminal length 0", espera_prompt=("#", ">"), timeout=5, mostrar=False)
                return True
            if "Password" in salida_enable:
                for _ in range(3):
                    enable_pass = input("Contrasena de enable: ")
                    salida_enable = enviar(con, enable_pass, espera_prompt=("#", ">"), timeout=8, mostrar=False)
                    if "#" in salida_enable:
                        enviar(con, "terminal length 0", espera_prompt=("#", ">"), timeout=5, mostrar=False)
                        return True
                print("No se pudo entrar en modo privilegiado.")
                return False
            print("No se pudo entrar en modo privilegiado.")
            return False
        return True

    print("Iniciando sesion en el switch...")
    for _ in range(3):
        if "Username" in salida or "login:" in salida.lower():
            usuario = pedir_texto("Usuario del switch: ", "usuario", 64, r"[A-Za-z0-9_.@-]+")
            salida = enviar(con, usuario, espera_prompt=("Password:", ">", "#"), timeout=8, mostrar=False)

        if "Password" in salida or not salida.strip():
            password = input("Contrasena del switch: ")
            salida = enviar(con, password, espera_prompt=("#", ">"), timeout=10, mostrar=False)

        if _has_prompt(salida):
            salida_enable = enviar(con, "enable", espera_prompt=("#", "Password:", ">"), timeout=8, mostrar=False)
            if "Password" in salida_enable:
                enable_pass = input("Contrasena de enable: ")
                salida_enable = enviar(con, enable_pass, espera_prompt=("#", ">"), timeout=8, mostrar=False)
            if "#" not in salida_enable and ">" in salida_enable:
                print("Login correcto, pero no se pudo entrar en modo privilegiado.")
                return False
            if ">" not in salida_enable:
                enviar(con, "terminal length 0", espera_prompt=("#", ">"), timeout=5, mostrar=False)
            print("Login correcto")
            return True

        print("Usuario o contrasena incorrectos, intenta de nuevo.")

    print("No se pudo iniciar sesion en el switch tras 3 intentos.")
    return False


def detectar_tipo_switch(con):
    global SWITCH_VENDOR

    salida = enviar(con, "show version", espera_prompt=("#", ">"), timeout=10, mostrar=False)
    texto = salida.lower()

    if "cisco" in texto or "ios software" in texto or "cisco ios" in texto:
        SWITCH_VENDOR = "cisco"
        print("Switch Cisco IOS detectado.")
        return True

    prompt = enviar(con, "", espera_prompt=("#", ">"), timeout=3, mostrar=False).lower()
    if "cisco" in prompt:
        SWITCH_VENDOR = "cisco"
        print("Switch Cisco IOS detectado por prompt.")
        return True

    if "alliedware" in texto or "allied telesis" in texto or "awplus" in texto:
        print("Este equipo parece Allied Telesis. Vuelve a Redes y usa el boton 'Switch Allied'.")
    else:
        print("No se ha detectado un switch Cisco IOS.")
        print("Revisa el puerto de consola o usa el boton adecuado en Redes.")
    return False

# ==========================================================
# OBTENER Y PARSEAR CONFIGURACIÓN
# ==========================================================

def obtener_running_config(con):
    print("\nObteniendo configuracion completa del switch...")
    try:
        con.reset_input_buffer()
    except serial.SerialException as exc:
        print(f"No se pudo limpiar el buffer serie: {exc}")
        return ""
    enviar(con, "terminal length 0", espera_prompt=("#", ">"), timeout=5, mostrar=False)
    salida = enviar(con, "show running-config", espera_prompt=("#", ">"), timeout=20, mostrar=False)
    if salida:
        print("Configuracion recibida correctamente.\n")
    else:
        print("No se recibio configuracion del switch.\n")
    return salida


def parsear_running_config(config_texto):
    datos = {"hostname": None, "gestion_ip": None, "vlanes": [], "usuarios": [], "puertos": []}
    vlan_actual = None
    interfaz_actual = None
    puerto_actual = None

    for linea in config_texto.splitlines():
        linea = linea.strip()

        if linea.startswith("hostname "):
            partes = linea.split(maxsplit=1)
            if len(partes) == 2:
                datos["hostname"] = partes[1]

        elif linea.startswith("vlan "):
            partes = linea.split()
            if len(partes) >= 2 and partes[1].isdigit():
                vlan_actual = partes[1]
                nombre = None
                if "name" in partes:
                    idx = partes.index("name")
                    nombre = " ".join(partes[idx + 1:]) or None
                datos["vlanes"].append((vlan_actual, nombre))

        elif linea.startswith("name ") and vlan_actual:
            nombre = linea.split(maxsplit=1)[1] if len(linea.split(maxsplit=1)) == 2 else None
            if datos["vlanes"]:
                datos["vlanes"][-1] = (vlan_actual, nombre)

        elif linea.startswith("username "):
            partes = linea.split()
            if len(partes) >= 3:
                usuario = partes[1]
                datos["usuarios"].append(usuario)

        elif linea.startswith("interface "):
            interfaz = linea.split()[1]
            interfaz_actual = interfaz
            puerto_actual = {"interfaz": interfaz, "modo": None, "descripcion": None, "vlans": None}
            datos["puertos"].append(puerto_actual)

        elif interfaz_actual and puerto_actual:
            if linea.startswith("description "):
                puerto_actual["descripcion"] = linea.split(maxsplit=1)[1]
            elif "access vlan" in linea:
                puerto_actual["modo"] = "access"
                puerto_actual["vlans"] = linea.split()[-1]
            elif "trunk allowed vlan" in linea:
                puerto_actual["modo"] = "trunk"
                puerto_actual["vlans"] = linea.split()[-1]
            elif re.match(r"ip address \d+\.\d+\.\d+\.\d+", linea):
                ip_match = re.findall(r"(\d+\.\d+\.\d+\.\d+)", linea)
                if ip_match:
                    datos["gestion_ip"] = ip_match[0]

        elif re.match(r"ip address \d+\.\d+\.\d+\.\d+", linea):
            ip_match = re.findall(r"(\d+\.\d+\.\d+\.\d+)", linea)
            if ip_match:
                datos["gestion_ip"] = ip_match[0]

        if linea == "!":
            vlan_actual = None
            interfaz_actual = None
            puerto_actual = None

    datos["puertos"] = [
        (p["interfaz"], p["modo"], p["descripcion"], p["vlans"])
        for p in datos["puertos"]
    ]
    return datos


def mostrar_resumen_config(datos):
    print("=" * 70)
    print("ESTADO ACTUAL DEL SWITCH")
    print("=" * 70)
    print(f"Hostname: {datos.get('hostname') or 'Desconocido'}")
    print(f"IP de gestión: {datos.get('gestion_ip') or 'No configurada'}")
    print("\nVLANES CONFIGURADAS:")
    if datos["vlanes"]:
        for v in datos["vlanes"]:
            print(f"  - VLAN {v[0]} → {v[1] or 'Sin nombre'}")
    else:
        print("  (No hay VLANs configuradas)")

    print("\nUSUARIOS:")
    if datos["usuarios"]:
        for u in datos["usuarios"]:
            print(f"  - {u}")
    else:
        print("  (No hay usuarios configurados)")

    print("\nPUERTOS:")
    if datos["puertos"]:
        for p in datos["puertos"]:
            print(f"  - {p[0]}: {p[1] or 'N/A'} | VLANs: {p[3] or '-'} | {p[2] or ''}")
    else:
        print("  (No hay puertos configurados)")
    print("=" * 70)


# ==========================================================
# FUNCIONES DE CONFIGURACIÓN
# ==========================================================

def cambiar_hostname(con):
    nuevo_nombre = pedir_hostname("Introduce el nuevo hostname: ")
    enviar(con, "conf t")
    enviar(con, f"hostname {nuevo_nombre}")
    enviar(con, "end")
    print(f"Hostname cambiado a {nuevo_nombre}")


def _crear_vlan_cisco(con, vlan_id, nombre):
    salida = ""
    salida += enviar(con, "configure terminal")
    salida += enviar(con, f"vlan {vlan_id}")
    salida += enviar(con, f"name {nombre}")
    enviar(con, "state active", mostrar=False)
    enviar(con, "no shutdown", mostrar=False)
    salida += enviar(con, "exit")
    salida += enviar(con, "end")
    return salida


def _crear_vlan_allied(con, vlan_id, nombre):
    salida = ""
    salida += enviar(con, "conf t")
    salida += enviar(con, "vlan database")
    salida += enviar(con, f"vlan {vlan_id} name {nombre}")
    salida += enviar(con, "end")
    return salida


def crear_vlan(con):
    vlan_id = pedir_numero("ID de la VLAN: ", 1, 4094, "VLAN")
    nombre = pedir_nombre_ios("Nombre de la VLAN: ", "nombre de VLAN")

    vtp_status = enviar(con, "show vtp status", timeout=8, mostrar=False)
    if re.search(r"operating mode\s*:\s*client", vtp_status or "", re.IGNORECASE):
        print(
            "El switch esta en VTP Client. En ese modo Cisco IOS no permite crear VLANs localmente.\n"
            "Cambia VTP a transparent/server o crea la VLAN en el servidor VTP antes de continuar."
        )
        return

    salida = _crear_vlan_cisco(con, vlan_id, nombre)
    if salida_tiene_error(salida):
        print(f"No se pudo confirmar la creacion de la VLAN {vlan_id}. Revisa el mensaje del switch.")
        return

    verificar = enviar(con, "show vlan brief", timeout=10, mostrar=False)
    if re.search(rf"(^|\s){re.escape(vlan_id)}(\s|$)", verificar):
        print(f"VLAN {vlan_id} ({nombre}) creada y detectada en la tabla VLAN.")
    else:
        print(f"VLAN {vlan_id} ({nombre}) enviada. Si no aparece, revisa 'show vlan brief' en el switch.")


def parsear_puertos(puertos_str):
    resultado = []
    grupos = [x.strip() for x in puertos_str.split(",") if x.strip()]
    for g in grupos:
        if "-" in g:
            inicio, fin = [x.strip() for x in g.split("-", 1)]
            m_inicio = re.match(r"^(.*?)(\d+)$", inicio)
            m_fin = re.match(r"^(.*?)(\d+)$", fin)
            if not m_inicio or not m_fin:
                raise ValueError(f"Rango de puertos no valido: {g}")
            prefijo = m_inicio.group(1)
            n1 = int(m_inicio.group(2))
            n2 = int(m_fin.group(2))
            if n2 < n1:
                raise ValueError(f"Rango invertido: {g}")
            if n2 - n1 > 128:
                raise ValueError("Rango demasiado grande; limita la operacion a 129 puertos como maximo.")
            for i in range(n1, n2 + 1):
                resultado.append(f"{prefijo}{i}")
        else:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9/._:-]*", g):
                raise ValueError(f"Puerto no valido: {g}")
            resultado.append(g)
    if not resultado:
        raise ValueError("No se ha indicado ningun puerto.")
    return resultado


def configurar_puertos(con):
    puertos_str = pedir_texto("Puertos Cisco (ej: Gi0/1-Gi0/4,GigabitEthernet0/6,Eth1/32): ", "puertos", 300, r"[A-Za-z0-9/._:,\- ]+")
    try:
        interfaces = parsear_puertos(puertos_str)
    except ValueError as exc:
        print(exc)
        return
    if not all(validar_interfaz_cisco(interfaz) for interfaz in interfaces):
        return
    descripcion = pedir_texto("Descripcion (opcional): ", "descripcion", 80, requerido=False)
    modo = pedir_texto("Modo del puerto (access/trunk): ", "modo", 6, r"access|trunk").lower()

    vlan_id = None
    vlans = None
    if modo == "access":
        vlan_id = pedir_numero("VLAN ID para los puertos access: ", 1, 4094, "VLAN")
    elif modo == "trunk":
        vlans = pedir_texto("Introduce VLANs permitidas (ej: 10,20,30 o 10-20): ", "lista de VLANs", 128, r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*")

    salida = _configurar_puertos_cisco(con, interfaces, descripcion, modo, vlan_id, vlans)
    if salida_tiene_error(salida):
        print("La configuracion Cisco ha devuelto error. Revisa que los nombres de interfaz sean IOS, por ejemplo Gi0/1 o GigabitEthernet0/1.")


def _configurar_puertos_cisco(con, interfaces, descripcion, modo, vlan_id, vlans):
    salida = ""
    salida += enviar(con, "configure terminal")

    if modo == "access" and vlan_id:
        salida += enviar(con, f"vlan {vlan_id}")
        enviar(con, "state active", mostrar=False)
        enviar(con, "no shutdown", mostrar=False)
        salida += enviar(con, "exit")

    for interfaz in interfaces:
        salida_interfaz = enviar(con, f"interface {interfaz}")
        salida += salida_interfaz
        if salida_tiene_error(salida_interfaz):
            print(
                f"No se pudo entrar en la interfaz {interfaz}. Revisa el nombre exacto con "
                "'show ip interface brief' o 'show interface status'."
            )
            salida += enviar(con, "end")
            return salida
        if descripcion:
            salida += enviar(con, f"description {descripcion}")
        if modo == "access":
            salida += enviar(con, "switchport mode access")
            salida += enviar(con, f"switchport access vlan {vlan_id}")
        elif modo == "trunk":
            salida_encapsulation = enviar(con, "switchport trunk encapsulation dot1q", mostrar=False)
            if not salida_tiene_error(salida_encapsulation):
                salida += salida_encapsulation
            salida += enviar(con, "switchport mode trunk")
            salida_trunk = enviar(con, f"switchport trunk allowed vlan add {vlans}")
            salida += salida_trunk
        salida += enviar(con, "no shutdown")
        salida += enviar(con, "exit")
        print(f"{interfaz} configurado como {modo} en modo Cisco IOS")

    salida += enviar(con, "end")
    for interfaz in interfaces:
        verificar = enviar(con, f"show running-config interface {interfaz}", timeout=10, mostrar=False)
        if modo == "access" and f"switchport access vlan {vlan_id}" in verificar:
            print(f"Verificado: {interfaz} esta en access VLAN {vlan_id}.")
        elif modo == "trunk" and "switchport trunk allowed vlan" in verificar:
            print(f"Verificado: {interfaz} tiene VLANs permitidas en trunk.")
        else:
            print(f"No se pudo verificar la configuracion final de {interfaz}. Revisa 'show running-config interface {interfaz}'.")
    return salida


def crear_usuario(con):
    usuario = pedir_texto("Nombre de usuario: ", "usuario", 64, r"[A-Za-z0-9_.@-]+")
    clave = pedir_secreto("Contrasena: ")
    enviar(con, "conf t")
    enviar(con, f"username {usuario} privilege 15 secret {clave}")
    enviar(con, "end")
    print(f"Usuario {usuario} creado correctamente.")


def habilitar_ping_ssh(con):
    global gestion_ip
    vlan_id = pedir_numero("VLAN de gestion (CREADA PREVIAMENTE): ", 1, 4094, "VLAN")
    ip = pedir_ipv4("Direccion IP de gestion: ", "IP de gestion")
    mascara = pedir_prefijo("Mascara (ej. /24): ")
    gateway = pedir_ipv4("Gateway (ej. 192.168.1.1): ", "gateway")
    troncal = pedir_interfaz("Puerto troncal (ej. Gi0/1 o GigabitEthernet0/1): ")
    if not validar_interfaz_cisco(troncal):
        return

    enviar(con, "configure terminal")
    enviar(con, f"interface vlan {vlan_id}", espera_prompt="#")
    enviar(con, f"ip address {ip} {prefijo_a_mascara(mascara)}", espera_prompt="#")
    enviar(con, "no shutdown", espera_prompt="#")
    enviar(con, "exit", espera_prompt="#")
    enviar(con, f"ip default-gateway {gateway}", espera_prompt="#")
    enviar(con, "ip domain-name easydeploy.local", espera_prompt="#")
    enviar_interactivo(
        con,
        "crypto key generate rsa modulus 2048",
        [(r"replace them|replace.*keys|yes/no", "yes"), (r"\[yes/no\]", "yes")],
        timeout=60,
    )
    enviar(con, "ip ssh version 2", espera_prompt="#")
    enviar(con, "line vty 0 4", espera_prompt="#")
    enviar(con, "transport input ssh", espera_prompt="#")
    enviar(con, "login local", espera_prompt="#")
    enviar(con, "exit", espera_prompt="#")
    enviar(con, f"interface {troncal}", espera_prompt="#")
    enviar(con, "switchport mode trunk", espera_prompt="#")
    enviar(con, f"switchport trunk allowed vlan add {vlan_id}", espera_prompt="#")
    enviar(con, "end")
    gestion_ip = ip
    print(f"SSH y gestión habilitados en {ip}")


def guardar_config(con):
    enviar(con, "write memory", timeout=30)
    print("Configuración guardada en memoria.")


def hacer_backup(con):
    print("\nCreando copia de seguridad del running-config...")
    config = obtener_running_config(con)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"backup_running_config_{fecha}.txt"
    ruta = ruta_backup_segura(nombre_archivo)
    print(f"La copia se guardara junto al ejecutable, en:\n{ruta}")
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(config)
    except OSError as exc:
        print(f"No se pudo guardar la copia de seguridad en la carpeta del ejecutable: {exc}")
        return
    print(f"Copia de seguridad guardada en:\n{ruta}\n")


def restaurar_fabrica(con):
    if not confirmar("Esto restaurara el switch a fabrica. Seguro? (s/n): "):
        print("Operación cancelada.")
        return
    enviar_interactivo(
        con,
        "write erase",
        [(r"\[confirm\]|confirm", ""), (r"\(y/n\)|\[yes/no\]", "y")],
        timeout=45,
    )
    enviar_interactivo(
        con,
        "reload",
        [
            (r"save\?|modified|system configuration has been modified", "no"),
            (r"\[confirm\]|proceed|confirm", ""),
            (r"\(y/n\)|\[yes/no\]|reboot", "y"),
        ],
        timeout=45,
    )
    print("Reiniciando switch...")
    print("Switch restaurado a fábrica.")
    con.close()
    raise SystemExit(0)


# ==========================================================
# MENÚ PRINCIPAL
# ==========================================================

def menu(con):
    while True:
        config_raw = obtener_running_config(con)
        datos = parsear_running_config(config_raw)
        mostrar_resumen_config(datos)

        print("\n" + "="*70)
        print("1. Cambiar hostname")
        print("2. Crear VLAN")
        print("3. Configurar puertos")
        print("4. Crear usuario")
        print("5. Habilitar Ping y SSH")
        print("6. Guardar configuración")
        print("7. Crear copia de seguridad (running-config)")
        print("8. Restaurar a fábrica")
        print("9. Salir")
        print("="*70)
        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            cambiar_hostname(con)
        elif opcion == "2":
            crear_vlan(con)
        elif opcion == "3":
            configurar_puertos(con)
        elif opcion == "4":
            crear_usuario(con)
        elif opcion == "5":
            habilitar_ping_ssh(con)
        elif opcion == "6":
            guardar_config(con)
        elif opcion == "7":
            hacer_backup(con)
        elif opcion == "8":
            restaurar_fabrica(con)
        elif opcion == "9":
            print("Saliendo del programa...")
            break
        else:
            print("Opción inválida.")


# ==========================================================
# MAIN
# ==========================================================

def main():
    """
    Flujo principal: selección de puerto con comprobación, apertura segura y manejo de error
    si no se puede abrir (por estar en uso). Luego continúa con login y menú.
    """
    con = None
    puerto = seleccionar_puerto()
    try:
        con = serial.Serial(puerto, 9600, timeout=1, write_timeout=3)
    except serial.SerialException as e:
        print(f"No se pudo abrir {puerto}: {e}")
        print("Asegurate de que ninguna otra aplicacion (MobaXterm, PuTTY, etc.) tenga abierto el puerto.")
        return
    try:
        time.sleep(2)
        if login(con):
            if detectar_tipo_switch(con):
                menu(con)
            else:
                print("No se abre el menu porque el equipo no coincide con Switch Cisco.")
        else:
            print("No se abre el menu porque no hay sesion valida en el switch.")
    except KeyboardInterrupt:
        print("\nProceso cancelado por el usuario.")
    finally:
        if con is not None and con.is_open:
            con.close()
            print("Conexion cerrada")


if __name__ == "__main__":
    main()


