import React, { useState } from 'react';
import { Sliders, Save, CheckCircle2, RefreshCw, Network, HelpCircle, Info } from 'lucide-react';

interface ConfigViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
}

export default function ConfigView({ onAppendLog }: ConfigViewProps) {
  const [saving, setSaving] = useState(false);
  
  // Settings values
  const [hostName, setHostName] = useState('EasyDeploy-Host');
  const [gateway, setGateway] = useState('192.168.1.1');
  const [dns1, setDns1] = useState('192.168.1.10');
  const [dns2, setDns2] = useState('8.8.8.8');
  const [lang, setLang] = useState('es-ES');
  const [timezone, setTimezone] = useState('GMT-5 Bogota/Lima');
  const [licenseKey, setLicenseKey] = useState('W269N-WFGWX-YVC9B-4J6C9-T83GX');

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    onAppendLog('SYSTEM', 'info', 'Preparando guardado de directivas de configuración local...');
    onAppendLog('NETWORK', 'info', `Aplicando cambios de interfaz: Gateway=${gateway}, DNS1=${dns1}. Reiniciando sockets...`);

    setTimeout(() => {
      onAppendLog('SYSTEM', 'success', '[✓] Ajustes de entorno persistidos y aplicados con éxito en el host local.');
      setSaving(false);
    }, 1200);
  };

  const adapters = [
    { name: 'Ethernet 1 (Intel Gigabit)', status: 'connected', ip: '192.168.1.10', mac: '00:15:5D:01:14:0A', speed: '1 Gbps' },
    { name: 'Ethernet 2 (vSwitch Interno)', status: 'connected', ip: '192.168.137.1', mac: '00:15:5D:01:14:0F', speed: '10 Gbps' },
    { name: 'WAN Connection (Realtek PCIe)', status: 'disconnected', ip: 'Sin asignar', mac: '00:15:5D:01:14:1C', speed: '0 Mbps' },
  ];

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
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>PARÁMETROS DEL HOST</span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>Ajustes del Entorno y Adaptadores</h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Personaliza la identidad del servidor de orquestación, mapeo de proxies locales, e interfaces de comunicación ethernet</p>
        </div>
      </div>

      {/* Settings Form split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core parameters form */}
        <form 
          onSubmit={handleSaveSettings} 
          className="lg:col-span-2 border rounded-xl p-5 space-y-4"
          style={{
            backgroundColor: 'var(--theme-bg-card)',
            borderColor: 'var(--theme-border-card)'
          }}
        >
          <h3 className="text-xs font-bold font-mono uppercase tracking-widest border-b pb-2 mb-2 flex items-center gap-2" style={{ color: 'var(--theme-text-primary)', borderColor: 'var(--theme-border-well)' }}>
            <Sliders size={14} style={{ color: 'var(--theme-accent-primary)' }} />
            <span>Preferencias y Parámetros del Entorno</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Hostname */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="host-name">Hostname de Servidor</label>
              <input
                type="text"
                id="host-name"
                value={hostName}
                onChange={(e) => setHostName(e.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-well)',
                  color: 'var(--theme-text-primary)'
                }}
              />
            </div>

            {/* License Key */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="license-key">Clave de Licencia Windows (KMS)</label>
              <input
                type="text"
                id="license-key"
                value={licenseKey}
                onChange={(e) => setLicenseKey(e.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-well)',
                  color: 'var(--theme-text-primary)'
                }}
              />
            </div>

            {/* Gateway */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="gateway-in">Puerta de Enlace (Gateway)</label>
              <input
                type="text"
                id="gateway-in"
                value={gateway}
                onChange={(e) => setGateway(e.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-well)',
                  color: 'var(--theme-text-primary)'
                }}
              />
            </div>

            {/* Language Selection */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="lang-select">Idioma de Despliegue</label>
              <select
                id="lang-select"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="w-full text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 cursor-pointer"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-well)',
                  color: 'var(--theme-text-primary)'
                }}
              >
                <option value="es-ES">Español (España) — es-ES</option>
                <option value="es-LA">Español (Latinoamérica) — es-LA</option>
                <option value="en-US">English (United States) — en-US</option>
              </select>
            </div>

            {/* Prim DNS */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="dns-1">DNS Primario (Active Directory)</label>
              <input
                type="text"
                id="dns-1"
                value={dns1}
                onChange={(e) => setDns1(e.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-well)',
                  color: 'var(--theme-text-primary)'
                }}
              />
            </div>

            {/* Sec DNS */}
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="dns-2">DNS Secundario (Forwarder WAN)</label>
              <input
                type="text"
                id="dns-2"
                value={dns2}
                onChange={(e) => setDns2(e.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{
                  backgroundColor: 'var(--theme-bg-well)',
                  borderColor: 'var(--theme-border-well)',
                  color: 'var(--theme-text-primary)'
                }}
              />
            </div>
          </div>

          <div className="border-t pt-4 flex justify-end" style={{ borderColor: 'var(--theme-border-well)' }}>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg text-xs font-bold text-white flex items-center gap-2 transition-all shadow-sm cursor-pointer"
              style={{ backgroundColor: 'var(--theme-accent-primary)' }}
            >
              {saving ? <RefreshCw size={12} className="animate-spin" /> : <Save size={12} />}
              <span>Guardar Configuración</span>
            </button>
          </div>
        </form>

        {/* Adapters active summary column */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold font-mono uppercase tracking-widest border-b pb-2" style={{ color: 'var(--theme-text-primary)', borderColor: 'var(--theme-border-well)' }}>
            ADAPTADORES DE RED DETECTADOS
          </h3>

          <div className="space-y-3">
            {adapters.map((adap, idx) => {
              const connected = adap.status === 'connected';
              return (
                <div 
                  key={idx} 
                  className="border rounded-xl p-4 space-y-1.5 transition-all"
                  style={{
                    backgroundColor: 'var(--theme-bg-card)',
                    borderColor: 'var(--theme-border-card)',
                    color: 'var(--theme-text-primary)'
                  }}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-bold font-sans truncate pr-2" title={adap.name} style={{ color: 'var(--theme-text-primary)' }}>{adap.name}</span>
                    <span 
                      className={`text-[9px] font-bold font-mono px-1.5 py-0.2 rounded border`}
                      style={connected ? {
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        color: '#10b981',
                        borderColor: 'rgba(16, 185, 129, 0.2)'
                      } : {
                        backgroundColor: 'var(--theme-bg-well)',
                        color: 'var(--theme-text-secondary)',
                        borderColor: 'var(--theme-border-well)',
                        opacity: 0.6
                      }}
                    >
                      {connected ? 'LINK UP' : 'CABLE DOWN'}
                    </span>
                  </div>
                  <div className="space-y-1 font-mono text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>
                    <div className="flex justify-between">
                      <span>IP Address:</span>
                      <span style={{ color: 'var(--theme-text-primary)' }}>{adap.ip}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>MAC Address:</span>
                      <span style={{ opacity: 0.8 }}>{adap.mac}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Velocidad:</span>
                      <span style={{ color: 'var(--theme-accent-primary)' }}>{adap.speed}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Info warnings */}
          <div 
            className="border rounded-xl p-3.5 flex gap-2"
            style={{
              backgroundColor: 'var(--theme-bg-well)',
              borderColor: 'var(--theme-border-well)'
            }}
          >
            <Info size={14} className="shrink-0 mt-0.5" style={{ color: 'var(--theme-accent-primary)' }} />
            <p className="text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>
              Las licencias de red se actualizan periódicamente contra el servidor KMS corporativo registrado en el Active Directory central.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
