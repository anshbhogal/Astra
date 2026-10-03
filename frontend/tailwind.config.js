/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          950: '#020617',
          900: '#0f172a',
          850: '#15203b',
          800: '#1e293b',
          700: '#334155',
        },
        astra: {
          blue: '#3b82f6',
          indigo: '#6366f1',
          violet: '#8b5cf6',
          cyan: '#06b6d4',
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#f43f5e'
        }
      }
    },
  },
  plugins: [],
}
