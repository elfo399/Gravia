import { Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';

export function ThemeToggle() {
  const { resolved, setTheme } = useTheme();
  return (
    <button
      type="button"
      className="theme-toggle"
      aria-label={resolved === 'dark' ? 'Attiva tema chiaro' : 'Attiva tema scuro'}
      title={resolved === 'dark' ? 'Tema chiaro' : 'Tema scuro'}
      onClick={() => setTheme(resolved === 'dark' ? 'light' : 'dark')}
    >
      {resolved === 'dark' ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  );
}

export function AppearanceCard() {
  const { theme, setTheme } = useTheme();
  return (
    <section className="card settings-card appearance-card">
      <div className="card-heading">
        <h2>Aspetto</h2>
        <Sun size={20} />
      </div>
      <p className="appearance-description">Il tuo spazio, nella luce che preferisci.</p>
      <fieldset className="theme-options" aria-label="Tema dell’interfaccia">
        {(
          [
            ['light', 'Chiaro', Sun],
            ['dark', 'Scuro', Moon],
            ['system', 'Sistema', Monitor],
          ] as const
        ).map(([value, label, Icon]) => (
          <button
            key={value}
            type="button"
            aria-pressed={theme === value}
            onClick={() => setTheme(value)}
          >
            <Icon size={20} />
            <span>{label}</span>
          </button>
        ))}
      </fieldset>
      <p className="settings-note">
        La scelta viene salvata in questo browser. Sistema segue automaticamente le impostazioni del
        dispositivo.
      </p>
    </section>
  );
}
