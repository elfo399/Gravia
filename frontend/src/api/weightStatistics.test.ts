import { describe, expect, it } from 'vitest';
import type { Measurement } from '../types/Measurement';
import { calculateWeightStatistics } from './weightStatistics';

describe('Weight statistics', () => {
  it('calculates change, mean and dynamic BMI', () => {
    const readings = [{ weight: 72.4 }, { weight: 73.2 }] as Measurement[];
    const result = calculateWeightStatistics(readings, 180);
    expect(result.change).toBeCloseTo(-0.8);
    expect(result.average).toBeCloseTo(72.8);
    expect(result.bmi).toBeCloseTo(22.3457);
    expect(calculateWeightStatistics(readings, 170).bmi).not.toEqual(result.bmi);
  });
  it('handles empty history and missing height', () => {
    expect(calculateWeightStatistics([])).toEqual({
      current: undefined,
      change: undefined,
      average: undefined,
      bmi: undefined,
      count: 0,
    });
    expect(calculateWeightStatistics([{ weight: 72 }] as Measurement[]).bmi).toBeUndefined();
  });
});
