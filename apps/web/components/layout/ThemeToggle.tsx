'use client';

import { Moon, Sun } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const { t } = useTranslation();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme === 'dark' ? t.theme.switchToLight : t.theme.switchToDark}
      className="focus-ring border-border bg-surface text-muted hover:text-foreground duration-base flex h-9 w-9 items-center justify-center rounded-full border transition-colors"
    >
      {theme === 'dark' ? (
        <Sun className="h-4 w-4" aria-hidden="true" />
      ) : (
        <Moon className="h-4 w-4" aria-hidden="true" />
      )}
    </button>
  );
}
