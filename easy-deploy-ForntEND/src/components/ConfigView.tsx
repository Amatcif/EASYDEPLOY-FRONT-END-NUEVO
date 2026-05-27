import React, { useEffect, useMemo, useState } from 'react';
import { Info, RefreshCw, Save, Sliders } from 'lucide-react';

interface ConfigViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  adaptersData?: Record<string, unknown>;
}

interface NetworkAdapterInfo {
  id: string;
  name: string;
  status: string;
  ip: string;
  gateway: string;
  dns1: string;
  dns2: string;
  mac: string;
  speed: string;
}

export default function ConfigView({ onAppendLog, onRunAction, adaptersData }: ConfigViewProps) {
  const [saving, setSaving] = useState(false);
  const [selectedAdapterId, setSelectedAdapterId] = useState('');
  const [hostName, setHostName] = useState('');
  const [gateway, setGateway] = useState('');
  const [dns1, setDns1] = useState('');
  const [dns2, setDns2] = useState('');
  const [lang, setLang] = useState('es-ES');
  const [timezone, setTimezone] = useState('Europe/Madrid');
  const [licenseKey, setLicenseKey] = useState('');

  const adapters = useMemo<NetworkAdapterInfo[]>(() => {
    const raw = adaptersData?.adapters;
    if (!Array.isArray(raw)) return [];
    return raw.map((item: any, index) => ({
      id: String(item.id || item.name || index),
      name: String(item.name || `Adaptador ${index + 1}`),
      status: String(item.status || 'Unknown'),
      ip: String(item.ip || 'Sin asignar'),
      gateway: String(item.gateway || ''),
      dns1: String(item.dns1 || ''),
      dns2: String(item.dns2 || ''),
      mac: String(item.mac || ''),
      speed: String(item.speed || ''),
    }));
  }, [adaptersData]);

  useEffect(() => {
    onRunAction('config.network_adapters', { stayOnPage: true }).catch((error) => {
      onAppendLog('NETWORK', 'warning', `No se pudieron cargar adaptadores reales: ${String(error)}`);
    });
  }, []);

  useEffect(() => {
    if (!adapters.length) return;
    const selected = adapters.find((item) => item.id === selectedAdapterId) || adapters[0];
    setSelectedAdapterId(selected.id);
    setGateway(selected.gateway);
    setDns1(selected.dns1);
    setDns2(selected.dns2);
  }, [adapters]);

  const handleSelectAdapter = (id: string) => {
    const selected = adapters.find((item) => item.id === id);
    setSelectedAdapterId(id);
    if (!selected) return;
    setGateway(selected.gateway);
    setDns1(selected.dns1);
    setDns2(selected.dns2);
    onAppendLog('NETWORK', 'info', `Adaptador seleccionado: ${selected.name}`);
  };

  const handleSaveSettings = (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    onAppendLog('SYSTEM', 'info', 'Guardado visual de ajustes preparado. No se aplican cambios de red sin una acción explícita.');
    onAppendLog('NETWORK', 'info', `Adaptador=${selectedAdapterId || 'sin selección'} | Gateway=${gateway || 'sin dato'} | DNS1=${dns1 || 'sin dato'}.`);

    window.setTimeout(() => {
      onAppendLog('SYSTEM', 'success', '[OK] Ajustes de entorno guardados en la sesión visual.');
      setSaving(false);
    }, 800);
  };

  return (
    <div className="space-y-6">
      <div
        className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-xl border"
        style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)', color: 'var(--theme-text-primary)' }}
      >
        <div>
          <span className="text-[10px] font-bold font-mono tracking-wider uppercase" style={{ color: 'var(--theme-accent-primary)' }}>
            PARÁMETROS DEL HOST
          </span>
          <h2 className="text-xl font-bold font-sans uppercase tracking-tight" style={{ color: 'var(--theme-text-primary)' }}>
            Ajustes del Entorno y Adaptadores
          </h2>
          <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
            Consulta adaptadores reales del servidor y prepara valores de red sin aplicar cambios automáticos.
          </p>
        </div>
        <button
          type="button"
          className="px-4 py-2 rounded-lg text-xs font-bold cursor-pointer"
          style={{ backgroundColor: 'var(--theme-accent-primary)', color: '#fff' }}
          onClick={() => onRunAction('config.network_adapters', { stayOnPage: true })}
        >
          Actualizar adaptadores
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <form
          onSubmit={handleSaveSettings}
          className="lg:col-span-2 border rounded-xl p-5 space-y-4"
          style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}
        >
          <h3
            className="text-xs font-bold font-mono uppercase tracking-widest border-b pb-2 mb-2 flex items-center gap-2"
            style={{ color: 'var(--theme-text-primary)', borderColor: 'var(--theme-border-well)' }}
          >
            <Sliders size={14} style={{ color: 'var(--theme-accent-primary)' }} />
            <span>Preferencias y datos detectados</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="adapter-select">
                Adaptador real
              </label>
              <select
                id="adapter-select"
                value={selectedAdapterId}
                onChange={(event) => handleSelectAdapter(event.target.value)}
                className="w-full text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 cursor-pointer"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
              >
                {!adapters.length && <option value="">Sin adaptadores cargados</option>}
                {adapters.map((adapter) => (
                  <option key={adapter.id} value={adapter.id}>
                    {adapter.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="host-name">
                Hostname de servidor
              </label>
              <input
                type="text"
                id="host-name"
                value={hostName}
                onChange={(event) => setHostName(event.target.value)}
                placeholder="Detectado por el sistema si procede"
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="gateway-in">
                Puerta de enlace
              </label>
              <input
                type="text"
                id="gateway-in"
                value={gateway}
                onChange={(event) => setGateway(event.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="lang-select">
                Idioma de despliegue
              </label>
              <select
                id="lang-select"
                value={lang}
                onChange={(event) => setLang(event.target.value)}
                className="w-full text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 cursor-pointer"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
              >
                <option value="es-ES">Español (España) - es-ES</option>
                <option value="es-LA">Español (Latinoamérica) - es-LA</option>
                <option value="en-US">English (United States) - en-US</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="dns-1">
                DNS primario
              </label>
              <input
                type="text"
                id="dns-1"
                value={dns1}
                onChange={(event) => setDns1(event.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="dns-2">
                DNS secundario
              </label>
              <input
                type="text"
                id="dns-2"
                value={dns2}
                onChange={(event) => setDns2(event.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="timezone">
                Zona horaria
              </label>
              <input
                type="text"
                id="timezone"
                value={timezone}
                onChange={(event) => setTimezone(event.target.value)}
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold font-mono" style={{ color: 'var(--theme-text-secondary)' }} htmlFor="license-key">
                Clave Windows/KMS
              </label>
              <input
                type="text"
                id="license-key"
                value={licenseKey}
                onChange={(event) => setLicenseKey(event.target.value)}
                placeholder="Sin clave cargada"
                className="w-full font-mono text-xs border rounded px-3 py-2 outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
                style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}
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
              <span>Guardar configuración</span>
            </button>
          </div>
        </form>

        <div className="space-y-4">
          <h3 className="text-xs font-bold font-mono uppercase tracking-widest border-b pb-2" style={{ color: 'var(--theme-text-primary)', borderColor: 'var(--theme-border-well)' }}>
            Adaptadores reales detectados
          </h3>

          <div className="space-y-3">
            {!adapters.length && (
              <div className="border rounded-xl p-4 text-xs" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)', color: 'var(--theme-text-secondary)' }}>
                Todavía no hay adaptadores cargados. Pulsa "Actualizar adaptadores".
              </div>
            )}

            {adapters.map((adapter) => {
              const connected = adapter.status.toLowerCase().includes('up') || adapter.status.toLowerCase().includes('connected');
              return (
                <button
                  key={adapter.id}
                  type="button"
                  onClick={() => handleSelectAdapter(adapter.id)}
                  className="w-full text-left border rounded-xl p-4 space-y-1.5 transition-all cursor-pointer"
                  style={{
                    backgroundColor: selectedAdapterId === adapter.id ? 'var(--theme-bg-well)' : 'var(--theme-bg-card)',
                    borderColor: selectedAdapterId === adapter.id ? 'var(--theme-accent-primary)' : 'var(--theme-border-card)',
                    color: 'var(--theme-text-primary)',
                  }}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-bold font-sans truncate pr-2" title={adapter.name}>{adapter.name}</span>
                    <span
                      className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded border"
                      style={connected ? {
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        color: '#10b981',
                        borderColor: 'rgba(16, 185, 129, 0.2)',
                      } : {
                        backgroundColor: 'var(--theme-bg-well)',
                        color: 'var(--theme-text-secondary)',
                        borderColor: 'var(--theme-border-well)',
                      }}
                    >
                      {adapter.status || 'Unknown'}
                    </span>
                  </div>
                  <div className="space-y-1 font-mono text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>
                    <div className="flex justify-between gap-2">
                      <span>IP:</span>
                      <span style={{ color: 'var(--theme-text-primary)' }}>{adapter.ip}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span>Gateway:</span>
                      <span>{adapter.gateway || '-'}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span>DNS:</span>
                      <span>{[adapter.dns1, adapter.dns2].filter(Boolean).join(', ') || '-'}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span>MAC:</span>
                      <span>{adapter.mac || '-'}</span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span>Velocidad:</span>
                      <span style={{ color: 'var(--theme-accent-primary)' }}>{adapter.speed || '-'}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          <div
            className="border rounded-xl p-3.5 flex gap-2"
            style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)' }}
          >
            <Info size={14} className="shrink-0 mt-0.5" style={{ color: 'var(--theme-accent-primary)' }} />
            <p className="text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>
              Esta pantalla consulta datos reales. Los cambios de red no se aplican automáticamente desde el frontend.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
