import axios from "axios";
import { useAuthStore } from "../store/useAuthStore";

// In production (Vercel), VITE_API_URL points to the backend host.
// In dev, leave it unset — Vite proxies /api → localhost:8000.
const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : "/api";

const api = axios.create({ baseURL: BASE });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);

export const apiBase = BASE;
export const backendOrigin = import.meta.env.VITE_API_URL || "";

export default api;
