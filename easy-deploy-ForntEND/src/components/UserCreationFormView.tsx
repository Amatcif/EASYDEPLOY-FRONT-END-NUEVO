import React, { useMemo, useState } from 'react';
import { Eye, EyeOff, Plus, Trash2, Play, FlaskConical, ArrowLeft } from 'lucide-react';

type Mode = 'ad' | 'exchange';

interface UserCreationFormViewProps {
  mode: Mode;
  onBack: () => void;
  onRunAction: (action: string, payload: Record<string, unknown>) => Promise<unknown>;
  onAppendLog: (source: string, type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
}

interface PreparedUser {
  id: string;
  label: string;
  payload: Record<string, unknown>;
}

function samFromName(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^A-Za-z0-9._-]+/g, '.')
    .replace(/^\.+|\.+$/g, '')
    .toLowerCase()
    .slice(0, 20);
}

function domainFromEmail(value: string) {
  const parts = value.trim().toLowerCase().split('@');
  return parts.length === 2 ? parts[1] : '';
}

export default function UserCreationFormView({ mode, onBack, onRunAction, onAppendLog }: UserCreationFormViewProps) {
  const isExchange = mode === 'exchange';
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [destination, setDestination] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [reuseData, setReuseData] = useState(false);
  const [lockedCommonData, setLockedCommonData] = useState(false);
  const [mustChange, setMustChange] = useState(false);
  const [cannotChange, setCannotChange] = useState(true);
  const [neverExpires, setNeverExpires] = useState(true);
  const [accountDisabled, setAccountDisabled] = useState(false);
  const [users, setUsers] = useState<PreparedUser[]>([]);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(false);

  const title = isExchange ? 'Crear usuarios Exchange' : 'Crear usuarios Active Directory';
  const subtitle = isExchange ?
     'Alta rápida o masiva de usuarios en Exchange con correo'
    : 'Alta rápida o masiva de usuarios en Active Directory';
  const action = isExchange ? 'exchange.create_users' : 'ad.create_users';

  const preparedText = useMemo(() => {
    if (!users.length) return 'Todavía no hay usuarios preparados.';
    return users.map((user, index) => `${String(index + 1).padStart(2, '0')}. ${user.label}`).join('\n');
  }, [users]);

  const setStatusLine = (message: string, isError = false) => {
    setStatus(message);
    setError(isError);
  };

  const resetForNextUser = (keepCommon: boolean) => {
    setEmail('');
    setDisplayName('');
    if (!keepCommon) {
      setDestination('');
      setPassword('');
      setMustChange(false);
      setCannotChange(true);
      setNeverExpires(true);
      setAccountDisabled(false);
      setLockedCommonData(false);
    } else {
      setLockedCommonData(true);
    }
  };

  const addUser = () => {
    const name = displayName.trim();
    const aliasOrEmail = email.trim().toLowerCase();
    const target = destination.trim();
    const pass = password;

    if (isExchange && !aliasOrEmail) {
      setStatusLine('Correo o alias es obligatorio.', true);
      return;
    }
    if (!name) {
      setStatusLine('Nombre de usuario / nombre visible es obligatorio.', true);
      return;
    }
    if (!pass) {
      setStatusLine('Contraseña es obligatoria.', true);
      return;
    }
    if (!isExchange && mustChange && (cannotChange || neverExpires)) {
      setStatusLine('Opciones incompatibles: cambiar contraseña al iniciar sesión no puede combinarse con no cambiarla o nunca expirar.', true);
      return;
    }

    const label = isExchange ?
       `${aliasOrEmail} | ${name} | ${target || 'Users'}`
      : `${name} (${samFromName(name)}) | ${target || 'Users'}`;

    if (users.some((user) => user.label.toLowerCase() === label.toLowerCase())) {
      setStatusLine('Ese usuario ya está preparado en la lista.', true);
      return;
    }

    const payload = isExchange ?
       {
          Email: aliasOrEmail,
          FirstName: name,
          OrganizationalUnit: target,
          Password: pass,
          Domain: domainFromEmail(aliasOrEmail),
        }
      : {
          Name: name,
          SamAccountName: samFromName(name),
          OrganizationalUnit: target,
          Password: pass,
          MustChangePassword: mustChange,
          CannotChangePassword: cannotChange,
          PasswordNeverExpires: neverExpires,
          AccountDisabled: accountDisabled,
        };

    const nextUsers = [...users, { id: `${Date.now()}-${users.length}`, label, payload }];
    setUsers(nextUsers);
    setStatusLine(`Usuario preparado: ${label}`, false);

    let keepCommon = false;
    if (reuseData) {
      keepCommon = window.confirm('¿Quieres reutilizar el destino, contraseña y opciones para los siguientes usuarios?');
    }
    resetForNextUser(keepCommon);
  };

  const removeLast = () => {
    if (!users.length) {
      setStatusLine('No hay usuarios preparados para eliminar.', true);
      return;
    }
    const removed = users[users.length - 1];
    setUsers(users.slice(0, -1));
    setStatusLine(`Eliminado de la lista: ${removed.label}`, false);
  };

  const run = (dryRun = false) => {
    if (!users.length) {
      setStatusLine('Añade al menos un usuario antes de ejecutar.', true);
      return;
    }
    const payloadUsers = users.map((user) => user.payload);
    onAppendLog(isExchange ? 'EXCHANGE' : 'AD', 'info', `${dryRun ? 'Dry-run' : 'Ejecución'} de ${payloadUsers.length} usuario(s) preparado(s).`);
    onRunAction(action, { users: payloadUsers, dryRun })
      .then(() => setStatusLine(dryRun ? 'Dry-run enviado al backend.' : 'Tarea enviada al backend. Revisa la consola.', false))
      .catch((err) => setStatusLine(`No se pudo enviar la tarea: ${String(err)}`, true));
  };

  return (
    <div className="h-full min-h-0 flex flex-col gap-4">
      <div className="border-t-2 pt-4 flex items-start justify-between gap-4" style={{ borderColor: 'var(--theme-accent-primary)' }}>
        <div className="flex items-start gap-3">
          <span className="mt-1 px-1.5 py-0.5 rounded text-xs font-black" style={{ backgroundColor: 'var(--theme-bg-well)', color: 'var(--theme-accent-primary)' }}>
            {isExchange ? 'EXC' : 'AD'}
          </span>
          <div>
            <h1 className="text-xl font-black" style={{ color: 'var(--theme-text-primary)' }}>{title}</h1>
            <p className="text-xs font-semibold" style={{ color: 'var(--theme-accent-primary)' }}>{subtitle}</p>
          </div>
        </div>
        <button type="button" onClick={onBack} className="px-3 py-2 rounded-lg border text-xs font-bold flex items-center gap-2" style={{ borderColor: 'var(--theme-border-well)', backgroundColor: 'var(--theme-bg-well)', color: 'var(--theme-text-primary)' }}>
          <ArrowLeft size={14} /> Volver
        </button>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[minmax(420px,0.9fr)_minmax(440px,1fr)] gap-4">
        <section className="min-h-0 overflow-auto rounded-xl border p-5 space-y-5" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}>
          <p className="text-[11px]" style={{ color: 'var(--theme-text-secondary)' }}>
            {isExchange ? 'Correo completo o alias; destino vacío usa Users. El dominio se comprueba al ejecutar.' : 'Destino en AD vacío usa Users. La comprobación real se hará al ejecutar.'}
          </p>

          <div className="space-y-3">
            <h3 className="text-xs font-bold" style={{ color: 'var(--theme-accent-primary)' }}>Datos del usuario</h3>
            {isExchange && (
              <label className="block space-y-2">
                <span className="text-xs font-bold">Correo o alias</span>
                <input value={email} onChange={(event) => setEmail(event.target.value)} className="w-full px-3 py-2 rounded-lg border bg-transparent outline-none" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }} />
              </label>
            )}
            <label className="block space-y-2">
              <span className="text-xs font-bold">{isExchange ? 'Nombre visible' : 'Nombre de usuario / nombre visible'}</span>
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} className="w-full px-3 py-2 rounded-lg border bg-transparent outline-none" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }} />
            </label>
          </div>

          <div className="space-y-3">
            <h3 className="text-xs font-bold" style={{ color: 'var(--theme-accent-primary)' }}>Destino y contraseña</h3>
            <label className="block space-y-2">
              <span className="text-xs font-bold">Destino en AD (opcional / avanzado)</span>
              <input disabled={lockedCommonData} value={destination} onChange={(event) => setDestination(event.target.value)} className="w-full px-3 py-2 rounded-lg border bg-transparent outline-none disabled:opacity-60" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }} />
              <span className="block text-[11px]" style={{ color: 'var(--theme-accent-primary)' }}>Si no escribes nada aquí, Easy Deploy usará Users automáticamente.</span>
            </label>
            <label className="block space-y-2">
              <span className="text-xs font-bold">Contraseña</span>
              <div className="flex gap-2">
                <input disabled={lockedCommonData} type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} className="flex-1 px-3 py-2 rounded-lg border bg-transparent outline-none disabled:opacity-60" style={{ borderColor: 'var(--theme-border-well)', color: 'var(--theme-text-primary)' }} />
                <button type="button" onClick={() => setShowPassword((value) => !value)} className="px-4 rounded-lg border text-xs font-bold flex items-center gap-2" style={{ borderColor: 'var(--theme-border-well)', backgroundColor: 'var(--theme-bg-well)', color: 'var(--theme-text-primary)' }}>
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />} Ver
                </button>
              </div>
            </label>
          </div>

          <label className="flex items-center gap-2 text-xs font-bold">
            <input type="checkbox" checked={reuseData} onChange={(event) => setReuseData(event.target.checked)} className="h-4 w-4" />
            Reutilizar datos para el siguiente usuario
          </label>

          {!isExchange && (
            <div className="space-y-3">
              <h3 className="text-xs font-bold" style={{ color: 'var(--theme-accent-primary)' }}>Opciones de contraseña y cuenta</h3>
              {[
                ['Cambiar contraseña al iniciar sesión', mustChange, setMustChange],
                ['No puede cambiar contraseña', cannotChange, setCannotChange],
                ['Contraseña nunca expira', neverExpires, setNeverExpires],
                ['Cuenta deshabilitada', accountDisabled, setAccountDisabled],
              ].map(([label, checked, setter]) => (
                <label key={String(label)} className="flex items-center gap-2 text-xs">
                  <input disabled={lockedCommonData} type="checkbox" checked={Boolean(checked)} onChange={(event) => (setter as React.Dispatch<React.SetStateAction<boolean>>)(event.target.checked)} className="h-4 w-4" />
                  {String(label)}
                </label>
              ))}
            </div>
          )}

          <p className="text-[11px]" style={{ color: 'var(--theme-accent-primary)' }}>
            {isExchange ? 'Dominio actual: pendiente' : 'Dominio AD: se comprobará al ejecutar.'}
          </p>
        </section>

        <section className="min-h-0 rounded-xl border p-4 flex flex-col" style={{ backgroundColor: 'var(--theme-bg-card)', borderColor: 'var(--theme-border-card)' }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-black">Usuarios preparados</h2>
            <span className="px-3 py-1 rounded-lg text-xs font-bold" style={{ backgroundColor: 'var(--theme-bg-well)', color: 'var(--theme-accent-primary)' }}>{users.length} usuario(s)</span>
          </div>
          <pre className="flex-1 min-h-[320px] overflow-auto rounded-lg border p-3 text-xs whitespace-pre-wrap" style={{ borderColor: 'var(--theme-border-well)', backgroundColor: 'var(--theme-bg-app)', color: 'var(--theme-text-primary)' }}>
            {preparedText}
          </pre>
        </section>
      </div>

      <div className="rounded-lg border min-h-[42px] px-4 py-2 text-xs flex items-center" style={{ borderColor: error ? '#b42318' : 'var(--theme-border-well)', color: error ? '#fca5a5' : 'var(--theme-text-secondary)', backgroundColor: 'var(--theme-bg-card)' }}>
        {status}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 shrink-0">
        <button type="button" onClick={addUser} className="py-3 rounded-lg text-sm font-bold flex items-center justify-center gap-2 text-white" style={{ backgroundColor: 'var(--theme-accent-primary)' }}><Plus size={16} /> Añadir usuario</button>
        <button type="button" onClick={removeLast} className="py-3 rounded-lg text-sm font-bold flex items-center justify-center gap-2" style={{ backgroundColor: '#64748b', color: '#fff' }}><Trash2 size={16} /> Eliminar último</button>
        <button type="button" onClick={() => run(true)} className="py-3 rounded-lg text-sm font-bold flex items-center justify-center gap-2" style={{ backgroundColor: '#475569', color: '#fff' }}><FlaskConical size={16} /> Probar dry-run</button>
        <button type="button" onClick={() => run(false)} className="py-3 rounded-lg text-sm font-bold flex items-center justify-center gap-2" style={{ backgroundColor: '#3b6f95', color: '#fff' }}><Play size={16} /> Terminar y ejecutar</button>
      </div>
    </div>
  );
}
