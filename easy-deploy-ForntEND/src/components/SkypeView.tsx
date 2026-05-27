import React, { useState } from 'react';
import { MessagesSquare, Play, HelpCircle, CheckCircle2, ShieldAlert, Settings, Info, RefreshCw } from 'lucide-react';
import { realActionId } from '../services/actionMap';

interface SkypeViewProps {
  onAppendLogs: (logs: string[]) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

export default function SkypeView({ onAppendLogs, onRunAction }: SkypeViewProps) {
  const [activeTask, setActiveTask] = useState<string | null>(null);
  const [stepsState, setStepsState] = useState<Record<string, 'pending' | 'completed'>>({
    skype_prereqs: 'pending',
    skype_install: 'pending',
    skype_perms: 'pending',
    skype_dns: 'pending',
  });

  const skypeTasks = [
    {
      id: 'skype_prereqs',
      title: '1. Prerrequisitos Skype Server 2019',
      desc: 'Instalar Media Foundation, activar compresión dinámica/estática en IIS, configurar .NET 4.5.2 y generar Topology Manager.',
      badge: 'Lync Prep Core'
    },
    {
      id: 'skype_install',
      title: '2. Instalar Skype Server Core SFB',
      desc: 'Desplegar base de datos RTC SQL Express local para el catálogo central CMS, solicitar certificados TLS e iniciar Front-End.',
      badge: 'Skype Core Inst'
    },
    {
      id: 'skype_perms',
      title: '3. Asignar Permisos y Habilitar Cuentas',
      desc: 'Otorgar privilegios RTCUniversalAdmins en la OU y habilitar la mensajería SIP para el equipo directivo y usuarios del dominio.',
      badge: 'SIP User Control'
    },
    {
      id: 'skype_dns',
      title: '4. Registrar Punteros DNS SRV',
      desc: 'Configurar registro SRV auto-discover "_sipinternaltls._tcp" puerto 5061 y vincular punteros A para el correcto inicio de sesión.',
      badge: 'DNS Auto-discover'
    }
  ];

  const handleExecuteTask = (taskId: string, title: string) => {
    setActiveTask(taskId);
    onAppendLogs([
      `[CLIENT] Iniciando tarea de Skype for Business: "${title}" ...`,
      `[CLIENT] Enviando acción permitida al backend Python real...`
    ]);

    onRunAction(realActionId(taskId))
      .then(() => setStepsState(prev => ({ ...prev, [taskId]: 'completed' })))
      .catch((error) => onAppendLogs([`[error] No se pudo enviar la acción ${taskId}: ${error}`]))
      .finally(() => setActiveTask(null));
  };

  const skypeServices = [
    { code: 'RTCSRV', name: 'Front-End (Servicio Comunicación Central)', active: stepsState.skype_install === 'completed' },
    { code: 'RTCPX', name: 'Web-Proxy (Servicios IIS y Conferencias web)', active: stepsState.skype_install === 'completed' },
    { code: 'RTCCMP', name: 'Conferencias (Compartición de Escritorio)', active: stepsState.skype_install === 'completed' }
  ];

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
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>INTEGRACIÓN MICROSOFT</span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Gestión de Skype for Business Server</h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Implementación automatizada de telefonía VoIP, conferencia segura, aprovisionamiento de cuentas SIP y resolución DNS</p>
        </div>
        <div 
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          }}
        >
          <MessagesSquare size={13} style={{ color: 'var(--theme-accent-primary)' }} />
          <span className="text-[10px] font-mono font-bold" style={{ color: 'var(--theme-text-secondary)' }}>Skype for Business Server 2019</span>
        </div>
      </div>

      {/* Grid wrapper */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Step-by-step panel */}
        <div className="lg:col-span-2 space-y-4">
          <h3 
            className="text-xs font-bold font-mono uppercase tracking-widest pb-1 border-b"
            style={{ color: 'var(--theme-text-secondary)', borderColor: 'var(--theme-border-well)' }}
          >
            PASOS DE DESPLIEGUE AUTOMÁTICO
          </h3>

          <div className="space-y-3">
            {skypeTasks.map((task) => {
              const isExecuting = activeTask === task.id;
              const isCompleted = stepsState[task.id] === 'completed';
              
              let cardStyle: React.CSSProperties = {
                backgroundColor: 'var(--theme-bg-card)',
                borderColor: 'var(--theme-border-card)',
                color: 'var(--theme-text-primary)'
              };
              let titleColor = 'var(--theme-text-primary)';
              
              if (isCompleted) {
                cardStyle = {
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'rgba(16, 185, 129, 0.25)',
                  opacity: 0.9
                };
                titleColor = 'var(--theme-text-secondary)';
              } else if (isExecuting) {
                cardStyle = {
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-accent-primary)',
                };
              }

              return (
                <div 
                  key={task.id} 
                  style={cardStyle}
                  className={`p-4 rounded-xl border transition-all flex flex-col md:flex-row justify-between md:items-center gap-4`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span 
                        className="text-[9px] font-semibold px-2 py-0.5 rounded font-mono border"
                        style={isCompleted ? {
                          backgroundColor: 'rgba(6, 78, 59, 0.2)',
                          borderColor: '#064e3b',
                          color: '#10b981'
                        } : {
                          backgroundColor: 'var(--theme-bg-well)',
                          borderColor: 'var(--theme-border-well)',
                          color: 'var(--theme-text-secondary)'
                        }}
                      >
                        {task.badge}
                      </span>
                      {isCompleted && (
                        <span className="text-emerald-500 font-mono text-[10px] font-bold flex items-center gap-1">
                          <CheckCircle2 size={11} className="stroke-[2.5]" />
                          <span>Hecho</span>
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-bold tracking-wide font-sans" style={{ color: titleColor }}>
                      {task.title}
                    </h4>
                    <p className="text-xs leading-relaxed mt-1" style={{ color: 'var(--theme-text-secondary)' }}>{task.desc}</p>
                  </div>

                  <div className="shrink-0 flex items-center">
                    <button
                      onClick={() => handleExecuteTask(task.id, task.title)}
                      disabled={activeTask !== null}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer`}
                      style={isCompleted ? {
                        backgroundColor: 'var(--theme-bg-well)',
                        borderColor: '#064e3b',
                        color: '#10b981'
                      } : activeTask !== null ? {
                        backgroundColor: 'var(--theme-bg-well)',
                        borderColor: 'var(--theme-border-well)',
                        color: 'var(--theme-text-secondary)',
                        opacity: 0.5,
                        cursor: 'not-allowed'
                      } : {
                        backgroundColor: 'var(--theme-accent-primary)',
                        color: '#ffffff'
                      }}
                    >
                      {activeTask === task.id ? (
                        <>
                          <RefreshCw size={12} className="animate-spin text-white" />
                          <span>Ejecutando...</span>
                        </>
                      ) : (
                        <>
                          <Play size={10} fill="currentColor" />
                          <span>{isCompleted ? 'Re-ejecutar' : 'Iniciar'}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Lync status side controls */}
        <div className="space-y-4">
          <h3 
            className="text-xs font-bold font-mono uppercase tracking-widest pb-1 border-b"
            style={{ color: 'var(--theme-text-secondary)', borderColor: 'var(--theme-border-well)' }}
          >
            SERVICIOS DE TELEFONÍA / SIP
          </h3>

          <div 
            className="p-4 rounded-xl border space-y-4"
            style={{
              backgroundColor: 'var(--theme-bg-card)',
              borderColor: 'var(--theme-border-card)',
              color: 'var(--theme-text-primary)'
            }}
          >
            {/* Port info */}
            <div 
              className="p-3 rounded-lg border space-y-1"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)'
              }}
            >
              <span className="text-[10px] font-bold block font-mono" style={{ color: 'var(--theme-text-secondary)' }}>PUERTOS VOIP CLAVE:</span>
              <div className="flex justify-between text-xs font-mono" style={{ color: 'var(--theme-text-primary)' }}>
                <span>SIP Signaling Secure:</span>
                <span style={{ color: 'var(--theme-accent-primary)' }}>5061 (TLS)</span>
              </div>
              <div className="flex justify-between text-xs font-mono" style={{ color: 'var(--theme-text-primary)' }}>
                <span>Skype AV Audio:</span>
                <span style={{ color: 'var(--theme-accent-primary)' }}>3478-4380 (UDP)</span>
              </div>
            </div>

            {/* Services checklist */}
            <div className="space-y-2.5">
              <span className="text-[10px] font-bold font-mono block" style={{ color: 'var(--theme-text-secondary)' }}>MÓDULOS DE SKYPE:</span>
              {skypeServices.map((srv) => (
                <div 
                  key={srv.code} 
                  className="p-3 rounded border flex justify-between items-center text-[11px]"
                  style={{
                    backgroundColor: 'var(--theme-bg-well)',
                    borderColor: 'var(--theme-border-well)'
                  }}
                >
                  <div className="truncate">
                    <span className="font-mono font-bold mr-1.5" style={{ color: 'var(--theme-accent-primary)' }}>[{srv.code}]</span>
                    <span className="font-sans" style={{ color: 'var(--theme-text-primary)' }}>{srv.name.split(' (')[0]}</span>
                  </div>
                  <div className="flex items-center gap-1 shrink-0 font-mono">
                    <span className={`w-1.5 h-1.5 rounded-full ${srv.active ? 'bg-emerald-400 animate-pulse' : 'bg-slate-700'}`} />
                    <span className={`text-[10px] font-bold ${srv.active ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {srv.active ? 'ON' : 'OFF'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Note helper box */}
            <div 
              className="border p-3 rounded-lg flex gap-2"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)'
              }}
            >
              <Info size={14} style={{ color: 'var(--theme-accent-primary)' }} className="shrink-0 mt-0.5" />
              <p className="text-[10px] leading-normal" style={{ color: 'var(--theme-text-secondary)' }}>
                Skype for Business necesita que el dominio de active directory use resoluciones locales y que las direcciones MAC estén reservadas para evitar conflictos de topología.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
