export type ActiveTab =
  | 'dashboard'
  | 'ad'
  | 'exchange'
  | 'skype'
  | 'offline_installers'
  | 'updates'
  | 'security'
  | 'guides'
  | 'tools'
  | 'configuration'
  | 'deployment_console'
  | 'networks'
  | 'ping'
  | 'versions'
  | 'credits';

export interface WindowsRegistry {
  Estado_Licencia: 'TRIAL' | 'ACTIVADO' | 'EXPIRADO' | 'BLOQUEADO';
  Fecha_Primera_Ejecucion: string;
  Fecha_Ultima_Ejecucion: string;
  Fecha_Expiracion: string;
  Build_Hash: string;
  Bloqueo_Flag: number;
  Dias_Transcurridos: number;
  Activado_Una_Vez: boolean;
}

export interface SystemLog {
  id: string;
  timestamp: string;
  source: 'SYSTEM' | 'AD' | 'EXCHANGE' | 'SKYPE' | 'NETWORK' | 'INSTALLER' | 'FIREWALL' | 'UPDATES';
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

export interface NetworkAdapter {
  id: string;
  name: string;
  interface: string;
  status: 'connected' | 'disconnected';
  ip: string;
  subnet: string;
  gateway: string;
  dns1: string;
  dns2: string;
  mac: string;
  speed: string;
}

export interface HardDrive {
  letter: string;
  label: string;
  icon: string;
  totalSize: number; // in GB
  usedSize: number; // in GB
  type: 'local' | 'network';
}

export interface ProcessItem {
  id: number;
  name: string;
  cpu: number; // in %
  ram: number; // in MB
  user: string;
  status: 'Running' | 'Suspended' | 'Idle';
}

export interface OfflineApp {
  id: string;
  name: string;
  version: string;
  category: string;
  size: string;
  installed: boolean;
  status: 'idle' | 'preparing' | 'installing' | 'completed' | 'error';
  progress: number;
}

export interface UpdatePatch {
  id: string;
  kbName: string;
  title: string;
  size: string;
  releaseDate: string;
  category: 'Seguridad' | 'Características' | 'Prerrequisito' | 'Controlador';
  installed: boolean;
  progress: number;
  status: 'pending' | 'downloading' | 'installing' | 'completed';
}

export interface FirewallRule {
  id: string;
  name: string;
  port: string;
  protocol: 'TCP' | 'UDP' | 'ICMP' | 'Cualquiera';
  direction: 'Inbound' | 'Outbound';
  action: 'Permitir' | 'Bloquear';
  active: boolean;
}

export interface GuideArticle {
  id: string;
  title: string;
  category: 'Instalación' | 'Configuración' | 'Resolución de Problemas' | 'Notas de Versión';
  readTime: string;
  tags: string[];
  content: string;
}
