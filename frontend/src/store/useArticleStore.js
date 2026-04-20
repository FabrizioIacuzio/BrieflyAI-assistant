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
  isGmail: false,
  filter: "Manual Selection",
  duration: 3,
  voiceAccent: "us",
  selectedIds: new Set(),
  starredIds: new Set(),
  search: "",

  fetchArticles: async () => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.get("/articles/gmail");
      set({ articles: data.articles, source: data.source, isGmail: true, loading: false });
    } catch (e) {
      // Gmail not connected (401) or error — fall back to news feed
      if (e.response?.status === 401) {
        set({ error: "gmail_auth", loading: false, articles: [], isGmail: false });
      } else {
        set({ error: e.message, loading: false, isGmail: false });
      }
    }
  },

  refreshArticles: async () => {
    set({ loading: true });
    try {
      const { data } = await api.get("/articles/gmail");
      set({ articles: data.articles, source: data.source, isGmail: true, loading: false });
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
    // For Gmail inbox, auto-select by topic match
    const { articles } = get();
    const lower = filterName.toLowerCase();
    const TOPIC_MAP = {
      "market volatility":     (a) => a.urgency_kw >= 6,
      "tech & ai sector":      (a) => a.topic === "AI & Tech",
      "bullish sentiment":     (a) => a.is_financial,
      "central banks & rates": (a) => a.topic === "Central Banks",
      "global energy":         (a) => a.topic === "Energy",
      "last 24 hours":         (a) => true,
      "major sources only":    (a) => a.is_financial,
    };
    const matcher = TOPIC_MAP[lower] ?? (() => false);
    const ids = articles.filter(matcher).map((a) => a.ID);
    set({ selectedIds: new Set(ids) });
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

  getSelectedArticles: () => {
    const { articles, selectedIds } = get();
    return articles.filter((a) => selectedIds.has(a.ID));
  },

  filteredArticles: () => {
    const { articles, search } = get();
    if (!search) return articles;
    const q = search.toLowerCase();
    return articles.filter(
      (a) =>
        a.Subject?.toLowerCase().includes(q) ||
        a.Sender?.toLowerCase().includes(q)
    );
  },
}));
