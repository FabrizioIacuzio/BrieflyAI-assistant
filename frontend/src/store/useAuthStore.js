import { create } from "zustand";

export const useAuthStore = create((set) => ({
  token: null,
  username: null,
  email: null,
  picture: null,   // Google profile photo URL
  login: (token, username, { email = null, picture = null } = {}) =>
    set({ token, username, email, picture }),
  logout: () => set({ token: null, username: null, email: null, picture: null }),
}));
