/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        // App Core Layers
        app: 'var(--bg-app)',
        sidebar: 'var(--bg-sidebar)',
        card: 'var(--bg-card)',
        field: 'var(--bg-field)',
        hover: 'var(--bg-hover)',
        // Compatibility Aliases
        base: 'var(--bg-app)',
        surface: 'var(--bg-card)',
        raised: 'var(--bg-field)',
        slate: {
          50: 'var(--text-primary)',
          100: 'var(--text-primary)',
          200: 'var(--text-primary)',
          300: 'var(--text-primary)',
          400: 'var(--text-secondary)',
          500: 'var(--text-muted)',
          600: 'var(--text-muted)',
          700: 'var(--border-field)',
          800: 'var(--border-card)',
          900: 'var(--bg-card)',
          950: 'var(--bg-field)',
        },

        // Borders
        border: 'var(--border-card)',
        'border-card': 'var(--border-card)',
        'border-field': 'var(--border-field)',

        // Typography
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        muted: 'var(--text-muted)',
        'on-sidebar': 'var(--text-on-sidebar)',
        'on-sidebar-muted': 'var(--text-on-sidebar-muted)',

        // Brand Action
        brand: {
          DEFAULT: 'var(--brand)',
          hover: 'var(--brand-hover)',
        },
        'on-brand': 'var(--on-brand)',
        secondaryAccent: 'var(--secondary)',

        // Status Colors
        status: {
          passed: 'var(--status-passed)',
          'passed-bg': 'var(--status-passed-bg)',
          failed: 'var(--status-failed)',
          'failed-bg': 'var(--status-failed-bg)',
          flaky: 'var(--status-flaky)',
          'flaky-bg': 'var(--status-flaky-bg)',
          running: 'var(--status-running)',
          'running-bg': 'var(--status-running-bg)',
          error: 'var(--status-error)',
          'error-bg': 'var(--status-error-bg)',
          skipped: 'var(--status-skipped)',
          'skipped-bg': 'var(--status-skipped-bg)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        'brand-glow': '0 0 0 1px var(--brand), 0 4px 14px rgba(91, 61, 245, 0.25)',
      },
      borderRadius: {
        DEFAULT: '8px',
        md: '8px',
        lg: '10px',
        xl: '12px',
        '2xl': '16px',
      },
    },
  },
  plugins: [],
}
