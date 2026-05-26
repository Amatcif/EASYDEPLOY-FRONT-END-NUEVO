const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");

const isDev = Boolean(process.env.EASYDEPLOY_PROTO_DEV_URL);

function createWindow() {
  const win = new BrowserWindow({
    width: 1240,
    height: 780,
    minWidth: 1024,
    minHeight: 680,
    show: false,
    autoHideMenuBar: true,
    title: "Easy Deploy Electron Prototype",
    backgroundColor: "#eef2f7",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    }
  });

  win.once("ready-to-show", () => {
    win.show();
    win.focus();
  });

  if (isDev) {
    win.loadURL(process.env.EASYDEPLOY_PROTO_DEV_URL);
  } else {
    win.loadFile(path.join(__dirname, "dist", "index.html"));
  }

  win.webContents.setWindowOpenHandler(({ url }) => {
    return url.startsWith("http://127.0.0.1") ? { action: "allow" } : { action: "deny" };
  });
}

ipcMain.handle("prototype:get-info", () => ({
  appName: "Easy Deploy",
  mode: "Prototipo visual aislado",
  engine: "Electron + React + Vite",
  offlineReady: true,
  realTasksConnected: false
}));

const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    const win = BrowserWindow.getAllWindows()[0];
    if (win) {
      if (win.isMinimized()) win.restore();
      win.show();
      win.focus();
    }
  });

  app.whenReady().then(createWindow);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}
