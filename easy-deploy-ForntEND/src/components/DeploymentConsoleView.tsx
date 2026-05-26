import React from 'react';
import { FolderOpen } from 'lucide-react';
import ConsolePanel from './ConsolePanel';

interface DeploymentConsoleViewProps {
  logs: string[];
  onClearConsole: () => void;
  onExecuteCommand: (cmd: string) => void;
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  backendProgress?: number;
  activeAction?: string | null;
  onOpenLogs?: () => void;
  onCancelTask?: () => void;
}

export default function DeploymentConsoleView({
  logs,
  onClearConsole,
  onExecuteCommand,
  backendProgress = 0,
  activeAction = null,
  onOpenLogs,
  onCancelTask,
}: DeploymentConsoleViewProps) {
  const progress = Math.max(0, Math.min(100, backendProgress));

  return (
    <div className="h-full min-h-0 flex flex-col gap-4">
      <div
        className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-xl border shrink-0"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
          color: 'var(--theme-text-primary)',
        }}
      >
        <div>
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>
            HISTORIAL DE EVENTOS
          </span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>
            Consola de despliegue y tareas
          </h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
            Panel para ver ejecuciones reales del backend Python, prompts, progreso y logs en vivo.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenLogs}
            className="px-3 py-2 rounded-lg border text-xs font-bold flex items-center gap-2 cursor-pointer"
            style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
          >
            <FolderOpen size={14} style={{ color: 'var(--theme-accent-primary)' }} />
            Logs
          </button>
          <span className="text-[10px] font-mono max-w-[260px] truncate" style={{ color: 'var(--theme-text-secondary)' }}>
            {activeAction ? `Ejecutando: ${activeAction}` : 'Sin tarea activa'}
          </span>
          <span className="text-2xl font-black font-mono" style={{ color: 'var(--theme-accent-primary)' }}>
            {progress}%
          </span>
        </div>
      </div>

      <div
        className="border rounded-xl p-4 shrink-0"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-3">
          <div>
            <span className="text-[10px] font-bold font-mono block uppercase" style={{ color: 'var(--theme-text-secondary)' }}>
              FLUJO OPERACIONAL
            </span>
            <span className="text-sm font-semibold" style={{ color: 'var(--theme-text-primary)' }}>
              Progreso de la tarea actual
            </span>
          </div>
        </div>
        <div
          className="w-full h-3 rounded-full overflow-hidden border p-0.5"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)',
          }}
        >
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, backgroundColor: 'var(--theme-accent-primary)' }}
          />
        </div>
      </div>

      <div className="flex-1 min-h-0 w-full">
        <ConsolePanel
          logs={logs}
          onClear={onClearConsole}
          onExecuteCommand={onExecuteCommand}
          title="Consola principal"
          className="w-full h-full min-h-[520px]"
          activeAction={activeAction}
          onCancelTask={onCancelTask}
        />
      </div>
    </div>
  );
}
