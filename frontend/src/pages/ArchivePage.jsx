import { useEffect, useState } from "react";
import { useBriefingStore } from "../store/useBriefingStore";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, Cell, ReferenceLine,
  ScatterChart, Scatter, ZAxis,
} from "recharts";

const SENTIMENT_COLORS = { Positive: "#059669", Neutral: "#d97706", Negative: "#dc2626" };

function SentimentChart({ data }) {
  const sorted = [...data].sort((a, b) => a.sentiment_score - b.sentiment_score);
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, sorted.length * 44)}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 10, right: 60, top: 10, bottom: 10 }}>
        <XAxis type="number" domain={[-1.2, 1.2]} tickFormatter={(v) => v.toFixed(1)} />
        <YAxis type="category" dataKey="label" width={180} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => v.toFixed(2)} />
        <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="3 3" />
        <Bar dataKey="sentiment_score" radius={3}>
          {sorted.map((e, i) => (
            <Cell key={i} fill={SENTIMENT_COLORS[e.sentiment] || "#64748b"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function ImpactChart({ data }) {
  const sorted = [...data].sort((a, b) => a.market_impact - b.market_impact);
  const colorFromImpact = (v) => {
    const t = (v - 1) / 9;
    const r = Math.round(253 + (220 - 253) * t);
    const g = Math.round(230 + (38 - 230) * t);
    const b = Math.round(138 + (38 - 138) * t);
    return `rgb(${r},${g},${b})`;
  };
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, sorted.length * 44)}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 10, right: 60, top: 10, bottom: 10 }}>
        <XAxis type="number" domain={[0, 12]} />
        <YAxis type="category" dataKey="label" width={180} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => `${v}/10`} />
        <Bar dataKey="market_impact" radius={3}>
          {sorted.map((e, i) => (
            <Cell key={i} fill={colorFromImpact(e.market_impact)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function UrgencyScatterChart({ data }) {
  const grouped = {};
  data.forEach((d) => {
    const s = d.sentiment || "Neutral";
    if (!grouped[s]) grouped[s] = [];
    grouped[s].push({ x: d.urgency + Math.random() * 0.36 - 0.18, y: d.market_impact + Math.random() * 0.36 - 0.18, name: d.label });
  });
  return (
    <ResponsiveContainer width="100%" height={360}>
      <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
        <XAxis dataKey="x" type="number" domain={[0.5, 11]} label={{ value: "Urgency", position: "bottom" }} tickCount={10} />
        <YAxis dataKey="y" type="number" domain={[0.5, 11]} label={{ value: "Market Impact", angle: -90, position: "insideLeft" }} tickCount={10} />
        <ZAxis range={[60, 60]} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} content={({ payload }) => {
          if (!payload?.length) return null;
          return (
            <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs shadow">
              {payload[0]?.payload?.name}
            </div>
          );
        }} />
        <Legend />
        <ReferenceLine x={5.5} stroke="#d1d5db" strokeDasharray="4 4" />
        <ReferenceLine y={5.5} stroke="#d1d5db" strokeDasharray="4 4" />
        {Object.entries(grouped).map(([sentiment, points]) => (
          <Scatter key={sentiment} name={sentiment} data={points}
            fill={SENTIMENT_COLORS[sentiment] || "#64748b"} fillOpacity={0.85} />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function TrendChart({ archive }) {
  const data = [...archive].reverse().map((b) => {
    const analytics = b.analytics || [];
    const avgSentiment = analytics.length
      ? analytics.reduce((s, r) => s + (r.sentiment_score || 0), 0) / analytics.length : 0;
    const avgUrgency = analytics.length
      ? analytics.reduce((s, r) => s + (r.urgency || 5), 0) / analytics.length : 5;
    const avgImpact = analytics.length
      ? analytics.reduce((s, r) => s + (r.market_impact || 5), 0) / analytics.length : 5;
    return {
      name: new Date(b.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }),
      sentiment: +avgSentiment.toFixed(2),
      urgency: +avgUrgency.toFixed(1),
      impact: +avgImpact.toFixed(1),
    };
  });

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
        <YAxis yAxisId="left" domain={[-1, 1]} label={{ value: "Sentiment", angle: -90, position: "insideLeft", style: { fontSize: 10 } }} />
        <YAxis yAxisId="right" orientation="right" domain={[0, 10]} label={{ value: "Score /10", angle: 90, position: "insideRight", style: { fontSize: 10 } }} />
        <Tooltip />
        <Legend />
        <Line yAxisId="left" type="monotone" dataKey="sentiment" stroke="#2563EB" strokeWidth={2} dot={{ r: 4 }} name="Avg Sentiment" />
        <Line yAxisId="right" type="monotone" dataKey="urgency" stroke="#7C3AED" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4 }} name="Avg Urgency" />
        <Line yAxisId="right" type="monotone" dataKey="impact" stroke="#059669" strokeWidth={2} strokeDasharray="3 3" dot={{ r: 4 }} name="Avg Impact" />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function ArchivePage() {
  const { archive, archiveLoading, fetchArchive, fetchTrendAnalysis, trendAnalysis, trendLoading } = useBriefingStore();
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("script");

  useEffect(() => { fetchArchive(); }, []);

  const briefing = selected != null ? archive[selected] : null;

  const analyticsData = briefing?.analytics?.map((r) => ({
    label: (r.subject || r.one_line_summary || "").slice(0, 42) + "…",
    sentiment: r.sentiment,
    sentiment_score: r.sentiment_score,
    urgency: r.urgency,
    market_impact: r.market_impact,
  })) || [];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <h1 className="text-xl font-bold text-slate-900">Archive</h1>

      {/* Trend chart (2+ briefings) */}
      {archive.length >= 2 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="label">Trend over time</p>
            <button
              onClick={fetchTrendAnalysis}
              disabled={trendLoading}
              className="btn-ghost text-xs"
            >
              {trendLoading ? "Analysing…" : "✨ Detect trends with AI"}
            </button>
          </div>
          <TrendChart archive={archive} />
          {trendAnalysis && (
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl p-4">
              <p className="label mb-2">AI Trend Insights</p>
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{trendAnalysis}</p>
            </div>
          )}
        </div>
      )}

      {/* Archive grid */}
      {archiveLoading ? (
        <div className="card p-8 text-center text-slate-400">Loading archive…</div>
      ) : archive.length === 0 ? (
        <div className="card p-8 text-center text-slate-400">
          No archived briefings yet. Generate your first briefing from the Inbox.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {archive.map((b, i) => (
            <div
              key={b.id}
              className={`card p-4 cursor-pointer transition-all hover:shadow-md hover:border-blue-200 ${
                selected === i ? "border-blue-400 bg-blue-50" : ""
              }`}
              onClick={() => setSelected(selected === i ? null : i)}
            >
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-semibold text-slate-800">
                  {new Date(b.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
                  <span className="text-slate-400 font-normal ml-1">
                    {new Date(b.created_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </p>
                {b.feedback === "up" && <span title="Marked useful">👍</span>}
                {b.feedback === "down" && <span title="Marked not useful">👎</span>}
                {b.scheduled && <span className="text-xs bg-purple-100 text-purple-600 px-1.5 rounded">⏰ Auto</span>}
              </div>
              <p className="text-xs text-slate-400 mb-3">
                {b.sources_count} sources · {b.duration_minutes} min
              </p>
              <div className="flex flex-wrap gap-1">
                {(b.clusters?.clusters || [])
                  .sort((a, b) => (a.priority || 99) - (b.priority || 99))
                  .slice(0, 3)
                  .map((c) => (
                    <span key={c.cluster_name} className="text-xs bg-blue-50 text-blue-700 border border-blue-100 rounded px-2 py-0.5 font-medium">
                      {c.cluster_name}
                    </span>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Briefing detail */}
      {briefing && (
        <div className="card overflow-hidden">
          <div className="border-b border-slate-100">
            <div className="flex border-b border-slate-100 px-2">
              {["script", "analytics", "debate"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-5 py-3 text-sm font-medium capitalize transition-colors ${
                    activeTab === tab
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          <div className="p-6">
            {activeTab === "script" && (
              <div className="space-y-4">
                {briefing.audio_url && (
                  <audio controls className="w-full" src={briefing.audio_url} />
                )}
                <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 text-sm text-slate-700 leading-relaxed max-h-96 overflow-y-auto">
                  {briefing.script}
                </div>
              </div>
            )}

            {activeTab === "analytics" && analyticsData.length > 0 && (
              <div className="space-y-8">
                <div>
                  <p className="label mb-3">Sentiment Score</p>
                  <SentimentChart data={analyticsData} />
                </div>
                <div>
                  <p className="label mb-3">Market Impact</p>
                  <ImpactChart data={analyticsData} />
                </div>
                <div>
                  <p className="label mb-3">Urgency vs Market Impact</p>
                  <UrgencyScatterChart data={analyticsData} />
                </div>
              </div>
            )}

            {activeTab === "debate" && (
              briefing.debate ? (
                <div className="space-y-3">
                  {[
                    { key: "cro",     label: "Chief Risk Officer", cls: "border-l-red-500 bg-red-50 text-red-700" },
                    { key: "trader",  label: "Trader",             cls: "border-l-green-500 bg-green-50 text-green-700" },
                    { key: "analyst", label: "Research Analyst",   cls: "border-l-blue-500 bg-blue-50 text-blue-700" },
                  ].map(({ key, label, cls }) => (
                    <div key={key} className={`border border-l-4 border-slate-200 rounded-lg p-4 ${cls.split(" ")[0]} ${cls.split(" ")[1]}`}>
                      <p className={`text-xs font-bold uppercase tracking-wider mb-1 ${cls.split(" ")[2]}`}>{label}</p>
                      <p className="text-sm text-slate-700 leading-relaxed">{briefing.debate[key]}</p>
                    </div>
                  ))}
                  {briefing.debate.consensus && (
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Consensus</p>
                      <p className="text-sm text-slate-600 italic">{briefing.debate.consensus}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No debate generated for this briefing.</p>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
