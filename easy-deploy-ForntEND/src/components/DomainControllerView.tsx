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

interface DomainControllerViewProps {
  onAppendLogs: (logs: string[]) => void;
  onClearConsole: () => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

export default function DomainControllerView({ onAppendLogs, onClearConsole, onRunAction }: DomainControllerViewProps) {
  const [activeTask, setActiveTask] = useState<string | null>(null);

  const adActions = [
    {
      id: 'ad_dc1',
      title: 'Promoción DC1 (Nuevo Bosque)',
      category: 'Configuración de Bosque',
      desc: 'Levantar un nuevo bosque de Active Directory asignándole el dominio raíz "easydeploy.local" con DNS seguro.',
      accent: 'indigo'
    },
    {
      id: 'ad_dc2',
      title: 'Promoción DC2 (Adicional)',
      category: 'Alta Disponibilidad',
      desc: 'Sincronizar un controlador adicional replicando SYSVOL, catálogo global y esquemas de Active Directory.',
      accent: 'indigo'
    },
    {
      id: 'ad_join',
      title: 'Unir equipo a dominio',
      category: 'Dominio',
      desc: 'Une el equipo al dominio usando las validaciones y prompts del Easy Deploy clásico.',
      accent: 'indigo'
    },
    {
      id: 'ad_gpo',
      title: 'Forzar Políticas GPO',
      category: 'Seguridad',
      desc: 'Actualizar las directivas locales y forzar reglas de complejidad de contraseñas de seguridad de los controladores.',
      accent: 'emerald'
    },
    {
      id: 'ad_users',
      title: 'Creación de Usuarios AD',
      category: 'Aprovisionamiento',
      desc: 'Importar y registrar en lote de forma automatizada las 18 cuentas del personal con OUs y grupos específicos.',
      accent: 'emerald'
    },
    {
      id: 'ad_netfx35',
      title: 'Net Framework 3.5',
      category: 'Prerequisito',
      desc: 'Instala NET-Framework-Core desde la ISO local de recursos configurada en Easy Deploy.',
      accent: 'emerald'
    },
    {
      id: 'ad_repadmin',
      title: 'Repadmin Health Check',
      category: 'Monitoreo de Red',
      desc: 'Analizar vecinos de replicación del bosque para comprobar errores de RPC, SID, o latencias de replicaciones AD DB.',
      accent: 'sky'
    },
    {
      id: 'ad_d2_d4',
      title: 'D2/D4 Autoritative Restore',
      category: 'Recuperación de Desastres',
      desc: 'Modificar BurFlags en el registro de Windows de sysvol para solucionar corrupción de replicación de Archivos (NtFrs).',
      accent: 'rose'
    },
    {
      id: 'system_time_sync',
      title: 'Sincronizar hora',
      category: 'Sistema',
      desc: 'Sincroniza la hora del servidor usando la tarea clásica de Easy Deploy.',
      accent: 'sky'
    },
    {
      id: 'system_kms',
      title: 'KMS',
      category: 'Activación Windows',
      desc: 'Convierte Evaluation cuando aplica y configura activación KMS con confirmación previa.',
      accent: 'rose'
    },
    {
      id: 'system_sql',
      title: 'SQL Server',
      category: 'Servidor',
      desc: 'Instala drivers, SSMS y lanza la ISO de SQL Server desde los recursos offline.',
      accent: 'indigo'
    },
    {
      id: 'system_jchat',
      title: 'JCHAT / Openfire',
      category: 'Colaboración',
      desc: 'Instala Java y Openfire reutilizando los instaladores offline del Easy Deploy clásico.',
      accent: 'emerald'
    },
    {
      id: 'system_jchat_cli',
      title: 'JCHAT CLI',
      category: 'Cliente',
      desc: 'Instala el MSI offline del cliente JCHAT CLI.',
      accent: 'emerald'
    },
    {
      id: 'system_sharepoint_install',
      title: 'SharePoint',
      category: 'Servidor',
      desc: 'Instala prerrequisitos y ejecuta SharePoint desde los recursos configurados.',
      accent: 'sky'
    }
  ];

  const handleExecuteAction = (actionId: string, title: string) => {
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

      {/* Diagnostic tools bar & AD Explorer list */}
      <div 
        className="p-5 rounded-xl border"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
          color: 'var(--theme-text-primary)'
        }}
      >
        <div className="flex justify-between items-center border-b pb-3 mb-4" style={{ borderColor: 'var(--theme-border-well)' }}>
          <div>
            <h3 className="text-xs font-bold font-mono uppercase tracking-widest" style={{ color: 'var(--theme-text-primary)' }}>Sincronización y Directorio</h3>
            <p className="text-[11px]" style={{ color: 'var(--theme-text-secondary)' }}>Metadatos de objetos registrados localmente en este servidor</p>
          </div>
          <span 
            className="border font-mono font-bold text-[10px] px-2.5 py-0.5 rounded"
            style={{
              backgroundColor: 'var(--theme-bg-well)',
              borderColor: 'var(--theme-border-well)',
              color: 'var(--theme-accent-primary)'
            }}
          >
            DB Saludable (NTDS.DIT)
          </span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
          <div className="p-3 rounded-lg border" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}>
            <span className="text-[10px] uppercase font-bold font-mono block mb-0.5" style={{ color: 'var(--theme-text-secondary)' }}>Grupos Globales</span>
            <span className="text-lg font-bold font-mono" style={{ color: 'var(--theme-accent-primary)' }}>14</span>
          </div>
          <div className="p-3 rounded-lg border" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}>
            <span className="text-[10px] uppercase font-bold font-mono block mb-0.5" style={{ color: 'var(--theme-text-secondary)' }}>Unidades Org</span>
            <span className="text-lg font-bold font-mono" style={{ color: '#10b981' }}>6</span>
          </div>
          <div className="p-3 rounded-lg border" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}>
            <span className="text-[10px] uppercase font-bold font-mono block mb-0.5" style={{ color: 'var(--theme-text-secondary)' }}>Cuentas Importadas</span>
            <span className="text-lg font-bold font-mono" style={{ color: 'var(--theme-accent-primary)' }}>18 / 18</span>
          </div>
          <div className="p-3 rounded-lg border" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}>
            <span className="text-[10px] uppercase font-bold font-mono block mb-0.5" style={{ color: 'var(--theme-text-secondary)' }}>Maestro FSMO</span>
            <span className="text-xs font-black font-mono block truncate" style={{ color: 'var(--theme-accent-primary)' }} title="EasyDeploy-DC1">EasyDeploy-DC1</span>
          </div>
        </div>
      </div>
    </div>
  );
}
