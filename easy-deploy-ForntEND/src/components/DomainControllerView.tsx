import React, { useState } from 'react';
import { 
  Users, 
  ShieldAlert, 
  Activity, 
  RefreshCw, 
  Settings, 
  FileCode, 
  Play, 
  Database, 
  Lock,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { realActionId } from '../services/actionMap';
import type { ActiveTab } from '../types';

interface DomainControllerViewProps {
  onAppendLogs: (logs: string[]) => void;
  onClearConsole: () => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  onSetTab: (tab: ActiveTab) => void;
}

export default function DomainControllerView({ onAppendLogs, onClearConsole, onRunAction, onSetTab }: DomainControllerViewProps) {
  const [activeTask, setActiveTask] = useState<string | null>(null);

  const adActions = [
    {
      id: 'ad_dc1',
      title: 'Promoción DC1 (Nuevo Bosque)',
      category: 'Configuración de Bosque',
      desc: 'Levanta un nuevo bosque de Active Directory con DNS y validaciones internas.',
      accent: 'indigo'
    },
    {
      id: 'ad_dc2',
      title: 'Promoción DC2 (Adicional)',
      category: 'Alta Disponibilidad',
      desc: 'Promociona un controlador adicional y replica SYSVOL, catálogo global y esquema de Active Directory.',
      accent: 'indigo'
    },
    {
      id: 'ad_join',
      title: 'Unir equipo a dominio',
      category: 'Dominio',
      desc: 'Une el equipo al dominio usando las preguntas y validaciones internas.',
      accent: 'indigo'
    },
    {
      id: 'ad_users',
      title: 'Creación de Usuarios AD',
      category: 'Aprovisionamiento',
      desc: 'Abre el formulario completo de usuarios AD y envía los datos al motor interno.',
      accent: 'emerald'
    },
    {
      id: 'ad_repadmin',
      title: 'Repadmin Health Check',
      category: 'Replicación',
      desc: 'Analiza la replicación del bosque con Repadmin y muestra la salida real en consola.',
      accent: 'sky'
    },
    {
      id: 'ad_d2_d4',
      title: 'D2/D4 Autoritative Restore',
      category: 'Recuperación',
      desc: 'Abre el asistente D2/D4 para recuperación SYSVOL/DFSR con confirmación.',
      accent: 'rose'
    }
  ];

  const handleExecuteAction = (actionId: string, title: string) => {
    if (actionId === 'ad_users') {
      onSetTab('ad_users_form');
      return;
    }
    if (actionId === 'ad_d2_d4') {
      onSetTab('d2d4_form');
      return;
    }
    setActiveTask(actionId);
    onAppendLogs([
      `[CLIENT] Ejecutando utilidad de Active Directory: "${title}" ...`,
      `[CLIENT] Enviando acción permitida al backend Python real...`
    ]);

    onRunAction(realActionId(actionId))
      .catch((error) => onAppendLogs([`[error] No se pudo enviar la acción ${actionId}: ${error}`]))
      .finally(() => setActiveTask(null));
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
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>INTEGRACIÓN MICROSOFT</span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Active Directory (Controlador de Dominio)</h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Automatiza la promoción de bosques, carga masiva de objetos AD, auditoría de réplicas y políticas sysvol</p>
        </div>
        <div 
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)',
          }}
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-mono font-bold" style={{ color: 'var(--theme-text-secondary)' }}>Esquema: LDAP v3 Standard</span>
        </div>
      </div>

      {/* Warning Card */}
      <div 
        className="border p-4 rounded-xl flex items-start gap-4"
        style={{
          backgroundColor: 'rgba(217, 119, 6, 0.08)',
          borderColor: 'rgba(217, 119, 6, 0.35)'
        }}
      >
        <ShieldAlert className="text-amber-500 shrink-0 mt-0.5" size={18} />
        <div>
          <h4 className="text-xs font-bold font-sans text-amber-500">Advertencia de Reemplazo de Credenciales y Rutas</h4>
          <p className="text-xs leading-relaxed mt-1" style={{ color: 'var(--theme-text-secondary)' }}>
            La promoción de controladores de dominio reconfigurará la puerta de enlace DNS local de este servidor a <code className="px-1 py-0.5 rounded text-[11px] text-amber-500 font-mono" style={{ backgroundColor: 'var(--theme-bg-well)', border: '1px solid var(--theme-border-well)' }}>127.0.0.1</code> de manera automática. El usuario administrador local pasará a ser Administrador del Dominio. Realice siempre un diagnóstico previo.
          </p>
        </div>
      </div>

      {/* Actions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {adActions.map((act) => {
          const isThisActive = activeTask === act.id;
          
          let borderHoverStyle: React.CSSProperties = {
            borderColor: 'var(--theme-border-card)',
          };
          let cardStyle: React.CSSProperties = {
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)'
          };
          let catBgClass = '';
          let catStyle: React.CSSProperties = {
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          };
          
          if (act.accent === 'indigo') {
            catStyle.color = 'var(--theme-accent-primary)';
          } else if (act.accent === 'emerald') {
            catStyle.color = '#10b981';
          } else if (act.accent === 'sky') {
            catStyle.color = '#0ea5e9';
          } else if (act.accent === 'rose') {
            catStyle.color = '#f43f5e';
          }

          if (isThisActive) {
            cardStyle = {
              backgroundColor: 'var(--theme-bg-well)',
              borderColor: 'var(--theme-accent-primary)',
              color: 'var(--theme-text-primary)'
            };
          }

          return (
            <div 
              key={act.id} 
              style={cardStyle}
              className={`p-4.5 rounded-xl border flex flex-col justify-between transition-all duration-200 hover:border-indigo-500/50`}
            >
              <div>
                <div className="flex justify-between items-start mb-2">
                  <span 
                    className="text-[9px] font-bold font-mono px-2 py-0.5 rounded-full uppercase border"
                    style={catStyle}
                  >
                    {act.category}
                  </span>
                  {isThisActive && (
                    <span className="flex h-2 w-2 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-bold mb-1.5 font-sans tracking-wide" style={{ color: 'var(--theme-text-primary)' }}>{act.title}</h3>
                <p className="text-xs leading-normal mb-4" style={{ color: 'var(--theme-text-secondary)' }}>{act.desc}</p>
              </div>

              <div className="border-t pt-3 flex justify-between items-center mt-auto" style={{ borderColor: 'var(--theme-border-well)' }}>
                <span className="text-[10px] font-mono text-slate-500" style={{ color: 'var(--theme-text-secondary)', opacity: 0.8 }}>PS Executable Module</span>
                <button
                  onClick={() => handleExecuteAction(act.id, act.title)}
                  disabled={activeTask !== null}
                  className={`px-3 py-1 rounded text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer`}
                  style={activeTask !== null ? {
                    backgroundColor: 'var(--theme-bg-well)',
                    color: 'var(--theme-text-secondary)',
                    borderColor: 'var(--theme-border-well)',
                    cursor: 'not-allowed',
                    opacity: 0.6
                  } : {
                    backgroundColor: 'var(--theme-bg-well)',
                    borderColor: 'var(--theme-border-well)',
                    color: 'var(--theme-accent-primary)'
                  }}
                >
                  {isThisActive ? 'Preparando...' : 'Ejecutar'}
                  <Play size={10} fill="currentColor" style={{ color: 'var(--theme-accent-primary)' }} />
                </button>
              </div>
            </div>
          );
        })}
      </div>


    </div>
  );
}
