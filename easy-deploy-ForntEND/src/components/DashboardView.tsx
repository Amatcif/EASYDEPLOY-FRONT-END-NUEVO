import React from 'react';
import { 
  CheckCircle2, 
  Layers, 
  Cpu, 
  Search, 
  FolderLock, 
  Terminal,
  Activity,
  HardDrive
} from 'lucide-react';
import { ActiveTab } from '../types';

interface DashboardViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onSetTab: (tab: ActiveTab) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  firewallState?: 'enabled' | 'disabled' | 'unknown';
}

export default function DashboardView({ onAppendLog, onSetTab, onRunAction, firewallState = 'unknown' }: DashboardViewProps) {
  const firewallLabel = firewallState === 'enabled' ? 'Firewall OK' : firewallState === 'disabled' ? 'Firewall OFF' : 'Sin comprobar';
  const firewallColor = firewallState === 'enabled' ? 'var(--theme-accent-primary)' : firewallState === 'disabled' ? '#ef4444' : 'var(--theme-text-secondary)';
  
  const handleDiskManagementClick = () => {
    onAppendLog('SYSTEM', 'info', 'Abriendo Disk Management.');
    onRunAction('dashboard.disk_management', { stayOnPage: true });
  };

  const handleEnvCheckClick = () => {
    onAppendLog('SYSTEM', 'info', 'Usuario solicit? comprobación del entorno desde panel rápido.');
    onRunAction('dashboard.system_info');
  };

  const handleRolesClick = () => {
    onAppendLog('SYSTEM', 'info', 'Consultando roles y características instalados.');
    onRunAction('dashboard.roles_installed');
  };

  const handleProcesosClick = () => {
    onAppendLog('SYSTEM', 'info', 'Consultando procesos activos con mayor consumo.');
    onRunAction('dashboard.top_processes');
  };

  const handlePingClick = () => {
    onAppendLog('NETWORK', 'info', 'Abriendo Monitor de ping de Easy Deploy.');
    onSetTab('ping');
  };

  return (
    <div className="space-y-6">
      {/* Visual Title Block matching screenshot layout */}
      <div 
        className="border-l-4 pl-4 py-1.5"
        style={{ borderColor: 'var(--theme-accent-primary)' }}
      >
        <h1 className="text-xl font-bold font-sans tracking-tight leading-none mb-1 text-slate-100" style={{ color: 'var(--theme-text-primary)' }}>
          Panel de despliegue
        </h1>
        <p className="text-xs font-sans text-slate-400" style={{ color: 'var(--theme-text-secondary)' }}>
          Empieza por las comprobaciones, valida recursos y ejecuta cada tarea con registro automático.
        </p>
      </div>

      {/* Top Indicators Bar (5 inline boxes) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {/* Box 1: Privilegios */}
        <div 
          onClick={() => onRunAction('dashboard.check_admin')}
          className="border rounded-xl p-4 flex flex-col justify-between hover:opacity-90 transition-all duration-150 cursor-pointer"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)'
          }}
        >
          <span className="text-[10px] font-bold uppercase tracking-wider font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
            Privilegios
          </span>
          <span className="text-sm font-bold mt-2 font-mono flex items-center gap-1.5" style={{ color: 'var(--theme-accent-primary)' }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
            Admin OK
          </span>
        </div>

        {/* Box 2: Recursos */}
        <div 
          onClick={() => onRunAction('dashboard.check_resources')}
          className="border rounded-xl p-4 flex flex-col justify-between hover:opacity-90 transition-all duration-150 cursor-pointer"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)'
          }}
        >
          <span className="text-[10px] font-bold uppercase tracking-wider font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
            Recursos
          </span>
          <span className="text-sm font-bold mt-2 font-mono flex items-center gap-1.5" style={{ color: 'var(--theme-accent-primary)' }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
            Recursos OK
          </span>
        </div>

        {/* Box 3: Logs */}
        <div 
          onClick={() => onRunAction('dashboard.open_logs')}
          className="border rounded-xl p-4 flex flex-col justify-between hover:opacity-90 transition-all duration-150 cursor-pointer"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)'
          }}
        >
          <span className="text-[10px] font-bold uppercase tracking-wider font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
            Logs
          </span>
          <span className="text-sm font-bold mt-2 font-mono flex items-center gap-1.5" style={{ color: 'var(--theme-accent-primary)' }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
            Activados
          </span>
        </div>

        {/* Box 4: Teclado ESP */}
        <div 
          onClick={() => onRunAction('dashboard.keyboard_es')}
          className="border rounded-xl p-4 flex flex-col justify-between hover:opacity-90 transition-all duration-150 cursor-pointer"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)'
          }}
        >
          <span className="text-[10px] font-bold uppercase tracking-wider font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
            Teclado ESP
          </span>
          <span className="text-sm font-bold mt-2 font-mono flex items-center gap-1.5" style={{ color: 'var(--theme-accent-primary)' }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
            ESP OK
          </span>
        </div>

        {/* Box 5: Firewall */}
        <div 
          onClick={() => onSetTab('security')}
          className="border rounded-xl p-4 flex flex-col justify-between cursor-pointer transition-all duration-150 group"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)',
            color: 'var(--theme-text-primary)'
          }}
        >
          <span className="text-[10px] font-bold uppercase tracking-wider font-sans group-hover:opacity-80 transition-colors" style={{ color: 'var(--theme-text-secondary)' }}>
            Firewall
          </span>
          <span className="text-sm font-bold mt-2 font-mono flex items-center gap-1.5" style={{ color: firewallColor }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: firewallColor }} />
            {firewallLabel}
          </span>
        </div>
      </div>

      {/* Main Grid: 4 Core Cards matching screenshot style */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Comprobar entorno */}
        <div 
          onClick={handleEnvCheckClick}
          className="border p-5 rounded-2xl cursor-pointer transition-all duration-300 group flex flex-col justify-between h-[150px] shadow-sm relative overflow-hidden hover:opacity-95"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <div className="absolute top-0 left-0 bottom-0 w-1 bg-transparent group-hover:bg-indigo-500" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-extrabold pr-0.5" style={{ color: 'var(--theme-accent-primary)' }}></span>
            </div>
            <h4 
              className="text-sm font-bold font-sans group-hover:opacity-80 transition-colors" 
              style={{ color: 'var(--theme-text-primary)' }}
            >
              Comprobar entorno
            </h4>
            <p className="text-[11px] leading-normal font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
              Revisa permisos de administrador, red y datos básicos del servidor.
            </p>
          </div>
        </div>

        {/* Card 2: Ver roles instalados */}
        <div 
          onClick={handleRolesClick}
          className="border p-5 rounded-2xl cursor-pointer transition-all duration-300 group flex flex-col justify-between h-[150px] shadow-sm relative overflow-hidden hover:opacity-95"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <div className="absolute top-0 left-0 bottom-0 w-1 bg-transparent group-hover:bg-indigo-500" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
          <div className="space-y-3">
            <div 
              className="text-[13px] font-black font-mono w-max px-1 border rounded"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)',
                color: 'var(--theme-accent-primary)'
              }}
            >
              R
            </div>
            <h4 
              className="text-sm font-bold font-sans group-hover:opacity-80 transition-colors" 
              style={{ color: 'var(--theme-text-primary)' }}
            >
              Ver roles instalados
            </h4>
            <p className="text-[11px] leading-normal font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
              Lista los roles y características instalados en Windows Server.
            </p>
          </div>
        </div>

        {/* Card 3: Top procesos */}
        <div 
          onClick={handleProcesosClick}
          className="border p-5 rounded-2xl cursor-pointer transition-all duration-300 group flex flex-col justify-between h-[150px] shadow-sm relative overflow-hidden hover:opacity-95"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <div className="absolute top-0 left-0 bottom-0 w-1 bg-transparent group-hover:bg-indigo-500" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
          <div className="space-y-3">
            <div 
              className="text-[9px] font-black font-mono uppercase tracking-widest px-1.5 py-0.5 border rounded w-max"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)',
                color: 'var(--theme-accent-primary)'
              }}
            >
              CPU
            </div>
            <h4 
              className="text-sm font-bold font-sans group-hover:opacity-80 transition-colors" 
              style={{ color: 'var(--theme-text-primary)' }}
            >
              Top procesos
            </h4>
            <p className="text-[11px] leading-normal font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
              Muestra los procesos que más consumen CPU y memoria.
            </p>
          </div>
        </div>

        {/* Card 4: Ping */}
        <div 
          onClick={handlePingClick}
          className="border p-5 rounded-2xl cursor-pointer transition-all duration-300 group flex flex-col justify-between h-[150px] shadow-sm relative overflow-hidden hover:opacity-95"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <div className="absolute top-0 left-0 bottom-0 w-1 bg-transparent group-hover:bg-indigo-500" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
          <div className="space-y-3">
            <div 
              className="text-[9px] font-black font-mono uppercase tracking-widest px-1.5 py-0.5 border rounded w-max"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)',
                color: 'var(--theme-accent-primary)'
              }}
            >
              PING
            </div>
            <h4 
              className="text-sm font-bold font-sans group-hover:opacity-80 transition-colors" 
              style={{ color: 'var(--theme-text-primary)' }}
            >
              Ping
            </h4>
            <p className="text-[11px] leading-normal font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
              Comprueba conectividad con una IP o dominio desde una ventana guiada.
            </p>
          </div>
        </div>
      </div>

      {/* Disks partitions block matching exactly the original screenshot */}
      <div 
        className="border rounded-2xl p-6"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)'
        }}
      >
        <h3 
          className="text-xs font-bold font-mono uppercase tracking-wider text-center mb-6"
          style={{ color: 'var(--theme-text-primary)' }}
        >
          SSD - Estado de discos
        </h3>

        <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 w-full">
            {/* Drive C: */}
            <div className="space-y-2.5">
              <div className="text-xs font-bold" style={{ color: 'var(--theme-text-primary)' }}>
                C:\ 339.3 GB libres
              </div>
              <div className="text-[10px] font-mono tracking-wide leading-tight" style={{ color: 'var(--theme-text-secondary)' }}>
                Total 930.6 GB | Uso 63%
              </div>
              <div 
                className="w-full h-1.5 rounded-full overflow-hidden border"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-card)'
                }}
              >
                <div 
                  className="h-full rounded-full transition-all duration-1000"
                  style={{ 
                    width: '63%',
                    backgroundColor: 'var(--theme-accent-primary)'
                  }}
                />
              </div>
            </div>

            {/* Drive D: */}
            <div className="space-y-2.5">
              <div className="text-xs font-bold" style={{ color: 'var(--theme-text-primary)' }}>
                D:\ 415.5 GB libres
              </div>
              <div className="text-[10px] font-mono tracking-wide leading-tight" style={{ color: 'var(--theme-text-secondary)' }}>
                Total 931.5 GB | Uso 55%
              </div>
              <div 
                className="w-full h-1.5 rounded-full overflow-hidden border"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-card)'
                }}
              >
                <div 
                  className="h-full rounded-full transition-all duration-1000"
                  style={{ 
                    width: '55%',
                    backgroundColor: 'var(--theme-accent-primary)',
                    opacity: 0.8
                  }}
                />
              </div>
            </div>

            {/* Drive G: */}
            <div className="space-y-2.5">
              <div className="text-xs font-bold" style={{ color: 'var(--theme-text-primary)' }}>
                G:\ 14.6 GB libres
              </div>
              <div className="text-[10px] font-mono tracking-wide leading-tight" style={{ color: 'var(--theme-text-secondary)' }}>
                Total 15.0 GB | Uso 2%
              </div>
              <div 
                className="w-full h-1.5 rounded-full overflow-hidden border"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-card)'
                }}
              >
                <div 
                  className="h-full rounded-full transition-all"
                  style={{ 
                    width: '2.6%',
                    backgroundColor: 'var(--theme-accent-primary)',
                    opacity: 0.9
                  }}
                />
              </div>
            </div>
          </div>

          {/* Disk Management Action Trigger */}
          <div className="shrink-0 w-full lg:w-auto text-right">
            <button
              onClick={handleDiskManagementClick}
              className="w-full lg:w-auto px-5 py-2.5 font-semibold rounded-lg text-xs tracking-wider transition-all duration-150 cursor-pointer shadow-sm text-center border"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-accent-primary)',
                color: 'var(--theme-text-primary)'
              }}
            >
              Disk Management
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

