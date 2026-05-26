import React, { useState } from 'react';
import { BookOpen, Book, HelpCircle, ArrowRight, Play, Info, CheckCircle, Compass, Terminal } from 'lucide-react';
import { GuideArticle } from '../types';

interface GuidesViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onSetCommandInput: (cmd: string) => void;
  onSetTab: (tab: any) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

export default function GuidesView({ onAppendLog, onSetCommandInput, onSetTab, onRunAction }: GuidesViewProps) {
  const [selectedCat, setSelectedCat] = useState<string>('all');
  
  const articles: GuideArticle[] = [
    {
      id: 'g1',
      title: 'Manual de Promoción de Active Directory',
      category: 'Instalación',
      readTime: '6 min',
      tags: ['AD DS', 'DNS', 'Powershell'],
      content: 'Para instalar un nuevo bosque de Active Directory de forma masiva desatendida, utilice la directiva de PowerShell "Install-ADDSForest" con flags automáticas. Tenga en cuenta apagar interfaces IPv6 secundarias si causan errores de DNS.'
    },
    {
      id: 'g2',
      title: 'Solución de Error de Replicación de Sysvol NtFrs',
      category: 'Resolución de Problemas',
      readTime: '8 min',
      tags: ['SYSVOL', 'D2/D4', 'NtFrs'],
      content: 'El error JRNL_WRAP_ERROR ocurre por rotación extrema de diarios USN. Puede repararlo deteniendo el servicio NtFrs, colocando el BurFlags del registro de Windows en C8 (modo D4 autotitativo de master) e iniciando el servicio nuevamente.'
    },
    {
      id: 'g3',
      title: 'Configuración Extendida de Prerrequisitos de Exchange',
      category: 'Configuración',
      readTime: '10 min',
      tags: ['IIS', 'Exchange', 'Clustering'],
      content: 'Exchange 2019 requiere dependencias estrictas de IIS y .NET 4.8. Asegúrese de instalar el módulo UCMA 4.0 (Unified Communications Managed API) antes de proceder con el comando Setup.exe /Mode:Install /Roles:Mailbox.'
    },
    {
      id: 'g4',
      title: 'Despliegues Offline Silenciosos de Programas Corporativos',
      category: 'Instalación',
      readTime: '5 min',
      tags: ['Firefox', 'Office', 'Adobe'],
      content: 'Para realizar instalaciones masivas fluidas, cada binario cuenta con flags silentes predeterminadas. (ej. Firefox: "/S", Adobe: "/qn /norestart"). Mapee siempre la unidad local E:\\ para evitar latencias de red.'
    },
    {
      id: 'g5',
      title: 'Notas de Despliegue de Skype Core Topology',
      category: 'Notas de Versión',
      readTime: '7 min',
      tags: ['Skype', 'Lync', 'SIP'],
      content: 'Skype requiere resoluciones DNS internas para poder autenticar llamadas SIP. Asegúrese de agregar punteros SRV _sipinternaltls._tcp para evitar errores de conexión recurrente en computadores portátiles.'
    }
  ];

  const filtered = selectedCat === 'all' 
    ? articles 
    : articles.filter(a => a.category === selectedCat);

  const guideActionMap: Record<string, string> = {
    g1: 'guides.open_dc1',
    g2: 'guides.open_d2d4',
    g3: 'guides.open_exchange',
    g4: 'tools.open_resources',
    g5: 'guides.open_skype',
  };

  const handleOpenGuide = (article: GuideArticle) => {
    const action = guideActionMap[article.id];
    if (!action) {
      onAppendLog('GUIDES', 'warning', `No hay PDF asociado a ${article.title}.`);
      return;
    }
    onAppendLog('GUIDES', 'info', `Abriendo guía mediante backend: ${article.title}`);
    onRunAction(action, { title: article.title }).catch((error) => {
      onAppendLog('GUIDES', 'error', `No se pudo abrir la guía: ${String(error)}`);
    });
  };


  const commandHints = [
    { label: 'Forzar gpupdate local', cmd: 'gpupdate /force' },
    { label: 'Mostrar réplicas de AD', cmd: 'repadmin /showrepl' },
    { label: 'Limpieza de temporales', cmd: 'powershell -Command "Clear-RecycleBin -Force; Remove-Item $env:TEMP\\* -Recurse"' },
    { label: 'Prueba ping a DC1', cmd: 'ping easydeploy-dc1.local' },
  ];

  const handleApplyCommand = (cmd: string) => {
    onSetCommandInput(cmd);
    onAppendLog('SYSTEM', 'info', `[!] ASISTENTE: Comando sugerido listo en la barra de control: "${cmd}".`);
    onSetTab('deployment_console');
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
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>CENTRO DE RECURSOS</span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Guías y Documentación de Operaciones</h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Manuales mecánicos paso a paso, procedimientos ante desastres sysvol, y flujos de empaquetado silent</p>
        </div>
        <div 
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg border"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          }}
        >
          <BookOpen size={14} style={{ color: 'var(--theme-accent-primary)' }} />
          <span className="text-[10px] font-mono font-bold" style={{ color: 'var(--theme-text-primary)' }}>Base de Conocimiento v2.4</span>
        </div>
      </div>

      {/* Main split: Library vs Quick commands wizard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main articles column */}
        <div className="lg:col-span-2 space-y-4">
          {/* Category Filters bar */}
          <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            {['all', 'Instalación', 'Configuración', 'Resolución de Problemas', 'Notas de Versión'].map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCat(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold select-none cursor-pointer border whitespace-nowrap transition-all`}
                style={selectedCat === cat ? {
                  backgroundColor: 'var(--theme-accent-primary)',
                  borderColor: 'var(--theme-accent-primary)',
                  color: '#ffffff'
                } : {
                  backgroundColor: 'var(--theme-bg-card)',
                  borderColor: 'var(--theme-border-card)',
                  color: 'var(--theme-text-secondary)'
                }}
              >
                {cat === 'all' ? 'Ver Todo' : cat}
              </button>
            ))}
          </div>

          <div className="space-y-4 max-h-[460px] overflow-y-auto pr-1">
            {filtered.map((art) => (
              <div 
                key={art.id} 
                className="border rounded-xl p-5 transition-colors"
                style={{
                  backgroundColor: 'var(--theme-bg-card)',
                  borderColor: 'var(--theme-border-card)',
                  color: 'var(--theme-text-primary)'
                }}
              >
                <div className="flex justify-between items-start gap-3 mb-2">
                  <span 
                    className="border px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase"
                    style={{
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'var(--theme-border-well)',
                      color: 'var(--theme-accent-primary)'
                    }}
                  >
                    {art.category}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500" style={{ color: 'var(--theme-text-secondary)' }}>{art.readTime} Lectura</span>
                </div>
                <h3 className="text-sm font-bold mb-2 font-sans" style={{ color: 'var(--theme-text-primary)' }}>{art.title}</h3>
                <p className="text-xs leading-relaxed font-sans pb-3.5 border-b" style={{ color: 'var(--theme-text-secondary)', borderColor: 'var(--theme-border-well)' }}>
                  {art.content}
                </p>

                <div className="mt-3.5 flex flex-wrap gap-1.5">
                  {art.tags.map((tag, idx) => (
                    <span 
                      key={idx} 
                      className="text-[10px] font-mono px-2 py-0.5 rounded border"
                      style={{
                        backgroundColor: 'var(--theme-bg-well)',
                        borderColor: 'var(--theme-border-well)',
                        color: 'var(--theme-text-secondary)'
                      }}
                    >
                      #{tag.toLowerCase()}
                    </span>
                  ))}
                </div>

                <button
                  onClick={() => handleOpenGuide(art)}
                  className="mt-4 px-3 py-1.5 rounded-lg text-xs font-bold border inline-flex items-center gap-2 cursor-pointer transition-all"
                  style={{
                    backgroundColor: 'var(--theme-bg-well)',
                    borderColor: 'var(--theme-border-well)',
                    color: 'var(--theme-accent-primary)'
                  }}
                >
                  <BookOpen size={13} />
                  <span>Abrir guía real</span>
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Interactive suggestions panel sidebar */}
        <div 
          className="border rounded-xl p-4.5 space-y-4 flex flex-col justify-between"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)'
          }}
        >
          <div>
            <div className="border-b pb-2 flex items-center gap-2 mb-4" style={{ borderColor: 'var(--theme-border-well)' }}>
              <Terminal size={14} style={{ color: 'var(--theme-accent-primary)' }} />
              <h4 className="text-xs font-bold font-mono uppercase" style={{ color: 'var(--theme-text-primary)' }}>CONSOLA SUGERIDA</h4>
            </div>

            <p className="text-xs leading-normal mb-4" style={{ color: 'var(--theme-text-secondary)' }}>
              Haga clic sobre cualquiera de las macros recomendadas abajo para pegar e interactuar directamente con la consola local de desarrollo.
            </p>

            <div className="space-y-3">
              {commandHints.map((hint, idx) => (
                <div 
                  key={idx} 
                  onClick={() => handleApplyCommand(hint.cmd)}
                  className="p-3 rounded-lg border transition-colors cursor-pointer group flex flex-col gap-1.5"
                  style={{
                    backgroundColor: 'var(--theme-bg-well)',
                    borderColor: 'var(--theme-border-well)'
                  }}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold group-hover:text-indigo-400 transition-colors" style={{ color: 'var(--theme-text-primary)' }}>
                      {hint.label}
                    </span>
                    <ArrowRight size={12} className="text-slate-600 group-hover:translate-x-0.5 transition-all" />
                  </div>
                  <code 
                    className="text-[10px] font-mono px-1.5 py-1 rounded truncate block border"
                    style={{
                      backgroundColor: 'var(--theme-bg-app)',
                      borderColor: 'var(--theme-border-card)',
                      color: 'var(--theme-accent-primary)'
                    }}
                  >
                    {hint.cmd}
                  </code>
                </div>
              ))}
            </div>
          </div>

          <div 
            className="border p-3.5 rounded-lg mt-4 flex items-start gap-2 text-[10px] leading-normal"
            style={{
              backgroundColor: 'var(--theme-bg-well)',
              borderColor: 'var(--theme-border-well)',
              color: 'var(--theme-text-secondary)'
            }}
          >
            <Info size={13} className="shrink-0 mt-0.5" style={{ color: 'var(--theme-accent-primary)' }} />
            <p>
              Toda la biblioteca es de uso interno exclusivo de los administradores locales. No comparta contraseñas de restauración de sysvol.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
