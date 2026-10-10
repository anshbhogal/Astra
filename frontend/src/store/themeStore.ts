import { create } from 'zustand';

export type Theme = 'dark' | 'light';

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const getInitialTheme = (): Theme => {
  const saved = localStorage.getItem('astra_theme');
  if (saved === 'light' || saved === 'dark') {
    return saved;
  }
  // Default to Voltage dark theme
  return 'dark';
};

const applyThemeToDOM = (theme: Theme) => {
  const root = document.documentElement;
  root.setAttribute('data-theme', theme);
  if (theme === 'dark') {
    root.classList.add('dark');
    root.classList.remove('light');
  } else {
    root.classList.add('light');
    root.classList.remove('dark');
  }
};

export const useThemeStore = create<ThemeState>((set) => {
  const initialTheme = getInitialTheme();
  applyThemeToDOM(initialTheme);

  return {
    theme: initialTheme,
    toggleTheme: () => {
      set((state) => {
        const nextTheme: Theme = state.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('astra_theme', nextTheme);
        applyThemeToDOM(nextTheme);
        return { theme: nextTheme };
      });
    },
    setTheme: (theme: Theme) => {
      localStorage.setItem('astra_theme', theme);
      applyThemeToDOM(theme);
      set({ theme });
    },
  };
});
