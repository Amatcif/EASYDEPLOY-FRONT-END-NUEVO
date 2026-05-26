#IMPORTACIONES DE MÓDULOS
import serial                  #PERMITE USAR EL PUERTO COM
import serial.tools.list_ports #DETECTA PUERTOS DISPONIBLES
import ipaddress
import sys
import time                    #PERMITE MANEJAR PAUSAS Y MEDICIONES DE TIEMPO
import re                      #NOS SIRVE PARA INTERPRETAR RESPUESTAS DEL ROUTER
import os                      #PERMITE INTERACTUAR CON EL SISTEMA OPERATIVO
from datetime import datetime  #FECHA Y HORA ACTUAL
from pathlib import Path


PROMPT_RE = re.compile(r"(?m)(?:^|[\r\n])[^\r\n]*(?:\([^\r\n]*\))?[>#]\s*$")
CONTROL_CHARS_RE = re.compile(r"[\r\n\x00-\x1f\x7f]")
CLI_ERROR_PATTERNS = (
    "% Invalid input",
    "% Incomplete command",
    "% Ambiguous command",
    "% Bad IP address",
    "% Unknown command",
    "% Unrecognized command",
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


def _read_until(con, expected="#", timeout=8, mostrar=False, hard_timeout=None):
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
        print("Aviso: el equipo devolvio un error de CLI. Revisa el comando anterior.")
    return buffer


def enviar(con, comando, espera_prompt="#", timeout=8, mostrar=False):
    try:
        _write_line(con, comando)
    except (ValueError, serial.SerialException) as exc:
        print(f"No se pudo enviar el comando de forma segura: {exc}")
        return ""
    return _read_until(con, espera_prompt, timeout=timeout, mostrar=mostrar)


def enviar_interactivo(con, comando, respuestas, timeout=60, mostrar=True):
    """Envia un comando que puede pedir confirmaciones y responde con limites de tiempo."""
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


def pedir_mascara(prompt):
    while True:
        valor = input(prompt).strip()
        try:
            return str(ipaddress.IPv4Network(f"0.0.0.0/{valor}").netmask)
        except ValueError:
            print("Mascara no valida. Usa formato 255.255.255.0.")


def pedir_wildcard(prompt):
    return pedir_ipv4(prompt, "Wildcard")


def pedir_interfaz(prompt):
    return pedir_texto(prompt, "interfaz", 64, r"[A-Za-z][A-Za-z0-9/._:-]*")


def pedir_hostname(prompt):
    return pedir_texto(prompt, "hostname", 63, r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


def pedir_dominio(prompt):
    while True:
        dominio = pedir_texto(prompt, "dominio", 253, r"[A-Za-z0-9.-]+")
        etiquetas = dominio.split(".")
        if all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", e) for e in etiquetas):
            return dominio.lower()
        print("Dominio no valido.")


def pedir_nombre_ios(prompt, campo="nombre"):
    return pedir_texto(prompt, campo, 64, r"[A-Za-z0-9_.:-]+")


def pedir_acl_estandar(prompt):
    while True:
        numero = int(pedir_numero(prompt, 1, 1999, "ACL"))
        if 1 <= numero <= 99 or 1300 <= numero <= 1999:
            return str(numero)
        print("ACL estandar valida: 1-99 o 1300-1999.")


def pedir_acl_extendida(prompt):
    while True:
        numero = int(pedir_numero(prompt, 100, 2699, "ACL"))
        if 100 <= numero <= 199 or 2000 <= numero <= 2699:
            return str(numero)
        print("ACL extendida valida: 100-199 o 2000-2699.")


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
    nombre = (nombre or "").strip()
    if not nombre:
        nombre = f"backup_router_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    nombre = Path(nombre).name
    if not re.fullmatch(r"[A-Za-z0-9_. -]{1,80}", nombre):
        nombre = f"backup_router_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    if not Path(nombre).suffix:
        nombre += ".txt"
    return carpeta_ejecutable() / nombre


# ==========================================================
# FUNCIONES BASE DE COMUNICACIÓN
# ==========================================================

# ==========================================================
# LOGIN Y DETECCIÓN DE PUERTOS
# ==========================================================

def test_port_available(device, baudrate=9600, timeout=1):
    try:
        with serial.Serial(device, baudrate=baudrate, timeout=timeout):
            return True
    except (serial.SerialException, OSError):
        return False


def seleccionar_puerto():
    while True:
        puertos = list(serial.tools.list_ports.comports())
        if not puertos:
            print("No se detectaron puertos serie. Revisa el cable USB/Serial y sus drivers.")
            raise SystemExit(1)

        print("\nPuertos serie disponibles:")
        for i, p in enumerate(puertos, start=1):
            print(f"{i}: {p.device} - {p.description}")

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
            except ValueError:
                print("Entrada no valida. Escribe el numero o el nombre del puerto COM.")
                continue
            if not 1 <= indice <= len(puertos):
                print("Numero fuera de rango.")
                continue
            device = puertos[indice - 1].device
        if test_port_available(device):
            return device

        print(f"\nEl puerto {device} esta ocupado o no se puede abrir.")
        print("Cierra MobaXterm, PuTTY u otra aplicacion que lo use, o elige otro puerto.")
        if not confirmar("Quieres reintentar la seleccion de puerto? (s/n): "):
            raise SystemExit(1)


def _despertar_dispositivo(con):
    try:
        con.reset_input_buffer()
        con.write(b"\r\n")
        time.sleep(0.4)
        con.write(b"\r\n")
    except serial.SerialException as exc:
        print(f"No se pudo comunicar con el router: {exc}")
        return ""
    return _read_until(con, ("Username", "login:", "Password:", ">", "#"), timeout=3, mostrar=False)


def _asegurar_modo_privilegiado(con):
    salida = enviar(con, "terminal length 0", espera_prompt=("#", ">"), timeout=5)
    if "#" in salida:
        return True

    salida = enviar(con, "enable", espera_prompt=("#", "Password:", ">"), timeout=8)
    if "#" in salida:
        enviar(con, "terminal length 0", espera_prompt="#", timeout=5)
        return True

    if "Password" in salida:
        for _ in range(3):
            password = input("Contrasena de enable: ")
            salida = enviar(con, password, espera_prompt=("#", ">"), timeout=8)
            if "#" in salida:
                enviar(con, "terminal length 0", espera_prompt="#", timeout=5)
                return True
            print("Contrasena de enable incorrecta o sin respuesta.")

    return False


def login(con):
    salida = _despertar_dispositivo(con)

    if _has_prompt(salida):
        if _asegurar_modo_privilegiado(con):
            print("Sesion iniciada en modo privilegiado.")
            return True
        print("No se pudo entrar en modo privilegiado.")
        return False

    for _ in range(3):
        if "Username" in salida or "login:" in salida.lower():
            usuario = pedir_texto("Usuario del router: ", "usuario", 64, r"[A-Za-z0-9_.@-]+")
            salida = enviar(con, usuario, espera_prompt=("Password:", ">", "#"), timeout=8)

        if "Password" in salida or not salida.strip():
            password = input("Contrasena del router: ")
            salida = enviar(con, password, espera_prompt=("#", ">"), timeout=10)

        if _has_prompt(salida):
            if _asegurar_modo_privilegiado(con):
                print("Login correcto.")
                return True
            print("Login correcto, pero no se pudo entrar en modo privilegiado.")
            return False

        print("No se detecto un prompt valido. Reintentando login...")
        salida = _despertar_dispositivo(con)

    print("No se pudo iniciar sesion en el router tras 3 intentos.")
    return False



# ==========================================================
# OBTENER Y PARSEAR CONFIGURACIÓN
# ==========================================================
def obtener_running_config(con):
    try:
        con.reset_input_buffer()
    except serial.SerialException as exc:
        print(f"No se pudo limpiar el buffer serie: {exc}")
        return ""
    enviar(con, "terminal length 0", espera_prompt=("#", ">"), timeout=5)
    salida = enviar(con, "show running-config", espera_prompt=("#", ">"), timeout=20, mostrar=False)
    if not salida:
        print("No se recibio configuracion del router.")
    return salida

def parsear_running_config(config, con):
    datos = {
        "hostname": None,
        "interfaces": [],
        "subinterfaces": [],
        "loopbacks": [],
        "ospf": False,
        "ospf_aprende": False,
        "redes_ospf": [],
        "tuneles": [],
        "rutas_estaticas": []
    }

    lineas = config.splitlines()

    for i, linea in enumerate(lineas):
        linea = linea.strip()

        # --- HOSTNAME ---
        if linea.startswith("hostname "):
            datos["hostname"] = linea.split()[1]

        # --- INTERFACES (incluye túneles) ---
        elif linea.startswith("interface "):
            interfaz = linea.split()[1]
            ip = None
            activo = True  # Cisco activa interfaces por defecto

            # Leer el bloque de la interfaz
            j = i + 1
            while j < len(lineas) and not lineas[j].startswith("interface ") and not lineas[j].startswith("!"):
                sub = lineas[j].strip()

                # Detectar IP (aunque tenga espacios delante)
                if sub.lstrip().startswith("ip address"):
                    partes = sub.split()
                    if len(partes) >= 3:
                        ip = partes[2]

                # Detectar shutdown
                if sub == "shutdown":
                    activo = False
                if sub == "no shutdown":
                    activo = True

                j += 1

            # Clasificación
            if "." in interfaz:
                datos["subinterfaces"].append(interfaz)

            elif "Loopback" in interfaz:
                datos["loopbacks"].append(f"{interfaz} ({ip})" if ip else interfaz)

            elif "Tunnel" in interfaz:
                # Los túneles siempre están activos salvo shutdown explícito
                if ip:
                    datos["tuneles"].append(f"{interfaz} ({ip})")

            else:
                # Interfaces físicas activas con IP
                if activo and ip:
                    datos["interfaces"].append(f"{interfaz} ({ip})")

        # --- DETECTAR OSPF ---
        elif linea.startswith("router ospf"):
            datos["ospf"] = True
            j = i + 1
            while j < len(lineas) and not lineas[j].startswith("!"):
                if "network" in lineas[j]:
                    partes = lineas[j].split()
                    if len(partes) >= 4:
                        red = partes[1]
                        wildcard = partes[2]
                        area = partes[4] if len(partes) >= 5 else "?"
                        datos["redes_ospf"].append(f"{red} {wildcard} area {area}")
                j += 1

        # --- RUTAS ESTÁTICAS ---
        elif linea.startswith("ip route"):
            partes = linea.split()
            if len(partes) >= 4:
                destino = partes[2]
                mascara = partes[3]
                via = partes[4] if len(partes) >= 5 else "?"
                datos["rutas_estaticas"].append(f"{destino}/{mascara} → {via}")

    # --- DETECTAR SI APRENDE RUTAS OSPF ---
    salida_rutas = enviar(con, "show ip route", espera_prompt="#", mostrar=False)
    if re.search(r"^O\s", salida_rutas, re.MULTILINE):
        datos["ospf_aprende"] = True

    return datos


def mostrar_resumen_config(datos):
    print("="*70)
    print("RESUMEN DE CONFIGURACIÓN ACTUAL")
    print("="*70)
    print(f"Hostname: {datos['hostname'] or 'No detectado'}")

    print("\nInterfaces activas:")
    for i in datos["interfaces"]:
        print(f"  - {i}")
    if not datos["interfaces"]:
        print("  (Ninguna detectada)")

    print("\nSubinterfaces:")
    for s in datos["subinterfaces"]:
        print(f"  - {s}")
    if not datos["subinterfaces"]:
        print("  (Ninguna detectada)")

    print("\nLoopbacks:")
    for l in datos["loopbacks"]:
        print(f"  - {l}")
    if not datos["loopbacks"]:
        print("  (Ninguna detectada)")

    print("\nOSPF:")
    if datos["ospf"]:
        print("  - OSPF habilitado")
        for r in datos["redes_ospf"]:
            print(f"    ▪ {r}")
        print(f"  - ¿Aprende por OSPF?: {'SI' if datos['ospf_aprende'] else 'NO'}")
    else:
        print("  - OSPF no detectado")

    print("\nTúneles configurados:")
    for t in datos["tuneles"]:
        print(f"  - {t}")
    if not datos["tuneles"]:
        print("  (Ninguno detectado)")

    print("\nRutas estáticas:")
    for r in datos["rutas_estaticas"]:
        print(f"  - {r}")
    if not datos["rutas_estaticas"]:
        print("  (Ninguna detectada)")

    print("="*70)
# ==========================================================
# FUNCIONES CONFIGURACIÓN BÁSICA
# ==========================================================
def cambiar_hostname(con):
    nuevo_nombre = pedir_hostname("Introduce el nuevo hostname: ")
    enviar(con, "conf t")
    enviar(con, f"hostname {nuevo_nombre}")
    enviar(con, "end")
    print(f"Hostname cambiado a {nuevo_nombre}")

def configurar_dominio(con):
    nuevo_dominio = pedir_dominio("Introduce el nombre de dominio: ")
    enviar(con, "conf t")
    enviar(con, f"ip domain-name {nuevo_dominio}")
    enviar(con, "end")
    print(f"Dominio cambiado a {nuevo_dominio}")

def crear_usuario(con):
    nuevo_usuario = pedir_texto("Introduce el nuevo nombre de usuario:\n", "usuario", 64, r"[A-Za-z0-9_.@-]+")
    nueva_contrasena = pedir_secreto("Introduce tu nueva contrasena:\n")
    enviar(con, "conf t")
    enviar(con, f"username {nuevo_usuario} privilege 15 secret 0 {nueva_contrasena}")
    enviar(con, "end")
    print(f"Usuario '{nuevo_usuario}' creado")
    
def configurar_banner(con):
    banner_motd = pedir_texto("Introduce el mensaje que quieres que salga al iniciar el router:\n", "banner", 240)
    delimitador = next((d for d in "#@$%&!" if d not in banner_motd), "#")
    enviar(con, "conf t")
    enviar(con, f"banner motd {delimitador}{banner_motd}{delimitador}")
    enviar(con, "end")
    print("Banner motd cambiado")


# ==========================================================
# FUNCIONES CONFIGURACIÓN DE INTERFACES
# ==========================================================

def configurar_interfaz(con):
    interfaz = pedir_interfaz("Introduce el nombre de la interfaz (ejemplo: GigabitEthernet0/0): ")
    ip = pedir_ipv4("Introduce la direccion IP (ejemplo: 192.168.1.1): ")
    mascara = pedir_mascara("Introduce la mascara de subred (ejemplo: 255.255.255.0): ")
    enviar(con, "conf t")
    enviar(con, f"interface {interfaz}")
    enviar(con, f"ip address {ip} {mascara}")
    enviar(con, "no shutdown")
    enviar(con, "exit")
    enviar(con, "end")
    print(f"Interfaz {interfaz} configurada con IP {ip}/{mascara} y activada.")


def crear_subinterfaces(con):
    interfaz_base = pedir_interfaz("Introduce la interfaz base (ejemplo: GigabitEthernet0/0): ")
    vlan = pedir_numero("Introduce el numero de VLAN (ejemplo: 10): ", 1, 4094, "VLAN")
    ip = pedir_ipv4("Introduce la direccion IP de la subinterfaz (ejemplo: 192.168.10.1): ")
    mascara = pedir_mascara("Introduce la mascara de subred (ejemplo: 255.255.255.0): ")
    subif = f"{interfaz_base}.{vlan}"
    enviar(con, "conf t")
    enviar(con, f"interface {subif}")
    enviar(con, f"encapsulation dot1Q {vlan}")
    enviar(con, f"ip address {ip} {mascara}")
    enviar(con, "no shutdown")
    enviar(con, "exit")
    enviar(con, "end")
    print(f"Subinterfaz {subif} creada en VLAN {vlan} con IP {ip}/{mascara} y activada.")


def configurar_loopback(con):
    loopback_id = pedir_numero("Introduce el numero de loopback (ejemplo: 0): ", 0, 2147483647, "Loopback")
    ip = pedir_ipv4("Introduce la direccion IP de la loopback (ejemplo: 10.10.10.1): ")
    mascara = pedir_mascara("Introduce la mascara de subred (ejemplo: 255.255.255.255): ")
    enviar(con, "conf t")
    enviar(con, f"interface Loopback{loopback_id}")
    enviar(con, f"ip address {ip} {mascara}")
    enviar(con, "exit")
    enviar(con, "end")
    print(f"Loopback{loopback_id} configurada con IP {ip}/{mascara}.")

# ==========================================================
# FUNCIONES CONFIGURACIÓN DE ENRUTAMIENTO
# ==========================================================

def configurar_rutas_estaticas(con):

    while True:
        print("\n--- CONFIGURAR RUTA ESTÁTICA ---")
        destino = pedir_ipv4("Introduce la red de destino (ejemplo: 192.168.20.0): ", "red destino")
        mascara = pedir_mascara("Introduce la mascara de red (ejemplo: 255.255.255.0): ")
        next_hop = pedir_ipv4("Introduce la direccion IP del siguiente salto (next-hop): ", "next-hop")

        enviar(con, "conf t")
        enviar(con, f"ip route {destino} {mascara} {next_hop}")
        enviar(con, "end")

        print(f"Ruta estática añadida: {destino} {mascara} vía {next_hop}")

        if not confirmar("Deseas agregar otra ruta estatica? (s/n): "):
            break

    input("\nPresiona Enter para volver al menú de enrutamiento...")


def configurar_ospf(con):
    proceso = pedir_numero("Introduce el ID del proceso OSPF (ejemplo: 1): ", 1, 65535, "proceso OSPF")
    router_id = pedir_ipv4("Introduce el Router ID (ejemplo: 1.1.1.1): ", "Router ID")
    enviar(con, "conf t")
    enviar(con, f"router ospf {proceso}")
    enviar(con, f"router-id {router_id}")

    while True:
        print("\n--- Añadir red a OSPF ---")
        red = pedir_ipv4("Introduce la red (ejemplo: 192.168.1.0): ", "red")
        wildcard = pedir_wildcard("Introduce la wildcard mask (ejemplo: 0.0.0.255): ")
        area = pedir_numero("Introduce el area (ejemplo: 0): ", 0, 4294967295, "area")
        enviar(con, f"network {red} {wildcard} area {area}")
        if not confirmar("Deseas anadir otra red a OSPF? (s/n): "):
            break

    enviar(con, "end")
    print(f"OSPF configurado con proceso {proceso} y Router ID {router_id}")
    input("\nPresiona Enter para volver al menú de enrutamiento...")


def mostrar_tabla_enrutamiento(con):
    print("\n--- TABLA DE ENRUTAMIENTO ---\n")
    enviar(con, "show ip route", mostrar=True)
    print("\nTabla de enrutamiento mostrada correctamente.")
    input("\nPresiona Enter para volver al menú de enrutamiento...")

# ==========================================================
# FUNCIONES DE SEGURIDAD
# ==========================================================

def configurar_ssh(con):

    print("\n--- CONFIGURAR SSH ---")

    #Obtener configuración actual
    config = obtener_running_config(con)

    #Comprobar si hay dominio y usuarios locales
    tiene_dominio = "ip domain-name" in config
    tiene_usuario = "username " in config

    #Si falta alguno, avisar y volver al menú principal
    if not tiene_dominio or not tiene_usuario:
        print("\n No se cumplen los requisitos para configurar SSH:")
        if not tiene_dominio:
            print("No se ha configurado un dominio (usa el menú de configuración básica).")
        if not tiene_usuario:
            print("No existen usuarios locales configurados (usa el menú de configuración básica).")
        print("\nPor favor, crea el dominio y al menos un usuario antes de continuar.")
        input("\nPresiona Enter para volver al menú principal...")
        return  # Sale de la función y vuelve al menú principal

    #Si todo está correcto, configurar SSH
    enviar(con, "conf t")
    enviar(con, "crypto key generate rsa modulus 2048", timeout=60)
    enviar(con, "ip ssh version 2")
    enviar(con, "line vty 0 4")
    enviar(con, "transport input ssh")
    enviar(con, "login local")
    enviar(con, "exit")
    enviar(con, "end")

    print("\nSSH configurado correctamente.")
    input("\nPresiona Enter para volver al menú de seguridad...")



def crear_acl(con):
    """
    Crea una Access Control List (ACL) estándar o extendida
    """
    print("\n--- CREAR ACL ---")
    tipo = input("¿Qué tipo de ACL deseas crear? (1 = Estándar, 2 = Extendida): ")

    if tipo == "1":
        while True:
            numero = int(pedir_numero("Introduce el numero de ACL (1-99 o 1300-1999): ", 1, 1999, "ACL"))
            if 1 <= numero <= 99 or 1300 <= numero <= 1999:
                numero = str(numero)
                break
            print("ACL estandar valida: 1-99 o 1300-1999.")
        while True:
            accion = pedir_texto("Accion (permit/deny): ", "accion", 6, r"permit|deny")
            origen = pedir_ipv4("Introduce la IP origen (ejemplo: 192.168.1.0): ", "origen")
            wildcard = pedir_wildcard("Introduce la wildcard mask (ejemplo: 0.0.0.255): ")
            enviar(con, "conf t")
            enviar(con, f"access-list {numero} {accion} {origen} {wildcard}")
            enviar(con, "end")
            if not confirmar("Deseas agregar otra regla a la ACL? (s/n): "):
                break

    elif tipo == "2":
        while True:
            numero = int(pedir_numero("Introduce el numero de ACL extendida (100-199 o 2000-2699): ", 100, 2699, "ACL"))
            if 100 <= numero <= 199 or 2000 <= numero <= 2699:
                numero = str(numero)
                break
            print("ACL extendida valida: 100-199 o 2000-2699.")
        while True:
            accion = pedir_texto("Accion (permit/deny): ", "accion", 6, r"permit|deny")
            protocolo = pedir_texto("Protocolo (ip, tcp, udp, icmp): ", "protocolo", 4, r"ip|tcp|udp|icmp")
            origen = pedir_ipv4("IP origen (ejemplo: 192.168.1.0): ", "origen")
            wildcard_origen = pedir_wildcard("Wildcard origen (ejemplo: 0.0.0.255): ")
            destino = pedir_ipv4("IP destino (ejemplo: 10.0.0.0): ", "destino")
            wildcard_destino = pedir_wildcard("Wildcard destino (ejemplo: 0.0.0.255): ")

            enviar(con, "conf t")
            enviar(con, f"access-list {numero} {accion} {protocolo} {origen} {wildcard_origen} {destino} {wildcard_destino}")
            enviar(con, "end")

            if not confirmar("Deseas agregar otra regla a la ACL? (s/n): "):
                break

    else:
        print("Opción no válida. Debes elegir 1 o 2.")
        return

    print(f"\nACL creada correctamente.")
    input("\nPresiona Enter para volver al menú de seguridad...")


def seguridad_puertos(con):
    """
    Aplica seguridad básica a los puertos (Port Security)
    """
    print("\n--- SEGURIDAD EN PUERTOS ---")
    interfaz = pedir_interfaz("Introduce la interfaz a proteger (ejemplo: FastEthernet0/1 o GigabitEthernet0/1): ")

    enviar(con, "conf t")
    enviar(con, f"interface {interfaz}")
    enviar(con, "switchport mode access")
    enviar(con, "switchport port-security")
    enviar(con, "switchport port-security maximum 1")
    enviar(con, "switchport port-security violation shutdown")
    enviar(con, "switchport port-security mac-address sticky")
    enviar(con, "end")

    print(f"\nSeguridad activada en la interfaz {interfaz}")
    input("\nPresiona Enter para volver al menú de seguridad...")
# ==========================================================
# FUNCIONES DE CONFIGURACIÓN AVANZADA
# ==========================================================
def configurar_tuneles_gre(con):
    print("\n--- CONFIGURAR TÚNEL GRE ---")

    tun_id = pedir_numero("ID del tunel (ej. 0): ", 0, 2147483647, "tunel")
    ip_tunnel = pedir_ipv4("IP del tunel (ej. 10.0.0.1): ", "IP del tunel")
    mask_tunnel = pedir_mascara("Mascara del tunel (ej. 255.255.255.252): ")
    tunnel_source = pedir_texto("Origen del tunel (interfaz o IP, ej. GigabitEthernet0/0 o 192.168.1.1): ", "origen del tunel", 64, r"[A-Za-z0-9/._:-]+")
    tunnel_destination = pedir_ipv4("Destino del tunel (IP remota, ej. 203.0.113.2): ", "destino del tunel")
    keepalive = confirmar("Enable keepalive? (s/n): ")

    enviar(con, "conf t")
    enviar(con, f"interface Tunnel{tun_id}")
    enviar(con, f"ip address {ip_tunnel} {mask_tunnel}")
    enviar(con, f"tunnel source {tunnel_source}")
    enviar(con, f"tunnel destination {tunnel_destination}")
    enviar(con, "tunnel mode gre ip")
    if keepalive:
        enviar(con, "keepalive 10 3")  # intervalo 10s, 3 intentos
    enviar(con, "no shutdown")
    enviar(con, "exit")
    enviar(con, "end")

    print(f"\nTúnel GRE Tunnel{tun_id} configurado entre {tunnel_source} → {tunnel_destination}.")
    input("\nPresiona Enter para volver al menú de configuración avanzada...")

def configurar_vpn_ipsec(con):
    print("\n--- CONFIGURAR VPN IPsec ---")

    # Parámetros fase 1 (ISAKMP/IKEv1)
    isakmp_policy = pedir_numero("Numero de politica ISAKMP (ej. 10): ", 1, 10000, "politica ISAKMP")
    pre_shared_key = pedir_secreto("Pre-Shared Key (PSK): ")
    peer_ip = pedir_ipv4("IP del peer remoto: ", "peer remoto")
    local_id = pedir_texto("Identidad local key-id (opcional, Enter para omitir): ", "identidad local", 64, r"[A-Za-z0-9_.:-]+", requerido=False)

    # Parámetros fase 2 (transform-set + ACL de tráfico interesante)
    ts_name = pedir_nombre_ios("Nombre del transform-set (ej. TS-ESP-AES-SHA): ", "transform-set")
    acl_num = pedir_acl_extendida("Numero de ACL para trafico interesante (100-199 o 2000-2699): ")
    local_subnet = pedir_ipv4("Subred local (ej. 192.168.1.0): ", "subred local")
    local_wild = pedir_wildcard("Wildcard local (ej. 0.0.0.255): ")
    remote_subnet = pedir_ipv4("Subred remota (ej. 10.10.10.0): ", "subred remota")
    remote_wild = pedir_wildcard("Wildcard remota (ej. 0.0.0.255): ")

    # Crypto map
    cmap_name = pedir_nombre_ios("Nombre del crypto map (ej. CMAP): ", "crypto map")
    cmap_seq = pedir_numero("Secuencia del crypto map (ej. 10): ", 1, 65535, "secuencia")
    iface_out = pedir_interfaz("Interfaz de salida para aplicar crypto map (ej. GigabitEthernet0/0): ")

    enviar(con, "conf t")

    # ISAKMP policy (ejemplo: AES/SHA/Group14/lifetime)
    enviar(con, f"crypto isakmp policy {isakmp_policy}")
    enviar(con, "encryption aes")
    enviar(con, "hash sha")
    enviar(con, "authentication pre-share")
    enviar(con, "group 14")
    enviar(con, "lifetime 86400")
    enviar(con, "exit")

    if local_id:
        enviar(con, f"crypto isakmp identity key-id {local_id}")

    enviar(con, f"crypto isakmp key {pre_shared_key} address {peer_ip}")

    # Transform-set
    enviar(con, f"crypto ipsec transform-set {ts_name} esp-aes esp-sha-hmac")

    # ACL tráfico interesante
    enviar(con, f"access-list {acl_num} permit ip {local_subnet} {local_wild} {remote_subnet} {remote_wild}")

    # Crypto map
    enviar(con, f"crypto map {cmap_name} {cmap_seq} ipsec-isakmp")
    enviar(con, f"set peer {peer_ip}")
    enviar(con, f"set transform-set {ts_name}")
    enviar(con, f"match address {acl_num}")
    enviar(con, "exit")

    # Aplicar crypto map a la interfaz de salida
    enviar(con, f"interface {iface_out}")
    enviar(con, f"crypto map {cmap_name}")
    enviar(con, "exit")
    enviar(con, "end")

    print(f"\nVPN IPsec configurada con peer {peer_ip}, crypto map {cmap_name} aplicado en {iface_out}.")
    input("\nPresiona Enter para volver al menú de configuración avanzada...")

def configurar_nat(con):
    print("\n--- CONFIGURAR NAT ---")
    print("1) NAT estático (1:1)")
    print("2) NAT dinámico/PAT (sobrecarga)")
    modo = input("Selecciona opcion: ").strip()

    inside_if = pedir_interfaz("Interfaz INSIDE (ej. GigabitEthernet0/1): ")
    outside_if = pedir_interfaz("Interfaz OUTSIDE (ej. GigabitEthernet0/0): ")

    enviar(con, "conf t")
    enviar(con, f"interface {inside_if}")
    enviar(con, "ip nat inside")
    enviar(con, "exit")
    enviar(con, f"interface {outside_if}")
    enviar(con, "ip nat outside")
    enviar(con, "exit")

    if modo == "1":
        local_ip = pedir_ipv4("IP local (inside) a publicar: ", "IP local")
        global_ip = pedir_ipv4("IP publica (outside): ", "IP publica")
        enviar(con, f"ip nat inside source static {local_ip} {global_ip}")
        enviar(con, "end")
        print(f"\nNAT estático configurado: {local_ip} → {global_ip}")

    elif modo == "2":
        acl_num = pedir_acl_extendida("Numero de ACL para trafico interno (100-199 o 2000-2699): ")
        inside_subnet = pedir_ipv4("Subred inside (ej. 192.168.1.0): ", "subred inside")
        inside_wild = pedir_wildcard("Wildcard inside (ej. 0.0.0.255): ")
        enviar(con, f"access-list {acl_num} permit ip {inside_subnet} {inside_wild} any")
        enviar(con, f"ip nat inside source list {acl_num} interface {outside_if} overload")
        enviar(con, "end")
        print(f"\nPAT configurado sobre {outside_if} para {inside_subnet}/{inside_wild}")

    else:
        enviar(con, "end")
        print("Opción de NAT inválida.")

    input("\nPresiona Enter para volver al menú de configuración avanzada...")

def configurar_qos(con):
    print("\n--- CONFIGURAR QoS BÁSICO ---")
    iface = pedir_interfaz("Interfaz a aplicar QoS (ej. GigabitEthernet0/0): ")
    class_name = pedir_nombre_ios("Nombre de la class-map (ej. CM-CRITICO): ", "class-map")
    policy_name = pedir_nombre_ios("Nombre de la policy-map (ej. PM-SALIDA): ", "policy-map")

    print("\nClasificación por ACL o DSCP:")
    print("1) ACL (tráfico interesante)")
    print("2) DSCP (ej. af41, ef)")
    modo = input("Selecciona opcion: ").strip()

    enviar(con, "conf t")

    if modo == "1":
        acl_num = pedir_acl_extendida("Numero de ACL (100-199 o 2000-2699): ")
        src = pedir_ipv4("Subred origen (ej. 192.168.1.0): ", "subred origen")
        src_w = pedir_wildcard("Wildcard origen (ej. 0.0.0.255): ")
        enviar(con, f"access-list {acl_num} permit ip {src} {src_w} any")
        enviar(con, f"class-map match-any {class_name}")
        enviar(con, f" match access-group {acl_num}")
        enviar(con, "exit")
    elif modo == "2":
        dscp = pedir_texto("Valor DSCP (ej. ef, af41, af31): ", "DSCP", 8, r"[A-Za-z0-9]+")
        enviar(con, f"class-map match-any {class_name}")
        enviar(con, f" match dscp {dscp}")
        enviar(con, "exit")
    else:
        enviar(con, "end")
        print("Opción de clasificación inválida.")
        return

    # Policy-map con ejemplo de prioridad y policing
    enviar(con, f"policy-map {policy_name}")
    enviar(con, f" class {class_name}")
    print("\nAcciones en la clase:")
    print("1) Prioridad LLQ (priority kbps)")
    print("2) Shaping (shape average bps)")
    print("3) Policing (police rate bps burst b)")
    accion = input("Selecciona accion: ").strip()

    if accion == "1":
        kbps = pedir_numero("Ancho de banda prioritario en kbps (ej. 2000): ", 1, 100000000, "kbps")
        enviar(con, f"  priority {kbps}")
    elif accion == "2":
        bps = pedir_numero("Banda media en bps (ej. 2000000): ", 1, 100000000000, "bps")
        enviar(con, f"  shape average {bps}")
    elif accion == "3":
        bps = pedir_numero("Rate en bps (ej. 1000000): ", 1, 100000000000, "bps")
        burst = pedir_numero("Burst en bytes (ej. 30000): ", 1, 1000000000, "burst")
        enviar(con, f"  police {bps} {burst} conform-action transmit exceed-action drop")
    else:
        print("Acción inválida, se crea la policy sin acciones específicas.")
    enviar(con, " exit")
    enviar(con, "exit")

    # Aplicar policy en salida de interfaz
    enviar(con, f"interface {iface}")
    enviar(con, f"service-policy output {policy_name}")
    enviar(con, "exit")
    enviar(con, "end")

    print(f"\nQoS aplicado en {iface} con policy {policy_name} y class-map {class_name}.")
    input("\nPresiona Enter para volver al menú de configuración avanzada...")

# ==========================================================
# FUNCIONES DE UTILIDADES Y HERRAMIENTAS
# ==========================================================

def guardar_configuracion(con):
    """
    Guarda la configuración en la NVRAM (startup-config).
    """
    print("\n--- GUARDAR CONFIGURACIÓN ---")
    enviar(con, "write memory", timeout=30, mostrar=True)
    print("Configuración guardada correctamente en la NVRAM.")
    input("\nPresiona Enter para volver al menú de utilidades...")


def copia_seguridad(con):
    """
    Hace una copia de seguridad de la configuración en un archivo local.
    """
    print("\n--- COPIA DE SEGURIDAD ---")
    filename = input("Introduce el nombre del archivo de copia (ej. backup.txt): ")
    config = obtener_running_config(con)

    # Guardar en archivo local
    ruta = ruta_backup_segura(filename)
    print(f"La copia se guardara junto al ejecutable, en:\n{ruta}")
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(config)
    except OSError as exc:
        print(f"No se pudo guardar la copia de seguridad en la carpeta del ejecutable: {exc}")
        input("\nPresiona Enter para volver al menu de utilidades...")
        return

    print(f"Copia de seguridad guardada en {ruta}")
    input("\nPresiona Enter para volver al menú de utilidades...")


def hacer_ping(con):
    """
    Ejecuta un ping desde el router hacia un destino.
    """
    print("\n--- HACER PING ---")
    destino = pedir_texto("Introduce la direccion IP o dominio a hacer ping: ", "destino", 253, r"[A-Za-z0-9_.:-]+")
    enviar(con, f"ping {destino}", mostrar=True)
    print(f"Ping ejecutado hacia {destino}")
    input("\nPresiona Enter para volver al menú de utilidades...")


def reiniciar(con):
    """
    Reinicia el router/switch.
    """
    print("\n--- REINICIAR DISPOSITIVO ---")
    if confirmar("Seguro que deseas reiniciar el dispositivo? (s/n): "):
        if confirmar("Quieres guardar la configuracion antes de reiniciar? (s/n): "):
            enviar(con, "write memory", timeout=30, mostrar=True)
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
        print("Dispositivo reiniciándose...")
    else:
        print("Reinicio cancelado.")
    input("\nPresiona Enter para volver al menú de utilidades...")


def reset_fabrica(con):
    """
    Restablece el dispositivo a valores de fábrica.
    """
    print("\n--- RESET DE FÁBRICA ---")
    if confirmar("Seguro que deseas borrar la configuracion y dejar de fabrica? (s/n): "):
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
        print("Configuración borrada. El dispositivo se reiniciará con valores de fábrica.")
    else:
        print("Reset cancelado.")
    input("\nPresiona Enter para volver al menú de utilidades...")


# ==========================================================
# SUBMENÚ CONFIGURACIÓN BÁSICA
# ==========================================================

def menu_conf_basica(con):
    while True:
        print("\n===== CONFIGURACIÓN BÁSICA =====")
        print("1. Cambiar hostname")
        print("2. Configurar dominio")
        print("3. Crear usuario")
        print("4. Configurar banner MOTD")
        print("5. Volver al menú principal")
        opcion = input("Selecciona una opción: ")  

        if opcion == "1":
            cambiar_hostname(con)
        elif opcion == "2":
            configurar_dominio(con)
        elif opcion == "3":
            crear_usuario(con)
        elif opcion == "4":
            configurar_banner(con)
        elif opcion == "5":
            break  # Sale del submenú y vuelve al principal
        else:
            print("Opción inválida. Inténtalo de nuevo.")      

# ==========================================================
# SUBMENÚ DE INTERFACES
# ==========================================================

def menu_conf_interfaces(con):
    while True:
        print("\n===== CONFIGURACIÓN DE INTERFACES =====")
        print("1. Configurar interfaz física")
        print("2. Crear subinterfaz")
        print("3. Configurar loopback")
        print("4. Volver al menú principal")
        opcion = input("Selecciona una opción: ")  

        if opcion == "1":
            configurar_interfaz(con)
        elif opcion == "2":
            crear_subinterfaces(con)
        elif opcion == "3":
            configurar_loopback(con)
        elif opcion == "4":
            break  # Sale del submenú y vuelve al principal
        else:
            print("Opción inválida. Inténtalo de nuevo.")     

# ==========================================================
# SUBMENÚ CONFIGURACIÓN DE ENRUNTAMIENTO
# ==========================================================

def menu_conf_enrutamiento(con):
    while True:
        print("\n===== CONFIGURACIÓN DE ENRUTAMIENTO =====")
        print("1. Configurar rutas estáticas")
        print("2. Configurar OSPF")
        print("3. Mostrar tabla de enrutamiento")
        print("4. Volver al menú principal")
        opcion = input("Selecciona una opción: ")  

        if opcion == "1":
            configurar_rutas_estaticas(con)
        elif opcion == "2":
            configurar_ospf(con)
        elif opcion == "3":
            mostrar_tabla_enrutamiento(con)
        elif opcion == "4":
            break  # Sale del submenú y vuelve al principal
        else:
            print("Opción inválida. Inténtalo de nuevo.")    

# ==========================================================
# SUBMENÚ DE SEGURIDAD
# ==========================================================

def menu_seguridad(con):
    while True:
        print("\n===== CONFIGURACIÓN DE SEGURIDAD =====")
        print("1. Configurar SSH")
        print("2. Crear ACL")
        print("3. Dar seguridad a los puertos")
        print("4. Volver al menú principal")
        opcion = input("Selecciona una opción: ")  

        if opcion == "1":
            configurar_ssh(con)
        elif opcion == "2":
            crear_acl(con)
        elif opcion == "3":
            seguridad_puertos(con)
        elif opcion == "4":
            break  # Sale del submenú y vuelve al principal
        else:
            print("Opción inválida. Inténtalo de nuevo.")    

# ==========================================================
# SUBMENÚ CONFIGURACIÓN AVANZADA
# ==========================================================

def menu_conf_avanzada(con):
    while True:
        print("\n===== CONFIGURACIÓN AVANZADA =====")
        print("1. Túneles GRE")
        print("2. VPN Ipsec")
        print("3. NAT")
        print("4. QoS Básico")
        print("5. Volver al menú principal")
        opcion = input("Selecciona una opción: ")  

        if opcion == "1":
            configurar_tuneles_gre(con)
        elif opcion == "2":
            configurar_vpn_ipsec(con)
        elif opcion == "3":
            configurar_nat(con)
        elif opcion == "4":
            configurar_qos(con)
        elif opcion == "5":
            break  # Sale del submenú y vuelve al principal
        else:
            print("Opción inválida. Inténtalo de nuevo.")  

# ==========================================================
# SUBMENÚ DE UTILIDADES Y HERRAMIENTAS
# ==========================================================

def menu_utilidades_herramientas(con):
    while True:
        print("\n===== UTILIDADES Y HERRAMIENTAS =====")
        print("1. Guardar Configuración")
        print("2. Hacer copia de seguridad")
        print("3. Hacer ping")
        print("4. Reiniciar")
        print("5. Poner de fábrica")
        print("6. Volver al menú principal")
        opcion = input("Selecciona una opción: ")  

        if opcion == "1":
            guardar_configuracion(con)
        elif opcion == "2":
            copia_seguridad(con)
        elif opcion == "3":
            hacer_ping(con)
        elif opcion == "4":
            reiniciar(con)
        elif opcion == "5":
            reset_fabrica(con)
        elif opcion == "6":
            break  # Sale del submenú y vuelve al principal
        else:
            print("Opción inválida. Inténtalo de nuevo.")       

# ==========================================================
# MENÚ PRINCIPAL
# ==========================================================

def menu(con):
    while True:
        config_raw = obtener_running_config(con)
        datos = parsear_running_config(config_raw, con)
        mostrar_resumen_config(datos)

        print("\n" + "="*70)
        print("1. Configuración básica")
        print("2. Configuración de interfaces")
        print("3. Enrutamiento")
        print("4. Seguridad")
        print("5. Configuración avanzada")
        print("6. Utilidades y herramientas")
        print("7. Salir")
        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            menu_conf_basica(con)
        elif opcion == "2":
            menu_conf_interfaces(con)
        elif opcion == "3":
            menu_conf_enrutamiento(con)
        elif opcion == "4":
            menu_seguridad(con)
        elif opcion == "5":
            menu_conf_avanzada(con)
        elif opcion == "6":
            menu_utilidades_herramientas(con)
        elif opcion == "7":
            print("Saliendo del programa...")
            break
        else:
            print("Opción inválida.")
#AÑADIDO###############
if __name__ == "__main__":
    con = None
    try:
        puerto = seleccionar_puerto()

        con = serial.Serial(
            port=puerto,
            baudrate=9600,
            timeout=1,
            write_timeout=3
        )

        time.sleep(2)  # Esperar a que el puerto este listo

        if login(con):
            menu(con)
        else:
            print("No se abre el menu porque no hay sesion valida en el router.")

    except serial.SerialException as e:
        print(f"Error al abrir el puerto serie: {e}")
    except KeyboardInterrupt:
        print("\nProceso cancelado por el usuario.")

    finally:
        if con is not None and con.is_open:
            con.close()
            print("Conexion cerrada")
