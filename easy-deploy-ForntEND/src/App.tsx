import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
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
import ServiceActionView from './components/ServiceActionView';
import CreditsView from './components/CreditsView';
import UserCreationFormView from './components/UserCreationFormView';
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
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const activeActionRef = useRef<string | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<BackendEvent | null>(null);
  const [promptValue, setPromptValue] = useState('');
  const promptInputRef = useRef<HTMLInputElement>(null);
  const [consoleInput, setConsoleInput] = useState({ enabled: false, placeholder: '', sensitive: false });
  const [notification, setNotification] = useState<{ title: string; message: string; level: 'info' | 'success' | 'warning' | 'error' } | null>(null);

  const remainingDays = 7 - Math.min(registry.Dias_Transcurridos, 7);
  const displayedVersion = String(appInfo.version || '2.2.5.28');

  const setCurrentAction = (action: string | null) => {
    activeActionRef.current = action;
    setActiveAction(action);
  };

  const nonCancelableActions = new Set([
    'ad.dc1',
    'ad.dc2',
    'ad.join_domain',
    'ad.d2d4',
    'exchange.prereqs',
    'exchange.install',
    'exchange.prepare_schema',
    'exchange.recover_server',
    'skype.prereqs',
    'skype.install',
    'sharepoint.install',
    'sharepoint.roles',
    'sql.install_2022',
    'programs.netfx35',
    'programs.install_all',
  ]);


  useEffect(() => {
    localStorage.setItem('premium-theme', theme);
  }, [theme]);
  
  // Custom console logs
  const [logs, setLogs] = useState<string[]>([
    'Easy Deploy Orchestrator [v2.2.5.28]',
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


  const formatResourceReport = (report: Record<string, unknown>) => {
    const root = String(report.root || 'Sin ruta');
    const complete = report.complete === true;
    const missing = Array.isArray(report.missing) ? report.missing.map(String) : [];
    const present = Number(report.present_count || 0);
    const total = Number(report.total || 0);
    if (complete) {
      return `Recursos correctos.

Carpeta: ${root}
Resultado: ${present}/${total} recursos encontrados.
No faltan carpetas críticas.`;
    }
    return `Recursos incompletos.

Carpeta: ${root}
Resultado: ${present}/${total} recursos encontrados.

Faltan recursos:
${missing.length ? missing.map((item) => `- ${item}`).join('\n') : '- No se pudo determinar la lista exacta.'}`;
  };

  const finishPrompt = (value: unknown) => {
    if (!pendingPrompt.prompt_id) return;
    backendClient.respondPrompt(String(pendingPrompt.prompt_id), value);
    setPendingPrompt(null);
    setPromptValue('');
  };


  useLayoutEffect(() => {
    if (!pendingPrompt || pendingPrompt.kind === 'confirm') return;

    const focusPrompt = () => {
      try {
        window.focus();
        const input = promptInputRef.current;
        if (!input) return;
        input.focus({ preventScroll: true });
        input.select();
        input.setSelectionRange(0, input.value.length);
      } catch (_) {
        promptInputRef.current.focus();
      }
    };

    focusPrompt();
    const frame = window.requestAnimationFrame(focusPrompt);
    const timers = [50, 150, 300].map((delay) => window.setTimeout(focusPrompt, delay));
    return () => {
      window.cancelAnimationFrame(frame);
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [pendingPrompt]);

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
        setLogs(prev => [...prev, `[BOOT] [i] Versión real cargada: ${String((info as any).version || 'desconocida')}`]);
        if ((info as any).smokeActions) {
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
        if (event.type === 'notification') {
          setNotification({
            title: String(event.title || 'Easy Deploy'),
            message: String(event.message || ''),
            level: (event.level as any) || 'info',
          });
        }
        return;
      }
      if (event.type === 'progress') {
        setBackendProgress(Math.round(Number(event.value || 0) * 100));
        return;
      }
      if (event.type === 'prompt' && event.prompt_id) {
        setActiveTab('deployment_console');
        setPromptValue(String(event.default || ''));
        setPendingPrompt(event);
        return;
      }
      if (event.type === 'console_input') {
        setActiveTab('deployment_console');
        setConsoleInput({
          enabled: Boolean(event.enabled),
          placeholder: String(event.placeholder || ''),
          sensitive: Boolean(event.sensitive),
        });
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
        setLogs(prev => [...prev, '[UPDATES] [AVISO] Instalador lanzado. Easy Deploy se cerrará para actualizar.']);
        setNotification({
          title: 'Actualización iniciada',
          message: 'El instalador de Easy Deploy se ha lanzado correctamente. La aplicación se cerrará en unos segundos para permitir la actualización.',
          level: 'warning',
        });
        window.setTimeout(() => {
          backendClient.quitApp();
        }, 1200);
        return;
      }
      if (event.type === 'finished') {
        if (event.action && event.result !== undefined) {
          setBackendData(prev => ({ ...prev, [String(event.action)]: event.result }));
        }
        if (event.action === 'dashboard.check_resources' && event.result && typeof event.result === 'object') {
          const report = event.result as Record<string, unknown>;
          setNotification({
            title: report.complete === true ? 'Recursos correctos' : 'Recursos incompletos',
            message: formatResourceReport(report),
            level: report.complete === true ? 'success' : 'warning',
          });
        }
        if (event.action === 'dashboard.check_admin' && event.result && typeof event.result === 'object') {
          const admin = (event.result as Record<string, unknown>).admin === true;
          setNotification({
            title: admin ? 'Privilegios de administrador' : 'Sin privilegios de administrador',
            message: admin ?
               'Easy Deploy se está ejecutando con privilegios de Administrador.'
              : 'Easy Deploy NO se está ejecutando con privilegios de Administrador. Cierra la aplicación y usa “Ejecutar como administrador”.',
            level: admin ? 'success' : 'warning',
          });
        }
        setLogs(prev => [...prev, `[${event.action || 'BACKEND'}] ${event.success ? '[OK]' : '[ERROR]'} Acción finalizada.`]);
        const currentAction = activeActionRef.current;
        const keepNetworkUntilInteractiveEnds = Boolean(currentAction && currentAction.startsWith('networks.') && event.action !== 'interactive_console');
        if (currentAction && !keepNetworkUntilInteractiveEnds) {
          setCurrentAction(null);
        }
      }
    });
  }, []);

  const runBackendAction = async (action: string, payload: Record<string, unknown> = {}) => {
    const bypassWhileRunning = new Set([
      'app.info',
      'dashboard.open_logs',
      'tools.open_logs',
      'updates.load_settings',
      'updates.launch_installer',
      'ping.favorites',
      'ping.add_favorite',
      'ping.delete_favorite',
      'dashboard.ping',
    ]);
    if (activeActionRef.current && !bypassWhileRunning.has(action)) {
      const current = activeActionRef.current;
      const message = `Ya hay una tarea en ejecución: ${current}. Cancela la tarea desde la consola o espera a que termine antes de ejecutar otra función.`;
      setNotification({ title: 'Tarea en ejecución', message, level: 'warning' });
      setLogs(prev => [...prev, `[SYSTEM] [AVISO] ${message}`]);
      if (activeTab !== 'deployment_console') {
        setActiveTab('deployment_console');
      }
      return { accepted: false, busy: true, currentAction: current };
    }

    const confirmRequired = new Set([
      'ad.dc1',
      'ad.dc2',
      'ad.join_domain',
      'ad.create_users',
      'ad.repadmin',
      'ad.d2d4',
      'kms.run',
      'system.kms',
      'sql.install_2022',
      'system.sql',
      'jchat.openfire',
      'jchat.cli',
      'system.jchat',
      'system.jchat_cli',
      'sharepoint.install',
      'sharepoint.roles',
      'tools.gpo_force',
      'exchange.prereqs',
      'exchange.prepare_schema',
      'exchange.install',
      'exchange.recover_server',
      'exchange.create_users',
      'skype.prereqs',
      'skype.install',
      'skype.permissions',
      'skype.dns',
      'programs.netfx35',
      'programs.firefox',
      'programs.winrar',
      'programs.adobe_reader',
      'programs.office_skype',
      'programs.install_all',
      'security.firewall_disable',
      'security.firewall_enable',
      'networks.switch_allied',
      'networks.switch_cisco',
      'networks.router',
    ]);
    if (confirmRequired.has(action) && payload.dryRun !== true) {
      const proceed = window.confirm(`Easy Deploy va a ejecutar una acción real:

${action}

La salida se mostrará en la consola o se pedirán datos mediante una ventana. ¿Quieres continuar`);
      if (!proceed) {
        setLogs(prev => [...prev, `[CLIENT] [AVISO] Acción cancelada por el usuario: ${action}`]);
        return { cancelled: true };
      }
    }

    const stayOnPage = payload.stayOnPage === true;
    const noConsoleActions = new Set([
      'app.info',
      'dashboard.check_admin',
      'dashboard.check_resources',
      'dashboard.open_logs',
      'dashboard.keyboard_es',
      'tools.open_logs',
      'tools.open_resources',
      'tools.versions',
      'tools.credits',
      'updates.load_settings',
      'updates.save_endpoint',
      'updates.check',
      'updates.download',
      'updates.launch_installer',
      'activation.status',
      'activation.activate',
      'activation.trial_status',
      'ping.favorites',
      'ping.add_favorite',
      'ping.delete_favorite',
      'dashboard.ping',
    ]);
    const nonBlockingActions = new Set([
      'app.info',
      'dashboard.open_logs',
      'tools.open_logs',
      'updates.load_settings',
      'ping.favorites',
      'ping.add_favorite',
      'ping.delete_favorite',
      'dashboard.ping',
    ]);
    const shouldOpenConsole = !stayOnPage && !noConsoleActions.has(action) && !action.startsWith('updates.') && !action.startsWith('activation.');
    const header = [
      `Easy Deploy Orchestrator [v${displayedVersion}]`,
      `Nueva tarea: ${action}`,
      `Inicio: ${new Date().toLocaleString()}`,
      '',
      `[CLIENT] Ejecutando acción real: ${action}`,
    ];

    setBackendProgress(0);
    if (!nonBlockingActions.has(action)) {
      setCurrentAction(action);
    }
    if (shouldOpenConsole) {
      setLogs(header);
      setActiveTab('deployment_console');
    } else {
      setLogs(prev => [...prev, `[CLIENT] Ejecutando acción real: ${action}`]);
    }
    try {
      const result = await backendClient.runAction(action, payload);
      if (result && typeof result === 'object' && (result as any).accepted === false) {
        if (activeActionRef.current === action) setCurrentAction(null);
      }
      return result;
    } catch (error) {
      if (activeActionRef.current === action) setCurrentAction(null);
      throw error;
    }
  };

  const handleAppendMultipleLogs = (lines: string[]) => {
    setLogs(prev => [...prev, ...lines]);
  };

  const handleClearConsole = () => {
    setLogs([]);
  };

  const handleCancelCurrentTask = async () => {
    const current = activeActionRef.current;
    if (!current && !pendingPrompt) {
      setNotification({
        title: 'Sin tarea activa',
        message: 'No hay ninguna acción en ejecución que cancelar.',
        level: 'info',
      });
      return;
    }

    if (current && nonCancelableActions.has(current)) {
      const message = `La tarea ${current} no se puede cancelar de forma segura porque instala roles, características o componentes críticos de Windows. Espera a que termine para no dejar el servidor en un estado intermedio.`;
      setNotification({ title: 'Tarea no cancelable', message, level: 'warning' });
      handleAppendLog('SYSTEM', 'warning', message);
      return;
    }

    if (pendingPrompt.prompt_id) {
      backendClient.respondPrompt(String(pendingPrompt.prompt_id), null);
      setPendingPrompt(null);
      setPromptValue('');
    }
    handleAppendLog('SYSTEM', 'warning', `Cancelación solicitada${current ? ` para: ${current}` : ''}.`);
    try {
      await backendClient.cancelAction();
    } finally {
      setCurrentAction(null);
      setBackendProgress(0);
    }
  };

  // Custom CLI Parser
  const handleExecuteCommand = (cmd: string) => {
    const sanitized = cmd.toLowerCase().trim();
    const timestamp = new Date().toTimeString().split(' ')[0];
    
    if (consoleInput.enabled) {
      const visible = consoleInput.sensitive ? '[oculto]' : cmd;
      setLogs(prev => [...prev, `> ${visible}`]);
      backendClient.sendConsoleInput(cmd);
      return;
    }

    setLogs(prev => [...prev, `> C:\\Deploy> ${cmd}`]);

    if (sanitized === 'help' || sanitized === '') {
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
      className={`flex h-screen w-screen font-sans overflow-hidden antialiased theme-${theme}`}
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
            <span className="text-[10px] font-bold font-mono tracking-widest uppercase" style={{ color: 'var(--theme-text-secondary)' }}>
              Panel de administración
            </span>
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
              onSetTab={setActiveTab}
            />
          )}

          {activeTab === 'ad_users_form' && (
            <UserCreationFormView
              mode="ad"
              onBack={() => setActiveTab('ad')}
              onRunAction={runBackendAction}
              onAppendLog={handleAppendLog}
            />
          )}

          {activeTab === 'kms' && (
            <ServiceActionView
              eyebrow="Activación Windows"
              title="KMS"
              subtitle="Conversión Evaluation y activación KMS reutilizando el motor clásico de Easy Deploy."
              actions={[{ id: 'kms_run', title: 'KMS', desc: 'Configura el servidor KMS, valida claves y lanza la activación con prompts seguros.', badge: 'KMS', action: 'kms.run' }]}
              onAppendLog={handleAppendLog}
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'exchange' && (
            <ExchangeView 
              onAppendLogs={handleAppendMultipleLogs} 
              onRunAction={runBackendAction}
              onSetTab={setActiveTab}
            />
          )}

          {activeTab === 'exchange_users_form' && (
            <UserCreationFormView
              mode="exchange"
              onBack={() => setActiveTab('exchange')}
              onRunAction={runBackendAction}
              onAppendLog={handleAppendLog}
            />
          )}

          {activeTab === 'sharepoint' && (
            <ServiceActionView
              eyebrow="Servidor Microsoft"
              title="SharePoint"
              subtitle="Instalación de prerrequisitos y SharePoint desde recursos offline."
              actions={[{ id: 'sharepoint_install', title: 'SharePoint', desc: 'Ejecuta la instalación de SharePoint con las validaciones del Easy Deploy clásico.', badge: 'SHAREPOINT', action: 'sharepoint.install' }]}
              onAppendLog={handleAppendLog}
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'sql' && (
            <ServiceActionView
              eyebrow="Base de datos"
              title="SQL"
              subtitle="Instalación de SQL Server desde recursos offline."
              actions={[{ id: 'sql_2022', title: 'SQL Server 2022', desc: 'Lanza la instalación de SQL Server 2022/SQL desde el paquete configurado.', badge: 'SQL', action: 'sql.install_2022' }]}
              onAppendLog={handleAppendLog}
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'skype' && (
            <SkypeView 
              onAppendLogs={handleAppendMultipleLogs} 
              onRunAction={runBackendAction}
            />
          )}

          {activeTab === 'jchat' && (
            <ServiceActionView
              eyebrow="Mensajería interna"
              title="JCHAT"
              subtitle="Instalación de Openfire/JCHAT CLI reutilizando recursos offline."
              actions={[
                { id: 'jchat_openfire', title: 'Jchat/Openfire', desc: 'Instala Java y Openfire como en Easy Deploy clásico.', badge: 'OPENFIRE', action: 'jchat.openfire' },
                { id: 'jchat_cli', title: 'Jchat CLI', desc: 'Instala el cliente JCHAT CLI desde el MSI offline.', badge: 'CLI', action: 'jchat.cli' },
              ]}
              onAppendLog={handleAppendLog}
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
                downloadData={(backendData['updates.downloaded'] || backendData['updates.download']) as Record<string, unknown> | undefined}
                backendProgress={backendProgress}
                appVersion={displayedVersion}
                onQuitApp={() => backendClient.quitApp()}
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
              activeAction={activeAction}
              onCancelTask={handleCancelCurrentTask}
              onOpenLogs={() => runBackendAction('dashboard.open_logs', { stayOnPage: true })}
              consoleInputEnabled={consoleInput.enabled}
              consoleInputPlaceholder={consoleInput.placeholder}
              consoleInputSensitive={consoleInput.sensitive}
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

      {pendingPrompt && (
        <div
          className="fixed inset-0 z-[999] flex items-center justify-center bg-black/60 px-4"
          onMouseDown={() => promptInputRef.current.focus({ preventScroll: true })}
        >
          <div className="w-full max-w-lg rounded-2xl border p-5 shadow-2xl" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)', color: 'var(--theme-text-primary)' }}>
            <h3 className="text-base font-bold mb-2">{String(pendingPrompt.title || 'Easy Deploy')}</h3>
            <p className="text-sm whitespace-pre-wrap mb-4" style={{ color: 'var(--theme-text-secondary)' }}>{String(pendingPrompt.message || '')}</p>
            {pendingPrompt.kind === 'confirm' ? (
              <div className="flex justify-end gap-2">
                {(pendingPrompt.buttons && pendingPrompt.buttons.length ? pendingPrompt.buttons : [{ text: 'No', value: false }, { text: 'Sí', value: true }]).map((button: any, index: number) => (
                  <button key={index} onClick={() => finishPrompt(button.value)} className="px-4 py-2 rounded-lg border text-sm font-bold" style={{ backgroundColor: button.value ? 'var(--theme-accent-primary)' : 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: button.value ? '#fff' : 'var(--theme-text-primary)' }}>
                    {String(button.text || button.value)}
                  </button>
                ))}
              </div>
            ) : (
              <form
                onSubmit={(event) => { event.preventDefault(); finishPrompt(promptValue); }}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') {
                    event.preventDefault();
                    finishPrompt(null);
                  }
                }}
                className="space-y-4"
              >
                <input
                  ref={promptInputRef}
                  autoFocus
                  type={pendingPrompt.is_password ? 'password' : 'text'}
                  inputMode="text"
                  autoComplete="off"
                  spellCheck={false}
                  value={promptValue}
                  onMouseDown={(event) => {
                    event.stopPropagation();
                    event.currentTarget.focus();
                  }}
                  onPointerDown={(event) => {
                    event.stopPropagation();
                    event.currentTarget.focus();
                  }}
                  onFocus={(event) => event.currentTarget.select()}
                  onChange={(event) => setPromptValue(event.target.value)}
                  className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm select-text focus:outline-none focus:ring-2"
                  style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)', userSelect: 'text', WebkitUserSelect: 'text', caretColor: 'var(--theme-accent-primary)' }}
                />
                <div className="flex justify-end gap-2">
                  <button type="button" onClick={() => finishPrompt(null)} className="px-4 py-2 rounded-lg border text-sm font-bold" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}>Cancelar</button>
                  <button type="submit" className="px-4 py-2 rounded-lg text-sm font-bold" style={{ backgroundColor: 'var(--theme-accent-primary)', color: '#fff' }}>Aceptar</button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {notification && (
        <div className="fixed inset-0 z-[998] flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-xl rounded-2xl border p-5 shadow-2xl" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)', color: 'var(--theme-text-primary)' }}>
            <h3 className="text-base font-bold mb-2">{notification.title}</h3>
            <pre className="text-sm whitespace-pre-wrap font-sans max-h-[420px] overflow-auto" style={{ color: 'var(--theme-text-secondary)' }}>{notification.message}</pre>
            <div className="flex justify-end mt-5">
              <button onClick={() => setNotification(null)} className="px-4 py-2 rounded-lg text-sm font-bold" style={{ backgroundColor: 'var(--theme-accent-primary)', color: '#fff' }}>Aceptar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
