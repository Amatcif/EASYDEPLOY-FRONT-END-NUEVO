README - CARPETA GIT PARA EASY DEPLOY

Este paquete esta preparado para que TODO quede dentro de una sola carpeta llamada:

GIT

Instalacion:
1. Copia la carpeta GIT completa dentro de la raiz del proyecto, junto a:
   EASY DEPLOY.py
   AGENTS.md
   .agents

La estructura correcta sera:

APLICACION/
├─ EASY DEPLOY.py
├─ AGENTS.md
├─ .agents/
└─ GIT/
   ├─ 01_GIT_ANTES_DE_CODEX.bat
   ├─ 02_GIT_DESPUES_DE_PROBAR.bat
   ├─ 03_GIT_VER_CHECKPOINTS.bat
   ├─ 04_GIT_VOLVER_A_CHECKPOINT.bat
   ├─ 05_GIT_RESTAURAR_BACKUP_PREVIO.bat
   ├─ CREAR_ACCESOS_CON_ICONOS.bat
   └─ icons/

Importante:
Aunque los .bat estan dentro de GIT, trabajan sobre la carpeta superior del proyecto.
No crearan el repositorio Git dentro de GIT, sino en la raiz del proyecto.

Para iconos:
1. Entra en la carpeta GIT.
2. Ejecuta CREAR_ACCESOS_CON_ICONOS.bat.
3. Se creara:
   GIT/Accesos con iconos/

Usa esos accesos directos para verlo mas claro.

Flujo recomendado:
1. 01 GIT - ANTES de Codex
2. Pedir cambios a Codex
3. Probar EASY DEPLOY
4. 02 GIT - DESPUES de probar si funciona
5. 04 GIT - VOLVER a checkpoint si algo se rompe
