const { contextBridge, ipcRenderer } = require('electron');

function createBackendApi() {
  return {
    runAction(action, payload) {
      return ipcRenderer.invoke('backend:runAction', action, payload || {});
    },
    cancelAction() {
      return ipcRenderer.invoke('backend:cancelAction');
    },
    respondPrompt(promptId, value) {
      return ipcRenderer.invoke('backend:respondPrompt', promptId, value);
    },
    onBackendEvent(callback) {
      const listener = (_event, payload) => callback(payload);
      ipcRenderer.on('backend:event', listener);
      return () => ipcRenderer.removeListener('backend:event', listener);
    },
    getBackendStatus() {
      return ipcRenderer.invoke('backend:getStatus');
    },
    getAppInfo() {
      return ipcRenderer.invoke('app:getInfo');
    },
    async pingPreload() {
      const mainPing = await ipcRenderer.invoke('preload:ping');
      return {
        ok: true,
        source: 'preload',
        preloadPath: __filename,
        timestamp: new Date().toISOString(),
        main: mainPing,
      };
    },
  };
}

const api = createBackendApi();

// Compatibilidad defensiva: algunas pantallas/servicios antiguos pueden buscar
// nombres distintos. Los tres apuntan al mismo bridge seguro.
contextBridge.exposeInMainWorld('easyDeployBackend', api);
contextBridge.exposeInMainWorld('electronAPI', api);
contextBridge.exposeInMainWorld('easyDeploy', api);

ipcRenderer.send('preload:loaded', {
  ok: true,
  source: 'preload',
  preloadPath: __filename,
  timestamp: new Date().toISOString(),
});
