import { Check, LoaderCircle } from 'lucide-react';
import { type SessionStatus, sessionLabels } from '../types/MeasurementSession';
export function MeasurementStatus({
  status,
  stability,
}: {
  status: SessionStatus | undefined;
  stability: number;
}) {
  return (
    <div
      className={`measurement-status ${status === 'COMPLETED' ? 'completed' : ''}`}
      role="status"
    >
      {status === 'COMPLETED' ? (
        <Check size={17} />
      ) : status && ['MEASURING', 'STABILIZING'].includes(status) ? (
        <LoaderCircle size={17} className="spin" />
      ) : (
        <span className="status-dot" />
      )}
      <span>{status ? sessionLabels[status] : 'Pronto per la tua prossima misurazione'}</span>
      {status === 'STABILIZING' && <strong>{Math.round(stability)}%</strong>}
    </div>
  );
}
