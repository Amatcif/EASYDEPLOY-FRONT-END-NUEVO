import React from 'react';
import { Archive, BookOpen, Command, Database, FileText, FolderOpen, History, Terminal, Users, Wrench } from 'lucide-react';

interface ToolsViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onAppendMultipleLogs: (logs: string[]) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

const toolSections = [
  {
    title: 'Sistema',
    items: [
      { label: 'AD Users and Computers', detail: 'Abrir consola dsa.msc', action: 'tools.aduc', icon: Users },
      { label: 'DNS Manager', detail: 'Abrir consola dnsmgmt.msc', action: 'tools.dns_manager', icon: Database },
      { label: 'Group Policy Management', detail: 'Abrir gpmc.msc', action: 'tools.gpmc', icon: Archive },
    ],
  },
  {
    title: 'Utilidades',
    items: [
      { label: 'Abrir Logs', detail: 'Carpeta de registros de Easy Deploy', action: 'tools.open_logs', icon: FileText },
      { label: 'Abrir Recursos', detail: 'Carpeta local de recursos offline', action: 'tools.open_resources', icon: FolderOpen },
      { label: 'CMD', detail: 'Símbolo del sistema como administrador', action: 'tools.cmd', icon: Terminal },
      { label: 'PowerShell', detail: 'PowerShell como administrador', action: 'tools.powershell', icon: Command },
    ],
  },
  {
    title: 'Easy Deploy',
    items: [
      { label: 'Versiones', detail: 'Historial de cambios', action: 'tools.versions', icon: History },
      { label: 'Créditos', detail: 'Autoría y módulos', action: 'tools.credits', icon: BookOpen },
    ],
  },
];

export default function ToolsView({ onAppendLog, onRunAction }: ToolsViewProps) {
  const runTool = (action: string, label: string) => {
    onAppendLog('TOOLS', 'info', `Ejecutando herramienta: ${label}`);
    onRunAction(action).catch((error) => {
      onAppendLog('TOOLS', 'error', `No se pudo ejecutar ${label}: ${String(error)}`);
    });
  };

  return (
    <div className="space-y-6">
      <div
        className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-xl border"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
          color: 'var(--theme-text-primary)',
        }}
      >
        <div>
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>
            HERRAMIENTAS ADMINISTRATIVAS
          </span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>
            Herramientas
          </h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
            Accesos administrativos reales del Easy Deploy clásico. No incluye pruebas simuladas ni testers genéricos.
          </p>
        </div>
        <div
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border font-mono text-[10px] font-bold"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)',
            color: 'var(--theme-text-primary)',
          }}
        >
          <Wrench size={12} style={{ color: 'var(--theme-accent-primary)' }} />
          <span>Acciones permitidas</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {toolSections.map((section) => (
          <section
            key={section.title}
            className="border rounded-xl p-5 space-y-3"
            style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}
          >
            <h3 className="text-xs font-bold font-mono uppercase tracking-widest pb-2 border-b" style={{ color: 'var(--theme-text-primary)', borderColor: 'var(--theme-border-well)' }}>
              {section.title}
            </h3>
            <div className="space-y-2.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.action}
                    onClick={() => runTool(item.action, item.label)}
                    className="w-full text-left p-3 rounded-lg border flex items-center gap-3 transition-colors hover:opacity-90"
                    style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}
                  >
                    <span
                      className="w-9 h-9 rounded-lg border flex items-center justify-center shrink-0"
                      style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-accent-primary)' }}
                    >
                      <Icon size={16} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-xs font-bold" style={{ color: 'var(--theme-text-primary)' }}>{item.label}</span>
                      <span className="block text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>{item.detail}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
