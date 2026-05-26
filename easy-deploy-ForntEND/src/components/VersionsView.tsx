import React from 'react';
import { History, Calendar, Check, ArrowLeft, ArrowUpRight } from 'lucide-react';
import { ActiveTab } from '../types';
import { changelogData } from '../changelogData';

interface VersionsViewProps {
  onSetTab: (tab: ActiveTab) => void;
}

export default function VersionsView({ onSetTab }: VersionsViewProps) {
  return (
    <div className="space-y-6">
      {/* Title block */}
      <div className="border-l-4 pl-4 py-1" style={{ borderColor: 'var(--theme-accent-primary)' }}>
        <h1 className="text-xl font-bold tracking-tight mb-1 font-sans text-slate-100" style={{ color: 'var(--theme-text-primary)' }}>
          Historial de versiones
        </h1>
        <p className="text-xs font-sans text-slate-400" style={{ color: 'var(--theme-text-secondary)' }}>
          Cambios publicados de Easy Deploy, ordenados de más reciente a más antiguo.
        </p>
      </div>

      {/* Changelog List container */}
      <div className="space-y-4">
        {changelogData.map((item, index) => (
          <div 
            key={item.version} 
            className="border rounded-xl p-5 transition-colors"
            style={{
              backgroundColor: 'var(--theme-bg-card)',
              borderColor: 'var(--theme-border-card)',
              color: 'var(--theme-text-primary)'
            }}
          >
            {/* Header portion */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3 mb-3.5" style={{ borderColor: 'var(--theme-border-well)' }}>
              <div className="flex items-center gap-3">
                <span 
                  className="border text-[11px] font-mono px-2.5 py-0.5 rounded-lg select-none font-bold"
                  style={{
                    backgroundColor: 'var(--theme-bg-well)',
                    borderColor: 'var(--theme-border-well)',
                    color: 'var(--theme-accent-primary)'
                  }}
                >
                  v{item.version}
                </span>

                {index === 0 && (
                  <span className="text-[10px] font-bold text-emerald-500 bg-emerald-950/20 px-2 py-0.5 border border-emerald-900/40 rounded uppercase font-sans animate-pulse">
                    Más reciente
                  </span>
                )}

                <span className="text-[10px] font-sans font-medium text-slate-500" style={{ color: 'var(--theme-text-secondary)', opacity: 0.8 }}>
                  {item.changes.length} cambios
                </span>
              </div>

              <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400" style={{ color: 'var(--theme-text-secondary)' }}>
                <Calendar size={11} className="text-slate-500" style={{ color: 'var(--theme-text-secondary)' }} />
                <span>{item.date}</span>
              </div>
            </div>

            {/* List of actions/changes */}
            <ul className="space-y-2.5 text-[11px] font-sans leading-relaxed text-slate-350" style={{ color: 'var(--theme-text-secondary)' }}>
              {item.changes.map((change, cIdx) => (
                <li key={cIdx} className="flex items-start gap-2">
                  <span className="mt-1 shrink-0 font-bold font-mono text-slate-400" style={{ color: 'var(--theme-accent-primary)' }}>-</span>
                  <span>{change}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Volver button on the bottom left matching the style in the original screen */}
      <div className="pt-2">
        <button
          onClick={() => onSetTab('dashboard')}
          className="px-6 py-2 border font-semibold rounded-lg text-xs tracking-wider transition-all duration-150 cursor-pointer flex items-center gap-2"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-accent-primary)'
          }}
        >
          <ArrowLeft size={13} style={{ color: 'var(--theme-accent-primary)' }} />
          <span>Volver</span>
        </button>
      </div>
    </div>
  );
}
