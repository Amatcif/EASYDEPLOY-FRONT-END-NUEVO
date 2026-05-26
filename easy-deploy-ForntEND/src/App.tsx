import React, { useState, useEffect } from 'react';
import { ActiveTab, SystemLog, WindowsRegistry } from './types';
import Sidebar from './components/Sidebar';
import DashboardView from './components/DashboardView';
import DomainControllerView from './components/DomainControllerView';
import ExchangeView from './components/ExchangeView';
import SkypeView from './components/SkypeView';
import ProgramsView from './components/ProgramsView';
import UpdatesView from './components/UpdatesView';
import SecurityView from './components/SecurityView';
import ActivationView from './components/ActivationView';
import GuidesView from './components/GuidesView';
import ToolsView from './components/ToolsView';
import ConfigView from './components/ConfigView';
import DeploymentConsoleView from './components/DeploymentConsoleView';
import NetworksView from './components/NetworksView';
import PingView from './components/PingView';
import ConsolePanel from './components/ConsolePanel';
import VersionsView from './components/VersionsView';
import CreditsView from './components/CreditsView';
import { backendClient, getDetectedBridgeApis } from './services/backendClient';
import type { BackendEvent } from './types/backend';
import { Terminal, Shield, RefreshCw, Cpu, Activity, Layout, Palette, Check, ChevronDown, Clock } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [theme, setTheme] = useState<'slate' | 'camel' | 'emerald' | 'cyber'>(() => {
    return (localStorage.getItem('premium-theme') as any) || 'slate';
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Licence and software status states
  const [systemDate, setSystemDate] = useState<Date>(new Date(2026, 4, 25, 14, 0, 0));
  const [registry, setRegistry] = useState<WindowsRegistry>({
    Estado_Licencia: 'TRIAL',
    Fecha_Primera_Ejecucion: '2026-05-25',
    Fecha_Ultima_Ejecucion: '2026-05-25',
    Fecha_Expiracion: '2026-06-01',
    Build_Hash: 'B9A4-F87E-2026',
    Bloqueo_Flag: 0,
    Dias_Transcurridos: 0,
    Activado_Una_Vez: false
  });
  const [appInfo, setAppInfo] = useState<Record<string, unknown>>({});
  const [backendProgress, setBackendProgress] = useState(0);
  const [backendData, setBackendData] = useState<Record<string, unknown>>({});

  const remainingDays = 7 - Math.min(registry.Dias_Transcurridos, 7);
  const displayedVersion = String(appInfo.version || '2.2.5.23');

  useEffect(() => {
    localStorage.setItem('premium-theme', theme);
  }, [theme]);
  
  // Custom console logs
  const [logs, setLogs] = useState<string[]>([
    'Easy Deploy Orchestrator [v2.2.5.23]',
    'Copyright (C) 2026 Easy Deploy. Todos los derechos reservados.',
    '',
    '[BOOT] [i] Cargando front-end React/Electron...',
    '[BOOT] [i] Esperando conexión con backend Python...',
  ]);

  // Method to append formatted string to terminal simulation
  const handleAppendLog = (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => {
    const timestamp = new Date().toTimeString().split(' ')[0];
    let prefix = '[i]';
    if (type === 'success') prefix = '[OK]';
    if (type === 'warning') prefix = '[AVISO]';
    if (type === 'error') prefix = '[ERROR]';

    setLogs(prev => [...prev, `[${timestamp}] [${source}] ${prefix} ${message}`]);
  };

  const formatBackendEvent = (event: BackendEvent) => {
    const source = String(event.source || event.action || 'BACKEND').toUpperCase();
    const level = event.level || (event.success === false ? 'error' : 'info');
    const message = String(event.message || event.title || JSON.stringify(event.result || {}));
    let prefix = '[i]';
    if (level === 'success') prefix = '[OK]';
    if (level === 'warning') prefix = '[AVISO]';
    if (level === 'error') prefix = '[ERROR]';
    return `[${source}] ${prefix} ${message}`;
  };

  useEffect(() => {
    const detectedApis = getDetectedBridgeApis();
    setLogs(prev => [...prev, `[BRIDGE] [i] APIs detectadas en window: ${JSON.stringify(detectedApis)}`]);

    backendClient.pingPreload()
      .then((result) => {
        setLogs(prev => [...prev, `[BRIDGE] ${result && (result as any).ok ? '[OK]' : '[ERROR]'} pingPreload: ${JSON.stringify(result)}`]);
      })
      .catch((error) => {
        setLogs(prev => [...prev, `[BRIDGE] [ERROR] pingPreload falló: ${String(error)}`]);
      });

    backendClient.getAppInfo()
      .then((info) => {
        setAppInfo(info || {});
        setLogs(prev => [...prev, `[BOOT] [i] Versión real cargada: ${String((info as any)?.version || 'desconocida')}`]);
        if ((info as any)?.smokeActions) {
          setLogs(prev => [...prev, '[BOOT] [i] Smoke test de acciones seguras activado por entorno.']);
          backendClient.runAction('dashboard.check_admin');
          backendClient.runAction('dashboard.check_resources');
          backendClient.runAction('dashboard.system_info');
          backendClient.runAction('dashboard.roles_installed');
          backendClient.runAction('dashboard.top_processes');
          backendClient.runAction('dashboard.ping', { target: '127.0.0.1' });
          backendClient.runAction('security.firewall_status');
          backendClient.runAction('updates.load_settings');
          backendClient.runAction('ad.dc1', { dryRun: true });
          backendClient.runAction('ad.dc2', { dryRun: true });
          backendClient.runAction('ad.d2d4', { dryRun: true });
          backendClient.runAction('exchange.prereqs', { dryRun: true });
          backendClient.runAction('exchange.install', { dryRun: true });
          backendClient.runAction('skype.install', { dryRun: true });
        }
      })
      .catch(() => setAppInfo({ mode: 'sin backend' }));

    backendClient.getBackendStatus()
      .then((status) => {
        setLogs(prev => [...prev, `[BRIDGE] [i] Estado backend: ${JSON.stringify(status)}`]);
      })
      .catch((error) => {
        setLogs(prev => [...prev, `[BRIDGE] [ERROR] No se pudo leer estado backend: ${String(error)}`]);
      });

    return backendClient.onBackendEvent((event) => {
      if (event.type === 'ready') {
        setLogs(prev => [...prev, '[BRIDGE] [OK] Backend Python conectado.']);
        backendClient.runAction('app.info');
        return;
      }
      if (event.type === 'log' || event.type === 'status' || event.type === 'error' || event.type === 'notification') {
        setLogs(prev => [...prev, formatBackendEvent(event)]);
        return;
      }
      if (event.type === 'progress') {
        setBackendProgress(Math.round(Number(event.value || 0) * 100));
        return;
      }
      if (event.type === 'prompt' && event.prompt_id) {
        const heading = `${event.title || 'Easy Deploy'}\n\n${event.message || ''}`;
        const value = event.kind === 'confirm'
          ? window.confirm(heading)
          : window.prompt(heading, String(event.default || ''));
        backendClient.respondPrompt(String(event.prompt_id), value);
        return;
      }
      if (event.type === 'data') {
        if (event.name) {
          setBackendData(prev => ({ ...prev, [String(event.name)]: event.value }));
        }
        if (event.name === 'app.info' && event.value && typeof event.value === 'object') {
          setAppInfo(event.value as Record<string, unknown>);
        }
        setLogs(prev => [...prev, `[DATA] ${event.name || 'backend'} actualizado.`]);
        return;
      }
      if (event.type === 'restart_required') {
        setLogs(prev => [...prev, '[UPDATES] [AVISO] Se ha lanzado el instalador. Easy Deploy debe cerrarse para actualizar.']);
        return;
      }
      if (event.type === 'finished') {
        setLogs(prev => [...prev, `[${event.action || 'BACKEND'}] ${event.success ? '[OK]' : '[ERROR]'} Acción finalizada.`]);
      }
    });
  }, []);

  const runBackendAction = async (action: string, payload: Record<string, unknown> = {}) => {
    setLogs(prev => [...prev, `[CLIENT] Ejecutando acción real: ${action}`]);
    const confirmRequired = new Set([
      'ad.dc1',
      'ad.dc2',
      'ad.join_domain',
      'ad.gpo',
      'ad.netfx35',
      'ad.repadmin',
      'ad.d2d4',
      'ad.create_users',
      'system.time_sync',
      'system.kms',
      'system.sql',
      'system.jchat',
      'system.jchat_cli',
      'sharepoint.roles',
      'sharepoint.install',
      'exchange.prereqs',
      'exchange.prepare_schema',
      'exchange.install',
      'exchange.recover_server',
      'exchange.create_users',
      'skype.prereqs',
      'skype.install',
      'skype.permissions',
      'skype.dns',
      'programs.firefox',
      'programs.winrar',
      'programs.adobe_reader',
      'programs.office_skype',
      'security.firewall_disable',
      'security.firewall_enable',
      'networks.switch_allied',
      'networks.switch_cisco',
      'networks.router',
    ]);
    if (confirmRequired.has(action) && payload.dryRun !== true) {
      const proceed = window.confirm(`Easy Deploy va a ejecutar una acción real:\n\n${action}\n\nLa salida se mostrará en la consola. ¿Quieres continuar?`);
      if (!proceed) {
        setLogs(prev => [...prev, `[CLIENT] [AVISO] Acción cancelada por el usuario: ${action}`]);
        return { cancelled: true };
      }
    }
    const stayOnPage = payload.stayOnPage === true;
    const visualOnly = action === 'app.info'
      || action.startsWith('updates.')
      || action.startsWith('activation.')
      || action === 'tools.versions'
      || action === 'tools.credits';
    if (!stayOnPage && !visualOnly) {
      setActiveTab('deployment_console');
    }
    return backendClient.runAction(action, payload);
  };

  const handleAppendMultipleLogs = (lines: string[]) => {
    setLogs(prev => [...prev, ...lines]);
  };

  const handleClearConsole = () => {
    setLogs([]);
  };

  // Custom CLI Parser
  const handleExecuteCommand = (cmd: string) => {
    const sanitized = cmd.toLowerCase().trim();
    const timestamp = new Date().toTimeString().split(' ')[0];
    
    setLogs(prev => [...prev, `> C:\\Deploy> ${cmd}`]);

    if (sanitized === 'help' || sanitized === '?') {
      setLogs(prev => [
        ...prev,
        'Comandos de Orquestación Disponibles:',
        '  ad-forest   - Promocionar DC1 y levantar nuevo bosque local',
        '  ad-reps     - Mostrar estado de vecinos de replicación RPC',
        '  exc-setup   - Iniciar instalación desatendida de Exchange Server',
        '  sys-clean   - Liberación profunda de temporales en disco C:',
        '  clear / cls - Vaciar terminal principal',
        '  info        - Mostrar especificaciones del servidor host'
      ]);
      return;
    }

    if (sanitized === 'clear' || sanitized === 'cls') {
      handleClearConsole();
      return;
    }

    if (sanitized === 'ad-forest') {
      setLogs(prev => [...prev, '[i] Buscando script "ad_dc1" en base local...']);
      runBackendAction('ad.dc1', { dryRun: true });
      return;
    }

    if (sanitized === 'ad-reps') {
      setLogs(prev => [...prev, '[i] Conectando con repadmin RPC sockets...']);
      runBackendAction('ad.repadmin');
      return;
    }

    if (sanitized === 'exc-setup') {
      setLogs(prev => [...prev, '[i] Iniciando instalador desatendido de Exchange...']);
      runBackendAction('exchange.install', { dryRun: true });
      return;
    }

    if (sanitized === 'sys-clean') {
      setLogs(prev => [...prev, '[SECURITY] [AVISO] Limpieza profunda no expuesta desde consola libre en esta fase.']);
      return;
    }

    if (sanitized === 'info') {
      setLogs(prev => [
        ...prev,
        `Easy Deploy Server Host Info:`,
        `  OS: Windows Server 2022 Datacenter`,
        `  CPU: Intel Xeon Silver 4214 @ 2.20GHz (6 Cores Virtuales)`,
        `  RAM asignada: 32 GB LPDDR4`,
        `  Directorio raíz de orquestación: C:\\Deploy`,
        `  Adaptadores Ethernet: 2 activos, 1 desconectado`
      ]);
      return;
    }

    setLogs(prev => [
      ...prev,
      `[${timestamp}] [SECURITY] [AVISO] Comando no permitido desde el renderer: "${cmd}". Usa botones conectados al backend.`
    ]);
  };

  return (
    <div 
      className={`flex h-screen w-screen font-sans overflow-hidden select-none antialiased theme-${theme}`}
      style={{
        backgroundColor: 'var(--theme-bg-app)',
        color: 'var(--theme-text-primary)'
      }}
    >
      {/* Sidebar navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} appVersion={displayedVersion} />
 
      {/* Main Workspace Frame */}
      <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden" style={{ backgroundColor: 'var(--theme-bg-main)' }}>
        {/* Universal Top Stats Banner */}
        <header 
          className="h-14 backdrop-blur-md border-b px-6 flex justify-between items-center shrink-0 relative z-45"
          style={{
            backgroundColor: 'var(--theme-bg-header)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <div className="flex items-center gap-3">
            <span 
              className="text-[10px] font-bold font-mono tracking-widest px-2 py-0.5 rounded border"
              style={{
                backgroundColor: 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)',
                color: 'var(--theme-accent-primary)'
              }}
            >
              EASY DEPLOY v{displayedVersion}
            </span>
            <div className="hidden sm:flex items-center gap-1.5 text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Bridge Python <strong style={{ color: 'var(--theme-text-primary)' }}>activo</strong></span>
            </div>
          </div>
 
          <div className="flex items-center gap-5 text-xs font-mono" style={{ color: 'var(--theme-text-secondary)' }}>
            {registry.Estado_Licencia !== 'ACTIVADO' && (
              <div 
                onClick={() => setActiveTab('updates')}
                className="px-3 py-1.5 rounded-lg border flex items-center gap-2 text-[11px] font-extrabold animate-pulse shrink-0 cursor-pointer hover:scale-102 transition-all shadow-sm"
                style={{
                  backgroundColor: 'rgba(249, 115, 22, 0.12)',
                  borderColor: 'rgba(249, 115, 22, 0.25)',
                  color: '#f97316'
                }}
                title="Haga clic para activar la clave de licencia"
              >
                <Clock size={12} />
                <span>Faltan {remainingDays} días de evaluación</span>
              </div>
            )}

            <div className="hidden lg:flex items-center gap-4 border-r pr-4 animate-fade-in" style={{ borderColor: 'var(--theme-border-card)' }}>
              <div className="flex items-center gap-1.5">
                <Cpu size={13} style={{ color: 'var(--theme-accent-primary)' }} />
                <span>CPU: <strong style={{ color: 'var(--theme-text-primary)' }}>22%</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <Activity size={13} style={{ color: 'var(--theme-accent-primary)' }} />
                <span>RAM: <strong style={{ color: 'var(--theme-text-primary)' }}>64%</strong></span>
              </div>
            </div>
 
            {/* Premium Theme Selector Tab */}
            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="px-3 py-1.5 rounded-lg flex items-center gap-2 text-[10px] border transition-all cursor-pointer shadow-sm"
                style={{
                  backgroundColor: 'var(--theme-bg-card)',
                  borderColor: 'var(--theme-border-card)',
                  color: 'var(--theme-text-secondary)'
                }}
              >
                <Palette size={11} style={{ color: 'var(--theme-accent-primary)' }} />
                <span>Temas</span>
                <ChevronDown size={10} className="opacity-60" />
              </button>
              
              {dropdownOpen && (
                <div 
                  className="absolute right-0 mt-1.5 w-48 rounded-xl border shadow-2xl py-1.5 z-50 text-[11px] font-sans"
                  style={{
                    backgroundColor: 'var(--theme-bg-sidebar)',
                    borderColor: 'var(--theme-border-card)',
                    color: 'var(--theme-text-primary)'
                  }}
                >
                  <div className="px-3 py-1 text-[9px] font-bold tracking-wider uppercase" style={{ color: 'var(--theme-text-secondary)' }}>Selección de Estilo</div>
                  {[
                    { id: 'slate', name: 'Océano oscuro', desc: 'Profundo índigo original' },
                    { id: 'camel', name: 'Blanco', desc: 'Blanco roto o marfil' },
                    { id: 'emerald', name: 'Bosque', desc: 'Estilo verde oliva/militar' },
                    { id: 'cyber', name: 'Neón', desc: 'Contraste digital extremo' }
                  ].map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        setTheme(t.id as any);
                        setDropdownOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 flex items-center justify-between transition-colors cursor-pointer"
                      style={theme === t.id ? {
                        backgroundColor: 'var(--theme-bg-app)',
                        color: 'var(--theme-accent-primary)'
                      } : {
                        color: 'var(--theme-text-primary)'
                      }}
                    >
                      <div className="flex flex-col">
                        <span className="font-semibold">{t.name}</span>
                        <span className="text-[9px] font-normal leading-tight" style={{ color: 'var(--theme-text-secondary)' }}>{t.desc}</span>
                      </div>
                      {theme === t.id && <Check size={11} className="shrink-0 ml-1.5" style={{ color: 'var(--theme-accent-primary)' }} />}
                    </button>
                  ))}
                </div>
              )}
            </div>
 
          </div>
        </header>

        {/* Action screens area */}
        <div className={`flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 ${activeTab === 'deployment_console' ? 'p-4' : 'p-6 space-y-6'}`}>
          {activeTab === 'dashboard' && (
            <DashboardView 
              onAppendLog={handleAppendLog} 
              onSetTab={setActiveTab} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'ad' && (
            <DomainControllerView 
              onAppendLogs={handleAppendMultipleLogs} 
              onClearConsole={handleClearConsole} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'exchange' && (
            <ExchangeView 
              onAppendLogs={handleAppendMultipleLogs} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'skype' && (
            <SkypeView 
              onAppendLogs={handleAppendMultipleLogs} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'offline_installers' && (
            <ProgramsView 
              onAppendLog={handleAppendLog} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'updates' && (
            <div className="space-y-8">
              <UpdatesView 
                onAppendLog={handleAppendLog} 
                onRunAction={runBackendAction}
                updateData={backendData['updates.check'] as Record<string, unknown> | undefined}
                appVersion={displayedVersion}
              />
              <ActivationView 
                registry={registry}
                setRegistry={setRegistry}
                systemDate={systemDate}
                setSystemDate={setSystemDate}
                onAppendLog={handleAppendLog}
                onRunAction={runBackendAction}
              />
            </div>
          )}

          {activeTab === 'security' && (
            <SecurityView 
              onAppendLog={handleAppendLog} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'guides' && (
            <GuidesView 
              onAppendLog={handleAppendLog} 
              onSetCommandInput={handleExecuteCommand}
              onSetTab={setActiveTab}
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'tools' && (
            <ToolsView 
              onAppendLog={handleAppendLog} 
              onAppendMultipleLogs={handleAppendMultipleLogs} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'configuration' && (
            <ConfigView 
              onAppendLog={handleAppendLog} 
            />
          )}

          {activeTab === 'deployment_console' && (
            <DeploymentConsoleView 
              logs={logs} 
              onClearConsole={handleClearConsole} 
              onExecuteCommand={handleExecuteCommand} 
              onAppendLog={handleAppendLog}
              backendProgress={backendProgress}
            />
          )}

          {activeTab === 'networks' && (
            <NetworksView
              onAppendLog={handleAppendLog}
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'ping' && (
            <PingView
              onAppendLog={handleAppendLog}
              onRunAction={runBackendAction}
              favoritesData={backendData['ping.favorites']}
              lastPingResult={backendData['ping.result'] as Record<string, unknown> | undefined}
            />
          )}

          {activeTab === 'versions' && (
            <VersionsView onSetTab={setActiveTab} />
          )}

          {activeTab === 'credits' && (
            <CreditsView onSetTab={setActiveTab} />
          )}
        </div>
      </main>
    </div>
  );
}
