import { useState } from 'react';
import { sessionsApi } from '../api/sessionsApi';
export function useMeasurementSession() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function perform(action: () => Promise<unknown>) {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Operazione non riuscita.');
    } finally {
      setBusy(false);
    }
  }
  return {
    busy,
    error,
    start: (profileId: string) => perform(() => sessionsApi.start(profileId)),
    cancel: (id: string) => perform(() => sessionsApi.cancel(id)),
  };
}
