# Easy Deploy - estructura del codigo

El punto de entrada sigue siendo `EASY DEPLOY.py`, pero ahora solo arranca la aplicacion.

## Estructura

- `easy_deploy_app/app.py`: clase principal `EASYDEPLOY` y configuracion inicial.
- `easy_deploy_app/constants.py`: constantes, expresiones regulares y valores de configuracion.
- `easy_deploy_app/core/progress.py`: base SQLite de progreso.
- `easy_deploy_app/core/sysutils.py`: utilidades de Windows, PowerShell, rutas, validacion y licencia.
- `easy_deploy_app/core/logging_utils.py`: logs persistentes por ejecucion.
- `easy_deploy_app/ui/environment.py`: estado de administrador, recursos y validaciones de UI.
- `easy_deploy_app/ui/actions.py`: menu superior y herramientas de diagnostico.
- `easy_deploy_app/ui/layout.py`: pantallas, dialogos, consola, progreso e hilos.
- `easy_deploy_app/tasks/sharepoint.py`: tareas SharePoint.
- `easy_deploy_app/tasks/exchange.py`: tareas Exchange.
- `easy_deploy_app/tasks/sql.py`: tareas SQL Server.
- `easy_deploy_app/tasks/jchat.py`: tareas JChat/Openfire.
- `easy_deploy_app/tasks/kms.py`: conversion/activacion KMS.
- `easy_deploy_app/tasks/system.py`: sincronizacion horaria.
- `easy_deploy_app/tasks/domain.py`: DC1, DC2 y unir a dominio.

## Logs

Cada tarea crea un log en:

`%LOCALAPPDATA%\EasyDeploy\logs`

Desde la app se puede abrir con `Archivo > Abrir Logs`.

El nombre del archivo incluye fecha, hora y tarea, por ejemplo:

`20260423-141530_task_exchange.log`

## Recursos externos

Las ISOs e instaladores grandes no se empaquetan dentro del `.exe`.
La app busca carpetas `EXCHANGE`, `SHAPRE`, `SQL` y `JCHAT` dentro de una carpeta llamada `EASY DEPLOY` o `EASYDEPLOY`.

Si necesitas forzar una ubicacion:

```powershell
$env:EASYDEPLOY_PAYLOAD_DIR = "C:\Ruta\A\EASY DEPLOY"
```

## Licencia

La clave no se guarda en texto plano. Se valida con SHA-256.
Para cambiarla, configura:

```powershell
$env:EASYDEPLOY_LICENSE_SHA256 = "hash_sha256_de_la_nueva_clave"
```
