'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { THEME_STORAGE_KEY, detectSystemTheme, readStoredTheme, type Theme } from './index';

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyThemeClass(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Starts at 'light' so server and first client render match (no hydration
  // mismatch) — the inline script in app/layout.tsx already applied the
  // real class to <html> before paint, so there's no visible flash even
  // though this piece of React state hasn't caught up yet. It catches up in
  // the effect below.
  const [theme, setThemeState] = useState<Theme>('light');

  useEffect(() => {
    const initial = readStoredTheme() ?? detectSystemTheme();
    setThemeState(initial);
    applyThemeClass(initial);
  }, []);

  const setTheme = (next: Theme) => {
    setThemeState(next);
    applyThemeClass(next);
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
  };

  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

/** Must be called under `ThemeProvider` (mounted once in app/layout.tsx). */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
