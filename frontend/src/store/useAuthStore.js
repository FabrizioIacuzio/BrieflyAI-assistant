import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      username: null,
      email: null,
      picture: null,
      login: (token, username, { email = null, picture = null } = {}) =>
        set({ token, username, email, picture }),
      logout: () => set({ token: null, username: null, email: null, picture: null }),
    }),
    { name: "briefly-auth" }
  )
);
