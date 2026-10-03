import { create } from 'zustand';

export type UserRole = 'ADMIN' | 'DEVELOPER' | 'TESTER' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
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

export const useAuthStore = create<AuthState>((set) => ({
  user: savedUser,
  token: savedToken,
  setAuth: (user, token) => {
    localStorage.setItem('astra_token', token);
    localStorage.setItem('astra_user', JSON.stringify(user));
    set({ user, token });
  },
  logout: () => {
    localStorage.removeItem('astra_token');
    localStorage.removeItem('astra_user');
    set({ user: null, token: null });
  },
}));
