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
        // Semantic Token Mapping
        base: 'var(--bg-base)',
        surface: 'var(--bg-surface)',
        raised: 'var(--bg-raised)',
        border: 'var(--border)',
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        muted: 'var(--text-muted)',
        
        brand: {
          DEFAULT: 'var(--brand)',
          hover: 'var(--brand-hover)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          fg: 'var(--accent-fg)',
        },

        // Status Tokens
        status: {
          passed: 'var(--status-passed)',
          failed: 'var(--status-failed)',
          flaky: 'var(--status-flaky)',
          running: 'var(--status-running)',
          error: 'var(--status-error)',
          skipped: 'var(--status-skipped)',
        },

        // Graph Semantic Colors
        graph: {
          module: '#22D3EE',
          endpoint: '#34D399',
          function: '#818CF8',
          project: '#FBBF24',
          impact: '#FBBF24',
          depends: '#22D3EE',
          riskHigh: '#F87171',
          riskMed: '#FBBF24',
        },

        // Preserve slate scale with theme-adaptive hexes
        slate: {
          950: '#080B14',
          900: '#0F1424',
          850: '#13192B',
          800: '#161C31',
          750: '#1C243D',
          700: '#232B45',
          600: '#475170',
          500: '#6A7597',
          400: '#9AA6C7',
          300: '#C7D0E8',
          200: '#E2E7F5',
          100: '#EEF2FF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        '2xs': ['11px', '14px'],
        xs: ['12px', '16px'],
        sm: ['14px', '20px'],
        base: ['16px', '24px'],
        lg: ['20px', '28px'],
        xl: ['28px', '36px'],
        '2xl': ['40px', '48px'],
      },
      borderRadius: {
        DEFAULT: '8px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '20px',
      },
      boxShadow: {
        glow: '0 0 0 1px var(--brand), 0 8px 24px rgba(124, 92, 255, 0.15)',
        'glow-accent': '0 0 0 1px var(--accent), 0 8px 20px rgba(198, 255, 61, 0.2)',
        'glow-status-pass': '0 0 12px rgba(34, 229, 143, 0.25)',
        'glow-status-fail': '0 0 12px rgba(255, 77, 106, 0.25)',
      },
    },
  },
  plugins: [],
}
