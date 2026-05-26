import React, { useEffect, useState } from 'react';
import { 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  Wifi, 
  Info, 
  Save, 
  Download 
} from 'lucide-react';

interface UpdatesViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  updateData?: Record<string, unknown>;
  appVersion: string;
}

export default function UpdatesView({ onAppendLog, onRunAction, updateData, appVersion }: UpdatesViewProps) {
  const [checking, setChecking] = useState(false);
  const [endpointRoute, setEndpointRoute] = useState(
    'https://www.dropbox.com/scl/fi/p8qbe0fzn17nk7qdah75x/update.json?rlkey=7yb1odpc9aptdrek0mk7iafgk&st=3yg87fc3&dl=1'
  );
  const [remoteVersion, setRemoteVersion] = useState('-');
  const [checkingStatus, setCheckingStatus] = useState('pendiente de comprobación.');
  const [notes, setNotes] = useState('sin notas cargadas.');
  const [sha256, setSha256] = useState('-');
  const [installerUrl, setInstallerUrl] = useState('-');
  const [updateAvailable, setUpdateAvailable] = useState(false);

  useEffect(() => {
    if (!updateData) return;

    const available = updateData.available === true;
    const remote = String(updateData.remote_version || updateData.version || '-');
    const rawNotes = updateData.notes;
    const formattedNotes = Array.isArray(rawNotes)
      ? rawNotes.map(String).join(' | ')
      : String(rawNotes || 'sin notas publicadas.');

    setRemoteVersion(remote);
    setUpdateAvailable(available);
    setNotes(formattedNotes);
    setSha256(String(updateData.sha256 || '-'));
    setInstallerUrl(String(updateData.installer_url || updateData.url || '-'));
    setCheckingStatus(
      available
        ? `hay una actualización disponible: ${remote}.`
        : 'Easy Deploy está actualizado.'
    );
    setChecking(false);
  }, [updateData]);

  const handleCheckUpdates = () => {
    setChecking(true);
    setCheckingStatus('conectando con el servidor de actualizaciones...');
    onAppendLog('UPDATES', 'info', `Iniciando consulta de actualización remota al servidor: ${endpointRoute}`);

    onRunAction('updates.check', { url: endpointRoute, stayOnPage: true })
      .then(() => {
        setCheckingStatus('consulta enviada al backend Python. Esperando resultado...');
      })
      .catch((error) => {
        setCheckingStatus('error al consultar actualizaciones.');
        onAppendLog('UPDATES', 'error', String(error));
      })
      .finally(() => setChecking(false));
  };

  const handleSaveRoute = () => {
    onRunAction('updates.save_endpoint', { url: endpointRoute, stayOnPage: true });
    onAppendLog('UPDATES', 'success', `Ruta del actualizador reconfigurada: "${endpointRoute}" guardada de forma segura.`);
  };

  const handleDownloadInstaller = () => {
    if (!updateAvailable || installerUrl === '-') return;
    setCheckingStatus('descargando instalador de actualización...');
    onRunAction('updates.download', {
      url: installerUrl,
      version: remoteVersion,
      sha256: sha256 === '-' ? '' : sha256,
      stayOnPage: true,
    });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div 
        className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-xl border"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
          color: 'var(--theme-text-primary)'
        }}
      >
        <div>
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>NÚCLEO DE MANTENIMIENTO & LICENCIAS</span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Actualizaciones y Activación del Sistema</h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Supervise parches acumulativos, KBs de seguridad para sistemas operativos MS y administre el registro de su clave de producto</p>
        </div>
      </div>

      {/* Actualizar Aplicación Form Panel (Exactly like the photo layout) */}
      <div 
        className="border rounded-2xl p-6 space-y-5"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)'
        }}
      >
        {/* Header inside Panel */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            {/* Custom rounded logo with "?" text inside */}
            <div 
              className="w-12 h-12 rounded-xl flex items-center justify-center font-mono text-base font-black border tracking-tighter"
              style={{ 
                backgroundColor: 'var(--theme-bg-well)', 
                borderColor: 'var(--theme-accent-primary)',
                color: 'var(--theme-accent-primary)' 
              }}
            >
              ?
            </div>
            <div>
              <h3 className="text-sm font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>
                Actualizar Aplicación
              </h3>
              <p className="text-[10px] font-mono leading-none" style={{ color: 'var(--theme-text-secondary)' }}>
                actualizador automático
              </p>
            </div>
          </div>

          <button
            onClick={handleCheckUpdates}
            disabled={checking}
            className="px-5 py-2 hover:opacity-95 text-xs font-bold rounded cursor-pointer text-white flex items-center gap-1.5 disabled:opacity-50 transition-all font-sans"
            style={{ backgroundColor: 'var(--theme-accent-primary)' }}
          >
            {checking && <RefreshCw size={12} className="animate-spin" />}
            <span>Comprobar</span>
          </button>
        </div>

        {/* Warning/Alert box (Exact text from screenshot) */}
        <div 
          className="p-4 rounded-xl border text-xs flex gap-2.5 leading-relaxed"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)',
            color: 'var(--theme-text-primary)'
          }}
        >
          <div className="shrink-0 mt-0.5">
            <span 
              className="w-5 h-5 rounded-full flex items-center justify-center font-mono text-[11px] font-bold border"
              style={{ borderColor: 'var(--theme-accent-primary)', color: 'var(--theme-accent-primary)' }}
            >
              i
            </span>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--theme-text-secondary)' }}>
            Las actualizaciones del programa pueden incorporar mejoras de estabilidad, seguridad, rendimiento y nuevas funciones. Cuando haya una nueva versión se descargará el instalador, cerrará la aplicación para aplicarla y conservará los datos locales durante el proceso.
          </p>
        </div>

        {/* Route endpoint block */}
        <div className="space-y-2">
          <label 
            className="text-[9px] font-black tracking-widest uppercase font-mono block" 
            style={{ color: 'var(--theme-text-primary)' }}
          >
            RUTA DEL ENDPOINT UPDATE.JSON
          </label>
          
          <div className="flex gap-2.5">
            <input 
              type="text"
              value={endpointRoute}
              onChange={(e) => setEndpointRoute(e.target.value)}
              className="flex-1 px-3.5 py-2 text-xs rounded-lg border font-mono bg-slate-950/45 focus:outline-none focus:border-indigo-500"
              style={{
                borderColor: 'var(--theme-border-well)',
                color: 'var(--theme-text-primary)'
              }}
            />
            <button
              onClick={handleSaveRoute}
              className="px-4 py-2 hover:opacity-90 text-xs font-bold rounded-lg border flex items-center gap-1.5 text-center shrink-0 cursor-pointer"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)',
                color: 'var(--theme-text-primary)'
              }}
            >
              <Save size={13} style={{ color: 'var(--theme-accent-primary)' }} />
              <span>Guardar ruta</span>
            </button>
          </div>
          
          <p className="text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>
            Dirección de consulta del actualizador para comprobar nuevas versiones del programa.
          </p>
        </div>

        {/* Status detail box */}
        <div 
          className="p-4 rounded-xl space-y-2.5 border"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          }}
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
            <div className="flex justify-between sm:justify-start gap-2">
              <span style={{ color: 'var(--theme-text-secondary)' }}>Versión local:</span>
              <span className="font-bold font-sans" style={{ color: 'var(--theme-text-primary)' }}>{appVersion}</span>
            </div>
            <div className="flex justify-between sm:justify-start gap-2">
              <span style={{ color: 'var(--theme-text-secondary)' }}>Versión remota:</span>
              <span className="font-bold font-sans" style={{ color: 'var(--theme-text-primary)' }}>{remoteVersion}</span>
            </div>
            <div className="flex justify-between sm:justify-start gap-2">
              <span style={{ color: 'var(--theme-text-secondary)' }}>URL usada:</span>
              <span className="font-bold font-sans truncate max-w-[420px]" style={{ color: 'var(--theme-text-primary)' }}>{endpointRoute}</span>
            </div>
            <div className="flex justify-between sm:justify-start gap-2">
              <span style={{ color: 'var(--theme-text-secondary)' }}>SHA256:</span>
              <span className="font-bold font-sans truncate max-w-[420px]" style={{ color: 'var(--theme-text-primary)' }}>{sha256}</span>
            </div>
          </div>

          <div className="space-y-1.5 text-xs font-mono pt-1">
            <div className="flex items-start gap-2">
              <span style={{ color: 'var(--theme-text-secondary)' }}>Estado:</span>
              <span className="font-sans font-bold" style={{ color: checking || updateAvailable ? 'var(--theme-accent-primary)' : 'var(--theme-text-primary)' }}>
                {checkingStatus}
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span style={{ color: 'var(--theme-text-secondary)' }}>Notas:</span>
              <span style={{ color: 'var(--theme-text-primary)' }}>{notes}</span>
            </div>
            <div className="flex items-start gap-2">
              <span style={{ color: 'var(--theme-text-secondary)' }}>Instalador:</span>
              <span className="break-all" style={{ color: 'var(--theme-text-primary)' }}>{installerUrl}</span>
            </div>
          </div>

          {updateAvailable && (
            <div className="pt-3">
              <button
                onClick={handleDownloadInstaller}
                className="px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 cursor-pointer"
                style={{ backgroundColor: 'var(--theme-accent-primary)', color: '#ffffff' }}
              >
                <Download size={13} />
                <span>Descargar instalador</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
