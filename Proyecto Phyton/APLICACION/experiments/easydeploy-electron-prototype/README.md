# Easy Deploy Electron Prototype

Prototipo aislado para estudiar si una futura version hibrida de Easy Deploy podria usar Electron + React + Vite como motor visual.

Este prototipo no forma parte de Easy Deploy real y no conecta tareas reales.

## Alcance

- Sidebar visual estilo Easy Deploy.
- Pantalla Inicio simulada.
- Botones simulados: Sistemas, Exchange, Ping, Programas y Guias.
- Consola visual simulada.
- IPC limitado a metadatos del prototipo.
- Sin PowerShell.
- Sin subprocess.
- Sin lectura de recursos reales.
- Sin licencia real.
- Sin rutas reales.

## Requisitos

- Node.js.
- npm.

Si PowerShell bloquea `npm.ps1`, usa `npm.cmd`.

## Instalacion

```powershell
npm.cmd install
```

## Ejecutar como app Electron

```powershell
npm.cmd run electron:dev
```

Este comando compila el bundle Vite y abre Electron cargando `dist/index.html`.

## Ejecutar solo en navegador para revisar UI

```powershell
npm.cmd run dev
```

Luego abre:

```text
http://127.0.0.1:5178
```

## Build web

```powershell
npm.cmd run build
```

## Empaquetar Windows

```powershell
npm.cmd run package:windows
```

La salida esperada queda en:

```text
dist_desktop/
```

## Criterios de evaluacion

- Tiempo aproximado desde doble click hasta ventana visible.
- Peso del instalador generado.
- Aspecto visual frente a CustomTkinter actual.
- Funcionamiento sin internet despues de instalar dependencias.
- Viabilidad de un puente futuro Python/PowerShell sin tocar tareas reales.

## Riesgos conocidos

- Electron aumenta el tamano final frente a PyInstaller.
- Una migracion real exigiria un puente seguro entre React/Electron y el motor Python actual.
- No se debe ejecutar PowerShell ni subprocess desde el renderer.
- La licencia/hash de Easy Deploy debe seguir siendo responsabilidad del motor Python actual si se avanza.
