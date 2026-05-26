import React, { useState } from 'react';
import { Play, ServerCog } from 'lucide-react';

export interface ServiceAction {
  id: string;
  title: string;
  desc: string;
  badge?: string;
  action: string;
}

interface ServiceActionViewProps {
  eyebrow: string;
  title: string;
  subtitle: string;
  actions: ServiceAction[];
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

export default function ServiceActionView({ eyebrow, title, subtitle, actions, onAppendLog, onRunAction }: ServiceActionViewProps) {
  const [activeAction, setActiveAction] = useState<string | null>(null);

  const run = (item: ServiceAction) => {
    setActiveAction(item.id);
    onAppendLog('SYSTEM', 'info', `Ejecutando ${item.title}.`);
    onRunAction(item.action)
      .catch((error) => onAppendLog('SYSTEM', 'error', `No se pudo ejecutar ${item.title}: ${String(error)}`))
      .finally(() => setActiveAction(null));
  };

  return (
    <div className="space-y-6">
      <div
        className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-xl border"
        style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)', color: 'var(--theme-text-primary)' }}
      >
        <div>
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>{eyebrow}</span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>{title}</h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>{subtitle}</p>
        </div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono text-[10px] font-bold" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}>
          <ServerCog size={13} style={{ color: 'var(--theme-accent-primary)' }} />
          <span>Backend Python real</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {actions.map((item) => {
          const active = activeAction === item.id;
          return (
            <div
              key={item.id}
              className="p-5 rounded-xl border flex flex-col justify-between min-h-[160px] transition-all hover:-translate-y-0.5"
              style={{ backgroundColor: active ? 'var(--theme-bg-well)' : 'var(--theme-bg-card)', borderColor: active ? 'var(--theme-accent-primary)' : 'var(--theme-border-card)' }}
            >
              <div>
                <span className="text-[9px] font-bold font-mono px-2 py-0.5 rounded uppercase border" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-accent-primary)' }}>
                  {item.badge || 'ACCIÓN'}
                </span>
                <h3 className="text-sm font-bold mt-3 mb-1.5" style={{ color: 'var(--theme-text-primary)' }}>{item.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--theme-text-secondary)' }}>{item.desc}</p>
              </div>
              <div className="border-t pt-3 mt-4 flex justify-end" style={{ borderColor: 'var(--theme-border-well)' }}>
                <button
                  onClick={() => run(item)}
                  disabled={activeAction !== null}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                  style={{ backgroundColor: 'var(--theme-accent-primary)', color: '#fff' }}
                >
                  <Play size={11} fill="currentColor" />
                  <span>{active ? 'Ejecutando...' : 'Ejecutar'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
