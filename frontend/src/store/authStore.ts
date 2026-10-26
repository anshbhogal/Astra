import { create } from 'zustand';

export type UserRole = 'ADMIN' | 'DEVELOPER' | 'TESTER' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  must_change_password?: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isSessionExpired: boolean;
  setAuth: (user: User, token: string) => void;
  updateUser: (updatedUser: Partial<User>) => void;
  logout: () => void;
  setSessionExpired: (expired: boolean) => void;
}

const savedToken = localStorage.getItem('astra_token');
const savedUserStr = localStorage.getItem('astra_user');
let savedUser: User | null = null;

if (savedUserStr) {
  try {
    savedUser = JSON.parse(savedUserStr);
  } catch (e) {
    savedUser = null;
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: savedUser,
  token: savedToken,
  isSessionExpired: false,
  setAuth: (user, token) => {
    localStorage.setItem('astra_token', token);
    localStorage.setItem('astra_user', JSON.stringify(user));
    set({ user, token, isSessionExpired: false });
  },
  updateUser: (updatedUser) => {
    const current = get().user;
    if (!current) return;
    const merged = { ...current, ...updatedUser };
    localStorage.setItem('astra_user', JSON.stringify(merged));
    set({ user: merged });
  },
  logout: () => {
    localStorage.removeItem('astra_token');
    localStorage.removeItem('astra_user');
    set({ user: null, token: null, isSessionExpired: false });
  },
  setSessionExpired: (expired: boolean) => {
    set({ isSessionExpired: expired });
  },
}));
