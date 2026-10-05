import type { Measurement } from '../types/Measurement';
export function calculateWeightStatistics(measurements: Measurement[], heightCm?: number | null) {
  const current = measurements[0]?.weight;
  const previous = measurements[1]?.weight;
  return {
    current,
    change: current !== undefined && previous !== undefined ? current - previous : undefined,
    average: measurements.length
      ? measurements.reduce((sum, item) => sum + item.weight, 0) / measurements.length
      : undefined,
    bmi: current !== undefined && heightCm ? current / (heightCm / 100) ** 2 : undefined,
    count: measurements.length,
  };
}
export const formatWeight = (weight?: number) =>
  weight === undefined
    ? '—'
    : weight.toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const formatDate = (date: string) =>
  new Date(date).toLocaleString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
