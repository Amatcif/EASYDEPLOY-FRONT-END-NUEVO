import { useEffect, useMemo, useState } from "react";

type PrototypeInfo = {
  appName: string;
  mode: string;
  engine: string;
  offlineReady: boolean;
  realTasksConnected: boolean;
};

declare global {
  interface Window {
    easyDeployPrototype?: {
      getInfo: () => Promise<PrototypeInfo>;
    };
  }
}

const modules = [
  { key: "inicio", label: "Inicio", detail: "Resumen visual de entorno y estado simulado." },
  { key: "sistemas", label: "Sistemas", detail: "Acceso simulado a AD, Exchange, Skype, SQL y JCHAT." },
  { key: "exchange", label: "Exchange", detail: "Bloque visual para prerrequisitos, schema y usuarios EXC." },
  { key: "ping", label: "Ping", detail: "Monitor multi-ping simulado, sin red ni subprocess." },
  { key: "programas", label: "Programas", detail: "Instaladores offline simulados: Office, Firefox, WinRAR y Adobe." },
  { key: "guias", label: "Guías", detail: "Acceso visual simulado a documentación PDF offline." }
];

const consoleLines = [
  "[INFO] Prototipo iniciado en modo aislado.",
  "[OK] UI React renderizada sin leer recursos reales.",
  "[OK] IPC limitado a metadatos del prototipo.",
  "[SIM] Sistemas, Exchange, Ping, Programas y Guías no ejecutan acciones.",
  "[WARN] Este prototipo no sustituye Easy Deploy v2.2.5.12."
];

function App() {
  const [active, setActive] = useState("inicio");
  const [info, setInfo] = useState<PrototypeInfo | null>(null);

  useEffect(() => {
    window.easyDeployPrototype?.getInfo().then(setInfo).catch(() => {
      setInfo({
        appName: "Easy Deploy",
        mode: "Navegador/Vite",
        engine: "React + Vite",
        offlineReady: true,
        realTasksConnected: false
      });
    });
  }, []);

  const activeModule = useMemo(
    () => modules.find((module) => module.key === active) ?? modules[0],
    [active]
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">ED</div>
          <div>
            <h1>Easy Deploy</h1>
            <p>Prototipo Electron</p>
          </div>
        </div>

        <nav className="nav-list" aria-label="Secciones del prototipo">
          {modules.map((module) => (
            <button
              key={module.key}
              className={module.key === active ? "nav-item active" : "nav-item"}
              type="button"
              onClick={() => setActive(module.key)}
            >
              <span>{module.label}</span>
              <small>Simulado</small>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span>Sin PowerShell</span>
          <span>Sin recursos reales</span>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Easy Deploy v2.2.5.12</p>
            <h2>{activeModule.label}</h2>
          </div>
          <div className="status-pill">Offline prototype</div>
        </header>

        <section className="hero-panel">
          <div>
            <p className="eyebrow">Motor visual en estudio</p>
            <h3>{activeModule.detail}</h3>
            <p>
              Esta pantalla solo mide estructura, aspecto y viabilidad de empaquetado.
              No conecta tareas reales, no lee rutas reales y no ejecuta comandos.
            </p>
          </div>
          <div className="engine-card">
            <span>Motor</span>
            <strong>{info?.engine ?? "Cargando..."}</strong>
            <small>{info?.mode ?? "Modo prototipo"}</small>
          </div>
        </section>

        <section className="dashboard-grid">
          <article className="metric-card">
            <span>Arranque</span>
            <strong>Medición manual</strong>
            <p>Usar `npm run electron:dev` o el EXE empaquetado para comparar tiempos.</p>
          </article>
          <article className="metric-card">
            <span>Offline</span>
            <strong>{info?.offlineReady ? "Preparado" : "Pendiente"}</strong>
            <p>El bundle local no requiere red para abrir la interfaz.</p>
          </article>
          <article className="metric-card">
            <span>Tareas reales</span>
            <strong>{info?.realTasksConnected ? "Conectadas" : "Desconectadas"}</strong>
            <p>Puente Python/PowerShell reservado para una fase posterior.</p>
          </article>
        </section>

        <section className="module-panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">Acciones simuladas</p>
              <h3>Botones de navegación técnica</h3>
            </div>
          </div>
          <div className="action-grid">
            {modules.slice(1).map((module) => (
              <button key={module.key} type="button" onClick={() => setActive(module.key)}>
                <span>{module.label}</span>
                <small>{module.detail}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="console-panel">
          <div className="console-header">
            <span>Consola simulada</span>
            <span>solo lectura</span>
          </div>
          <pre>
            {consoleLines.map((line) => `${line}\n`).join("")}
          </pre>
        </section>
      </main>
    </div>
  );
}

export default App;
