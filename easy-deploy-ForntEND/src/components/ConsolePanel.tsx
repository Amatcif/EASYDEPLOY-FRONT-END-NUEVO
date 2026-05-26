import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Copy, Trash2, Play, Ban } from 'lucide-react';

interface ConsolePanelProps {
  logs: string[];
  onClear: () => void;
  onExecuteCommand: (cmd: string) => void;
  title?: string;
  className?: string;
  activeAction?: string | null;
  onCancelTask?: () => void;
  inputEnabled?: boolean;
  inputPlaceholder?: string;
  inputSensitive?: boolean;
}

export default function ConsolePanel({ 
  logs, 
  onClear, 
  onExecuteCommand, 
  title = 'Consola de Despliegue de Sistemas',
  className = "h-[320px]",
  activeAction = null,
  onCancelTask,
  inputEnabled = false,
  inputPlaceholder = "Escribe 'help' para ver comandos, o responde a la tarea interactiva...",
  inputSensitive = false,
}: ConsolePanelProps) {
  const [inputVal, setInputVal] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;
    
    const cmd = inputVal.trim();
    setHistory(prev => [cmd, ...prev]);
    setHistoryIdx(-1);
    
    if (onExecuteCommand) {
      onExecuteCommand(cmd);
    }
    setInputVal('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0 && historyIdx < history.length - 1) {
        const nextIdx = historyIdx + 1;
        setHistoryIdx(nextIdx);
        setInputVal(history[nextIdx]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIdx > 0) {
        const nextIdx = historyIdx - 1;
        setHistoryIdx(nextIdx);
        setInputVal(history[nextIdx]);
      } else if (historyIdx === 0) {
        setHistoryIdx(-1);
        setInputVal('');
      }
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    // Visual cue alert would work but avoiding alert, we can just show custom feedback
  };

  return (
    <div className={`bg-slate-950 rounded-xl border border-slate-800 shadow-2xl overflow-hidden flex flex-col font-mono text-sm leading-relaxed ${className}`}>
      {/* Header bar */}
      <div className="bg-slate-900 px-4 py-2.5 border-b border-slate-800 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-emerald-500 animate-pulse" />
          <span className="font-semibold text-xs text-slate-200 tracking-wider uppercase">{title}</span>
          <span className="bg-emerald-950 border border-emerald-800 text-[10px] text-emerald-400 font-medium px-2 py-0.5 rounded-full flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
            LIVE
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copyToClipboard}
            type="button"
            className="p-1 px-2.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors flex items-center gap-1.5 text-xs font-mono border border-slate-800 hover:border-slate-700"
            title="Copiar logs al portapapeles"
          >
            <Copy size={13} />
            <span>Copiar</span>
          </button>
          <button
            onClick={onClear}
            type="button"
            className="p-1 px-2.5 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition-colors flex items-center gap-1.5 text-xs font-mono border border-slate-800 hover:border-rose-950"
            title="Limpiar Consola"
          >
            <Trash2 size={13} />
            <span>Limpiar</span>
          </button>
        </div>
      </div>

      {/* Terminal Screen Container */}
      <div className="p-4 overflow-y-auto flex-1 flex flex-col gap-1.5 min-h-0 bg-slate-950/95 scrollbar-thin scrollbar-thumb-slate-800">
        <div className="text-slate-500 text-xs pb-1 border-b border-slate-900 border-dashed">
          --- CONSOLA DE DESPLIEGUE SEGURO REGISTRADA EN PUERTO 3000 ---
        </div>
        
        {logs.length === 0 ? (
          <div className="text-slate-600 italic py-4 flex flex-col items-center justify-center gap-2 flex-1 text-center">
            <Terminal size={32} className="text-slate-800 stroke-1" />
            <p className="text-xs">No hay actividad registrada en la sesión actual</p>
            <p className="text-[11px] text-slate-700">Ejecuta tareas desde los paneles superiores para visualizar logs interactivos en vivo</p>
          </div>
        ) : (
          logs.map((log, idx) => {
            let colorClass = 'text-slate-300';
            if (log.startsWith('[✓]') || log.includes('SUCCESS') || log.includes('éxito') || log.includes('OK') || log.includes('completó correctamente')) {
              colorClass = 'text-emerald-400 font-medium';
            } else if (log.startsWith('[!]') || log.startsWith('⚠️') || log.includes('ADVERTENCIA') || log.includes('WARNING')) {
              colorClass = 'text-amber-400';
            } else if (log.startsWith('[error]') || log.includes('ERROR') || log.includes('falló') || log.includes('failed')) {
              colorClass = 'text-rose-400 font-medium';
            } else if (log.startsWith('⚡') || log.includes('C:\\>') || log.startsWith('PS C:\\')) {
              colorClass = 'text-sky-400 font-semibold';
            } else if (log.startsWith('[i]') || log.startsWith('[+]') || log.startsWith('CN=') || log.startsWith('DC=')) {
              colorClass = 'text-indigo-300';
            }

            return (
              <div key={idx} className={`${colorClass} whitespace-pre-wrap select-all text-xs tracking-wide leading-relaxed`}>
                {log}
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>

      {/* Active Input Line */}
      <form onSubmit={handleSubmit} className="border-t border-slate-800 bg-slate-950 p-2 flex items-center gap-3 shrink-0">
        <span className="text-sky-500 font-bold pl-2 flex items-center gap-1 shrink-0">
          <span>PS</span>
          <span className="text-slate-400 font-mono text-xs">C:\Deploy&gt;</span>
        </span>
        <input
          type={inputSensitive ? 'password' : 'text'}
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={inputEnabled ? inputPlaceholder : "Escribe 'help' para ver comandos, o ensaya comandos personalizados..."}
          className="bg-transparent text-slate-100 flex-1 outline-none font-mono text-xs w-full py-1 caret-emerald-500 placeholder-slate-600 focus:placeholder-slate-500"
          id="terminal-input"
        />
        <div className="flex items-center gap-1.5 pr-2 shrink-0">
          <span className="text-[10px] text-slate-600 hidden md:inline select-none border border-slate-800 px-1.5 py-0.5 rounded uppercase font-sans">
            {inputEnabled ? 'Entrada interactiva' : 'Enter para ejecutar'}
          </span>
          <button
            type="button"
            onClick={onCancelTask}
            disabled={!activeAction}
            className="p-1 px-3 bg-rose-950/40 border border-rose-900/70 rounded text-rose-300 hover:text-rose-100 hover:border-rose-500 text-xs flex items-center gap-1 transition-all disabled:opacity-35 disabled:cursor-not-allowed"
            title={activeAction ? `Cancelar tarea actual: ${activeAction}` : 'No hay una tarea activa que cancelar'}
          >
            <Ban size={11} />
            <span className="font-mono text-[11px]">Cancelar</span>
          </button>
          <button
            type="submit"
            className="p-1 px-3 bg-slate-900 border border-slate-800 rounded text-sky-400 hover:text-sky-300 hover:border-sky-800 text-xs flex items-center gap-1 transition-all"
          >
            <Play size={11} fill="currentColor" />
            <span className="font-mono text-[11px]">RUN</span>
          </button>
        </div>
      </form>
    </div>
  );
}
