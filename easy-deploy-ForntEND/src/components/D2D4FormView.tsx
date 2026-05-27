import { AlertTriangle, PlayCircle, RotateCcw, ShieldAlert } from 'lucide-react';

interface D2D4FormViewProps {
  onBack: () => void;
  onRunAction: (action: string, payload?: Record<string, unknown>, options?: { stayOnPage?: boolean }) => void;
}

export function D2D4FormView({ onBack, onRunAction }: D2D4FormViewProps) {
  const run = (mode: 'D2' | 'D4', dryRun: boolean) => {
    onRunAction(
      'ad.d2d4',
      {
        mode,
        operation: mode,
        dryRun,
      },
      { stayOnPage: false },
    );
  };

  return (
    <section className="view-shell">
      <div className="section-hero compact">
        <div>
          <span className="eyebrow">Active Directory / SYSVOL</span>
          <h1>D2/D4</h1>
          <p>
            Recuperación controlada de replicación DFSR para SYSVOL. Selecciona la operación y revisa el
            aviso antes de ejecutar.
          </p>
        </div>
        <button className="btn btn-secondary cursor-pointer" type="button" onClick={onBack}>
          <RotateCcw size={16} />
          Volver
        </button>
      </div>

      <div className="content-card warning-card">
        <div className="card-heading">
          <ShieldAlert size={22} />
          <div>
            <h2>Operación sensible</h2>
            <p>
              D2 y D4 modifican el flujo de recuperación de SYSVOL. No ejecutes estas acciones sin una copia
              de seguridad y una ventana de mantenimiento.
            </p>
          </div>
        </div>
      </div>

      <div className="grid two-columns">
        <article className="content-card action-choice">
          <div className="card-heading">
            <AlertTriangle size={22} />
            <div>
              <h2>D2 no autoritativo</h2>
              <p>Usa D2 cuando este controlador debe volver a sincronizar SYSVOL desde otro controlador sano.</p>
            </div>
          </div>
          <div className="button-row">
            <button className="btn btn-secondary cursor-pointer" type="button" onClick={() => run('D2', true)}>
              Probar dry-run
            </button>
            <button className="btn btn-primary cursor-pointer" type="button" onClick={() => run('D2', false)}>
              <PlayCircle size={16} />
              Ejecutar D2
            </button>
          </div>
        </article>

        <article className="content-card action-choice">
          <div className="card-heading">
            <AlertTriangle size={22} />
            <div>
              <h2>D4 autoritativo</h2>
              <p>Usa D4 solo cuando este controlador debe publicar SYSVOL como referencia autoritativa.</p>
            </div>
          </div>
          <div className="button-row">
            <button className="btn btn-secondary cursor-pointer" type="button" onClick={() => run('D4', true)}>
              Probar dry-run
            </button>
            <button className="btn btn-danger cursor-pointer" type="button" onClick={() => run('D4', false)}>
              <PlayCircle size={16} />
              Ejecutar D4
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}
