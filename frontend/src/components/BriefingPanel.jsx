import { useState, useRef } from "react";
import {
  Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ReferenceLine,
  ScatterChart, Scatter, Legend,
} from "recharts";
import { useBriefingStore } from "../store/useBriefingStore";
import { useAuthStore } from "../store/useAuthStore";

const STEP_LABELS = [
  "Clustering & ranking articles",
  "Generating briefing script",
  "Synthesising audio",
  "Running AI analysis",
];

const SENTIMENT_COLORS = {
  Positive: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", hex: "#10B981" },
  Neutral:  { bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-200",   hex: "#F59E0B" },
  Negative: { bg: "bg-red-50",     text: "text-red-700",     border: "border-red-200",      hex: "#EF4444" },
};

const DEBATE_PERSONAS = [
  { key: "cro",     label: "Chief Risk Officer", icon: "⚠", borderColor: "border-l-rose-400",   chipBg: "bg-rose-50",   chipText: "text-rose-700" },
  { key: "trader",  label: "Active Trader",      icon: "↗", borderColor: "border-l-teal-400",   chipBg: "bg-teal-50",   chipText: "text-teal-700" },
  { key: "analyst", label: "Research Analyst",   icon: "◎", borderColor: "border-l-indigo-400", chipBg: "bg-indigo-50", chipText: "text-indigo-700" },
];

// ── Pipeline progress ─────────────────────────────────────────────────────────

function PipelineProgress({ steps }) {
  return (
    <div className="card p-6 space-y-3">
      <p className="label mb-3">Generating briefing</p>
      {STEP_LABELS.map((label, i) => {
        const step   = steps[i];
        const status = step?.status || "pending";
        return (
          <div key={i} className="flex items-center gap-3">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
              status === "done"    ? "bg-green-100 text-green-600" :
              status === "running" ? "bg-blue-100 text-blue-600"  :
                                    "bg-slate-100 text-slate-400"
            }`}>
              {status === "done" ? "✓" : status === "running" ? "…" : i + 1}
            </div>
            <span className={`text-sm ${
              status === "done"    ? "text-slate-600"          :
              status === "running" ? "text-blue-700 font-medium" :
                                    "text-slate-400"
            }`}>{label}</span>
            {status === "running" && (
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Audio player ──────────────────────────────────────────────────────────────

function AudioPlayer({ audioUrl }) {
  const token   = useAuthStore((s) => s.token);
  const authUrl = audioUrl
    ? `${audioUrl}?token=${encodeURIComponent(token || "")}`
    : null;
  const audioRef = useRef(null);
  const [speed, setSpeed] = useState(1);

  const setRate = (r) => {
    setSpeed(r);
    if (audioRef.current) audioRef.current.playbackRate = r;
  };

  if (!authUrl) return null;
  return (
    <div className="bg-slate-800 rounded-xl p-4 space-y-3">
      <audio ref={audioRef} controls className="w-full" src={authUrl}>
        Your browser does not support audio.
      </audio>
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Speed:</span>
        {[0.75, 1, 1.25, 1.5, 2].map((r) => (
          <button
            key={r}
            onClick={() => setRate(r)}
            className={`text-xs px-2 py-0.5 rounded font-medium transition-colors ${
              speed === r ? "bg-blue-500 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            {r}×
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Insights / charts panel ───────────────────────────────────────────────────

function InsightsPanel({ analytics }) {
  if (!analytics?.length) return null;

  const pos = analytics.filter(r => r.sentiment === "Positive").length;
  const neu = analytics.filter(r => r.sentiment === "Neutral").length;
  const neg = analytics.filter(r => r.sentiment === "Negative").length;
  const avgImpact   = (analytics.reduce((s, r) => s + r.market_impact, 0) / analytics.length).toFixed(1);
  const avgUrgency  = (analytics.reduce((s, r) => s + r.urgency, 0) / analytics.length).toFixed(1);

  // Chart 1 — Sentiment score per article, sorted ascending
  const sentimentBars = [...analytics]
    .sort((a, b) => a.sentiment_score - b.sentiment_score)
    .map(r => ({
      name:  (r.one_line_summary || "").slice(0, 40) + "…",
      score: parseFloat((r.sentiment_score ?? 0).toFixed(2)),
      fill:  SENTIMENT_COLORS[r.sentiment]?.hex || "#94A3B8",
    }));

  // Chart 2 — Urgency vs Market Impact scatter, grouped by sentiment with jitter
  const jitter = (i, slot) => ((i * 7 + slot * 13) % 19) / 100 - 0.09;
  const scatterGroups = { Positive: [], Neutral: [], Negative: [] };
  analytics.forEach((r, i) => {
    const s = r.sentiment in scatterGroups ? r.sentiment : "Neutral";
    scatterGroups[s].push({
      x:     +(r.urgency      + jitter(i, 0)).toFixed(2),
      y:     +(r.market_impact + jitter(i, 1)).toFixed(2),
      label: (r.one_line_summary || "").slice(0, 55),
      rawX:  r.urgency,
      rawY:  r.market_impact,
    });
  });

  // Chart 3 — Market impact ranking, heat-coloured
  const impactBars = [...analytics]
    .sort((a, b) => a.market_impact - b.market_impact)
    .map(r => ({
      name:   (r.one_line_summary || "").slice(0, 40) + "…",
      impact: r.market_impact,
      fill:   r.market_impact >= 8 ? "#dc2626" : r.market_impact >= 5 ? "#f59e0b" : "#fde68a",
    }));

  const chartH    = Math.max(260, analytics.length * 44);
  const axisStyle = { tick: { fontSize: 11, fill: "#94A3B8" } };
  const gridStyle = { strokeDasharray: "3 3", stroke: "#E2E8F0" };
  const ttStyle   = { fontSize: 12, borderRadius: 8, border: "1px solid #E2E8F0" };

  const KPI_CARDS = [
    { value: pos,                label: "Positive",    color: "#059669", bg: "#ecfdf5" },
    { value: neu,                label: "Neutral",     color: "#d97706", bg: "#fffbeb" },
    { value: neg,                label: "Negative",    color: "#dc2626", bg: "#fef2f2" },
    { value: `${avgImpact}/10`,  label: "Avg Impact",  color: "#2563eb", bg: "#eff6ff" },
    { value: `${avgUrgency}/10`, label: "Avg Urgency", color: "#7c3aed", bg: "#f5f3ff" },
  ];

  return (
    <div className="space-y-6">
      <p className="label text-base">Insights</p>

      {/* KPI cards */}
      <div className="grid grid-cols-5 gap-3">
        {KPI_CARDS.map(({ value, label, color, bg }) => (
          <div key={label} className="rounded-xl p-4 border border-slate-100" style={{ background: bg }}>
            <p className="text-2xl font-black" style={{ color }}>{value}</p>
            <p className="text-xs font-semibold text-slate-500 mt-1 uppercase tracking-wide">{label}</p>
          </div>
        ))}
      </div>

      {/* Chart 1: Sentiment score horizontal bar */}
      <div className="card p-4">
        <p className="label mb-1">Sentiment Score</p>
        <p className="text-xs text-slate-400 mb-3">← Bearish &nbsp;|&nbsp; Neutral &nbsp;|&nbsp; Bullish →</p>
        <ResponsiveContainer width="100%" height={chartH}>
          <BarChart layout="vertical" data={sentimentBars}
            margin={{ top: 4, right: 64, bottom: 4, left: 8 }}>
            <CartesianGrid {...gridStyle} horizontal={false} />
            <XAxis type="number" domain={[-1.2, 1.2]} {...axisStyle} />
            <YAxis type="category" dataKey="name" width={200}
              tick={{ fontSize: 11, fill: "#64748B" }} />
            <Tooltip formatter={v => [v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2), "Score"]}
              contentStyle={ttStyle} />
            <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <Bar dataKey="score" radius={[0, 3, 3, 0]}
              label={{ position: "right", fontSize: 11, fill: "#64748B",
                formatter: v => v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2) }}>
              {sentimentBars.map((e, i) => <Cell key={i} fill={e.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Chart 2: Urgency vs Market Impact scatter */}
      <div className="card p-4">
        <p className="label mb-3">Urgency vs Market Impact</p>
        <ResponsiveContainer width="100%" height={420}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 48, left: 10 }}>
            <CartesianGrid {...gridStyle} />
            <XAxis type="number" dataKey="x" domain={[0, 11]} name="Urgency"
              label={{ value: "Urgency  (1 = Long-term · 10 = Breaking News)",
                position: "insideBottom", offset: -12, fontSize: 11, fill: "#94A3B8" }}
              {...axisStyle} />
            <YAxis type="number" dataKey="y" domain={[0, 11]} name="Impact"
              label={{ value: "Market Impact  (1 = Minimal · 10 = Major Move)",
                angle: -90, position: "insideLeft", offset: 14, fontSize: 11, fill: "#94A3B8" }}
              {...axisStyle} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }}
              content={({ payload }) => {
                const d = payload?.[0]?.payload;
                if (!d) return null;
                return (
                  <div className="bg-white border border-slate-200 rounded-lg p-3 text-xs shadow-sm max-w-xs">
                    <p className="font-semibold text-slate-800 mb-1">{d.label}</p>
                    <p className="text-slate-500">Urgency: <b>{d.rawX}/10</b> · Impact: <b>{d.rawY}/10</b></p>
                  </div>
                );
              }}
            />
            <ReferenceLine x={5.5} stroke="#d1d5db" strokeDasharray="4 4" />
            <ReferenceLine y={5.5} stroke="#d1d5db" strokeDasharray="4 4" />
            <Legend verticalAlign="bottom" height={32} wrapperStyle={{ fontSize: 12 }} />
            {Object.entries(scatterGroups).map(([sentiment, data]) => (
              <Scatter key={sentiment} name={sentiment} data={data}
                fill={SENTIMENT_COLORS[sentiment]?.hex || "#94A3B8"} opacity={0.88} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Chart 3: Market impact ranking */}
      <div className="card p-4">
        <p className="label mb-3">Market Impact Score  (LLM-rated)</p>
        <ResponsiveContainer width="100%" height={chartH}>
          <BarChart layout="vertical" data={impactBars}
            margin={{ top: 4, right: 72, bottom: 4, left: 8 }}>
            <CartesianGrid {...gridStyle} horizontal={false} />
            <XAxis type="number" domain={[0, 12]} {...axisStyle} />
            <YAxis type="category" dataKey="name" width={200}
              tick={{ fontSize: 11, fill: "#64748B" }} />
            <Tooltip formatter={v => [`${v} / 10`, "Impact"]} contentStyle={ttStyle} />
            <Bar dataKey="impact" radius={[0, 3, 3, 0]}
              label={{ position: "right", fontSize: 11, fill: "#64748B",
                formatter: v => `${v} / 10` }}>
              {impactBars.map((e, i) => <Cell key={i} fill={e.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Debate panel ──────────────────────────────────────────────────────────────

function DebatePanel({ briefingId }) {
  const { runDebate, current } = useBriefingStore();
  const [loading, setLoading] = useState(false);
  const debate = current?.debate;

  const handleRun = async () => {
    setLoading(true);
    try { await runDebate(briefingId); }
    finally { setLoading(false); }
  };

  if (!debate) {
    return (
      <div>
        <button onClick={handleRun} disabled={loading} className="btn-ghost text-sm">
          {loading ? "Convening war room…" : "⚔ Run multi-agent debate"}
        </button>
        <p className="text-xs text-slate-400 mt-1">CRO · Trader · Analyst debate this briefing</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {DEBATE_PERSONAS.map(({ key, label, icon, borderColor, chipBg, chipText }) => (
        <div key={key} className={`bg-white border border-slate-100 border-l-4 ${borderColor} rounded-lg p-4 shadow-sm`}>
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${chipBg} ${chipText}`}>
              {icon} {label}
            </span>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed">{debate[key]}</p>
        </div>
      ))}
      {debate.consensus && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Consensus</p>
          <p className="text-sm text-slate-600 leading-relaxed">{debate.consensus}</p>
        </div>
      )}
      <button onClick={handleRun} disabled={loading} className="btn-ghost text-xs">
        {loading ? "Regenerating…" : "↺ Regenerate"}
      </button>
    </div>
  );
}

// ── Feedback panel ────────────────────────────────────────────────────────────

function FeedbackPanel({ briefingId }) {
  const { submitFeedback, current } = useBriefingStore();
  const [note, setNote]       = useState("");
  const [hovered, setHovered] = useState(0);
  const [saved, setSaved]     = useState(false);
  const feedback = current?.feedback; // 1–5 integer or null

  const handleRate = async (rating) => {
    await submitFeedback(briefingId, rating, "");
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleNoteBlur = () => {
    if (note.trim() && feedback) submitFeedback(briefingId, feedback, note);
  };

  const displayRating = hovered || feedback || 0;

  return (
    <div>
      <p className="label mb-3">Rate this briefing</p>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => handleRate(star)}
            className={`text-2xl leading-none transition-all hover:scale-110 ${
              star <= displayRating ? "text-amber-400" : "text-slate-200 hover:text-amber-200"
            }`}
          >★</button>
        ))}
      </div>
      {saved && <p className="text-sm text-green-600 mt-2">Thanks for your feedback!</p>}
      {!saved && feedback != null && feedback <= 2 && (
        <div className="mt-3">
          <input
            className="input text-sm"
            placeholder="What could be improved? (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={handleNoteBlur}
          />
        </div>
      )}
    </div>
  );
}

// ── Chat panel ────────────────────────────────────────────────────────────────

function ChatPanel({ briefingId }) {
  const { chatMessages, sendChat } = useBriefingStore();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) return;
    const q = question;
    setQuestion("");
    setLoading(true);
    await sendChat(briefingId, q);
    setLoading(false);
  };

  return (
    <div className="space-y-3">
      {chatMessages.map((m, i) => (
        <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
          <div className={`max-w-[80%] text-sm rounded-xl px-4 py-2.5 leading-relaxed ${
            m.role === "user" ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
          }`}>
            {m.content}
          </div>
        </div>
      ))}
      {loading && (
        <div className="flex justify-start">
          <div className="bg-slate-100 text-slate-400 text-sm rounded-xl px-4 py-2.5">Thinking…</div>
        </div>
      )}
      <div className="flex gap-2">
        <input
          className="input flex-1 text-sm"
          placeholder="Ask about the briefing…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
        />
        <button onClick={handleAsk} disabled={!question.trim() || loading} className="btn-primary px-4">
          Ask
        </button>
      </div>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function BriefingPanel() {
  const { generating, steps, current, genError, sendEmail } = useBriefingStore();
  const [emailSent, setEmailSent]     = useState(false);
  const [emailError, setEmailError]   = useState("");
  const [emailLoading, setEmailLoading] = useState(false);

  const handleEmail = async () => {
    setEmailLoading(true);
    setEmailError("");
    try {
      await sendEmail(current.id);
      setEmailSent(true);
    } catch (e) {
      setEmailError(e.response?.data?.detail || e.message);
    } finally {
      setEmailLoading(false);
    }
  };

  const alerts = current?.analytics?.filter(
    (r) => r.urgency >= 8 || r.market_impact >= 8
  ) || [];

  return (
    <div className="space-y-5">
      {generating && <PipelineProgress steps={steps} />}

      {genError && (
        <div className="card p-4 border-red-200 bg-red-50">
          <p className="text-sm text-red-600">Generation failed: {genError}</p>
        </div>
      )}

      {current && (
        <>
          {/* Risk alert */}
          {alerts.length > 0 && (
            <div className="bg-red-50 border border-l-4 border-l-red-500 border-red-200 rounded-xl p-4">
              <p className="text-xs font-bold text-red-700 uppercase tracking-wider mb-2">⚠ High-Impact Alert</p>
              <ul className="space-y-1">
                {alerts.map((r, i) => (
                  <li key={i} className="text-sm text-red-800">
                    {r.one_line_summary}
                    <span className="ml-2 text-xs text-red-500">[U{r.urgency}/10 · I{r.market_impact}/10]</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="card overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
              <div>
                <p className="label">Latest Briefing</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {new Date(current.created_at).toLocaleString()} · {current.duration_minutes} min · {current.sources_count} sources
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={handleEmail} disabled={emailLoading || emailSent} className="btn-ghost text-xs">
                  {emailSent ? "✓ Sent" : emailLoading ? "Sending…" : "📧 Email to me"}
                </button>
                {current.audio_url && (
                  <a href={current.audio_url} download className="btn-ghost text-xs">↓ MP3</a>
                )}
              </div>
            </div>
            {emailError && (
              <div className="px-6 py-2 bg-red-50 border-b border-red-100">
                <p className="text-xs text-red-600">{emailError}</p>
              </div>
            )}

            <div className="p-6 space-y-6">
              {/* Audio */}
              <AudioPlayer audioUrl={current.audio_url} />

              {/* Script + Topics */}
              <div className="flex gap-5">
                <div className="flex-1">
                  <p className="label mb-2">Script</p>
                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 text-sm text-slate-700 leading-relaxed max-h-60 overflow-y-auto">
                    {current.script}
                  </div>
                  <a
                    href={"data:text/plain," + encodeURIComponent(current.script)}
                    download={`briefing_${current.id}.txt`}
                    className="text-xs text-blue-600 hover:underline mt-2 block"
                  >
                    ↓ Download script
                  </a>
                </div>
                <div className="w-40 flex-shrink-0">
                  <p className="label mb-2">Topics</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(current.clusters?.clusters || [])
                      .sort((a, b) => (a.priority || 99) - (b.priority || 99))
                      .map((c) => (
                        <span key={c.cluster_name} className="text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-md px-2 py-0.5 font-medium">
                          {c.cluster_name}
                        </span>
                      ))}
                  </div>
                </div>
              </div>

              {/* Article Scores */}
              {current.analytics?.length > 0 && (
                <div>
                  <p className="label mb-3">Article Scores</p>
                  <div className="space-y-2">
                    {current.analytics.map((r, i) => {
                      const sc = SENTIMENT_COLORS[r.sentiment] || SENTIMENT_COLORS.Neutral;
                      return (
                        <div key={i} className="flex items-center gap-3 text-sm">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${sc.bg} ${sc.text} border ${sc.border} flex-shrink-0`}>
                            {r.sentiment}
                          </span>
                          <span className="flex-1 truncate text-slate-700">{r.one_line_summary}</span>
                          <span className="text-xs text-slate-400 flex-shrink-0">U{r.urgency} · I{r.market_impact}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <hr className="border-slate-100" />

              {/* ── INSIGHTS / CHARTS ── */}
              <InsightsPanel analytics={current.analytics} />

              <hr className="border-slate-100" />

              {/* Feedback */}
              <FeedbackPanel briefingId={current.id} />

              {/* Debate */}
              <div>
                <p className="label mb-3">Multi-Agent Analysis</p>
                <DebatePanel briefingId={current.id} />
              </div>

              {/* Chat */}
              <div>
                <p className="label mb-3">Chat about this briefing</p>
                <ChatPanel briefingId={current.id} />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
