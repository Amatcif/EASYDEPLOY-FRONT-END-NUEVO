import React, { useState } from 'react';
import { DownloadCloud, Play, CheckCircle2, AlertTriangle, ShieldCheck, Sparkles, HelpCircle } from 'lucide-react';
import { OfflineApp } from '../types';
import { realActionId } from '../services/actionMap';

interface ProgramsViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

export default function ProgramsView({ onAppendLog, onRunAction }: ProgramsViewProps) {
  const [apps, setApps] = useState<OfflineApp[]>([
    { id: 'netfx35', name: 'Net Framework 3.5', version: 'Windows Feature offline', category: 'Prerrequisito', size: 'ISO local', installed: false, status: 'idle', progress: 0 },
    { id: 'firefox', name: 'Mozilla Firefox Standalone', version: '112.0.1 x64', category: 'Navegadores', size: '53.4 MB', installed: false, status: 'idle', progress: 0 },
    { id: 'winrar', name: 'WinRAR Archiver', version: '6.11 Pro x64', category: 'Utilidades', size: '3.2 MB', installed: false, status: 'idle', progress: 0 },
    { id: 'adobe_reader', name: 'Adobe Acrobat Reader DC', version: '22.003 x84', category: 'Ofimática', size: '184 MB', installed: false, status: 'idle', progress: 0 },
    { id: 'office_skype', name: 'Microsoft Office 2021 LTSC + Skype Client', version: 'Full Suite v2108', category: 'Ofimática', size: '3.4 GB', installed: false, status: 'idle', progress: 0 },
  ]);

  const [globalInstalling, setGlobalInstalling] = useState(false);

  const triggerSilentInstall = (appId: string) => {
    const selected = apps.find(app => app.id === appId);
    setApps(prev => prev.map(app => app.id === appId ? { ...app, status: 'preparing', progress: 10 } : app));
    onAppendLog('INSTALLER', 'info', `Enviando instalación real al backend Python: ${selected?.name || appId}`);
    onRunAction(realActionId(appId))
      .then(() => {
        setApps(prev => prev.map(app => app.id === appId ? { ...app, status: 'installing', progress: 45 } : app));
      })
      .catch((error) => {
        onAppendLog('INSTALLER', 'error', `No se pudo enviar la instalación ${appId}: ${error}`);
        setApps(prev => prev.map(app => app.id === appId ? { ...app, status: 'error', progress: 0 } : app));
      })
      .finally(() => {
        setTimeout(() => {
          setApps(prev => prev.map(app => app.id === appId ? { ...app, status: 'idle', progress: 0 } : app));
        }, 1200);
      });
  };

  const handleInstallAll = () => {
    setGlobalInstalling(true);
    onAppendLog('INSTALLER', 'warning', `[!] REQUERIMIENTO GLOBAL: Iniciando Instalar todo el arsenal con ${apps.length} componentes offline.`);
    setApps(prev => prev.map(app => ({ ...app, status: 'preparing', progress: 10 })));

    onRunAction('programs.install_all')
      .then(() => {
        setApps(prev => prev.map(app => ({ ...app, status: 'installing', progress: 45 })));
      })
      .catch((error) => {
        onAppendLog('INSTALLER', 'error', `No se pudo iniciar Instalar todo el arsenal: ${String(error)}`);
        setApps(prev => prev.map(app => ({ ...app, status: 'error', progress: 0 })));
      })
      .finally(() => {
        setTimeout(() => {
          setApps(prev => prev.map(app => ({ ...app, status: 'idle', progress: 0 })));
          setGlobalInstalling(false);
        }, 1500);
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
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>LOGÍSTICA OFFLINE</span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Instaladores Corporativos Fuera de Línea</h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Panel de empaquetados e instalación desatendida mediante interruptores de línea de comando directos SILENT /S /qn</p>
        </div>
        <button
          onClick={handleInstallAll}
          disabled={globalInstalling}
          className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 cursor-pointer transition-all`}
          style={globalInstalling ? {
            backgroundColor: 'var(--theme-bg-well)',
            color: 'var(--theme-text-secondary)',
            borderColor: 'var(--theme-border-well)',
            cursor: 'not-allowed',
            opacity: 0.6
          } : {
            backgroundColor: 'var(--theme-accent-primary)',
            color: '#ffffff'
          }}
        >
          <Play size={13} fill="currentColor" />
          <span>Instalar Todo el Arsenal</span>
        </button>
      </div>

      {/* Disconnected Notice Card */}
      <div 
        className="border p-4 rounded-xl flex items-start gap-4"
        style={{
          backgroundColor: 'var(--theme-bg-well)',
          borderColor: 'var(--theme-border-well)'
        }}
      >
        <AlertTriangle className="text-indigo-400 shrink-0 mt-0.5" size={18} style={{ color: 'var(--theme-accent-primary)' }} />
        <div>
          <h4 className="text-xs font-bold font-sans uppercase tracking-wide" style={{ color: 'var(--theme-text-primary)' }}>AVISO: DESPLIEGUE MASIVO SIN INTERNET</h4>
          <p className="text-xs leading-relaxed mt-1" style={{ color: 'var(--theme-text-secondary)' }}>
            Todos los componentes en esta pantalla están alojadas físicamente en la carpeta local <code className="px-1 py-0.5 rounded text-[11px] font-mono" style={{ backgroundColor: 'var(--theme-bg-well)', border: '1px solid var(--theme-border-well)', color: 'var(--theme-accent-primary)' }}>E:\Deploy\Installers\</code>. La estación de trabajo de destino no requiere conexión física a internet WAN ni configuración proxy.
          </p>
        </div>
      </div>

      {/* Grid containing apps */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {apps.map((app) => {
          const isPending = app.status === 'idle';
          const isPrep = app.status === 'preparing';
          const isInstalling = app.status === 'installing';
          const isCompleted = app.status === 'completed';

          let progressStyle: React.CSSProperties = {
            backgroundColor: 'var(--theme-accent-primary)'
          };
          if (isPrep) progressStyle = { backgroundColor: '#f59e0b' };
          if (isCompleted) progressStyle = { backgroundColor: '#10b981' };

          return (
            <div 
              key={app.id} 
              className="rounded-xl p-4 flex flex-col justify-between border transition-all"
              style={{
                backgroundColor: 'var(--theme-bg-card)',
                borderColor: 'var(--theme-border-card)',
                color: 'var(--theme-text-primary)'
              }}
            >
              <div>
                <div className="flex justify-between items-start mb-2">
                  <span 
                    className="text-[9px] font-bold font-mono px-2 py-0.5 rounded uppercase border"
                    style={{
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'var(--theme-border-well)',
                      color: 'var(--theme-accent-primary)'
                    }}
                  >
                    {app.category}
                  </span>
                  <span className="text-[10px] font-mono font-medium" style={{ color: 'var(--theme-text-secondary)' }}>{app.size}</span>
                </div>
                <h3 className="text-sm font-bold line-clamp-1 font-sans" style={{ color: 'var(--theme-text-primary)' }}>{app.name}</h3>
                <p className="text-[11px] font-mono mt-0.5" style={{ color: 'var(--theme-text-secondary)' }}>Versión: {app.version}</p>
              </div>

              {/* Progress and controls section */}
              <div className="mt-4 pt-3 border-t" style={{ borderColor: 'var(--theme-border-well)' }}>
                {app.progress > 0 && (
                  <div className="mb-3 space-y-1">
                    <div className="flex justify-between text-[10px] font-mono" style={{ color: 'var(--theme-text-secondary)' }}>
                      <span>{isCompleted ? 'Instalado con éxito' : isPrep ? 'Preparando...' : 'Instalación Silenciosa...' }</span>
                      <span className="font-bold">{app.progress}%</span>
                    </div>
                    <div className="w-full h-1 rounded-full overflow-hidden border" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}>
                      <div 
                        className={`h-full transition-all duration-300`} 
                        style={{ width: `${app.progress}%`, ...progressStyle }}
                      />
                    </div>
                  </div>
                )}

                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-mono text-slate-500" style={{ color: 'var(--theme-text-secondary)', opacity: 0.8 }}>MOD: Standalone</span>
                  <button
                    onClick={() => triggerSilentInstall(app.id)}
                    disabled={app.status !== 'idle' && app.status !== 'completed'}
                    className={`px-3 py-1 bg-slate-950 hover:bg-slate-850 rounded border border-slate-800 text-[11px] font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                      isCompleted 
                        ? 'text-emerald-400 border-emerald-950 hover:bg-slate-900' 
                        : 'text-indigo-400'
                    }`}
                    style={isCompleted ? {
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'rgba(16, 185, 129, 0.4)',
                      color: '#10b981'
                    } : (app.status !== 'idle' && app.status !== 'completed') ? {
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'var(--theme-border-well)',
                      color: 'var(--theme-text-secondary)',
                      opacity: 0.5,
                      cursor: 'not-allowed'
                    } : {
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'var(--theme-border-well)',
                      color: 'var(--theme-accent-primary)'
                    }}
                  >
                    {isCompleted ? (
                      <>
                        <CheckCircle2 size={11} className="stroke-[2.5]" />
                        <span>Re-instalar</span>
                      </>
                    ) : isInstalling || isPrep ? (
                      <span>Corriendo...</span>
                    ) : (
                      <>
                        <DownloadCloud size={11} />
                        <span>Instalar</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
