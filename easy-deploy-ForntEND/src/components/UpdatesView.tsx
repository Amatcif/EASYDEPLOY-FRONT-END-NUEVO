import React, { useEffect, useMemo, useState } from 'react';
import { RefreshCw, Info, Save, Download, PackageCheck } from 'lucide-react';

interface UpdatesViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  updateData: Record<string, unknown>;
  settingsData?: Record<string, unknown>;
  downloadData: Record<string, unknown>;
  backendProgress: number;
  appVersion: string;
  onQuitApp: () => Promise<unknown>;
}

type DownloadState = 'idle' | 'downloading' | 'downloaded' | 'launching' | 'error';

export default function UpdatesView({
  onAppendLog,
  onRunAction,
  updateData,
  settingsData,
  downloadData,
  backendProgress = 0,
  appVersion,
  onQuitApp,
}: UpdatesViewProps) {
  const [checking, setChecking] = useState(false);
  const [endpointRoute, setEndpointRoute] = useState(
    'https://www.dropbox.com/scl/fi/p8qbe0fzn17nk7qdah75x/update.json?rlkey=7yb1odpc9aptdrek0mk7iafgk&st=na1ikvk4&dl=1'
  );
  const [remoteVersion, setRemoteVersion] = useState('-');
  const [checkingStatus, setCheckingStatus] = useState('pendiente de comprobación.');
  const [notes, setNotes] = useState('sin notas cargadas.');
  const [sha256, setSha256] = useState('');
  const [installerUrl, setInstallerUrl] = useState('');
  const [installerFilename, setInstallerFilename] = useState('');
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [downloadState, setDownloadState] = useState<DownloadState>('idle');
  const [downloadedPath, setDownloadedPath] = useState('');
  const [downloadProgress, setDownloadProgress] = useState(0);

  const visibleProgress = useMemo(() => {
    if (downloadState === 'downloaded' || downloadState === 'launching') return 100;
    if (downloadState === 'downloading') return Math.max(1, Math.min(100, backendProgress || downloadProgress));
    return 0;
  }, [backendProgress, downloadProgress, downloadState]);

  useEffect(() => {
    onRunAction('updates.load_settings', { stayOnPage: true }).catch((error) => {
      onAppendLog('UPDATES', 'warning', `No se pudo cargar la ruta guardada del actualizador: ${String(error)}`);
    });
  }, []);

  useEffect(() => {
    const savedUrl = String(settingsData?.url || '');
    if (savedUrl) setEndpointRoute(savedUrl);
  }, [settingsData]);

  useEffect(() => {
    if (!updateData) return;

    const available = updateData.available === true;
    const remote = String(updateData.remote_version || updateData.version || '-');
    const rawNotes = updateData.notes;
    const formattedNotes = Array.isArray(rawNotes) ?
       rawNotes.map(String).join(' | ')
      : String(rawNotes || 'sin notas publicadas.');

    setRemoteVersion(remote);
    setUpdateAvailable(available);
    setNotes(formattedNotes);
    setSha256(String(updateData.sha256 || ''));
    setInstallerUrl(String(updateData.installer_url || updateData.url || updateData.downloadUrl || updateData.downloadURL || ''));
    setInstallerFilename(String(updateData.filename || ''));
    setCheckingStatus(
      available ?
         `hay una actualización disponible: ${remote}.`
        : 'Easy Deploy está actualizado.'
    );
    setChecking(false);
    if (!available) {
      setDownloadState('idle');
      setDownloadProgress(0);
      setDownloadedPath('');
    }
  }, [updateData]);

  useEffect(() => {
    if (!downloadData || downloadState !== 'downloading') return;
    const path = String(downloadData.path || '');
    if (!path || path === downloadedPath) return;

    setDownloadedPath(path);
    setDownloadState('downloaded');
    setDownloadProgress(100);
    setCheckingStatus('instalador descargado correctamente.');

    const proceed = window.confirm(
      'El instalador de Easy Deploy se ha descargado correctamente.\n\n' +
      'Ahora se cerrará Easy Deploy y se lanzará el instalador para aplicar la actualización.\n' +
      'Cuando el instalador termine, el archivo descargado se eliminará automáticamente.\n\n' +
      '¿Quieres continuar ahora?'
    );

    if (proceed) {
      launchDownloadedInstaller(path);
    }
  }, [downloadData, downloadState, downloadedPath]);

  const handleCheckUpdates = () => {
    setChecking(true);
    setCheckingStatus('conectando con el servidor de actualizaciones...');
    setDownloadState('idle');
    setDownloadProgress(0);
    setDownloadedPath('');
    onAppendLog('UPDATES', 'info', `Iniciando consulta de actualización remota al servidor configurado.`);

    onRunAction('updates.check', { url: endpointRoute, stayOnPage: true })
      .then(() => {
        setCheckingStatus('consulta enviada al backend Python. Esperando resultado...');
      })
      .catch((error) => {
        setCheckingStatus('error al consultar actualizaciones.');
        onAppendLog('UPDATES', 'error', String(error));
        setChecking(false);
      });
  };

  const handleSaveRoute = () => {
    const proceed = window.confirm(
      'Vas a cambiar la ruta del endpoint update.json.\n\n' +
      'Si la URL es incorrecta, Easy Deploy no podrá comprobar actualizaciones.\n\n' +
      '¿Quieres guardar esta nueva ruta?'
    );
    if (!proceed) {
      onAppendLog('UPDATES', 'warning', 'Cambio de ruta de actualizador cancelado por el usuario.');
      return;
    }
    onRunAction('updates.save_endpoint', { url: endpointRoute, stayOnPage: true });
    onAppendLog('UPDATES', 'success', 'Ruta del actualizador guardada de forma segura.');
  };

  const handleDownloadInstaller = () => {
    if (!updateAvailable || !installerUrl) return;
    const proceed = window.confirm(
      `Se descargará el instalador de Easy Deploy ${remoteVersion}.\n\n` +
      'Al terminar la descarga, Easy Deploy te pedirá confirmación para cerrar el programa y lanzar el instalador.\n\n' +
      '¿Quieres iniciar la descarga?'
    );
    if (!proceed) return;

    setDownloadState('downloading');
    setDownloadProgress(1);
    setCheckingStatus('descargando instalador de actualización...');
    onRunAction('updates.download', {
      url: installerUrl,
      version: remoteVersion,
      filename: installerFilename,
      sha256,
      stayOnPage: true,
    }).catch((error) => {
      setDownloadState('error');
      setCheckingStatus('error descargando el instalador.');
      onAppendLog('UPDATES', 'error', String(error));
    });
  };

  const launchDownloadedInstaller = (path = downloadedPath) => {
    if (!path) return;
    setDownloadState('launching');
    setCheckingStatus('lanzando instalador. Easy Deploy se cerrará cuando el backend confirme el arranque...');
    onRunAction('updates.launch_installer', { path, stayOnPage: true })
      .catch((error) => {
        setDownloadState('error');
        setCheckingStatus('no se pudo lanzar el instalador.');
        onAppendLog('UPDATES', 'error', String(error));
      });
  };

  return (
    <div className="space-y-6">
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
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Comprueba nuevas versiones de Easy Deploy, descarga el instalador y aplica la actualización de forma controlada.</p>
        </div>
      </div>

      <div
        className="border rounded-2xl p-6 space-y-5"
        style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center border"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-accent-primary)',
                color: 'var(--theme-accent-primary)'
              }}
            >
              <PackageCheck size={22} />
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
            disabled={checking || downloadState === 'downloading' || downloadState === 'launching'}
            className="px-5 py-2 hover:opacity-95 text-xs font-bold rounded cursor-pointer text-white flex items-center gap-1.5 disabled:opacity-50 transition-all font-sans"
            style={{ backgroundColor: 'var(--theme-accent-primary)' }}
          >
            {checking && <RefreshCw size={12} className="animate-spin" />}
            <span>Comprobar</span>
          </button>
        </div>

        <div
          className="p-4 rounded-xl border text-xs flex gap-2.5 leading-relaxed"
          style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
        >
          <div className="shrink-0 mt-0.5">
            <span className="w-5 h-5 rounded-full flex items-center justify-center border" style={{ borderColor: 'var(--theme-accent-primary)', color: 'var(--theme-accent-primary)' }}>
              <Info size={12} />
            </span>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--theme-text-secondary)' }}>
            Las actualizaciones del programa pueden incorporar mejoras de estabilidad, seguridad, rendimiento y nuevas funciones. Cuando haya una nueva versión se descargará el instalador, se avisará antes de cerrar Easy Deploy y el archivo descargado se eliminará tras terminar la instalación.
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-[9px] font-black tracking-widest uppercase font-mono block" style={{ color: 'var(--theme-text-primary)' }}>
            RUTA DEL ENDPOINT
          </label>
          <div className="flex gap-2.5">
            <input
              type="text"
              value={endpointRoute}
              onChange={(e) => setEndpointRoute(e.target.value)}
              className="flex-1 px-3.5 py-2 text-xs rounded-lg border font-mono bg-slate-950/45 focus:outline-none focus:border-indigo-500"
              style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
            />
            <button
              onClick={handleSaveRoute}
              className="px-4 py-2 hover:opacity-90 text-xs font-bold rounded-lg border flex items-center gap-1.5 text-center shrink-0 cursor-pointer"
              style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
            >
              <Save size={13} style={{ color: 'var(--theme-accent-primary)' }} />
              <span>Guardar ruta</span>
            </button>
          </div>
          <p className="text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>
            Dirección de consulta del actualizador para comprobar nuevas versiones del programa.
          </p>
        </div>

        <div
          className="p-4 rounded-xl space-y-4 border"
          style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}
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
          </div>

          {(updateAvailable || downloadState !== 'idle') && (
            <div className="space-y-2 pt-1">
              <div className="flex justify-between text-[10px] font-mono" style={{ color: 'var(--theme-text-secondary)' }}>
                <span>
                  {downloadState === 'downloading' && 'Descargando instalador...'}
                  {downloadState === 'downloaded' && 'Instalador descargado.'}
                  {downloadState === 'launching' && 'Instalador lanzado. Cerrando Easy Deploy...'}
                  {downloadState === 'error' && 'Error en la actualización.'}
                  {downloadState === 'idle' && 'Preparado para descargar.'}
                </span>
                <span className="font-bold">{visibleProgress}%</span>
              </div>
              <div className="w-full h-2 rounded-full overflow-hidden border" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-well)' }}>
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${visibleProgress}%`, backgroundColor: downloadState === 'error' ? '#ef4444' : 'var(--theme-accent-primary)' }} />
              </div>
            </div>
          )}

          {updateAvailable && downloadState !== 'launching' && (
            <div className="pt-1 flex flex-wrap gap-2">
              <button
                onClick={handleDownloadInstaller}
                disabled={downloadState === 'downloading'}
                className="px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 cursor-pointer disabled:opacity-50"
                style={{ backgroundColor: 'var(--theme-accent-primary)', color: '#ffffff' }}
              >
                <Download size={13} />
                <span>{downloadState === 'downloading' ? 'Descargando...' : 'Descargar instalador'}</span>
              </button>
              {downloadedPath && downloadState === 'downloaded' && (
                <button
                  onClick={() => launchDownloadedInstaller()}
                  className="px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 cursor-pointer border"
                  style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
                >
                  Lanzar instalador
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
