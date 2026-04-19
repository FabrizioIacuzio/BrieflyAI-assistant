import { create } from "zustand";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import api from "../api/client";
import { useAuthStore } from "./useAuthStore";

const STEPS = [
  { label: "Clustering & ranking articles" },
  { label: "Generating briefing script" },
  { label: "Synthesising audio" },
  { label: "Running AI analysis" },
];

export const useBriefingStore = create((set, get) => ({
  // Generation state
  generating: false,
  jobId: null,
  steps: STEPS.map((s) => ({ ...s, status: "pending" })),
  genError: null,

  // Current briefing (latest generated)
  current: null,

  // Archive
  archive: [],
  archiveLoading: false,

  // Chat
  chatMessages: [],

  // Trend analysis
  trendAnalysis: null,
  trendLoading: false,

  startGeneration: async (articleIds, { duration, voiceAccent, filterUsed }) => {
    set({
      generating: true, genError: null,
      steps: STEPS.map((s) => ({ ...s, status: "pending" })),
      current: null,
      chatMessages: [],
    });

    try {
      const { data } = await api.post("/briefings/generate", {
        article_ids: articleIds,
        duration_minutes: duration,
        voice_accent: voiceAccent,
        filter_used: filterUsed,
      });
      const { job_id } = data;
      set({ jobId: job_id });

      const token = useAuthStore.getState().token;
      await new Promise((resolve, reject) => {
        fetchEventSource(`/api/briefings/stream/${job_id}?token=${token}`, {
          onmessage(ev) {
            try {
              const msg = JSON.parse(ev.data);
              const { step, status } = msg;

              if (step === "complete") {
                // Fetch the completed briefing
                api.get(`/briefings/${msg.briefing_id}`).then(({ data: b }) => {
                  set({ current: b, generating: false });
                  get().fetchArchive();
                });
                resolve();
                return;
              }

              if (step === "error") {
                set({ genError: msg.message, generating: false });
                reject(new Error(msg.message));
                return;
              }

              if (typeof step === "number") {
                set((s) => ({
                  steps: s.steps.map((st, i) =>
                    i === step ? { ...st, status } : st
                  ),
                }));
              }
            } catch (_) {}
          },
          onerror(err) {
            set({ genError: "Stream error", generating: false });
            reject(err);
          },
        });
      });
    } catch (e) {
      set({ genError: e.message, generating: false });
    }
  },

  fetchArchive: async () => {
    set({ archiveLoading: true });
    try {
      const { data } = await api.get("/briefings");
      set({ archive: data, archiveLoading: false });
    } catch (_) {
      set({ archiveLoading: false });
    }
  },

  submitFeedback: async (briefingId, feedback, note = "") => {
    await api.post(`/briefings/${briefingId}/feedback`, { feedback, note });
    set((s) => ({
      current: s.current?.id === briefingId ? { ...s.current, feedback, feedback_note: note } : s.current,
      archive: s.archive.map((b) =>
        b.id === briefingId ? { ...b, feedback, feedback_note: note } : b
      ),
    }));
  },

  sendChat: async (briefingId, question) => {
    set((s) => ({
      chatMessages: [...s.chatMessages, { role: "user", content: question }],
    }));
    try {
      const { data } = await api.post(`/briefings/${briefingId}/chat`, { question });
      set((s) => ({
        chatMessages: [...s.chatMessages, { role: "assistant", content: data.answer }],
      }));
    } catch (e) {
      set((s) => ({
        chatMessages: [...s.chatMessages, { role: "assistant", content: "Error: " + e.message }],
      }));
    }
  },

  runDebate: async (briefingId) => {
    const { data } = await api.post(`/briefings/${briefingId}/debate`);
    set((s) => ({
      current: s.current?.id === briefingId ? { ...s.current, debate: data } : s.current,
      archive: s.archive.map((b) => (b.id === briefingId ? { ...b, debate: data } : b)),
    }));
    return data;
  },

  sendEmail: async (briefingId) => {
    await api.post(`/briefings/${briefingId}/email`);
  },

  fetchTrendAnalysis: async () => {
    set({ trendLoading: true, trendAnalysis: null });
    try {
      const { data } = await api.post("/briefings/trend-analysis");
      set({ trendAnalysis: data.analysis, trendLoading: false });
    } catch (e) {
      set({ trendAnalysis: e.response?.data?.detail || e.message, trendLoading: false });
    }
  },

  clearChat: () => set({ chatMessages: [] }),
}));
