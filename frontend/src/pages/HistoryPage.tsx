import { Check, History, Pencil, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { measurementsApi } from '../api/measurementsApi';
import { formatDate, formatWeight } from '../api/weightStatistics';
import { Button } from '../components/ui/Button';
import { useGraviaData } from '../hooks/useGraviaData';
export function HistoryPage() {
  const { measurements, profiles, profileId, refresh } = useGraviaData();
  const [allProfiles, setAllProfiles] = useState(false);
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [editing, setEditing] = useState('');
  const [notes, setNotes] = useState('');
  const [deleting, setDeleting] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const selected = measurements.filter((item) => allProfiles || item.profileId === profileId);
  const filtered = selected.filter(
    (item) =>
      (!from || new Date(item.measuredAt) >= new Date(`${from}T00:00:00`)) &&
      (!to || new Date(item.measuredAt) <= new Date(`${to}T23:59:59.999`)),
  );
  async function change(action: () => Promise<unknown>) {
    setBusy(true);
    setError('');
    try {
      await action();
      setEditing('');
      setDeleting('');
      await refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Operazione non riuscita.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title">
        <div className="eyebrow">IL TUO PERCORSO</div>
        <h1>Storico misurazioni</h1>
        <p>Ogni pesata, un punto di partenza per capirti meglio.</p>
      </div>
      <section className="card">
        <div className="history-filters">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={allProfiles}
              onChange={(event) => setAllProfiles(event.target.checked)}
            />
            Tutti i profili
          </label>
          <label>
            Dal
            <input
              type="date"
              aria-label="Data iniziale"
              value={from}
              onChange={(event) => setFrom(event.target.value)}
            />
          </label>
          <label>
            Al
            <input
              type="date"
              aria-label="Data finale"
              value={to}
              onChange={(event) => setTo(event.target.value)}
            />
          </label>
          <span>{filtered.length} misurazioni</span>
        </div>
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        {filtered.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Data e ora</th>
                  <th>Profilo</th>
                  <th>Peso</th>
                  <th>Variazione</th>
                  <th>Stabilità</th>
                  <th>Nota</th>
                  <th>
                    <span className="sr-only">Azioni</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const profileReadings = measurements.filter(
                    (reading) => reading.profileId === item.profileId,
                  );
                  const previous =
                    profileReadings[
                      profileReadings.findIndex((reading) => reading.id === item.id) + 1
                    ];
                  const delta = previous ? item.weight - previous.weight : undefined;
                  return (
                    <tr key={item.id}>
                      <td>{formatDate(item.measuredAt)}</td>
                      <td>{profiles.find((profile) => profile.id === item.profileId)?.name}</td>
                      <td>
                        <strong>{formatWeight(item.weight)} kg</strong>
                      </td>
                      <td>
                        {delta === undefined
                          ? '—'
                          : `${delta > 0 ? '+' : ''}${formatWeight(delta)} kg`}
                      </td>
                      <td>
                        <span className="stability-badge">{Math.round(item.stability)}%</span>
                      </td>
                      <td>
                        {editing === item.id ? (
                          <div className="note-editor">
                            <input
                              aria-label="Nota misurazione"
                              maxLength={1000}
                              value={notes}
                              onChange={(event) => setNotes(event.target.value)}
                            />
                            <Button
                              variant="ghost"
                              aria-label="Salva nota"
                              disabled={busy}
                              onClick={() => change(() => measurementsApi.update(item.id, notes))}
                            >
                              <Check size={16} />
                            </Button>
                            <Button
                              variant="ghost"
                              aria-label="Annulla nota"
                              onClick={() => setEditing('')}
                            >
                              <X size={16} />
                            </Button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="note-button"
                            onClick={() => {
                              setEditing(item.id);
                              setNotes(item.notes || '');
                            }}
                          >
                            <span>{item.notes || 'Aggiungi nota'}</span>
                            <Pencil size={13} />
                          </button>
                        )}
                      </td>
                      <td>
                        {deleting === item.id ? (
                          <div className="inline-confirm">
                            <Button
                              variant="destructive"
                              disabled={busy}
                              onClick={() => change(() => measurementsApi.delete(item.id))}
                            >
                              Elimina
                            </Button>
                            <Button variant="ghost" onClick={() => setDeleting('')}>
                              Annulla
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="ghost"
                            aria-label="Elimina misurazione"
                            onClick={() => setDeleting(item.id)}
                          >
                            <Trash2 size={16} />
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <History size={34} />
            <h2>Nessuna misurazione in questo periodo</h2>
            <p>Inizia una pesata dalla dashboard o modifica i filtri.</p>
          </div>
        )}
      </section>
    </>
  );
}
