const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("easyDeployPrototype", {
  getInfo: () => ipcRenderer.invoke("prototype:get-info")
});
