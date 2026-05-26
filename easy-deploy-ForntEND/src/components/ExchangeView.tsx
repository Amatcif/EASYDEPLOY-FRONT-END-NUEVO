import React, { useState } from 'react';
import { Mail, CheckCircle2, Loader2, Play, ArrowRight } from 'lucide-react';
import { realActionId } from '../services/actionMap';
import type { ActiveTab } from '../types';

interface ExchangeViewProps {
  onAppendLogs: (logs: string[]) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  onSetTab: (tab: ActiveTab) => void;
}

export default function ExchangeView({ onAppendLogs, onRunAction, onSetTab }: ExchangeViewProps) {
  const [activeTask, setActiveTask] = useState<string | null>(null);
  const [stepsState, setStepsState] = useState<Record<string, 'pending' | 'completed'>>({
    exchange_prereqs: 'pending',
    exchange_prepare_ad: 'pending',
    exchange_install: 'pending',
    exchange_users: 'pending',
    exchange_recover: 'pending'
  });

  const cards = [
    {
      id: 'exchange_prereqs',
      code: 'PRE',
      title: 'Prerrequisitos Exchange',
      desc: 'Instala roles, características y prerrequisitos locales antes de ejecutar Setup.',
      borderColorClass: 'border-l-[#2563eb]', // Blue
      glowColorClass: 'shadow-[#2563eb]/10 hover:border-[#2563eb]/45',
      badgeBg: 'bg-[#2563eb]/10 text-[#3b82f6] border border-[#2563eb]/20',
    },
    {
      id: 'exchange_prepare_ad',
      code: 'AD',
      title: 'Prepare Schema',
      desc: 'Comprueba el dominio y ejecuta PrepareSchema, PrepareAD y PrepareAllDomains.',
      borderColorClass: 'border-l-[#10b981]', // Emerald/Teal
      glowColorClass: 'shadow-[#10b981]/10 hover:border-[#10b981]/45',
      badgeBg: 'bg-[#10b981]/10 text-[#10b981] border border-[#10b981]/20',
    },
    {
      id: 'exchange_install',
      code: 'X',
      title: 'Instalar Exchange',
      desc: 'Lanza Setup desde el medio de Exchange.',
      borderColorClass: 'border-l-[#2563eb]', // Blue
      glowColorClass: 'shadow-[#2563eb]/10 hover:border-[#2563eb]/45',
      badgeBg: 'bg-[#2563eb]/10 text-[#3b82f6] border border-[#2563eb]/20',
    },
    {
      id: 'exchange_users',
      code: 'U',
      title: 'Crear usuarios EXC',
      desc: 'Alta rápida de usuarios AD con buzón Exchange y resumen de resultados.',
      borderColorClass: 'border-l-[#8b5cf6]', // Violet/Purple
      glowColorClass: 'shadow-[#8b5cf6]/10 hover:border-[#8b5cf6]/45',
      badgeBg: 'bg-[#8b5cf6]/10 text-[#8b5cf6] border border-[#8b5cf6]/20',
    },
    {
      id: 'exchange_recover',
      code: 'REC',
      title: 'RecoverServer Exchange',
      desc: 'Recupera un servidor Exchange registrado en AD sin borrar objetos del dominio.',
      borderColorClass: 'border-l-[#f97316]', // Orange/Amber
      glowColorClass: 'shadow-[#f97316]/10 hover:border-[#f97316]/45',
      badgeBg: 'bg-[#f97316]/10 text-[#f97316] border border-[#f97316]/20',
    }
  ];

  const handleExecuteTask = (taskId: string, title: string) => {
    if (taskId === 'exchange_users') {
      onSetTab('exchange_users_form');
      return;
    }
    setActiveTask(taskId);
    onAppendLogs([
      `[CLIENT] Iniciando tarea de Exchange: "${title}" ...`,
      `[CLIENT] Enviando acción permitida al backend Python real...`
    ]);

    onRunAction(realActionId(taskId))
      .then(() => setStepsState(prev => ({ ...prev, [taskId]: 'completed' })))
      .catch((error) => onAppendLogs([`[error] No se pudo enviar la acción ${taskId}: ${error}`]))
      .finally(() => setActiveTask(null));
  };

  return (
    <div className="space-y-6">
      {/* Title block with vertical green bar identical to current layout style */}
      <div 
        className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 backdrop-blur-md p-5 rounded-2xl border"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
          color: 'var(--theme-text-primary)'
        }}
      >
        <div className="border-l-4 pl-4 py-1" style={{ borderColor: 'var(--theme-accent-primary)' }}>
          <h1 className="text-xl font-bold font-sans uppercase tracking-tight leading-none mb-1 shadow-sm" style={{ color: 'var(--theme-text-primary)' }}>
            Exchange
          </h1>
          <p className="text-xs font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
            Elige si quieres instalar prerrequisitos o preparar AD/schema desde el medio de Exchange.
          </p>
        </div>
        <div 
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border shrink-0"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          }}
        >
          <Mail size={13} style={{ color: 'var(--theme-accent-primary)' }} className="animate-pulse" />
          <span className="text-[10px] font-mono font-bold" style={{ color: 'var(--theme-text-secondary)' }}>Exchange Server 2019 CU15 Standard</span>
        </div>
      </div>

      {/* Grid: 5 customized cards layout exactly as requested */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cards.map((card) => {
          const isExecuting = activeTask === card.id;
          const isCompleted = stepsState[card.id] === 'completed';
          
          let cardStyle: React.CSSProperties = {
            backgroundColor: isExecuting ? 'var(--theme-bg-well)' : 'var(--theme-bg-card)',
            borderColor: isExecuting ? 'var(--theme-accent-primary)' : 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)',
            borderLeftWidth: '4px'
          };
          
          return (
            <div
              key={card.id}
              onClick={() => {
                if (!isExecuting) {
                  handleExecuteTask(card.id, card.title);
                }
              }}
              style={cardStyle}
              className={`relative border rounded-2xl p-6 cursor-pointer transition-all duration-300 flex flex-col justify-between group min-h-[160px] shadow-sm select-none ${card.borderColorClass} ${
                isExecuting ? 'ring-1 ring-indigo-500/25 animate-pulse' : ''
              }`}
            >
              <div>
                {/* Horizontal marker area */}
                <div className="flex justify-between items-start mb-4">
                  <span 
                    className="text-[11px] font-black font-mono px-2.5 py-0.5 rounded border"
                    style={{
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'var(--theme-border-well)',
                      color: 'var(--theme-accent-primary)'
                    }}
                  >
                    {card.code}
                  </span>
                  
                  {/* Executive action indicator */}
                  <div className="flex items-center gap-1.5 select-none">
                    {isExecuting ? (
                      <span className="text-[10px] font-mono font-bold flex items-center gap-1" style={{ color: 'var(--theme-accent-primary)' }}>
                        <Loader2 size={11} className="animate-spin" style={{ color: 'var(--theme-accent-primary)' }} />
                        Ejecutando...
                      </span>
                    ) : isCompleted ? (
                      <span className="text-[10px] font-mono font-bold text-emerald-500 flex items-center gap-1">
                        <CheckCircle2 size={12} className="stroke-[2.5]" />
                        Instalado
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono flex items-center gap-1" style={{ color: 'var(--theme-text-secondary)' }}>
                        <Play size={10} fill="currentColor" className="opacity-60 group-hover:opacity-100" />
                        Lanzar
                      </span>
                    )}
                  </div>
                </div>

                <h4 className="text-sm font-bold font-sans transition-colors mb-2" style={{ color: 'var(--theme-text-primary)' }}>
                  {card.title}
                </h4>
                <p className="text-[11px] leading-normal font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
                  {card.desc}
                </p>
              </div>

              {/* Action trigger footer strip */}
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider mt-4 select-none" style={{ color: 'var(--theme-accent-primary)' }}>
                <span>{isCompleted ? 'Re-ejecutar proceso' : 'Comenzar instalación desatendida'}</span>
                <ArrowRight size={11} className="group-hover:translate-x-0.5 transition-transform" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
