/**
 * Global auth state — Zustand store.
 * Persists tokens in localStorage so they survive page reloads.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

const useAuthStore = create(
  persist(
    (set, get) => ({
      // ── State ──────────────────────────────────────────────────── //
      user: null,
      org: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      // ── Actions ───────────────────────────────────────────────── //
      setAuth: ({ user, org, access_token, refresh_token }) => {
        // Sync to localStorage so axios interceptor can read them
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);
        // Set cookie so proxy.js (route guard) can read it server-side
        document.cookie = `bc_access_token=${access_token}; path=/; max-age=3600; SameSite=Lax`;
        set({
          user,
          org,
          accessToken: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true,
        });
      },

      updateAccessToken: (token) => {
        localStorage.setItem("access_token", token);
        set({ accessToken: token });
      },

      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        // Clear route-guard cookie
        document.cookie = "bc_access_token=; path=/; max-age=0";
        set({
          user: null,
          org: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      // Helpers
      getRole: () => get().user?.role || null,
      isCA: () => ["ca_owner", "ca_staff"].includes(get().user?.role),
      isClient: () => get().user?.role === "client",
      getOrgId: () => get().org?.id || null,
    }),
    {
      name: "bc_auth",
      // Only persist user/org info, NOT tokens (tokens are in localStorage directly)
      partialize: (state) => ({ user: state.user, org: state.org }),
    }
  )
);

export default useAuthStore;
