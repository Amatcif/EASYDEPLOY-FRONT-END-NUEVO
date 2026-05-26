import React from 'react';
import { 
  LayoutDashboard, 
  ShieldCheck, 
  Mail, 
  MessagesSquare, 
  DownloadCloud, 
  RefreshCw, 
  Lock, 
  BookOpen, 
  Wrench, 
  Sliders, 
  Terminal,
  Shield, 
  Settings,
  Cpu,
  Database,
  Activity,
  Network,
  History,
  Award,
  Key,
  ServerCog
} from 'lucide-react';
import { ActiveTab } from '../types';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  systemName?: string;
  appVersion?: string;
}

type SidebarItem = {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  badge?: string;
};

export default function Sidebar({ activeTab, setActiveTab, systemName = "Easy Deploy", appVersion = "2.2.5.27" }: SidebarProps) {
  const menuGroups: Array<{ title: string; items: SidebarItem[] }> = [
    {
      title: "Control General",
      items: [
        { id: 'dashboard', name: 'Panel de Control', icon: LayoutDashboard },
      ]
    },
    {
      title: "Sistemas",
      items: [
        { id: 'ad', name: 'Active Directory', icon: Shield },
        { id: 'kms', name: 'KMS', icon: Key },
        { id: 'exchange', name: 'Exchange Server', icon: Mail },
        { id: 'sharepoint', name: 'SharePoint', icon: ServerCog },
        { id: 'sql', name: 'SQL', icon: Database },
        { id: 'skype', name: 'Skype for Business', icon: MessagesSquare },
        { id: 'jchat', name: 'JCHAT', icon: Cpu },
        { id: 'offline_installers', name: 'Instaladores Offline', icon: DownloadCloud },
        { id: 'security', name: 'Seguridad y Auditoría', icon: Lock },
      ]
    },
    {
      title: "Red y comunicaciones",
      items: [
        { id: 'networks', name: 'Redes', icon: Network },
        { id: 'ping', name: 'Monitor de ping', icon: Activity },
      ]
    },
    {
      title: "Herramientas y Ayuda",
      items: [
        { id: 'tools', name: 'Herramientas', icon: Wrench },
        { id: 'guides', name: 'Guías y Manuales', icon: BookOpen },
        { id: 'configuration', name: 'Ajustes del Entorno', icon: Sliders },
        { id: 'updates', name: 'Actualizaciones y Activación', icon: RefreshCw },
      ]
    },
    {
      title: "Información de interés",
      items: [
        { id: 'versions', name: 'Versiones', icon: History },
        { id: 'credits', name: 'Créditos', icon: Award },
      ]
    },
    {
      title: "Diagnóstico Avanzado",
      items: [
        { id: 'deployment_console', name: 'Consola', icon: Terminal },
      ]
    }
  ];

  return (
    <aside 
      className="w-68 border-r flex flex-col h-full shrink-0"
      style={{
        backgroundColor: 'var(--theme-bg-sidebar)',
        borderColor: 'var(--theme-border-card)',
        color: 'var(--theme-text-primary)'
      }}
    >
      {/* Brand Header */}
      <div className="p-4 border-b flex flex-col gap-2 shrink-0" style={{ borderColor: 'var(--theme-border-card)' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black shadow-lg shadow-indigo-500/20">
            <span className="text-base tracking-tighter">ED</span>
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight uppercase font-sans" style={{ color: 'var(--theme-text-primary)' }}>{systemName}</h1>
            <p className="text-[10px] font-medium tracking-wide" style={{ color: 'var(--theme-accent-primary)' }}>v{appVersion}</p>
          </div>
        </div>

      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 overflow-y-auto px-2.5 py-4 space-y-5 scrollbar-thin scrollbar-thumb-slate-800">
        {menuGroups.map((group, gIdx) => (
          <div key={gIdx} className="space-y-1">
            <h2 className="px-3 text-[10px] font-bold tracking-widest uppercase font-mono pb-1" style={{ color: 'var(--theme-text-secondary)' }}>
              {group.title}
            </h2>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id as ActiveTab)}
                    className="w-full text-left px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-between transition-all duration-150 border border-transparent"
                    style={isActive ? {
                      backgroundColor: 'var(--theme-bg-app)',
                      color: 'var(--theme-accent-primary)',
                      borderColor: 'var(--theme-border-card)'
                    } : {
                      color: 'var(--theme-text-secondary)'
                    }}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon size={14} style={{ color: isActive ? 'var(--theme-accent-primary)' : 'var(--theme-text-secondary)' }} />
                      <span className="truncate">{item.name}</span>
                    </div>
                    {item.badge && (
                      <span 
                        className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded border"
                        style={{
                          backgroundColor: 'var(--theme-bg-well)',
                          borderColor: 'var(--theme-border-well)',
                          color: 'var(--theme-accent-primary)'
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

    </aside>
  );
}
