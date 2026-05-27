import React from 'react';
import { BookOpen, FileText } from 'lucide-react';

interface GuidesViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onSetCommandInput: (cmd: string) => void;
  onSetTab: (tab: any) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

interface GuideButton {
  label: string;
  action: string;
}

interface GuideGroup {
  badge: string;
  title: string;
  description: string;
  accent: string;
  guides: GuideButton[];
}

const guideGroups: GuideGroup[] = [
  {
    badge: 'AD',
    title: 'Dominio y Active Directory',
    description: 'Controladores, roles FSMO, confianza y recuperación SYSVOL.',
    accent: '#38bdf8',
    guides: [
      { label: 'Guía DC1', action: 'guides.open_dc1' },
      { label: 'Guía DC2', action: 'guides.open_dc2' },
      { label: 'Guía Intercambio Roles', action: 'guides.open_fsmo' },
      { label: 'Guía Relación de Confianza', action: 'guides.open_trust' },
      { label: 'Guía D2 D4', action: 'guides.open_d2d4' },
    ],
  },
  {
    badge: 'CORE',
    title: 'Core y Coi',
    description: 'Guías de correo, colaboración y servicios de comunicación.',
    accent: '#a5b4fc',
    guides: [
      { label: 'Guía Exchange', action: 'guides.open_exchange' },
      { label: 'Guía Skype', action: 'guides.open_skype' },
      { label: 'Guía Jchat', action: 'guides.open_jchat' },
      { label: 'Guía Sharepoint', action: 'guides.open_sharepoint' },
    ],
  },
  {
    badge: 'WIN',
    title: 'Servicios Windows',
    description: 'Servicios de infraestructura, certificados y despliegue de red.',
    accent: '#9ccc65',
    guides: [
      { label: 'Guía Certificados', action: 'guides.open_certificates' },
      { label: 'Guía DHCP', action: 'guides.open_dhcp' },
      { label: 'Guía File Server', action: 'guides.open_file_server' },
      { label: 'Guía WDS', action: 'guides.open_wds' },
      { label: 'Guía WSUS', action: 'guides.open_wsus' },
    ],
  },
];

export default function GuidesView({ onAppendLog, onRunAction }: GuidesViewProps) {
  const openGuide = (guide: GuideButton) => {
    onAppendLog('GUIDES', 'info', `Abriendo guía PDF: ${guide.label}`);
    onRunAction(guide.action, { title: guide.label, stayOnPage: true }).catch((error) => {
      onAppendLog('GUIDES', 'error', `No se pudo abrir la guía: ${String(error)}`);
    });
  };

  return (
    <div className="space-y-6">
      <div
        className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-xl border"
        style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)', color: 'var(--theme-text-primary)' }}
      >
        <div>
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>
            CENTRO DE RECURSOS
          </span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>
            Guías y documentación
          </h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
            Biblioteca PDF local organizada por áreas de despliegue.
          </p>
        </div>
        <div
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg border"
          style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}
        >
          <BookOpen size={14} style={{ color: 'var(--theme-accent-primary)' }} />
          <span className="text-[10px] font-mono font-bold" style={{ color: 'var(--theme-text-primary)' }}>
            {guideGroups.reduce((count, group) => count + group.guides.length, 0)} guías
          </span>
        </div>
      </div>

      <div className="space-y-5 max-h-[calc(100vh-190px)] overflow-y-auto pr-1">
        {guideGroups.map((group) => (
          <section
            key={group.title}
            className="border rounded-xl p-5 space-y-4"
            style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: group.accent }}
          >
            <div className="h-1 rounded-full" style={{ backgroundColor: group.accent }} />
            <div className="flex items-start gap-3">
              <span
                className="text-[10px] font-bold font-mono px-2 py-1 rounded"
                style={{ backgroundColor: 'var(--theme-bg-well)', color: group.accent }}
              >
                {group.badge}
              </span>
              <div>
                <h3 className="text-lg font-bold" style={{ color: 'var(--theme-text-primary)' }}>{group.title}</h3>
                <p className="text-xs mt-1" style={{ color: 'var(--theme-text-secondary)' }}>{group.description}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {group.guides.map((guide) => (
                <button
                  key={guide.action}
                  type="button"
                  onClick={() => openGuide(guide)}
                  className="text-left rounded-lg border px-3 py-3 flex items-center gap-2 cursor-pointer hover:opacity-90 transition-opacity"
                  style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
                >
                  <FileText size={14} style={{ color: group.accent }} />
                  <span className="text-xs font-bold">{guide.label}</span>
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
