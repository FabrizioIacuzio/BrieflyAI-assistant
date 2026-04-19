import { create } from "zustand";
import api from "../api/client";

const FILTER_OPTIONS = [
  "Manual Selection",
  "Market Volatility",
  "Tech & AI Sector",
  "Bullish Sentiment",
  "Central Banks & Rates",
  "Global Energy",
  "Last 24 Hours",
  "Major Sources Only",
];

export { FILTER_OPTIONS };

export const useArticleStore = create((set, get) => ({
  articles: [],
  source: null,
  loading: false,
  error: null,
  filter: "Manual Selection",
  duration: 3,
  voiceAccent: "us",
  selectedIds: new Set(),
  starredIds: new Set(),
  search: "",

  fetchArticles: async () => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.get("/articles");
      set({ articles: data.articles, source: data.source, loading: false });
    } catch (e) {
      set({ error: e.message, loading: false });
    }
  },

  refreshArticles: async () => {
    set({ loading: true });
    try {
      const { data } = await api.get("/articles/refresh");
      set({ articles: data.articles, source: data.source, loading: false });
    } catch (e) {
      set({ error: e.message, loading: false });
    }
  },

  applyFilter: async (filterName) => {
    set({ filter: filterName });
    if (filterName === "Manual Selection") {
      set({ selectedIds: new Set() });
      return;
    }
    try {
      const { data } = await api.get(`/articles/filter/${encodeURIComponent(filterName)}`);
      set({ selectedIds: new Set(data.selected_ids) });
    } catch (e) {
      console.error("Filter error:", e);
    }
  },

  toggleSelected: (id) => {
    const s = new Set(get().selectedIds);
    s.has(id) ? s.delete(id) : s.add(id);
    set({ selectedIds: s });
  },

  toggleStar: (id) => {
    const s = new Set(get().starredIds);
    s.has(id) ? s.delete(id) : s.add(id);
    set({ starredIds: s });
  },

  setSearch: (search) => set({ search }),
  setDuration: (duration) => set({ duration }),
  setVoiceAccent: (voiceAccent) => set({ voiceAccent }),

  filteredArticles: () => {
    const { articles, search, starredIds } = get();
    if (!search) return articles;
    const q = search.toLowerCase();
    return articles.filter(
      (a) =>
        a.Subject?.toLowerCase().includes(q) ||
        a.Sender?.toLowerCase().includes(q)
    );
  },
}));
