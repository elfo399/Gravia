import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppearanceCard, ThemeToggle } from '../components/ThemeControls';
import { ThemeProvider } from './useTheme';

let dark = false;
let changes = new Set<(event: MediaQueryListEvent) => void>();
function application() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
      <AppearanceCard />
    </ThemeProvider>,
  );
}
function systemTheme(value: boolean) {
  dark = value;
  act(() => {
    for (const listener of changes) listener({ matches: value } as MediaQueryListEvent);
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  dark = false;
  changes = new Set();
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      get matches() {
        return dark;
      },
      addEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) =>
        changes.add(listener),
      removeEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) =>
        changes.delete(listener),
    })),
  );
});

describe('appearance preferences', () => {
  it('defaults to system and follows changes immediately', () => {
    application();
    expect(screen.getByRole('button', { name: 'Sistema' })).toHaveAttribute('aria-pressed', 'true');
    expect(document.documentElement).toHaveAttribute('data-theme', 'light');
    systemTheme(true);
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  });
  it('saves an explicit choice and restores it on a fresh mount', () => {
    const { unmount } = application();
    fireEvent.click(screen.getByRole('button', { name: 'Scuro' }));
    expect(localStorage.getItem('gravia.theme')).toBe('dark');
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    unmount();
    application();
    expect(screen.getByRole('button', { name: 'Scuro' })).toHaveAttribute('aria-pressed', 'true');
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  });
  it('keeps an explicit choice when system appearance changes', () => {
    localStorage.setItem('gravia.theme', 'light');
    application();
    systemTheme(true);
    expect(document.documentElement).toHaveAttribute('data-theme', 'light');
    fireEvent.click(screen.getByRole('button', { name: 'Sistema' }));
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  });
  it('toggles appearance from the header with an accessible label', () => {
    application();
    fireEvent.click(screen.getByRole('button', { name: 'Attiva tema scuro' }));
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    fireEvent.click(screen.getByRole('button', { name: 'Attiva tema chiaro' }));
    expect(localStorage.getItem('gravia.theme')).toBe('light');
  });
  it('handles an invalid saved preference', () => {
    localStorage.setItem('gravia.theme', 'invalid');
    application();
    expect(screen.getByRole('button', { name: 'Sistema' })).toHaveAttribute('aria-pressed', 'true');
  });
  it('still changes appearance if storage is unavailable', () => {
    application();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage unavailable');
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scuro' }));
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  });
  it('synchronizes a preference changed in another tab', () => {
    application();
    act(() =>
      window.dispatchEvent(new StorageEvent('storage', { key: 'gravia.theme', newValue: 'dark' })),
    );
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  });
});
