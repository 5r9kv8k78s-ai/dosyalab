import type { Config } from 'tailwindcss';
import tailwindcssAnimate from 'tailwindcss-animate';

const withOpacity = (variable: string) => `rgb(var(${variable}) / <alpha-value>)`;

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Semantic design-system palette. Each token resolves through a CSS
        // variable (see globals.css :root) so opacity modifiers like
        // `bg-primary/10` work and the palette can be retuned in one place.
        primary: {
          DEFAULT: withOpacity('--color-primary'),
          hover: withOpacity('--color-primary-hover'),
          light: withOpacity('--color-primary-light'),
          foreground: withOpacity('--color-on-primary'),
        },
        secondary: {
          DEFAULT: withOpacity('--color-secondary'),
          hover: withOpacity('--color-secondary-hover'),
          light: withOpacity('--color-secondary-light'),
          foreground: withOpacity('--color-on-secondary'),
        },
        success: {
          DEFAULT: withOpacity('--color-success'),
          bg: withOpacity('--color-success-bg'),
        },
        warning: {
          DEFAULT: withOpacity('--color-warning'),
          bg: withOpacity('--color-warning-bg'),
        },
        danger: {
          DEFAULT: withOpacity('--color-danger'),
          bg: withOpacity('--color-danger-bg'),
        },
        background: withOpacity('--color-background'),
        surface: withOpacity('--color-surface'),
        border: withOpacity('--color-border'),
        foreground: withOpacity('--color-foreground'),
        muted: {
          DEFAULT: withOpacity('--color-muted'),
          foreground: withOpacity('--color-muted-foreground'),
        },

        // Deprecated alias kept only until every usage is migrated to
        // `primary` — do not use in new code.
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      // Typography scale tokens: text-display, text-h1, text-h2, text-h3,
      // text-body, text-small, text-button.
      fontSize: {
        display: ['3rem', { lineHeight: '1.1', fontWeight: '800', letterSpacing: '-0.02em' }],
        h1: ['2.25rem', { lineHeight: '1.2', fontWeight: '700', letterSpacing: '-0.01em' }],
        h2: ['1.875rem', { lineHeight: '1.25', fontWeight: '700' }],
        h3: ['1.5rem', { lineHeight: '1.3', fontWeight: '600' }],
        body: ['1rem', { lineHeight: '1.6', fontWeight: '400' }],
        small: ['0.875rem', { lineHeight: '1.5', fontWeight: '400' }],
        button: ['0.9375rem', { lineHeight: '1', fontWeight: '600' }],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        full: 'var(--radius-full)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },
      transitionDuration: {
        fast: 'var(--duration-fast)',
        base: 'var(--duration-base)',
        slow: 'var(--duration-slow)',
      },
      zIndex: {
        dropdown: 'var(--z-dropdown)',
        sticky: 'var(--z-sticky)',
        overlay: 'var(--z-overlay)',
        modal: 'var(--z-modal)',
        toast: 'var(--z-toast)',
        tooltip: 'var(--z-tooltip)',
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
