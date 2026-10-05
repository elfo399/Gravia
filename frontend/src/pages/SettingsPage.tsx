import { Bluetooth, Database, SlidersHorizontal } from 'lucide-react';
import { useEffect, useState } from 'react';
import { apiRequest } from '../api/apiRequest';
import { useGraviaData } from '../hooks/useGraviaData';

interface BoardSettings {
  boardMode: string;
  minimumWeight: number;
  requiredStability: number;
  stableDuration: number;
  sessionTimeout: number;
}
export function SettingsPage() {
  const { live } = useGraviaData();
  const [settings, setSettings] = useState<BoardSettings | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    apiRequest<BoardSettings>('/settings')
      .then(setSettings)
      .catch((error) => setError(error.message));
  }, []);
  return (
    <>
      <div className="page-title">
        <div className="eyebrow">IL TUO DISPOSITIVO</div>
        <h1>Impostazioni</h1>
        <p>Tutto ciò che serve per conoscere la tua Gravia.</p>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      <div className="settings-grid">
        <section className="card settings-card">
          <div className="card-heading">
            <h2>Balance Board</h2>
            <Bluetooth size={20} />
          </div>
          <div className="setting-row">
            <span>Modalità board</span>
            <strong>
              {settings?.boardMode === 'demo'
                ? 'Demo'
                : settings?.boardMode === 'real'
                  ? 'Reale'
                  : '…'}
            </strong>
          </div>
          <p className="settings-note">
            {settings?.boardMode === 'demo'
              ? 'La modalità Demo simula una pesata completa con quattro sensori. Non occorre collegare alcun dispositivo.'
              : 'Premi Power sulla Balance Board per accenderla. Premilo di nuovo per spegnerla.'}
          </p>
          <div className="setting-row">
            <span>Connessione hardware</span>
            <strong>{live.board?.connected ? 'Connessa' : 'Non connessa'}</strong>
          </div>
          {live.board?.battery != null && (
            <div className="setting-row">
              <span>Batteria</span>
              <strong>{live.board.battery}%</strong>
            </div>
          )}
          {live.board?.lastError && (
            <p className="inline-error" role="status">
              {live.board.lastError}
            </p>
          )}
        </section>
        <section className="card settings-card">
          <div className="card-heading">
            <h2>Parametri di misurazione</h2>
            <SlidersHorizontal size={20} />
          </div>
          {[
            { label: 'Peso minimo', value: settings?.minimumWeight, unit: 'kg' },
            { label: 'Stabilità richiesta', value: settings?.requiredStability, unit: '%' },
            { label: 'Durata stabile', value: settings?.stableDuration, unit: 'secondi' },
            { label: 'Timeout sessione', value: settings?.sessionTimeout, unit: 'secondi' },
          ].map((item) => (
            <div className="setting-row" key={item.label}>
              <span>{item.label}</span>
              <strong>
                {item.value ?? '…'} {item.unit}
              </strong>
            </div>
          ))}
          <p className="settings-note">
            Configura questi valori nel file .env e ricrea il container per applicarli.
          </p>
        </section>
        <section className="card settings-card">
          <div className="card-heading">
            <h2>I tuoi dati, a casa</h2>
            <Database size={20} />
          </div>
          <div className="setting-row">
            <span>Database</span>
            <strong>SQLite · locale</strong>
          </div>
          <div className="setting-row">
            <span>Versione</span>
            <strong>0.2.0</strong>
          </div>
          <p className="settings-note">
            Profili e misurazioni restano sul tuo computer, nella cartella data del progetto.
          </p>
        </section>
      </div>
    </>
  );
}
