import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  username: string | null;
  role: string | null;
  setAuth: (token: string, refresh: string, username: string, role: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      username: null,
      role: null,
      setAuth: (token, refreshToken, username, role) =>
        set({ token, refreshToken, username, role }),
      logout: () => set({ token: null, refreshToken: null, username: null, role: null }),
    }),
    { name: 'aiz-auth' }
  )
);
