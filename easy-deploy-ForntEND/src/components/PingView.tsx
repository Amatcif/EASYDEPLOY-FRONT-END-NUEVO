import React, { useEffect, useRef, useState } from 'react';
import { Activity, BookmarkPlus, Play, Square, Trash2, X } from 'lucide-react';

interface PingFavorite {
  name?: string;
  host: string;
}

interface PingCard {
  id: string;
  host: string;
  name: string;
  interval: number;
  running: boolean;
  ok?: boolean;
  lastOutput: string;
  lastChecked: string;
}

interface PingViewProps {
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  onRunAction: (action: string, payload?: Record<string, unknown>) => Promise<unknown>;
  favoritesData?: unknown;
  lastPingResult?: Record<string, unknown>;
}

function asFavorites(value: unknown): PingFavorite[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => ({
      name: String((item as Record<string, unknown>)?.name || ''),
      host: String((item as Record<string, unknown>)?.host || ''),
    }))
    .filter((item) => item.host);
}

function statusFor(card: PingCard) {
  if (!card.running) return { label: 'Parado', color: '#94a3b8' };
  if (card.ok === true) return { label: 'Correcto', color: '#10b981' };
  if (card.ok === false) return { label: 'Error', color: '#ef4444' };
  return { label: 'Esperando', color: '#94a3b8' };
}

export default function PingView({ onAppendLog, onRunAction, favoritesData, lastPingResult }: PingViewProps) {
  const [host, setHost] = useState('');
  const [name, setName] = useState('');
  const [interval, setIntervalValue] = useState(2);
  const [cards, setCards] = useState<PingCard[]>([]);
  const [favorites, setFavorites] = useState<PingFavorite[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  useEffect(() => {
    onRunAction('ping.favorites', { stayOnPage: true });
    return () => {
      timers.current.forEach((timer) => clearInterval(timer));
      timers.current.clear();
    };
  }, []);

  useEffect(() => {
    setFavorites(asFavorites(favoritesData));
  }, [favoritesData]);

  useEffect(() => {
    if (!lastPingResult) return;
    const target = String(lastPingResult.target || '');
    if (!target) return;
    const output = String(lastPingResult.output || '');
    const ok = lastPingResult.ok === true;
    const checked = new Date().toLocaleTimeString();
    setCards((prev) => prev.map((card) => (
      card.host.toLowerCase() === target.toLowerCase()
        ? { ...card, ok, lastOutput: output, lastChecked: checked }
        : card
    )));
  }, [lastPingResult]);

  const requestPing = (target: string) => {
    onRunAction('dashboard.ping', { target, stayOnPage: true });
  };

  const stopPing = (id: string) => {
    const timer = timers.current.get(id);
    if (timer) clearInterval(timer);
    timers.current.delete(id);
    setCards((prev) => prev.map((card) => card.id === id ? { ...card, running: false } : card));
  };

  const removePing = (id: string) => {
    stopPing(id);
    setCards((prev) => prev.filter((card) => card.id !== id));
  };

  const startPing = (card: PingCard) => {
    stopPing(card.id);
    setCards((prev) => prev.map((item) => item.id === card.id ? { ...item, running: true } : item));
    requestPing(card.host);
    const timer = setInterval(() => requestPing(card.host), Math.max(1, card.interval) * 1000);
    timers.current.set(card.id, timer);
  };

  const addPing = (presetHost?: string, presetName?: string) => {
    const target = String(presetHost || host).trim();
    if (!target) {
      onAppendLog('PING', 'warning', 'Introduce una IP o nombre DNS antes de iniciar el ping.');
      return;
    }
    const exists = cards.some((card) => card.host.toLowerCase() === target.toLowerCase());
    if (exists && !window.confirm(`Ya tienes un ping agregado para:\n\n${target}\n\n¿Quieres añadirlo igualmente?`)) {
      return;
    }
    const card: PingCard = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      host: target,
      name: String(presetName || name || target).trim(),
      interval: Math.max(1, interval),
      running: true,
      lastOutput: 'Esperando primera respuesta...',
      lastChecked: '-',
    };
    setCards((prev) => [...prev, card]);
    setHost('');
    setName('');
    startPing(card);
  };

  const saveFavorite = () => {
    const target = host.trim();
    if (!target) {
      onAppendLog('PING', 'warning', 'Introduce una IP o nombre DNS para guardar en Favoritos.');
      return;
    }
    onRunAction('ping.add_favorite', { host: target, name: name.trim(), stayOnPage: true });
  };

  const deleteFavorite = (target: string) => {
    onRunAction('ping.delete_favorite', { host: target, stayOnPage: true });
  };

  return (
    <div className="space-y-6">
      <div className="border rounded-2xl p-5" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}>
        <div className="flex items-center gap-3">
          <Activity size={22} style={{ color: 'var(--theme-accent-primary)' }} />
          <div>
            <h2 className="text-xl font-bold uppercase" style={{ color: 'var(--theme-text-primary)' }}>Monitor de ping</h2>
            <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
              Ejecuta varios pings a la vez, conserva favoritos y envía la salida real del backend a la consola.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-5">
        <div className="space-y-5">
          <div className="border rounded-2xl p-5 grid grid-cols-1 md:grid-cols-[1fr_1fr_110px_auto_auto] gap-3 items-end" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}>
            <label className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--theme-text-secondary)' }}>IP o nombre DNS</span>
              <input value={host} onChange={(event) => setHost(event.target.value)} className="w-full px-3 py-2 rounded-lg border text-sm bg-transparent" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }} />
            </label>
            <label className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--theme-text-secondary)' }}>Nombre opcional</span>
              <input value={name} onChange={(event) => setName(event.target.value)} className="w-full px-3 py-2 rounded-lg border text-sm bg-transparent" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }} />
            </label>
            <label className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--theme-text-secondary)' }}>Segundos</span>
              <input type="number" min={1} value={interval} onChange={(event) => setIntervalValue(Number(event.target.value || 1))} className="w-full px-3 py-2 rounded-lg border text-sm bg-transparent" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }} />
            </label>
            <button onClick={() => addPing()} className="px-4 py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2" style={{ backgroundColor: 'var(--theme-accent-primary)', color: '#fff' }}>
              <Play size={13} fill="currentColor" /> Añadir ping
            </button>
            <button onClick={saveFavorite} className="px-4 py-2 rounded-lg border text-xs font-bold flex items-center justify-center gap-2" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}>
              <BookmarkPlus size={13} /> Favorito
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {cards.map((card) => {
              const status = statusFor(card);
              return (
                <div
                  key={card.id}
                  className="border rounded-2xl p-4 space-y-3 relative overflow-hidden"
                  style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: status.color }}
                >
                  <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: status.color }} />
                  <div className="flex items-start justify-between gap-3 pl-1">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: status.color }} />
                        <h3 className="text-sm font-bold" style={{ color: 'var(--theme-text-primary)' }}>{card.name}</h3>
                      </div>
                      <p className="text-xs font-mono mt-1" style={{ color: 'var(--theme-text-secondary)' }}>{card.host} · {status.label}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removePing(card.id)}
                      className="w-8 h-8 rounded-lg border flex items-center justify-center font-bold"
                      title="Cerrar este ping"
                      style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)', backgroundColor: 'var(--theme-bg-well)' }}
                    >
                      <X size={15} />
                    </button>
                  </div>
                  <pre className="text-[11px] leading-relaxed max-h-40 overflow-auto whitespace-pre-wrap rounded-xl p-3 border" style={{ backgroundColor: 'var(--theme-bg-well)', borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}>{card.lastOutput}</pre>
                  <div className="flex items-center justify-between text-[10px]" style={{ color: 'var(--theme-text-secondary)' }}>
                    <span>Última comprobación: {card.lastChecked}</span>
                    <button onClick={() => card.running ? stopPing(card.id) : startPing(card)} className="px-3 py-1.5 rounded-lg border flex items-center gap-1.5" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }}>
                      {card.running ? <Square size={11} /> : <Play size={11} fill="currentColor" />} {card.running ? 'Parar' : 'Iniciar'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <aside className="border rounded-2xl p-4 max-h-[620px] overflow-hidden flex flex-col" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--theme-text-primary)' }}>Favoritos</h3>
          <div className="space-y-2 overflow-y-auto pr-1">
            {favorites.length === 0 && (
              <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>Todavía no hay pings guardados.</p>
            )}
            {favorites.map((item) => (
              <div key={item.host} className="border rounded-xl p-3 flex items-center justify-between gap-2" style={{ borderColor: 'var(--theme-border-well)', backgroundColor: 'var(--theme-bg-well)' }}>
                <button className="text-left min-w-0 flex-1" onClick={() => addPing(item.host, item.name || item.host)}>
                  <span className="block text-xs font-bold truncate" style={{ color: 'var(--theme-text-primary)' }}>{item.name || item.host}</span>
                  <span className="block text-[10px] font-mono truncate" style={{ color: 'var(--theme-text-secondary)' }}>{item.host}</span>
                </button>
                <button onClick={() => deleteFavorite(item.host)} className="p-2 rounded-lg border" style={{ borderColor: 'var(--theme-border-well)', color: '#ef4444' }}>
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
