import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BmiRange } from './BmiRange';

describe('adult BMI range', () => {
  it.each([
    [18.49, 'Sottopeso'],
    [18.5, 'Normopeso'],
    [24.999, 'Normopeso'],
    [25, 'Sovrappeso'],
    [29.999, 'Sovrappeso'],
    [30, 'Obesità'],
  ])('classifies the unrounded value %s as %s', (value, category) => {
    render(<BmiRange value={value} />);
    expect(screen.getByText(category).className).toBe('current');
  });
  it.each([undefined, Number.NaN, Number.POSITIVE_INFINITY, 0])(
    'shows no marker or category for missing/invalid BMI %s',
    (value) => {
      const { container } = render(<BmiRange value={value} />);
      expect(container.querySelector('.bmi-marker')).toBeNull();
      expect(container.querySelector('.current')).toBeNull();
      expect(screen.getByText(/BMI non disponibile/)).toBeTruthy();
    },
  );
  it.each([
    [8, '0%'],
    [45, '100%'],
  ])('keeps BMI %s within the visible scale', (value, position) => {
    const { container } = render(<BmiRange value={value as number} />);
    expect(
      (container.querySelector('.bmi-marker') as HTMLElement).style.getPropertyValue(
        '--bmi-position',
      ),
    ).toBe(position);
  });
});
