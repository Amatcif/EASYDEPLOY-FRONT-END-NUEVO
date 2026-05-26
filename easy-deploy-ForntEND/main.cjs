const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const packageMetadata = require('./package.json');
const preloadPath = path.join(__dirname, 'preload.js');
const appVersion = packageMetadata.easyDeployVersion || packageMetadata.version || 'unknown';

let mainWindow = null;
let backendProcess = null;
let backendSpec = null;
let backendLastError = '';
let rendererReady = false;
let pendingRendererEvents = [];

function electronLogPath() {
  const base = process.env.LOCALAPPDATA || appInstallDir();
  return path.join(base, 'EasyDeploy', 'logs', 'electron-main.log');
}

function writeMainLog(level, message, details) {
  try {
    const logPath = electronLogPath();
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    const suffix = details ? ` ${JSON.stringify(details)}` : '';
    fs.appendFileSync(logPath, `[${new Date().toISOString()}] [${level}] ${message}${suffix}\n`, 'utf8');
  } catch (_) {
    // El log de Electron nunca debe impedir que arranque la aplicacion.
  }
}

function repairMojibake(value) {
  if (typeof value === 'string') {
    if (!/[ÃÂ]/.test(value)) return value;
    try {
      return Buffer.from(value, 'latin1').toString('utf8');
    } catch (_) {
      return value;
    }
  }
  if (Array.isArray(value)) {
    return value.map(repairMojibake);
  }
  if (value && typeof value === 'object') {
    const repaired = {};
    for (const [key, item] of Object.entries(value)) {
      repaired[key] = repairMojibake(item);
    }
    return repaired;
  }
  return value;
}

function configureGpuCompatibility() {
  app.disableHardwareAcceleration();
  app.commandLine.appendSwitch('disable-gpu');
  app.commandLine.appendSwitch('disable-gpu-compositing');
  app.commandLine.appendSwitch('disable-gpu-rasterization');
  app.commandLine.appendSwitch('disable-accelerated-2d-canvas');
  app.commandLine.appendSwitch('disable-accelerated-video-decode');
  app.commandLine.appendSwitch('disable-gpu-sandbox');
  app.commandLine.appendSwitch(
    'disable-features',
    'UseSkiaRenderer,CanvasOopRasterization,VizDisplayCompositor'
  );
  writeMainLog('info', 'GPU/aceleración gráfica desactivada por compatibilidad Windows Server.', {
    argv: process.argv,
    packaged: app.isPackaged,
  });
}

configureGpuCompatibility();

function appInstallDir() {
  try {
    return path.dirname(process.execPath);
  } catch (_) {
    return __dirname;
  }
}

function projectBackendCwd() {
  if (app.isPackaged) {
    return appInstallDir();
  }
  return path.resolve(__dirname, '..', 'Proyecto Phyton', 'APLICACION');
}

function candidateBackendExecutables() {
  const candidates = [];

  if (app.isPackaged) {
    candidates.push({
      label: 'packaged-extraResources',
      command: path.join(process.resourcesPath || '', 'backend', 'easydeploy_backend.exe'),
      args: [],
      cwd: appInstallDir(),
    });
    candidates.push({
      label: 'packaged-beside-exe',
      command: path.join(appInstallDir(), 'backend', 'easydeploy_backend.exe'),
      args: [],
      cwd: appInstallDir(),
    });
    candidates.push({
      label: 'packaged-resources-root',
      command: path.join(process.resourcesPath || '', 'easydeploy_backend.exe'),
      args: [],
      cwd: appInstallDir(),
    });
  }

  candidates.push({
    label: 'local-backend-dist',
    command: path.join(__dirname, 'backend_dist', 'easydeploy_backend.exe'),
    args: [],
    cwd: __dirname,
  });

  candidates.push({
    label: 'python-module',
    command: process.env.EASYDEPLOY_PYTHON || 'py',
    args: ['-3', '-m', 'easy_deploy_app.bridge.bridge_server'],
    cwd: projectBackendCwd(),
  });

  return candidates;
}

function backendExecutable() {
  const candidates = candidateBackendExecutables();
  for (const candidate of candidates) {
    if (candidate.args.length === 0 && candidate.command.toLowerCase().endsWith('.exe')) {
      if (fs.existsSync(candidate.command)) {
        return candidate;
      }
    }
  }

  // Último recurso en desarrollo: Python por módulo.
  return candidates[candidates.length - 1];
}

function sendToRenderer(event) {
  const payload = {
    timestamp: new Date().toISOString(),
    ...event,
  };
  writeMainLog(payload.level || payload.type || 'event', payload.message || payload.type || 'backend:event', {
    source: payload.source,
    action: payload.action,
    id: payload.id,
  });
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (rendererReady) {
      mainWindow.webContents.send('backend:event', payload);
    } else {
      pendingRendererEvents.push(payload);
    }
  } else {
    pendingRendererEvents.push(payload);
  }
}

function flushRendererEvents() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const events = pendingRendererEvents;
  pendingRendererEvents = [];
  for (const event of events) {
    mainWindow.webContents.send('backend:event', event);
  }
}

function startBackend() {
  if (backendProcess && !backendProcess.killed) return;

  const spec = backendExecutable();
  backendSpec = spec;
  backendLastError = '';
  const backendExists = spec.args.length === 0 && spec.command.toLowerCase().endsWith('.exe')
    ? fs.existsSync(spec.command)
    : true;

  sendToRenderer({
    type: 'status',
    source: 'BRIDGE',
    level: 'info',
    message: `Iniciando backend Python: ${spec.label} | ${spec.command} ${spec.args.join(' ')} | cwd=${spec.cwd} | backendExists=${backendExists}`,
  });
  writeMainLog('info', 'Backend seleccionado', { spec, backendExists });

  try {
    backendProcess = spawn(spec.command, spec.args, {
      cwd: spec.cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        EASYDEPLOY_ELECTRON: '1',
        EASYDEPLOY_INSTALL_DIR: appInstallDir(),
      },
    });
  } catch (error) {
    backendLastError = String(error && error.message ? error.message : error);
    backendProcess = null;
    sendToRenderer({
      type: 'error',
      source: 'BRIDGE',
      level: 'error',
      message: `No se pudo arrancar el backend Python: ${backendLastError}`,
    });
    return;
  }

  let stdoutBuffer = '';
  backendProcess.stdout.on('data', (chunk) => {
    stdoutBuffer += chunk.toString('utf8');
    let index = stdoutBuffer.indexOf('\n');
    while (index >= 0) {
      const line = stdoutBuffer.slice(0, index).trim();
      stdoutBuffer = stdoutBuffer.slice(index + 1);
      if (line) {
        try {
          sendToRenderer(repairMojibake(JSON.parse(line)));
        } catch (_error) {
          sendToRenderer({ type: 'log', source: 'PYTHON', level: 'info', message: line });
        }
      }
      index = stdoutBuffer.indexOf('\n');
    }
  });

  backendProcess.stderr.on('data', (chunk) => {
    const text = chunk.toString('utf8').trim();
    if (!text) return;
    backendLastError = text;
    sendToRenderer({
      type: 'log',
      source: 'PYTHON',
      level: 'error',
      message: text,
    });
  });

  backendProcess.on('error', (error) => {
    backendLastError = String(error && error.message ? error.message : error);
    sendToRenderer({
      type: 'error',
      source: 'BRIDGE',
      level: 'error',
      message: `Error de proceso backend: ${backendLastError}`,
    });
    backendProcess = null;
  });

  backendProcess.on('exit', (code, signal) => {
    sendToRenderer({
      type: 'status',
      source: 'BRIDGE',
      level: code === 0 ? 'info' : 'error',
      message: `Backend Python finalizado. Codigo=${code} Senal=${signal || ''}`,
    });
    backendProcess = null;
  });
}

function postToBackend(message) {
  startBackend();
  if (!backendProcess || !backendProcess.stdin || !backendProcess.stdin.writable) {
    const detail = backendLastError ? ` Último error: ${backendLastError}` : '';
    throw new Error(`Backend Python no disponible.${detail}`);
  }
  backendProcess.stdin.write(JSON.stringify(message) + '\n', 'utf8');
}

function createWindow() {
  Menu.setApplicationMenu(null);
  rendererReady = false;

  const indexPath = path.join(__dirname, 'dist', 'index.html');
  const loadTarget = app.isPackaged ? indexPath : (process.env.EASYDEPLOY_VITE_URL || 'http://localhost:3000');
  writeMainLog('info', 'Creando BrowserWindow', {
    version: appVersion,
    packaged: app.isPackaged,
    argv: process.argv,
    gpuDisabled: true,
    dirname: __dirname,
    preloadPath,
    preloadExists: fs.existsSync(preloadPath),
    indexPath,
    indexExists: fs.existsSync(indexPath),
    loadTarget,
    resourcesPath: process.resourcesPath || '',
  });

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 700,
    title: 'EASY DEPLOY',
    autoHideMenuBar: true,
    webPreferences: {
      preload: preloadPath,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  if (app.isPackaged) {
    mainWindow.loadFile(indexPath);
  } else {
    mainWindow.loadURL(loadTarget);
  }

  mainWindow.webContents.on('did-finish-load', () => {
    rendererReady = true;
    sendToRenderer({
      type: 'status',
      source: 'ELECTRON',
      level: 'info',
      message: `Front-end cargado. GPU/aceleración gráfica desactivada por compatibilidad Windows Server. version=${appVersion} packaged=${app.isPackaged} argv=${JSON.stringify(process.argv)} dirname=${__dirname} preloadPath=${preloadPath} preloadExists=${fs.existsSync(preloadPath)} indexPath=${indexPath} indexExists=${fs.existsSync(indexPath)} loadTarget=${loadTarget} resources=${process.resourcesPath || ''}`,
    });
    flushRendererEvents();
    startBackend();
  });

  mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription) => {
    sendToRenderer({
      type: 'error',
      source: 'ELECTRON',
      level: 'error',
      message: `Error cargando front-end (${errorCode}): ${errorDescription}`,
    });
  });

  mainWindow.webContents.on('console-message', (_event, level, message, line, sourceId) => {
    writeMainLog(`renderer-console-${level}`, message, { line, sourceId });
  });

  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    writeMainLog('error', 'render-process-gone', details);
    sendToRenderer({
      type: 'error',
      source: 'ELECTRON',
      level: 'error',
      message: `Renderer finalizado inesperadamente: ${JSON.stringify(details)}`,
    });
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
    rendererReady = false;
  });
}


ipcMain.handle('preload:ping', async () => {
  const spec = backendSpec || backendExecutable();
  const backendExists = spec.args.length === 0 && spec.command.toLowerCase().endsWith('.exe')
    ? fs.existsSync(spec.command)
    : true;
  const indexPath = path.join(__dirname, 'dist', 'index.html');
  writeMainLog('info', 'preload:ping recibido desde renderer', {
    preloadPath,
    preloadExists: fs.existsSync(preloadPath),
    backendPath: spec.command,
    backendExists,
  });
  return {
    ok: true,
    source: 'electron-main',
    version: appVersion,
    argv: process.argv,
    gpuDisabled: true,
    dirname: __dirname,
    preloadPath,
    preloadExists: fs.existsSync(preloadPath),
    packaged: app.isPackaged,
    resourcesPath: process.resourcesPath || '',
    installDir: appInstallDir(),
    indexPath,
    indexExists: fs.existsSync(indexPath),
    backendPath: spec.command,
    backendExists,
    backendSpec: spec,
    timestamp: new Date().toISOString(),
  };
});

ipcMain.on('preload:loaded', (_event, payload) => {
  writeMainLog('info', 'preload:loaded recibido', payload);
  sendToRenderer({
    type: 'status',
    source: 'ELECTRON',
    level: 'success',
    message: `Preload cargado: ${payload && payload.preloadPath ? payload.preloadPath : preloadPath}`,
  });
});

ipcMain.handle('backend:runAction', async (_event, action, payload = {}) => {
  const id = crypto.randomUUID();
  sendToRenderer({
    type: 'log',
    id,
    action,
    source: 'ELECTRON',
    level: 'info',
    message: `[ELECTRON] runAction recibido: ${action}`,
  });
  try {
    postToBackend({ id, type: 'run_action', action, payload });
    return { id, accepted: true };
  } catch (error) {
    const message = String(error && error.message ? error.message : error);
    sendToRenderer({ type: 'error', id, action, source: 'BRIDGE', level: 'error', message });
    return { id, accepted: false, error: message };
  }
});

ipcMain.handle('backend:cancelAction', async () => {
  const id = crypto.randomUUID();
  try {
    postToBackend({ id, type: 'cancel' });
    return { id, accepted: true };
  } catch (error) {
    const message = String(error && error.message ? error.message : error);
    sendToRenderer({ type: 'error', id, source: 'BRIDGE', level: 'error', message });
    return { id, accepted: false, error: message };
  }
});

ipcMain.handle('backend:respondPrompt', async (_event, promptId, value) => {
  try {
    postToBackend({ type: 'prompt_response', prompt_id: promptId, value });
    return true;
  } catch (error) {
    sendToRenderer({
      type: 'error',
      source: 'BRIDGE',
      level: 'error',
      message: `No se pudo responder al prompt: ${String(error && error.message ? error.message : error)}`,
    });
    return false;
  }
});

ipcMain.handle('backend:getStatus', async () => {
  return {
    running: Boolean(backendProcess && !backendProcess.killed),
    spec: backendSpec,
    lastError: backendLastError,
    resourcesPath: process.resourcesPath || '',
    installDir: appInstallDir(),
  };
});

ipcMain.handle('app:quit', async () => {
  writeMainLog('info', 'Cierre solicitado por actualizador desde renderer.');
  setTimeout(() => app.quit(), 250);
  return { ok: true };
});

ipcMain.handle('app:getInfo', async () => {
  return {
    name: 'EASY DEPLOY',
    version: packageMetadata.easyDeployVersion || app.getVersion(),
    packaged: app.isPackaged,
    backendCwd: projectBackendCwd(),
    installDir: appInstallDir(),
    resourcesPath: process.resourcesPath || '',
    smokeActions: process.env.EASYDEPLOY_STARTUP_SMOKE_ACTIONS === '1' || process.argv.includes('--smoke-actions'),
  };
});

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  process.on('uncaughtException', (error) => {
    writeMainLog('error', 'uncaughtException', {
      message: error && error.message ? error.message : String(error),
      stack: error && error.stack ? error.stack : '',
    });
    sendToRenderer({
      type: 'error',
      source: 'ELECTRON',
      level: 'error',
      message: `Error no controlado en Electron main: ${error && error.message ? error.message : String(error)}`,
    });
  });

  process.on('unhandledRejection', (reason) => {
    writeMainLog('error', 'unhandledRejection', {
      reason: reason && reason.message ? reason.message : String(reason),
      stack: reason && reason.stack ? reason.stack : '',
    });
    sendToRenderer({
      type: 'error',
      source: 'ELECTRON',
      level: 'error',
      message: `Promesa rechazada en Electron main: ${reason && reason.message ? reason.message : String(reason)}`,
    });
  });

  app.on('child-process-gone', (_event, details) => {
    writeMainLog('error', 'child-process-gone', details);
  });

  app.whenReady().then(createWindow);

  app.on('before-quit', () => {
    try {
      if (backendProcess && !backendProcess.killed) {
        backendProcess.stdin.write(JSON.stringify({ type: 'shutdown' }) + '\n', 'utf8');
        backendProcess.kill();
      }
    } catch (_) {
      // Cierre defensivo: no bloquea la salida de Electron.
    }
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
}
