import type { BackendApi, BackendEvent } from '../types/backend';

const demoEvents = new EventTarget();

function getBridge(): BackendApi | undefined {
  return window.easyDeployBackend || window.electronAPI || window.easyDeploy;
}

export function getDetectedBridgeApis() {
  return {
    easyDeployBackend: Boolean(window.easyDeployBackend),
    electronAPI: Boolean(window.electronAPI),
    easyDeploy: Boolean(window.easyDeploy),
    windowKeys: Object.keys(window).filter((key) => key.toLowerCase().includes('easy') || key.toLowerCase().includes('electron')),
  };
}

function emitDemo(event: BackendEvent) {
  demoEvents.dispatchEvent(new CustomEvent('backend', { detail: event }));
}

function makeId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function fallbackRunAction(action: string, payload: Record<string, unknown> = {}) {
  const id = makeId();
  emitDemo({
    type: 'error',
    id,
    action,
    source: 'BRIDGE',
    level: 'error',
    message:
      `Backend Electron/Python no expuesto. Acción no ejecutada: ${action}. ` +
      `Esto significa que preload.js no cargó o se está abriendo el front-end con navegador/Vite en vez de Electron. ` +
      `Payload: ${JSON.stringify(payload)}`,
  });
  emitDemo({ type: 'finished', id, action, success: false, result: { backend_missing: true } });
  return Promise.resolve({ id, accepted: false, error: 'Backend Electron/Python no expuesto.' });
}

export const backendClient = {
  runAction(action: string, payload: Record<string, unknown> = {}) {
    const bridge = getBridge();
    if (bridge?.runAction) {
      return bridge.runAction(action, payload);
    }
    return fallbackRunAction(action, payload);
  },

  cancelAction() {
    const bridge = getBridge();
    if (bridge?.cancelAction) {
      return bridge.cancelAction();
    }
    return fallbackRunAction('cancel');
  },

  respondPrompt(promptId: string, value: unknown) {
    const bridge = getBridge();
    if (bridge?.respondPrompt) {
      return bridge.respondPrompt(promptId, value);
    }
    return Promise.resolve(false);
  },

  sendConsoleInput(value: string) {
    const bridge = getBridge();
    if (bridge?.sendConsoleInput) {
      return bridge.sendConsoleInput(value);
    }
    return Promise.resolve(false);
  },

  onBackendEvent(callback: (event: BackendEvent) => void) {
    const bridge = getBridge();
    if (bridge?.onBackendEvent) {
      return bridge.onBackendEvent(callback);
    }
    const listener = (event: Event) => callback((event as CustomEvent<BackendEvent>).detail);
    demoEvents.addEventListener('backend', listener);
    setTimeout(() => {
      const exposed = Object.keys(window)
        .filter((key) => key.toLowerCase().includes('easy') || key.toLowerCase().includes('electron'))
        .join(', ');
      emitDemo({
        type: 'error',
        source: 'BRIDGE',
        level: 'error',
        message:
          'La app se está ejecutando sin preload de Electron. Los botones no pueden llegar al backend Python. ' +
          `Objetos detectados en window: ${exposed || 'ninguno'}.`,
      });
    }, 250);
    return () => demoEvents.removeEventListener('backend', listener);
  },

  getBackendStatus() {
    const bridge = getBridge();
    if (bridge?.getBackendStatus) {
      return bridge.getBackendStatus();
    }
    return Promise.resolve({ running: false, error: 'Backend no expuesto' });
  },

  getAppInfo() {
    const bridge = getBridge();
    if (bridge?.getAppInfo) {
      return bridge.getAppInfo();
    }
    return Promise.resolve({ name: 'Easy Deploy', version: 'demo', mode: 'browser-demo' });
  },

  quitApp() {
    const bridge = getBridge();
    if (bridge?.quitApp) {
      return bridge.quitApp();
    }
    return Promise.resolve({ ok: false, error: 'quitApp no expuesto' });
  },

  pingPreload() {
    const bridge = getBridge();
    if (bridge?.pingPreload) {
      return bridge.pingPreload();
    }
    return Promise.resolve({ ok: false, error: 'preload no expuesto' });
  },
};
