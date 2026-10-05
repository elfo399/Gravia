import { Pencil, Plus, Trash2, UserRound } from 'lucide-react';
import { type FormEvent, useState } from 'react';
import { profilesApi } from '../api/profilesApi';
import { Button } from '../components/ui/Button';
import { useGraviaData } from '../hooks/useGraviaData';
import { isActivityActive } from '../types/ActivitySession';
import { activeStatuses } from '../types/MeasurementSession';
export function ProfilesPage() {
  const { profiles, profileId, selectProfile, refresh, live } = useGraviaData();
  const sessionActive =
    isActivityActive(live.activityStatus?.status) ||
    (!!live.sessionEvent && activeStatuses.includes(live.sessionEvent.status));
  const [editing, setEditing] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [height, setHeight] = useState('');
  const [deleting, setDeleting] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const value = height ? Number(height) : null;
      if (editing) await profilesApi.update(editing, name, value);
      else await profilesApi.create(name, value);
      setEditing(null);
      await refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Salvataggio non riuscito.');
    } finally {
      setBusy(false);
    }
  }
  async function remove(id: string) {
    setBusy(true);
    setError('');
    try {
      await profilesApi.delete(id);
      setDeleting('');
      await refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Eliminazione non riuscita.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title page-title-actions">
        <div>
          <div className="eyebrow">UNO SPAZIO PER OGNUNO</div>
          <h1>I tuoi profili</h1>
          <p>Esperienze personali, sullo stesso dispositivo.</p>
        </div>
        <Button
          onClick={() => {
            setEditing('');
            setName('');
            setHeight('');
            setError('');
          }}
        >
          <Plus size={18} />
          Nuovo profilo
        </Button>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      {editing !== null && (
        <form className="card profile-form" onSubmit={save}>
          <h2>{editing ? 'Modifica profilo' : 'Crea il tuo profilo'}</h2>
          <div className="form-fields">
            <label>
              Nome
              <input
                autoComplete="given-name"
                required
                maxLength={80}
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Come ti chiami?"
              />
            </label>
            <label>
              Altezza (cm)
              <input
                type="number"
                min="50"
                max="250"
                step="0.1"
                value={height}
                onChange={(event) => setHeight(event.target.value)}
                placeholder="Facoltativa"
              />
            </label>
          </div>
          <p className="muted">
            L’altezza permette di calcolare il BMI. Puoi aggiungerla anche in seguito.
          </p>
          <div className="form-actions">
            <Button type="submit" disabled={busy || !name.trim()}>
              {busy ? 'Salvataggio…' : 'Salva profilo'}
            </Button>
            <Button variant="outline" type="button" onClick={() => setEditing(null)}>
              Annulla
            </Button>
          </div>
        </form>
      )}
      <div className="profiles-grid">
        {profiles.map((profile) => (
          <section
            className={`card person-card ${profile.id === profileId ? 'selected-profile' : ''}`}
            key={profile.id}
          >
            <div className="person-heading">
              <span className="person-avatar">{profile.name[0].toUpperCase()}</span>
              {profile.id === profileId && <span className="selected-badge">Profilo attivo</span>}
            </div>
            <h2>{profile.name}</h2>
            <p>{profile.heightCm ? `${profile.heightCm} cm` : 'Altezza non specificata'}</p>
            <div className="person-actions">
              <Button
                variant="outline"
                disabled={profile.id === profileId || sessionActive}
                onClick={() => selectProfile(profile.id)}
              >
                Seleziona
              </Button>
              <Button
                variant="ghost"
                aria-label={`Modifica ${profile.name}`}
                onClick={() => {
                  setEditing(profile.id);
                  setName(profile.name);
                  setHeight(profile.heightCm?.toString() || '');
                  setError('');
                }}
              >
                <Pencil size={16} />
              </Button>
              <Button
                variant="ghost"
                aria-label={`Elimina ${profile.name}`}
                onClick={() => setDeleting(profile.id)}
              >
                <Trash2 size={16} />
              </Button>
            </div>
            {deleting === profile.id && (
              <div className="profile-delete">
                <p>Eliminare {profile.name}, tutte le sue misurazioni e il suo storico Training?</p>
                <Button variant="destructive" disabled={busy} onClick={() => remove(profile.id)}>
                  Elimina profilo e dati
                </Button>
                <Button variant="ghost" onClick={() => setDeleting('')}>
                  Annulla
                </Button>
              </div>
            )}
          </section>
        ))}
      </div>
      {!profiles.length && (
        <div className="card empty-state">
          <UserRound size={34} />
          <h2>Il primo passo è il tuo nome</h2>
          <p>Crea un profilo per iniziare a misurare.</p>
        </div>
      )}
    </>
  );
}
