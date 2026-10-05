import type { ReactNode } from 'react';
import { createContext, useContext, useEffect, useLayoutEffect, useState } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
const storageKey = 'gravia.theme';
const query = '(prefers-color-scheme: dark)';
const preference = (value: string | null): ThemePreference =>
  value === 'light' || value === 'dark' ? value : 'system';
const ThemeContext = createContext<{
  theme: ThemePreference;
  resolved: 'light' | 'dark';
  setTheme: (theme: ThemePreference) => void;
} | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, updateTheme] = useState<ThemePreference>(() => {
    try {
      return preference(localStorage.getItem(storageKey));
    } catch {
      return 'system';
    }
  });
  const [systemDark, setSystemDark] = useState(() => window.matchMedia?.(query).matches ?? false);
  const resolved = theme === 'system' ? (systemDark ? 'dark' : 'light') : theme;
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = resolved;
  }, [resolved]);
  useEffect(() => {
    const media = window.matchMedia?.(query);
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches);
    const onStorage = (event: StorageEvent) => {
      if (event.key === storageKey || event.key === null) updateTheme(preference(event.newValue));
    };
    media?.addEventListener('change', onChange);
    window.addEventListener('storage', onStorage);
    return () => {
      media?.removeEventListener('change', onChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);
  function setTheme(value: ThemePreference) {
    updateTheme(value);
    try {
      localStorage.setItem(storageKey, value);
    } catch {
      // The appearance still changes when browser storage is unavailable.
    }
  }
  return (
    <ThemeContext.Provider value={{ theme, resolved, setTheme }}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('ThemeProvider is required');
  return context;
}
