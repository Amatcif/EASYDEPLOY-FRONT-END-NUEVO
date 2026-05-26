import React, { useEffect, useState } from 'react';
import { 
  Key, 
  Unlock, 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  RefreshCw,
  Clock
} from 'lucide-react';
import { WindowsRegistry } from '../types';

interface ActivationViewProps {
  registry: WindowsRegistry;
  setRegistry: React.Dispatch<React.SetStateAction<WindowsRegistry>>;
  systemDate: Date;
  setSystemDate: React.Dispatch<React.SetStateAction<Date>>;
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

export default function ActivationView({ 
  registry, 
  setRegistry, 
  systemDate, 
  setSystemDate, 
  onAppendLog,
  onRunAction 
}: ActivationViewProps) {
  const [enteredKey, setEnteredKey] = useState('');
  const [keyError, setKeyError] = useState('');
  const [keySuccess, setKeySuccess] = useState(false);

  const formatDateString = (d: Date) => {
    return d.toISOString().split('T')[0];
  };

  useEffect(() => {
    onRunAction('activation.status');
  }, []);

  const handlePassDays = (days: number) => {
    if (registry.Bloqueo_Flag === 1) {
      onAppendLog('SECURITY', 'error', 'Error: El programa se encuentra BLOQUEADO permanentemente por retroceso del reloj o corrupción de licencia.');
      return;
    }

    const nextDate = new Date(systemDate);
    nextDate.setDate(nextDate.getDate() + days);
    setSystemDate(nextDate);

    // Calc elapsed days
    const firstRun = new Date(registry.Fecha_Primera_Ejecucion);
    const diffTime = Math.abs(nextDate.getTime() - firstRun.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    setRegistry(prev => {
      const expD = new Date(prev.Fecha_Expiracion);
      let status = prev.Estado_Licencia;

      if (nextDate > expD) {
        status = 'EXPIRADO';
      }

      const updated = {
        ...prev,
        Fecha_Ultima_Ejecucion: formatDateString(nextDate),
        Dias_Transcurridos: diffDays,
        Estado_Licencia: status
      };

      if (status === 'EXPIRADO' && prev.Estado_Licencia !== 'EXPIRADO') {
        onAppendLog('SECURITY', 'warning', `Aviso de expiración: El periodo de evaluación ha finalizado tras superar el rango programado.`);
      }

      return updated;
    });

    onAppendLog('SECURITY', 'info', `Simulación: Avanzados ${days} días. Fecha de sistema simulada: ${formatDateString(nextDate)}.`);
  };

  const handleActivateLicense = (e: React.FormEvent) => {
    e.preventDefault();
    setKeyError('');
    setKeySuccess(false);

    if (registry.Bloqueo_Flag === 1) {
      setKeyError('No se puede activar: El software está BLOQUEADO por tamper. Rediríjase al administrador para asistencia.');
      return;
    }

    if (registry.Activado_Una_Vez) {
      setKeyError('Límite de seguridad: Esta clave ya fue activada para el equipo host.');
      return;
    }

    onRunAction('activation.activate', { code: enteredKey.trim() })
      .then(() => {
        setKeySuccess(true);
        onAppendLog('SECURITY', 'info', 'Validación enviada al backend de licencia real.');
      })
      .catch((error) => {
        setKeyError('No se pudo validar la clave en el backend real.');
        onAppendLog('SECURITY', 'error', String(error));
      });
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column Left: Integridad de firma y estado */}
        <div 
          className="border p-5 rounded-2xl relative overflow-hidden flex flex-col justify-between"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <div>
            <div className="flex items-center justify-between border-b pb-3.5 mb-4" style={{ borderColor: 'var(--theme-border-well)' }}>
              <h4 className="text-xs font-black tracking-wider uppercase font-mono" style={{ color: 'var(--theme-text-primary)' }}>Integridad de firma y estado</h4>
              <ShieldCheck size={16} style={{ color: 'var(--theme-accent-primary)' }} />
            </div>

            {/* Large Indicator box */}
            <div 
              className="p-4 rounded-xl text-center space-y-1.5"
              style={{
                backgroundColor: 
                  registry.Estado_Licencia === 'BLOQUEADO' ? 'rgba(239, 68, 68, 0.08)' :
                  registry.Estado_Licencia === 'EXPIRADO' ? 'rgba(249, 115, 22, 0.08)' :
                  registry.Estado_Licencia === 'ACTIVADO' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(99, 102, 241, 0.08)',
                border: '1px solid',
                borderColor:
                  registry.Estado_Licencia === 'BLOQUEADO' ? 'rgba(239, 68, 68, 0.3)' :
                  registry.Estado_Licencia === 'EXPIRADO' ? 'rgba(249, 115, 22, 0.3)' :
                  registry.Estado_Licencia === 'ACTIVADO' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(99, 102, 241, 0.3)'
              }}
            >
              <span className="text-[9px] font-black uppercase font-mono tracking-wider block text-slate-500">ESTADO ACTUAL RECONOCIDO:</span>
              
              <div className="flex items-center justify-center gap-2">
                {registry.Estado_Licencia === 'BLOQUEADO' && (
                  <>
                    <ShieldAlert className="text-rose-500" size={18} />
                    <span className="text-base font-black text-rose-500 font-mono tracking-wider">🔒 BLOQUEADO</span>
                  </>
                )}
                {registry.Estado_Licencia === 'EXPIRADO' && (
                  <>
                    <AlertTriangle className="text-amber-500" size={18} />
                    <span className="text-base font-black text-amber-500 font-mono tracking-wider">⚠️ EVAL EXPIRADA</span>
                  </>
                )}
                {registry.Estado_Licencia === 'ACTIVADO' && (
                  <>
                    <ShieldCheck className="text-emerald-500" size={18} />
                    <span className="text-base font-black text-emerald-500 font-mono tracking-wider">👑 PREMIUM ACTIVADO</span>
                  </>
                )}
                {registry.Estado_Licencia === 'TRIAL' && (
                  <>
                    <RefreshCw className="text-indigo-400 animate-spin" size={14} />
                    <span className="text-base font-black text-indigo-400 font-mono tracking-wider">⚡ EVALUACIÓN (TRIAL)</span>
                  </>
                )}
              </div>

              <p className="text-[10px]" style={{ color: 'var(--theme-text-primary)' }}>
                {registry.Estado_Licencia === 'BLOQUEADO' && 'Bloqueador activado por alteración horaria. El programa requiere restaurar la persistencia.'}
                {registry.Estado_Licencia === 'EXPIRADO' && 'El plazo máximo de 7 días concluyó. Ingrese clave de activación para seguir usándolo.'}
                {registry.Estado_Licencia === 'ACTIVADO' && 'Uso corporativo ilimitado activo. Firma del kernel aprobada.'}
                {registry.Estado_Licencia === 'TRIAL' && `Software operando en modo libre. Expira en ${7 - Math.min(registry.Dias_Transcurridos, 7)} días.`}
              </p>
            </div>
          </div>

          {/* Small details */}
          <div className="space-y-2 mt-6 text-[11px] font-mono leading-relaxed pt-3 border-t" style={{ color: 'var(--theme-text-secondary)', borderColor: 'var(--theme-border-well)' }}>
            <div className="flex justify-between border-b pb-1" style={{ borderColor: 'var(--theme-border-well)' }}>
              <span>Uso registrado:</span>
              <span className="font-bold font-sans" style={{ color: 'var(--theme-text-primary)' }}>{registry.Dias_Transcurridos} / 30 días</span>
            </div>
            <div className="flex justify-between border-b pb-1" style={{ borderColor: 'var(--theme-border-well)' }}>
              <span>Firma digital:</span>
              <span className="font-bold" style={{ color: 'var(--theme-text-primary)' }}>sha256-{registry.Build_Hash.substring(0, 8)}</span>
            </div>
            <div className="flex justify-between">
              <span>Registro de licencia:</span>
              <span className="font-bold" style={{ color: 'var(--theme-text-primary)' }}>{registry.Activado_Una_Vez ? 'Activado Premium' : 'No Activado (Licencia temporal)'}</span>
            </div>
          </div>
        </div>

        {/* Column Right: Activación y evaluación del software */}
        <div 
          className="border p-5 rounded-2xl relative overflow-hidden flex flex-col justify-between"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <div>
            <div className="flex items-center justify-between border-b pb-3.5 mb-4" style={{ borderColor: 'var(--theme-border-well)' }}>
              <h4 className="text-xs font-black tracking-wider uppercase font-mono" style={{ color: 'var(--theme-text-primary)' }}>Formulario de validación</h4>
              <Key size={16} style={{ color: 'var(--theme-accent-primary)' }} />
            </div>

            <p className="text-xs leading-relaxed mb-4" style={{ color: 'var(--theme-text-secondary)' }}>
              Introduzca la clave de licencia provista de forma física o mediante su cuenta para activar las características avanzadas y eliminar el aviso de evaluación.
            </p>

            {/* Actual Activation Key Input Form */}
            <form onSubmit={handleActivateLicense} className="border p-4 rounded-xl space-y-3" style={{ borderColor: 'var(--theme-border-well)' }}>
              <div className="flex items-center justify-between font-mono">
                <h4 className="text-xs font-bold font-sans animate-fade-in" style={{ color: 'var(--theme-text-primary)' }}>Licencia de Software</h4>
                <span className="text-[9px]" style={{ color: 'var(--theme-text-secondary)' }}>ID: {registry.Build_Hash.substring(0, 9)}</span>
              </div>
              
              <div className="flex gap-2">
                <input
                   type="text"
                   value={enteredKey}
                   onChange={(e) => setEnteredKey(e.target.value)}
                   placeholder="ED-LIC-2026-...."
                   disabled={registry.Bloqueo_Flag === 1}
                   className="flex-1 px-3 py-1.5 text-xs rounded border bg-slate-950/40 focus:outline-none focus:border-indigo-500 font-mono"
                   style={{ borderColor: 'var(--theme-border-card)', color: 'var(--theme-text-primary)' }}
                />
                <button
                  type="submit"
                  disabled={registry.Bloqueo_Flag === 1}
                   className="px-4 py-1.5 hover:opacity-90 text-xs font-bold rounded cursor-pointer text-white flex items-center gap-1.5 disabled:opacity-40 shrink-0"
                   style={{ backgroundColor: 'var(--theme-accent-primary)' }}
                >
                  <Unlock size={12} />
                  <span>Activar</span>
                </button>
              </div>

              {keyError && <p className="text-[10px] font-bold text-rose-500 font-mono">⚡ Error: {keyError}</p>}
              {keySuccess && <p className="text-[10px] font-bold text-emerald-500 font-mono">✓ ¡Éxito! Licencia Premium Válida por 30 días.</p>}
            </form>
          </div>

        </div>
      </div>
    </div>
  );
}
