import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MeasurementStatus } from './MeasurementStatus';

describe('MeasurementStatus', () => {
  it.each([
    ['WAITING_FOR_USER', 'Sali sulla bilancia'],
    ['MEASURING', 'Misurazione in corso'],
    ['STABILIZING', 'Resta fermo'],
    ['COMPLETED', 'Misurazione completata'],
    ['CANCELLED', 'Misurazione annullata'],
    ['ERROR', 'Misurazione interrotta'],
  ] as const)('renders %s', (status, label) => {
    render(<MeasurementStatus status={status} stability={96} />);
    expect(screen.getByRole('status')).toHaveTextContent(label);
    if (status === 'STABILIZING') expect(screen.getByText('96%')).toBeInTheDocument();
  });
});
