import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Shield
} from 'lucide-react';

interface SecurityViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  firewallState?: 'enabled' | 'disabled' | 'unknown';
}

export default function SecurityView({ onAppendLog, onRunAction, firewallState = 'unknown' }: SecurityViewProps) {
  const firewallOn = firewallState === 'enabled';
  const firewallUnknown = firewallState === 'unknown';

  const [firewallRules, setFirewallRules] = useState([
    { id: 'r1', name: 'Permitir Active Directory LDAP Sockets', port: '389, 636', protocol: 'TCP', direction: 'Inbound', action: 'Permitir', active: true },
    { id: 'r2', name: 'Bloquear Puertos Legados NetBIOS', port: '137, 138, 139', protocol: 'UDP', direction: 'Inbound', action: 'Bloquear', active: true },
    { id: 'r3', name: 'Forzar Encriptación Estricta SMB v3', port: '445', protocol: 'TCP', direction: 'Inbound', action: 'Permitir', active: true },
    { id: 'r4', name: 'Deshabilitar Logins RDP Sin Certificado', port: '3389', protocol: 'TCP', direction: 'Inbound', action: 'Bloquear', active: false },
    { id: 'r5', name: 'Permitir Puertos SMTP Exchange Hub', port: '25, 465, 587', protocol: 'TCP', direction: 'Inbound', action: 'Permitir', active: true },
    { id: 'r6', name: 'Permitir Skype VoIP Signaling (TLS)', port: '5061', protocol: 'TCP', direction: 'Inbound', action: 'Permitir', active: true },
  ]);

  const [aclLogs, setAclLogs] = useState([
    { time: '16:04:12', ip: '192.168.1.45', port: '445 (SMB)', status: 'ALLOW', desc: 'Validación de firma SMBv3 exitosa' },
    { time: '16:04:15', ip: '10.0.12.18', port: '139 (NetBIOS)', status: 'DENIED', desc: 'Bloqueado por Regla Legada Habilitada' },
    { time: '16:04:22', ip: '192.168.1.10', port: '25 (SMTP)', status: 'ALLOW', desc: 'Flujo entrante de Exchange Server' },
    { time: '16:04:31', ip: '192.168.1.99', port: '3389 (RDP)', status: 'DENIED', desc: 'Intento de login sin certificado TLS de cliente' },
  ]);

  // Periodic simulated ACL packets filter logs
  useEffect(() => {
    const addresses = ['192.168.1.10', '192.168.1.72', '10.0.12.5', '192.168.1.45'];
    const ports = ['389 (LDAP)', '445 (SMB3)', '5061 (SIP)', '3389 (RDP)'];
    
    const interval = setInterval(() => {
      const randomIp = addresses[Math.floor(Math.random() * addresses.length)];
      const randomPort = ports[Math.floor(Math.random() * ports.length)];
      const isAllowed = Math.random() > 0.3;
      
      const newLog = {
        time: new Date().toTimeString().split(' ')[0],
        ip: randomIp,
        port: randomPort,
        status: isAllowed ? 'ALLOW' : 'DENIED',
        desc: isAllowed ? 'Acceso canal autenticado aprobado' : 'Intento bloqueado por el administrador local'
      };

      setAclLogs(prev => [newLog, ...prev.slice(0, 10)]);
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    onAppendLog('SECURITY', 'info', `Cargando directivas de red local en tiempo real.`);
    onRunAction('security.firewall_status', { stayOnPage: true });
  }, []);

  // Firewall Toggles
  const handleToggleRule = (id: string, name: string) => {
    setFirewallRules(prev => prev.map(r => {
      if (r.id === id) {
        const nextState = !r.active;
        onAppendLog('FIREWALL', 'info', `Directiva de Firewall: Regla "${name}" configurada como [${nextState ? 'Habilitada' : 'Deshabilitada'}].`);
        return { ...r, active: nextState };
      }
      return r;
    }));
  };

  return (
    <div className="space-y-6">
      {/* Visual Navigation Bar */}
      <div 
        className="backdrop-blur-md p-5 rounded-2xl border"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)'
        }}
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Shield size={16} style={{ color: 'var(--theme-accent-primary)' }} />
              <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>NÚCLEO DE PROTECCIÓN Y CONTROL</span>
            </div>
            <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Cortafuegos de Red Local</h2>
            <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
              Configure directivas locales, supervise el filtrado asíncrono e interactúe con los puertos y sockets de los servidores locales vinculados.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Stats Widgets */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Core firewall switch */}
          <div className="p-4 rounded-xl border flex items-center justify-between" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}>
            <div>
              <span className="text-[10px] font-bold block font-mono" style={{ color: 'var(--theme-text-secondary)' }}>ESTADO DEL FIREWALL</span>
              <span className="text-base font-bold" style={{ color: firewallOn ? '#10b981' : '#ef4444' }}>
                {firewallUnknown ? 'Estado pendiente' : firewallOn ? 'Cortafuegos Activo' : 'CORTAFUEGOS APAGADO'}
              </span>
              <p className="text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>Reglas de Directiva Local</p>
            </div>
            <button
              onClick={() => {
                onAppendLog('FIREWALL', firewallOn ? 'warning' : 'success', `Se ha modificado el estado general del Firewall a: [${!firewallOn ? 'ENCENDIDO' : 'APAGADO'}].`);
                onRunAction(firewallOn ? 'security.firewall_disable' : 'security.firewall_enable', { stayOnPage: true });
              }}
              className="w-11 h-6 rounded-full p-0.5 transition-colors cursor-pointer border"
              style={{
                backgroundColor: firewallOn ? 'var(--theme-accent-primary)' : 'var(--theme-bg-well)',
                borderColor: 'var(--theme-border-well)'
              }}
            >
              <div className={`bg-white w-5 h-5 rounded-full shadow-md transform transition-transform ${firewallOn ? 'translate-x-5' : 'translate-x-0'}`} />
            </button>
          </div>

          {/* Environment integrity badge */}
          <div className="p-4 rounded-xl border flex items-center justify-between" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}>
            <div>
              <span className="text-[10px] text-slate-500 font-bold block font-mono">INTEGRIDAD DEL ENTORNO</span>
              <span className="text-base font-bold font-mono" style={{ color: 'var(--theme-text-primary)' }}>Validaciones y Firmas Activas</span>
              <p className="text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>Seguridad de puertos auditada sin alertas</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-emerald-950 flex items-center justify-center text-emerald-400">
              <ShieldCheck size={18} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Rules table list */}
          <div className="lg:col-span-8 p-5 border rounded-2xl" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}>
            <div className="flex items-center justify-between border-b pb-3 mb-4" style={{ borderColor: 'var(--theme-border-well)' }}>
              <h4 className="text-xs font-black tracking-widest uppercase font-mono" style={{ color: 'var(--theme-text-primary)' }}>Política de Cortafuegos y Reglas de Puerto</h4>
              <ShieldCheck size={16} style={{ color: 'var(--theme-accent-primary)' }} />
            </div>

            <div className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
              {firewallRules.map((rule) => {
                let alertAction = rule.action === 'Permitir';
                return (
                  <div 
                    key={rule.id} 
                    className="p-3.5 rounded-xl border flex items-center justify-between gap-3" 
                    style={{ 
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'var(--theme-border-well)' 
                    }}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span 
                          className="text-[8px] font-black font-mono px-1.5 py-0.5 rounded-sm border"
                          style={alertAction ? {
                            backgroundColor: 'rgba(16, 185, 129, 0.12)',
                            color: '#10b981',
                            borderColor: 'rgba(16, 185, 129, 0.25)'
                          } : {
                            backgroundColor: 'rgba(239, 68, 68, 0.12)',
                            color: '#ef4444',
                            borderColor: 'rgba(239, 68, 68, 0.25)'
                          }}
                        >
                          {rule.action.toUpperCase()}
                        </span>
                        <span className="text-[10px] font-mono font-medium" style={{ color: 'var(--theme-text-secondary)' }}>
                          {rule.direction} | Protocolo: {rule.protocol}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold truncate" style={{ color: 'var(--theme-text-primary)' }}>{rule.name}</h4>
                      <p className="text-[10px] font-mono mt-0.5" style={{ color: 'var(--theme-text-secondary)' }}>Rangos de Sockets: {rule.port}</p>
                    </div>

                    <div className="shrink-0 flex items-center">
                      <button
                        onClick={() => handleToggleRule(rule.id, rule.name)}
                        className="w-9 h-5 rounded-full p-0.5 transition-colors cursor-pointer border"
                        style={{
                          backgroundColor: rule.active ? 'var(--theme-accent-primary)' : 'var(--theme-bg-well)',
                          borderColor: 'var(--theme-border-well)'
                        }}
                      >
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${rule.active ? 'translate-x-4' : 'translate-x-0'}`} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Audit Logs side details */}
          <div className="lg:col-span-4 p-5 border rounded-2xl space-y-4" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}>
            <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--theme-border-well)' }}>
              <span className="text-xs font-bold uppercase font-mono" style={{ color: 'var(--theme-text-primary)' }}>Filtros Preventivos ACL</span>
              <span className="text-[9px] bg-indigo-500/10 px-1.5 py-0.5 rounded text-indigo-400 font-mono font-bold">En vivo</span>
            </div>

            <div className="space-y-3.5 max-h-[350px] overflow-y-auto">
              {aclLogs.map((log, idx) => {
                let isDenied = log.status === 'DENIED';
                return (
                  <div 
                    key={idx} 
                    className="p-3 rounded-lg border text-[10px] font-mono space-y-1.5" 
                    style={{ 
                      backgroundColor: 'var(--theme-bg-well)',
                      borderColor: 'var(--theme-border-well)' 
                    }}
                  >
                    <div className="flex justify-between items-center p-1 rounded" style={{ backgroundColor: 'rgba(0,0,0,0.05)' }}>
                      <span className="font-sans font-semibold" style={{ color: 'var(--theme-text-secondary)' }}>{log.time}</span>
                      <span 
                        className="text-[8px] font-black px-1 py-0.2 rounded border shrink-0" 
                        style={isDenied ? {
                          backgroundColor: 'rgba(239, 68, 68, 0.12)',
                          color: '#ef4444',
                          borderColor: 'rgba(239, 68, 68, 0.25)'
                        } : {
                          backgroundColor: 'rgba(16, 185, 129, 0.12)',
                          color: '#10b981',
                          borderColor: 'rgba(16, 185, 129, 0.25)'
                        }}
                      >
                        {log.status}
                      </span>
                    </div>
                    <div>
                      <span className="font-bold" style={{ color: 'var(--theme-text-primary)' }}>IP: {log.ip}</span>
                      <span className="block" style={{ color: 'var(--theme-text-secondary)' }}>Puerto destino: {log.port}</span>
                      <span className="block mt-1 italic text-[9px]" style={{ color: 'var(--theme-text-secondary)', opacity: 0.85 }}>{log.desc}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
