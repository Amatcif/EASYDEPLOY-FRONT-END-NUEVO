import React, { useState } from 'react';
import { 
  Network, 
  ExternalLink, 
  Terminal, 
  Router as RouterIcon, 
  Lock, 
  Map, 
  Sliders, 
  ChevronRight,
  Info
} from 'lucide-react';

interface NetworkCard {
  id: string;
  code: string;
  name: string;
  description: string;
  locked: boolean;
  icon: React.ComponentType<any>;
  details?: string[];
}

interface NetworksViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
}

const networkActionMap: Record<string, string> = {
  at: 'networks.switch_allied',
  cs: 'networks.switch_cisco',
  rt: 'networks.router',
  asa: 'networks.asa',
  cp: 'networks.checkpoint',
  topo: 'networks.topology',
  ip: 'networks.ip_addressing',
};

export default function NetworksView({ onAppendLog, onRunAction }: NetworksViewProps) {
  const [selectedCardId, setSelectedCardId] = useState<string | null>('at');

  const cards: NetworkCard[] = [
    {
      id: 'at',
      code: 'AT',
      name: 'Switch Allied',
      description: 'Gestión local mediante consola de detección AlliedWare Plus y secuencias de comandos Allied Telesis.',
      locked: false,
      icon: ExternalLink,
      details: [
        'Versión actual: AlliedWare Plus v5.5.2',
        'Administración segura por puerto de consola o interfaz web.',
        'Características: Soporte de apilado VCStack, VLAN avanzada, enrutamiento estático y DHCP Snooping.'
      ]
    },
    {
      id: 'cs',
      code: 'CS',
      name: 'Switch Cisco',
      description: 'Gestión local interactiva integrada mediante IOS de Cisco y comandos del firmware oficial.',
      locked: false,
      icon: Terminal,
      details: [
        'Versión actual: Cisco IOS Software C2960 Base',
        'Configuraciones soportadas: Creación de VLANs, puertos de acceso, puertos trunk y seguridad de puerto (Port Security).',
        'Modo privilegios mediante clave habilitada de terminal.'
      ]
    },
    {
      id: 'rt',
      code: 'RT',
      name: 'Router',
      description: 'Enrutador multiproveedor para interconexión de redes, subredes e implementación de gateways corporativos.',
      locked: false,
      icon: RouterIcon,
      details: [
        'Versión actual: Edge-vRouter v10.4-LTS',
        'Protocolos pre-cargados: OSPF v2, BGP de frontera y enrutamiento directo.',
        'Soporte completo para traducción de direcciones NAT y reglas avanzadas de reenvío de puertos.'
      ]
    },
    {
      id: 'asa',
      code: 'ASA',
      name: 'Asa',
      description: 'Acceso reservado para futuras tareas de seguridad y políticas de firewall Cisco ASA.',
      locked: true,
      icon: Lock
    },
    {
      id: 'cp',
      code: 'CP',
      name: 'Checkpoint',
      description: 'Acceso reservado para futuras tareas administrativas y políticas del gateway Check Point.',
      locked: true,
      icon: Lock
    },
    {
      id: 'topo',
      code: 'TOPO',
      name: 'Generación de topologías de red',
      description: 'Acceso reservado para generar dinámicamente mapas de red y topologías visuales del entorno local.',
      locked: true,
      icon: Map
    },
    {
      id: 'ip',
      code: 'IP',
      name: 'Gestión de direccionamiento',
      description: 'Acceso reservado para la administración integrada de direccionamiento IP, subredes y rangos (IPAM).',
      locked: true,
      icon: Sliders
    }
  ];

  const handleCardClick = (card: NetworkCard) => {
    setSelectedCardId(card.id);
    const action = networkActionMap[card.id];
    if (!action) {
      onAppendLog('NETWORK', 'warning', `No hay acción backend asignada para ${card.name}.`);
      return;
    }
    onAppendLog('NETWORK', card.locked ? 'warning' : 'info', `${card.name}: enviando acción al backend (${action}).`);
    onRunAction(action, { locked: card.locked, label: card.name }).catch((error) => {
      onAppendLog('NETWORK', 'error', `No se pudo ejecutar ${card.name}: ${String(error)}`);
    });
  };

  const selectedCard = cards.find(c => c.id === selectedCardId);

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div 
        className="backdrop-blur-md p-5 rounded-2xl border"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)'
        }}
      >
        <div className="flex items-center gap-3 mb-1">
          <div className="w-2.5 h-6 bg-emerald-500 rounded-sm" />
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Redes</h2>
        </div>
        <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
          Administra y consulta las características de los adaptadores de red, switches y enlaces del sistema corporativo.
        </p>
      </div>

      {/* Main Grid: Allied/Cisco/Router Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards.map((card) => {
          const CardIcon = card.icon;
          const isActive = selectedCardId === card.id && !card.locked;
          
          if (card.locked) {
            return (
              <div 
                key={card.id} 
                className="border p-5 rounded-2xl relative overflow-hidden select-none opacity-50"
                style={{
                  backgroundColor: 'var(--theme-bg-app)',
                  borderColor: 'var(--theme-border-well)'
                }}
              >
                <div className="absolute top-0 left-0 bottom-0 w-1 bg-gradient-to-b from-slate-700 to-slate-800 opacity-30" />
                <div className="flex justify-between items-start mb-3">
                  <span className="text-xs font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }}>{card.code}</span>
                  <Lock size={14} style={{ color: 'var(--theme-text-secondary)' }} />
                </div>
                <h4 className="text-sm font-semibold font-sans mb-1.5" style={{ color: 'var(--theme-text-primary)' }}>{card.name}</h4>
                <p className="text-[11px] leading-normal" style={{ color: 'var(--theme-text-secondary)' }}>{card.description}</p>
              </div>
            );
          }

          return (
            <div 
              key={card.id}
              onClick={() => handleCardClick(card)}
              className="relative border rounded-2xl p-5 cursor-pointer transition-all duration-300 flex flex-col justify-between hover:translate-y-[-2px] group"
              style={{
                backgroundColor: isActive ? 'var(--theme-indigo-950)' : 'var(--theme-bg-card)',
                borderColor: isActive ? 'var(--theme-accent-primary)' : 'var(--theme-border-card)',
                boxShadow: isActive ? '0 4px 12px var(--theme-accent-primary)15' : 'none'
              }}
            >
              {isActive && (
                <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-2xl" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
              )}
              <div>
                <div className="flex justify-between items-start mb-3">
                  <span 
                    className="text-xs font-black font-mono px-2 py-0.5 rounded border"
                    style={{
                      backgroundColor: 'var(--theme-bg-app)',
                      borderColor: isActive ? 'var(--theme-accent-primary)' : 'var(--theme-border-well)',
                      color: isActive ? 'var(--theme-accent-primary)' : 'var(--theme-text-secondary)'
                    }}
                  >
                    {card.code}
                  </span>
                  <CardIcon size={14} className="transition-colors" style={{
                    color: isActive ? 'var(--theme-accent-primary)' : 'var(--theme-text-secondary)'
                  }} />
                </div>
                <h4 className="text-sm font-bold font-sans mb-1.5 transition-colors" style={{
                  color: isActive ? 'var(--theme-accent-primary)' : 'var(--theme-text-primary)'
                }}>{card.name}</h4>
                <p className="text-[11px] leading-normal mb-4" style={{ color: 'var(--theme-text-secondary)' }}>{card.description}</p>
              </div>
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider mt-auto select-none" style={{ color: 'var(--theme-accent-primary)' }}>
                <span>Abrir consola</span>
                <ChevronRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}
