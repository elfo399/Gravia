import type { LiveMeasurement } from '../types/Measurement';
import { activeStatuses } from '../types/MeasurementSession';
import { useGraviaData } from './useGraviaData';

export function useBoardReading() {
  const { profileId, measurements, live } = useGraviaData();
  const latest = measurements.find((item) => item.profileId === profileId);
  const belongsToProfile = live.sessionEvent?.profileId === profileId;
  const sessionStatus = belongsToProfile ? live.sessionEvent?.status : undefined;
  const status =
    sessionStatus === 'COMPLETED' &&
    live.completed &&
    !measurements.some((item) => item.id === live.completed?.id)
      ? undefined
      : sessionStatus;
  const active = !!live.sessionEvent && activeStatuses.includes(live.sessionEvent.status);
  const showingLive = belongsToProfile && (active || status === 'COMPLETED');
  const reading: LiveMeasurement | null = showingLive
    ? live.reading
    : latest
      ? {
          sessionId: latest.sessionId,
          weight: latest.weight,
          stability: latest.stability,
          sensors: {
            frontLeft: latest.frontLeft,
            frontRight: latest.frontRight,
            rearLeft: latest.rearLeft,
            rearRight: latest.rearRight,
          },
          centerOfPressure: { x: latest.centerX, y: latest.centerY },
        }
      : null;
  return { latest, reading, status, active, showingLive };
}
