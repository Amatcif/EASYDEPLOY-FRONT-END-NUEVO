export interface ChangelogItem {
  version: string;
  date: string;
  changes: string[];
}

export const changelogData: ChangelogItem[] = [
  {
    version: '2.2.5.25',
    date: '26/05/2026',
    changes: [
      'Pulida pestaña Actualizaciones: ocultadas URL/SHA/instalador, añadida barra de descarga y flujo descargar-instalar-cerrar.',
      'Corregidos avisos de Privilegios y confirmación al cambiar el endpoint update.json.',
      'Mejorado el foco de prompts React para KMS, AD, Exchange, dominio y entradas antiguas.',
      'La consola limpia la salida al iniciar una tarea nueva y añade acceso directo a Logs.',
      'Mejorado Monitor de ping con estados verde/rojo/gris y botón X para cerrar cada ping.',
      'Reforzada apertura de Logs y herramientas interactivas de red desde el backend real.'
    ]
  },
  {
    version: '2.2.5.24',
    date: '26/05/2026',
    changes: [
      'Reorganizado Sistemas con KMS, SharePoint, SQL y JCHAT como secciones propias.',
      'Movido Net Framework 3.5 a Instaladores Offline e incluido en Instalar todo el arsenal.',
      'Movido Forzar políticas GPO a Herramientas > Sistema.',
      'Eliminados paneles técnicos visibles de bridge/preload/teclado y bloques decorativos de Active Directory.',
      'Añadidos prompts React para datos de Ping, usuarios AD/Exchange, dominio y acciones antiguas que pedían entradas.',
      'Recursos, Logs y Actualizaciones muestran resultado sin redirigir innecesariamente a consola.'
    ]
  },
  {
    version: '2.2.5.23',
    date: '26/05/2026',
    changes: [
      'Corregido mapeo de botones del nuevo front-end contra Easy Deploy clásico.',
      'Restaurado comportamiento de redirección automática a consola para acciones reales.',
      'Restauradas funciones reales de Recursos, Top procesos, Roles instalados, Comprobar entorno y Ping.',
      'Mejorada pestaña Actualizaciones para mostrar resultado en la propia pantalla.',
      'Limpieza de textos, tildes, ñ, etiquetas antiguas y elementos visuales no funcionales.'
    ]
  },
  {
    version: '2.2.5.22',
    date: '26/05/2026',
    changes: [
      'Desactivada la aceleración gráfica de Electron para mejorar el arranque en Windows Server 2019.',
      'Añadido diagnóstico de compatibilidad GPU al log de arranque sin cambiar el bridge ni las tareas reales.'
    ]
  },
  {
    version: '2.2.5.21',
    date: '26/05/2026',
    changes: [
      'Corregida la carga de preload en Electron con diagnóstico visible y pingPreload desde el renderer.',
      'Reforzado el bridge Electron/Python con logs diferenciados de cliente, Electron, backend y registro de acciones.',
      'Añadido self-test seguro del backend Python y dry-run para validar acciones peligrosas sin ejecutarlas.',
      'Limpieza de builds Electron para evitar instalar artefactos antiguos.'
    ]
  },
  {
    version: '2.2.5.19',
    date: '25/05/2026',
    changes: [
      'Corregido el arranque instalado de Electron con rutas relativas para Vite y título EASY DEPLOY.',
      'Reforzado el bridge Electron/Python con diagnóstico visible de backend, errores de arranque y estado de rutas.',
      'Mejorada la ejecución de acciones desde el front-end para enviar botones reales al backend y mostrar errores en consola.',
      'Conectadas acciones de Redes y Guías al backend en lugar de dejarlas solo como selección visual.'
    ]
  },
  {
    version: '2.2.5.18',
    date: '19/05/2026',
    changes: [
      'Migrado front-end principal a React/Electron manteniendo backend Python de Easy Deploy.',
      'Conectadas acciones principales del nuevo front-end con funciones reales del motor antiguo.',
      'Añadido bridge seguro Electron/Python con logs, progreso y prompts.',
      'Adaptado build/instalador con clave de activación única por compilación.',
      'Añadida y probada función actualizar APP mediante internet.'
    ]
  },
  {
    version: '2.2.5.14',
    date: '19/05/2026',
    changes: [
      'Añadida pantalla Actualizar con endpoint JSON configurable para comprobar versiones remotas desde Dropbox.',
      'Añadido flujo de descarga y lanzamiento de instalador de actualización con limpieza posterior del archivo descargado.',
      'Añadido empaquetador/instalador para instalar Easy Deploy en Program Files y crear acceso directo de escritorio.',
      'Pulida Fase 1 visual de sidebar, cabeceras, tarjetas y tiles de Inicio sin cambiar lógica.',
      'Mantenida la estructura CustomTkinter y el comportamiento existente.',
      'Corregido Instalar Exchange para lanzar Setup sin bloquear por prerrequisitos previos.',
      'Mejorada la detección e instalación de IIS URL Rewrite en Prerrequisitos Exchange.',
      'Añadido botón Prerrequisitos Exchange dentro de Sistemas > Exchange.',
      'Separado el flujo de prerrequisitos y la instalación principal de Exchange.',
      'Instalar Exchange lanza Setup desde el medio de Exchange y deja el Readiness Check al instalador oficial.',
      'Automatizado el uso de OTROS\\NetFramework3.5.iso para instalar .NET Framework 3.5 y prerrequisitos de Skype sin pedir montar el ISO manualmente.',
      'Actualizado el comprobador de recursos para validar la ISO local de .NET Framework 3.5.'
    ]
  },
  {
    version: '2.2.4.4',
    date: '18/05/2026',
    changes: [
      'Corregida regresión visual en Crear usuarios AD/EXC causada por colores de CustomTkinter mal formados.',
      'Pulidos visualmente los formularios Crear usuarios AD y Crear usuarios EXC para mejorar jerarquía, secciones, ayudas y panel de usuarios preparados sin cambiar su lógica.',
      'Corregida la casilla Reutilizar datos en Crear usuarios AD/EXC para que solo pregunte si está marcada.',
      'Mejorado el comportamiento del modal Reutilizar datos como ventana hija del formulario.',
      'Pulido visual del panel Apariencia y añadido cierre automático al hacer click fuera.',
      'Pulido visual del drawer Herramientas manteniendo Versiones y Créditos dentro del menú.',
      'Pulido visual de Créditos / Acerca de con secciones más claras para autores, módulos y aviso legal.',
      'Ajustado Crear usuarios EXC para que, si Destino en AD queda vacío, use automáticamente el contenedor Users del dominio.',
      'Unificados textos y etiquetas de Crear usuarios AD/EXC para mantener español completo y coherencia visual entre formularios.',
      'Añadido botón Instalar Jchat CLI dentro de Sistemas > JCHAT para lanzar el MSI offline.',
      'Actualizado el comprobador de recursos JCHAT para validar el instalador MSI de JCHAT CLI.'
    ]
  },
  {
    version: '2.2.3.5',
    date: '17/05/2026',
    changes: [
      'Añadida una línea separadora vertical sutil entre la barra lateral y el área principal, adaptada a la paleta visual activa.',
      'Reorganizada la barra superior dejando Apariencia como único acceso visible y moviendo Versiones y Créditos al menú Herramientas.',
      'Eliminadas las acciones Reiniciar UI y Salir del menú Herramientas para simplificar la interfaz.',
      'Añadido selector compacto de Apariencia para agrupar Paleta y modo Light/Dark.',
      'Mejorado el sistema de ventanas minimizadas dentro de la aplicación para evitar botones superpuestos y permitir seleccionar qué ventana restaurar.',
      'Corregido el foco de las cajas de escritura para evitar parpadeos y pérdida de cursor al escribir.',
      'Normalizado el ciclo de vida de ventanas secundarias para evitar duplicados, abrirlas delante de Easy Deploy y no dejarlas como topmost permanente.',
      'Corregido el estado visual de Recursos para actualizarse al momento si faltan archivos tras abrir la aplicación.',
      'Alineado el comprobador de recursos con Skype Server, prerrequisitos offline y nuevas guías Skype/D2-D4.',
      'Corregido falso positivo visual en consola para que la característica Web-Http-Errors de IIS no aparezca marcada como error durante los prerrequisitos de Skype.',
      'Corregido arranque de tareas desde consola añadiendo la importación re que necesitaba layout.py para el filtrado visual de líneas como Web-Http-Errors.'
    ]
  },
  {
    version: '2.2.2.13',
    date: '16/05/2026',
    changes: [
      'Añadido botón Puntero DNS Skype para crear/actualizar registros A internos y el SRV _sipinternaltls._tcp necesarios antes de la instalación de Skype for Business Server.',
      'Actualizado el aviso de Instalar Skype para recordar primero Permisos a usuario y Puntero DNS Skype.',
      'Corregido Permisos a usuario Skype para mostrar y contar correctamente los grupos procesados, evitando que las líneas ADDED/OKMEMBER quedaran capturadas internamente por PowerShell.',
      'Corregido Permisos a usuario Skype para evitar error de sintaxis PowerShell al informar grupos por SID y permitir continuar con la asignación de Schema Admins, Enterprise Admins y Domain Admins.',
      'Corregido Permisos a usuario Skype para resolver grupos AD por SID/DN de forma robusta y evitar Identity vacío al añadir Schema Admins, Enterprise Admins o Domain Admins.',
      'Corregido Permisos a usuario Skype para tratar correctamente objetos AD devueltos por PowerShell y evitar el error System.Object[].',
      'Rehecha la función Permisos a usuario de Skype reutilizando la lógica robusta de Crear usuarios AD: comprobación previa informativa y ejecución real mediante script PowerShell temporal.',
      'Corregido Permisos a usuario de Skype con comprobación previa de entorno AD/RSAT, botón recolocado abajo y salida PowerShell con tildes reparada.',
      'Añadido botón Permisos a usuario en Skype para comprobar y asignar grupos AD/RBAC necesarios para instalación y administración.',
      'Corregida la comprobación de entorno AD del botón Permisos a usuario Skype para evitar falsos negativos en controladores de dominio y mejorar la lectura de tildes en consola.',
      'Añadido botón Créditos junto a Versiones con reparto de autoría y aviso legal de derechos reservados.',
      'Mejorados los prerrequisitos de Skype para instalación offline usando Sources\\SxS y aviso de que Windows Features puede tardar varios minutos.',
      'La consola de Skype mueve la barra de progreso por fases durante prerrequisitos largos y muestra Reiniciar sistema cuando Windows deja reinicio pendiente.',
      'Corregidos falsos positivos de consola para que nombres técnicos como Web-Http-Errors no aparezcan como error rojo.',
      'Integrado Skype for Business Server con submenú propio: prerrequisitos e instalación desde ISO.',
      'Actualizado el comprobador de recursos para validar ISO y prerrequisitos de Skype, además de las nuevas guías.',
      'Añadidas Guía Skype y Guía D2 D4 al apartado Guías, abriéndose como el resto de PDFs.',
      'Añadidos botones Repadmin y D2 D4 en Controlador de dominio.',
      'Mejorado el asistente D2/D4 DFSR SYSVOL con una interfaz más guiada y minimalista.',
      'Ajustado el logo lateral para quedar más grande y centrado.',
      'Mejorada la fluidez al redimensionar la ventana principal y al maximizar o restaurar la aplicación.',
      'Reducidos parpadeos internos al cambiar entre secciones y al usar la Guía rápida.',
      'Las páginas principales usan ahora scroll estable y la barra se oculta automáticamente cuando no hace falta.',
      'Optimizada la carga de Versiones para abrir más rápido tras la primera consulta.',
      'Reducido trabajo repetido en Estado de Almacenamiento reutilizando la información de discos ya detectada.',
      'Limpieza interna de imports, código legacy y helpers repetidos sin cambiar el comportamiento visible.'
    ]
  },
  {
    version: '2.2.1',
    date: '15/05/2026',
    changes: [
      'Corregida la función para meter usuarios en Exchange y automatizar la reutilización de datos como dominio, correo, OU y contraseña.',
      'Corregida la detección de RPC-over-HTTP-Proxy para que Exchange instale correctamente esa característica antes del Readiness Check.',
      'Mejorado el comprobador de características de Exchange, DC1 y DC2 con estados visibles por componente.',
      'La consola muestra ahora ✓ verde en elementos instalados y ✗ roja en elementos pendientes o con error.',
      'Ajustado el formulario Crear usuarios Exchange para que los campos, el botón Ver y las acciones no se corten en la columna izquierda.'
    ]
  },
  {
    version: '2.2.0',
    date: '14/05/2026',
    changes: [
      'Corregidos los botones del creador de usuarios Exchange para que mantengan altura fija y no se compriman.',
      'El formulario de creación de usuarios Exchange usa ahora campos desplazables y una zona fija de acciones.',
      'Los avisos al usuario ahora calculan altura dinámica y activan scroll interno cuando el texto no cabe en pantalla.',
      'Actualizados los prerrequisitos de Exchange con las características oficiales WCF y RPC requeridas por Exchange Server 2019.',
      'Añadida verificación posterior de características Exchange para avisar exactamente qué componente sigue pendiente.',
      'Corregida la altura y reserva de espacio de los botones Sí/No en diálogos largos.',
      'Aumentado el ancho de los botones Sí/No en los diálogos de confirmación.',
      'Ajustado el texto de confirmación de RecoverServer Exchange.',
      'Renombrado el acceso de Exchange a RecoverServer Exchange para evitar confundirlo con una limpieza de Active Directory.',
      'Office + Skype ahora usa la carpeta offline preparada con setup.exe, configuration.xml y archivos Office descargados.',
      'Office + Skype ejecuta Instalar_Office_Oculto.vbs cuando existe en la carpeta officeoffline para evitar mostrar CMD.',
      'Actualizados los avisos de Office + Skype para explicar el inicio de instalación y el uso del lanzador oculto.',
      'Actualizada la validación de recursos OFFICE\\officeoffline para comprobar setup.exe, configuration.xml, Instalar_Office_Oculto.vbs, el bat y la carpeta Office interna.',
      'El botón Office + Skype ya no espera el código de salida del bat para evitar falsos errores con código 1.',
      'Office + Skype deja de abrir la consola de Easy Deploy cuando existe la carpeta OFFICE\\officeoffline preparada.',
      'Añadido registro del código de salida de Office + Skype para diagnosticar instalaciones canceladas o fallidas.'
    ]
  },
  {
    version: '2.1.100',
    date: '14/05/2026',
    changes: [
      'Añadido botón RecoverServer Exchange dentro de Exchange para ejecutar recuperación oficial de servidor de forma guiada.',
      'RecoverServer monta el medio de Exchange desde recursos, usa /Mode:RecoverServer y detecta /TargetDir si Exchange estaba en ruta personalizada.',
      'Añadidos avisos específicos para RecoverServer sobre nombre de equipo, permisos, versión CU, ruta personalizada y reinicio pendiente.',
      'Añadido botón Office + Skype dentro de Programas.',
      'Añadida instalación conjunta offline de Office y Skype for Business mediante configuration.xml y Office Deployment Tool.',
      'Añadida detección automática de Product ID compatible con el medio Office incluido en recursos.',
      'Bloqueada la mezcla de Office 32 bits con instalación Office + Skype de 64 bits para evitar errores de arquitectura.',
      'Añadida validación de recursos OFFICE y SKYPE dentro de la comprobación de recursos.',
      'Mejorado Prepare Schema para comprobar las versiones AD de Exchange antes de cada paso y omitir automaticamente los pasos ya preparados.',
      'Detectado el error de validacion interna de roles de Exchange y tratado como paso ya preparado cuando Active Directory confirma las versiones correctas.',
      'Mejorado Prepare Schema de Exchange con comprobacion previa de RSAT-ADDS-Tools, sesion de dominio y grupos Schema Admins/Enterprise Admins.',
      'Anadida instalacion automatica de RSAT-ADDS-Tools cuando falte antes de ejecutar Prepare Schema.',
      'Mejorados los avisos de error de Prepare Schema para explicar si falla por cuenta local, grupos insuficientes, RSAT, DNS, reinicio pendiente o nivel funcional del bosque.',
      'Corregido el monitor de ping para que una tarjeta detenida por Stop pase a estado visual gris.',
      'Ajustado Recursos para abrir la carpeta directamente cuando esta OK y abrir selector solo cuando falten recursos o no se encuentre la ruta.',
      'Corregida la apertura de Recursos OK para abrir la carpeta con Explorer sin relanzar Easy Deploy.',
      'Corregido el cambio Light/Dark para aplicar el modo visual sin cerrar ni ocultar la aplicacion.',
      'Bloqueada la apertura de segundas instancias para evitar que Easy Deploy vuelva a pedir licencia encima de una sesion abierta.',
      'Protegido el selector de Recursos para que no pueda abrirse dos veces a la vez al corregir una carpeta incompleta.',
      'Mejorado el aviso de Recursos incompletos para mostrar solo carpetas y archivos faltantes con rutas claras.',
      'Eliminado el boton minimizar de la ventana inicial de licencia para evitar que desaparezca antes de abrir la interfaz principal.',
      'Activado Crear usuarios EXC dentro de Exchange con formulario rapido y lista visible de usuarios preparados.',
      'Anadida reutilizacion de dominio, OrganizationalUnit y password para acelerar altas masivas.',
      'Anadida validacion de dominio antes de preparar usuarios Exchange.',
      'El script de usuarios Exchange informa usuarios creados y fallidos, y elimina el archivo temporal al finalizar.',
      'Limpiados los textos de Redes para no mostrar nombres internos de archivos Python al usuario.',
      'Corregido el panel SSD para mostrar Estado de discos en una sola linea y evitar cortes al redimensionar.',
      'Mejorados los dialogos de entrada de datos para poder minimizarlos y restaurarlos sin bloquear la aplicacion.',
      'Actualizado DC1/DC2 para detectar carpetas NTDS y SYSVOL en letras de unidad distintas y usar esas rutas reales durante la promocion.',
      'Rehecho el monitor de ping: ventana redimensionable, tarjetas mas compactas, stop/reanudar por ping y detener/reanudar todos.',
      'Anadido intervalo configurable para ping continuo, aviso de pings duplicados y Favoritos persistentes para destinos habituales.',
      'Corregido el tamano minimo de las tarjetas del monitor de ping para que se vea completa la IP, el estado y el boton Anadir a Favoritos.',
      'Ajustado el reparto de columnas del monitor de ping para que las tarjetas se adapten sin aplastar el contenido.',
      'Anadido nombre personalizado opcional al crear un ping para identificar rapidamente cada destino.',
      'Actualizadas las tarjetas del monitor de ping para mostrar nombre e IP a la vez.',
      'Mejorados los Favoritos de ping para guardar y recuperar tambien el nombre personalizado junto a la IP.',
      'Anadido boton Borrar a la derecha de cada ping guardado en Favoritos.',
      'Los Favoritos se refrescan al borrar un destino y eliminan tambien el registro persistente guardado.'
    ]
  },
  {
    version: '2.1.89',
    date: '12/05/2026',
    changes: [
      'Reordenado Exchange para mostrar Prepare Schema a la izquierda como primer paso recomendado.',
      'Anadido aviso previo al boton Instalar Exchange para confirmar que la maquina ya esta en dominio y que Prepare Schema/AD se ha ejecutado.',
      'Corregida la tarjeta Firewall para que no quede en No detectado cuando Windows Firewall esta activo o desactivado.',
      'Anadida lectura rapida del registro de Windows Firewall como respaldo si PowerShell tarda o falla.'
    ]
  },
  {
    version: '2.1.88',
    date: '12/05/2026',
    changes: [
      'Eliminada la barra exterior duplicada de los dialogos para dejar solo la cabecera interna de Easy Deploy.',
      'Corregido el boton minimizar interno para ocultar solo el aviso sin minimizar la aplicacion completa.',
      'Anadido boton temporal de restaurar aviso dentro de la app cuando un dialogo interno se minimiza.'
    ]
  },
  {
    version: '2.1.87',
    date: '12/05/2026',
    changes: [
      'Corregido el minimizado de los dialogos de prerrequisitos de DC1 y DC2 para que solo se minimice el aviso, no toda la aplicacion.',
      'Convertidos los avisos internos en ventanas independientes de Windows para evitar bloqueos al cambiar de ventana o minimizar.',
      'Al minimizar un aviso se libera el bloqueo modal y al restaurarlo vuelve a capturar el foco de forma controlada.',
      'Actualizada la politica de versiones: cada cambio de la aplicacion debe subir version y quedar reflejado en el apartado Versiones.'
    ]
  },
  {
    version: '2.1.86',
    date: '12/05/2026',
    changes: [
      'Corregidos los dialogos de confirmacion de DC1 y DC2 para que no queden siempre por encima de todas las ventanas.',
      'Anadido boton de minimizar en los dialogos internos para evitar bloqueos visuales cuando se trabaja con otras ventanas.',
      'Mejorada la apertura de guias PDF: ahora se abren directamente con Firefox si esta instalado y, si no, con Microsoft Edge.',
      'Eliminados los botones de instalar Firefox/Adobe desde Guias para que el apartado no lance instaladores ni deje la app esperando una eleccion.',
      'Eliminada la apertura de guias con Adobe Reader porque su comportamiento no era fiable en los equipos de destino.',
      'Anadido boton Net Framework 3.5 en Sistemas > Controlador de dominio para instalar Net-Framework-Core desde el CD/ISO local de Windows Server.',
      'Mejorado Net Framework 3.5 con deteccion de Sources\\SxS y reintento por DISM si Install-WindowsFeature no confirma la instalacion.',
      'Anadido aviso obligatorio en DC2 antes del reinicio para que el usuario lea el paso manual de promocion tras reiniciar.',
      'Actualizado el historial visible de Versiones para dejar agrupados todos los arreglos del dia en esta version.'
    ]
  },
  {
    version: '2.1.82',
    date: '11/05/2026',
    changes: [
      'Añadido apartado Programas en la barra lateral debajo de Redes.',
      'Añadidos accesos para lanzar los instaladores de Firefox y WinRAR desde la carpeta OTROS.',
      'Añadido acceso a Adobe Reader desde Programas.',
      'Añadido apartado Guías para abrir documentación PDF desde la carpeta GUIAS.',
      'Corregida apertura de PDFs en Guías usando Microsoft Edge de forma directa.',
      'Añadida selección manual de carpeta de recursos con informe de archivos encontrados y faltantes.',
      'Mejorada la colocación automática del bloque inferior de la barra lateral al añadir nuevos apartados.',
      'Convertida la herramienta Ping en un monitor multi-ping con varias tarjetas simultáneas.',
      'Añadido botón para agregar nuevos pings mientras otros siguen ejecutándose.',
      'Añadido estado visual verde/rojo según respuesta o pérdida de conectividad.'
    ]
  },
  {
    version: '2.1.75',
    date: '03/05/2026',
    changes: [
      'Añadido el apartado Versiones en la barra superior, a la izquierda del selector Light/Dark.',
      'La pantalla Versiones muestra ahora los cambios por versión y fecha.',
      'El historial aparece ordenado con los cambios más recientes arriba y los primeros cambios abajo.'
    ]
  },
  {
    version: '2.1.69',
    date: '02/05/2026',
    changes: [
      'Se han movido archivos para mejorar la eficiencia del programa.',
      'Organizados iconos y recursos visuales en una carpeta dedicada.',
      'Mejorado el empaquetado del ejecutable para incluir recursos visuales y herramientas auxiliares.',
      'Limpieza de archivos antiguos y elementos duplicados de compilación.'
    ]
  },
  {
    version: '2.1.65',
    date: '01/05/2026',
    changes: [
      'Añadido aviso visual cuando Switch Allied, Switch Cisco o Router finalizan con código 1.',
      'El aviso explica al usuario que revise cable de consola, driver USB/Serial, puerto COM o programas externos.',
      'Corregida la configuración Cisco para VLANs, trunk y verificación por interfaz.',
      'Detectado VTP Client para avisar cuando Cisco no permite crear VLANs localmente.',
      'Añadida la pestaña Seguridad dentro de Guía rápida.'
    ]
  },
  {
    version: '2.1.62',
    date: '30/04/2026',
    changes: [
      'Añadido apartado Seguridad en la barra lateral.',
      'Creado Seguridad > Firewall con acciones Activar firewall y Desactivar firewall.',
      'Añadido widget Firewall en Inicio, verde solo si Domain, Private y Public están activados.',
      'Corregidos los comandos PowerShell de firewall para activar y desactivar perfiles correctamente.'
    ]
  },
  {
    version: '2.1.57',
    date: '29/04/2026',
    changes: [
      'Corregida visualización de acentos, ñ y caracteres españoles en consola e interfaz.',
      'Separado el color del estado Admin y Recursos en la esquina inferior izquierda.',
      'Añadidos avisos más claros para errores que antes solo quedaban escritos en consola.',
      'Revisadas ventanas informativas para que el usuario deba aceptar mensajes importantes.'
    ]
  },
  {
    version: '2.1.53',
    date: '28/04/2026',
    changes: [
      'Corregidos botones Aceptar/Cancelar en diálogos de entrada como licencia Windows/KMS.',
      'Revisadas ventanas modernas de entrada para evitar cajas antiguas y controles ocultos.',
      'Mejorada la robustez del arranque y la captura de foco en la ventana inicial de licencia.',
      'Añadidas comprobaciones para reforzar el acceso inicial de la aplicación.'
    ]
  },
  {
    version: '2.1.47',
    date: '27/04/2026',
    changes: [
      'Revisado flujo de prerrequisitos SharePoint y AppFabric.',
      'Añadido desbloqueo de instaladores locales para evitar problemas de Zone.Identifier.',
      'Añadida instalación y verificación específica de AppFabric y su actualización CU.',
      'Añadidos avisos de reinicio y botón Reiniciar sistema cuando SharePoint/AppFabric lo requiere.'
    ]
  },
  {
    version: '2.1.41',
    date: '26/04/2026',
    changes: [
      'Mejorado SharePoint para detectar roles y prerrequisitos ya instalados antes de reinstalar.',
      'Añadidos mensajes de confirmación cuando no hay nada pendiente por instalar.',
      'Ajustada extracción de ISO/CD para esperar confirmación del usuario y no tapar instaladores.',
      'Actualizada tarjeta SharePoint a Prerrequisitos y SharePoint.'
    ]
  },
  {
    version: '2.1.37',
    date: '25/04/2026',
    changes: [
      'Prepare Schema de Exchange busca ExchangeServer2019-x64-cu15 dentro de los recursos.',
      'La comprobación del CD/ISO de Exchange queda más transparente para el usuario.',
      'Se evita pedir manualmente Setup.exe si la app puede detectarlo desde recursos.',
      'Exchange y SharePoint evitan reinstalar prerrequisitos ya presentes cuando pueden comprobarlo.'
    ]
  },
  {
    version: '2.1.33',
    date: '24/04/2026',
    changes: [
      'Ampliada Guía rápida con pestañas, explicaciones de Sistemas, Redes, Recursos, Consola y Errores.',
      'Corregido bloqueo de scroll al maximizar y abrir Guía rápida > Errores.',
      'Mejorada la herramienta Ping con ping continuo, repetir, cambiar destino y accesos a DNS/gateway.',
      'Hecho dinámico el estado de discos para refrescar cambios sin reiniciar la app.'
    ]
  },
  {
    version: '2.1.30',
    date: '23/04/2026',
    changes: [
      'Añadido panel Estado de discos en Inicio con acceso a Disk Management.',
      'El panel se adapta en altura cuando hay más unidades para no cortar información.',
      'Añadido refresco periódico del estado de discos.',
      'Mejorado el botón Disk Management para seguir el patrón visual de las tarjetas.'
    ]
  },
  {
    version: '2.1.24',
    date: '22/04/2026',
    changes: [
      'Añadido widget Teclado ESP en Inicio.',
      'El widget puede aplicar Español/España como teclado principal del sistema.',
      'Sincronizar hora configura España, formato regional y reloj de 24 horas.',
      'Eliminada la ruta de recursos visible al pie de Inicio para dejar una pantalla más limpia.'
    ]
  },
  {
    version: '2.1.22',
    date: '21/04/2026',
    changes: [
      'Eliminado reinicio innecesario antes de convertir Windows Server Evaluation.',
      'KMS detecta mejor cuando Windows ya no es Evaluation después de reiniciar manualmente.',
      'Ajustado el esquema de versión a 2.1.0 hasta 2.1.100 antes de saltar a 2.2.0.',
      'Revisada la conversión Evaluation para pedir clave solo cuando corresponde.'
    ]
  },
  {
    version: '2.1.16',
    date: '20/04/2026',
    changes: [
      'Añadida opción Prepare Schema dentro de Exchange.',
      'Se solicitan dominio y Organization Name antes de preparar AD/schema.',
      'Se comprueba conectividad con ping antes de ejecutar comandos de Exchange.',
      'PrepareSchema, PrepareAD y PrepareAllDomains se ejecutan por consola con barra de progreso.'
    ]
  },
  {
    version: '2.1.10',
    date: '18/04/2026',
    changes: [
      'Rehecho flujo KMS para convertir Server Evaluation con clave genérica GVLK cuando corresponde.',
      'Ocultado el progreso textual de DISM para usar la barra de progreso superior.',
      'Tratado el código 1168 como reinicio pendiente cuando la conversión realmente queda aplicada.',
      'KMS continúa con activación cuando el sistema ya no es Evaluation.'
    ]
  },
  {
    version: '2.1.5',
    date: '10/04/2026',
    changes: [
      'Añadido apartado Redes con Switch Allied, Switch Cisco y Router.',
      'Integrados scripts interactivos dentro de la consola interna de Easy Deploy.',
      'Añadido botón Cancelar junto a Enviar para cerrar herramientas interactivas.',
      'Corregido Volver para regresar a Redes si se ejecutó Switch o Router.'
    ]
  },
  {
    version: '2.1.0',
    date: '05/04/2026',
    changes: [
      'Reordenado Sistemas: Controlador de dominio, Sincronizar hora, KMS, SQL, JCHAT, Exchange, SharePoint y Skype for Business.',
      'Eliminados botones Abrir de tarjetas para que toda la tarjeta sea pulsable.',
      'Centrados textos dentro de tarjetas para mejorar la lectura.',
      'Añadidas futuras acciones de AD, Exchange, JCHAT, redes y seguridad como estructura preparada.'
    ]
  },
  {
    version: '2.0.3',
    date: '29/03/2026',
    changes: [
      'Mejoradas ventanas modernas de entrada para licencia, dominio, KMS y datos solicitados al usuario.',
      'Unificadas ventanas de información para eliminar cajas antiguas de Windows cuando era posible.',
      'Mejorado redimensionado de pantalla y aparición de scroll solo cuando el contenido no cabe.',
      'Añadida recomendación de compilación segura con PyInstaller, UPX y licencia en hash.'
    ]
  },
  {
    version: '2.0.2',
    date: '22/03/2026',
    changes: [
      'Añadido menú Herramientas lateral dentro de la ventana.',
      'Separadas visualmente secciones Diagnóstico, Sistema, Utilidades y Acciones.',
      'Añadido scroll al menú Herramientas cuando no caben todas las opciones.',
      'Añadidas utilidades administrativas: AD Users and Computers, DNS Manager, Group Policy Management, CMD y PowerShell.'
    ]
  },
  {
    version: '2.0.1',
    date: '08/03/2026',
    changes: [
      'Dividido el programa en módulos Python por UI, tareas, sistema, logging y acciones.',
      'Añadido sistema de logs persistentes por tarea.',
      'Añadida consola integrada con salida en directo y ruta de log actual.',
      'Añadidas comprobaciones de administrador, recursos y estado general.'
    ]
  },
  {
    version: '2.0.0',
    date: '01/03/2026',
    changes: [
      'Inicio de la rama moderna de Easy Deploy.',
      'Rediseñada la interfaz principal con estilo moderno, tarjetas, sidebar y modo claro/oscuro.',
      'Añadida pantalla de licencia más visual y coherente con Easy Deploy.',
      'Añadida versión visible en la barra superior.'
    ]
  },
  {
    version: '1.9.0',
    date: '25/01/2026',
    changes: [
      'Cierre de la rama antigua antes del rediseño moderno.',
      'La app queda como instalador monolítico con SharePoint roles, SharePoint prerrequisitos, KMS y botones reservados.',
      'Se mantiene una sola ventana con logo, botones, barra de progreso, porcentaje y consola interna.'
    ]
  },
  {
    version: '1.8.0',
    date: '18/01/2026',
    changes: [
      'Pulida la ventana principal CustomTkinter con centrado, tamaño mínimo y layout por columnas.',
      'Añadido logo visible en la pantalla principal usando recursos empaquetables.',
      'Añadido pie de página con autoría y marca Beta 0.2.',
      'Preparado el aspecto final de la rama antigua antes del cambio grande de interfaz.'
    ]
  },
  {
    version: '1.7.0',
    date: '09/01/2026',
    changes: [
      'Reservados botones para futuras funciones como Exchange y nuevos bloques de despliegue.',
      'Preparada la cuadrícula de ocho botones para crecer más allá de SharePoint y KMS.',
      'Añadidos botones preparados para conectar nuevas funcionalidades poco a poco.',
      'Revisada la estructura visual básica de la pantalla principal.'
    ]
  },
  {
    version: '1.6.0',
    date: '02/01/2026',
    changes: [
      'Consolidado el flujo de ejecución por hilos para que las tareas largas no bloqueen completamente la UI.',
      'Integrada redirección de salida a una consola interna.',
      'Mejorada la visibilidad de porcentaje y progreso durante tareas de roles, prerrequisitos y KMS.',
      'Añadido botón de reinicio del sistema al terminar operaciones que lo requieren.'
    ]
  },
  {
    version: '1.5.0',
    date: '19/12/2025',
    changes: [
      'Añadida activación KMS con comandos /ipk, /skms y /ato.',
      'Añpado cambio de edición con DISM /Set-Edition para Server Datacenter.',
      'Añadidas claves genéricas por versión de Windows Server y Windows 10 Pro.',
      'Añadida comprobación básica de servidor KMS mediante ping.',
      'Añadida detección de edición actual de Windows con DISM.',
      'Añadida detección de Windows Evaluation mediante script de licencia.',
      'Añadida lectura de versión y edición desde systeminfo para elegir clave KMS.'
    ]
  },
  {
    version: '1.4.0',
    date: '05/12/2025',
    changes: [
      'Añadido instalador especial de AppFabric mediante PowerShell.',
      'Añadida ejecución de instaladores MSI y EXE desde la carpeta SHAPRE.',
      'Añadida programación RunOnce para continuar prerrequisitos tras reinicio.',
      'Añadida limpieza de progreso cuando termina la secuencia de prerrequisitos.'
    ]
  },
  {
    version: '1.3.0',
    date: '21/11/2025',
    changes: [
      'Añadida secuencia de prerrequisitos SharePoint desde la carpeta Desktop\\SHAPRE.',
      'Añadido archivo progreso_instalacion.txt para recordar el paso después de reinicios.',
      'Añadida detección básica de Visual C++ Redistributable desde el registro.',
      'Preparado salto de instaladores ya presentes.'
    ]
  },
  {
    version: '1.2.0',
    date: '07/11/2025',
    changes: [
      'Añadida instalación de roles y características SharePoint en dos bloques.',
      'Añadida comprobación con Get-WindowsFeature antes de instalar cada feature.',
      'Añadida instalación mediante Install-WindowsFeature desde PowerShell.',
      'Añadido resumen final de fallos y elementos instalados.'
    ]
  },
  {
    version: '1.1.0',
    date: '24/10/2025',
    changes: [
      'Primer salto funcional desde el prototipo inicial.',
      'Añadida pantalla splash con escudo y mensaje de bienvenida.',
      'Añadida carga de logotipo.ico y EscudoRT.png desde ruta compatible con PyInstaller.',
      'Añadida consola interna para mostrar salida de comandos al usuario.',
      'Añadida ejecución de tareas en segundo plano con threading.',
      'Añadida barra de progreso real para tareas largas.',
      'Añadido botón Cancelar y variable global de cancelación para detener bucles de instalación.',
      'Preparada la base para roles, prerrequisitos y KMS dentro de la misma ventana.'
    ]
  },
  {
    version: '1.0.0',
    date: '10/10/2025',
    changes: [
      'Inicio real del proyecto Easy Deploy.',
      'Creada primera ventana CustomTkinter para centralizar tareas de despliegue.',
      'Primer enfoque de app personal para desplegar prerrequisitos y características de Windows.',
      'Centrada la ventana principal como base inicial.'
    ]
  }
];
