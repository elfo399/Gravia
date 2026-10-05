export interface CalibrationSession {
  id: string;
  stage: 'TARE' | 'REFERENCE' | 'VERIFY';
  busy: boolean;
  referenceWeight: number | null;
  weightScale: number | null;
  measuredWeightBefore: number | null;
  measuredWeightAfter: number | null;
  absoluteError: number | null;
  percentageError: number | null;
  valid: boolean | null;
}
