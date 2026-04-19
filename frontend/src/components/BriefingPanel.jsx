import { useState, useRef } from "react";
import { useBriefingStore } from "../store/useBriefingStore";

const STEP_LABELS = [
  "Clustering & ranking articles",
  "Generating briefing script",
  "Synthesising audio",
  "Running AI analysis",
];

const SENTIMENT_COLORS = {
  Positive: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  Neutral:  { bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-200" },
  Negative: { bg: "bg-red-50",     text: "text-red-700",     border: "border-red-200" },
};

const DEBATE_PERSONAS = [
  { key: "cro",     label: "Chief Risk Officer", icon: "⚠",  color: "border-l-red-500",    bg: "bg-red-50",    text: "text-red-700" },
  { key: "trader",  label: "Trader",             icon: "📈", color: "border-l-green-500",  bg: "bg-green-50",  text: "text-green-700" },
  { key: "analyst", label: "Research Analyst",   icon: "📊", color: "border-l-blue-500",   bg: "bg-blue-50",   text: "text-blue-700" },
];

function PipelineProgress({ steps }) {
  return (
    <div className="card p-6 space-y-3">
      <p className="label mb-3">Generating briefing</p>
      {STEP_LABELS.map((label, i) => {
        const step = steps[i];
        const status = step?.status || "pending";
        return (
          <div key={i} className="flex items-center gap-3">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
              status === "done"    ? "bg-green-100 text-green-600" :
              status === "running" ? "bg-blue-100 text-blue-600" :
                                    "bg-slate-100 text-slate-400"
            }`}>
              {status === "done" ? "✓" : status === "running" ? "…" : i + 1}
            </div>
            <span className={`text-sm ${
              status === "done"    ? "text-slate-600" :
              status === "running" ? "text-blue-700 font-medium" :
                                    "text-slate-400"
            }`}>
              {label}
            </span>
            {status === "running" && (
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function AudioPlayer({ audioUrl }) {
  const audioRef = useRef(null);
  const [speed, setSpeed] = useState(1);

  const setPlaybackRate = (rate) => {
    setSpeed(rate);
    if (audioRef.current) audioRef.current.playbackRate = rate;
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4 space-y-3">
      <audio ref={audioRef} controls className="w-full" src={audioUrl}>
        Your browser does not support audio.
      </audio>
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Speed:</span>
        {[0.75, 1, 1.25, 1.5, 2].map((r) => (
          <button
            key={r}
            onClick={() => setPlaybackRate(r)}
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
      {DEBATE_PERSONAS.map(({ key, label, icon, color, bg, text }) => (
        <div key={key} className={`${bg} border border-l-4 ${color} border-slate-200 rounded-lg p-4`}>
          <p className={`text-xs font-bold ${text} uppercase tracking-wider mb-1`}>{icon} {label}</p>
          <p className="text-sm text-slate-700 leading-relaxed">{debate[key]}</p>
        </div>
      ))}
      {debate.consensus && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Consensus</p>
          <p className="text-sm text-slate-600 italic leading-relaxed">{debate.consensus}</p>
        </div>
      )}
      <button onClick={handleRun} disabled={loading} className="btn-ghost text-xs">
        {loading ? "Regenerating…" : "↺ Regenerate debate"}
      </button>
    </div>
  );
}

function FeedbackPanel({ briefingId }) {
  const { submitFeedback, current } = useBriefingStore();
  const [note, setNote] = useState("");
  const feedback = current?.feedback;

  const handleFeedback = (val) => submitFeedback(briefingId, val, note);

  return (
    <div>
      <p className="label mb-3">Was this briefing useful?</p>
      <div className="flex gap-3">
        <button
          onClick={() => handleFeedback("up")}
          className={`text-2xl transition-transform hover:scale-110 ${
            feedback === "up" ? "opacity-100" : "opacity-40 hover:opacity-80"
          }`}
        >👍</button>
        <button
          onClick={() => handleFeedback("down")}
          className={`text-2xl transition-transform hover:scale-110 ${
            feedback === "down" ? "opacity-100" : "opacity-40 hover:opacity-80"
          }`}
        >👎</button>
      </div>
      {feedback === "up" && <p className="text-sm text-green-600 mt-2">Thanks! Glad it helped.</p>}
      {feedback === "down" && (
        <div className="mt-3 space-y-2">
          <input
            className="input text-sm"
            placeholder="What could be improved?"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => note && submitFeedback(briefingId, "down", note)}
          />
        </div>
      )}
    </div>
  );
}

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
            m.role === "user"
              ? "bg-blue-600 text-white"
              : "bg-slate-100 text-slate-700"
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

export default function BriefingPanel() {
  const { generating, steps, current, genError, sendEmail } = useBriefingStore();
  const [emailSent, setEmailSent] = useState(false);
  const [emailError, setEmailError] = useState("");
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

  // Risk alert: articles with urgency or impact >= 8
  const alerts = current?.analytics?.filter(
    (r) => r.urgency >= 8 || r.market_impact >= 8
  ) || [];

  return (
    <div className="space-y-5">
      {/* Generation progress */}
      {generating && <PipelineProgress steps={steps} />}

      {/* Error */}
      {genError && (
        <div className="card p-4 border-red-200 bg-red-50">
          <p className="text-sm text-red-600">Generation failed: {genError}</p>
        </div>
      )}

      {/* Completed briefing */}
      {current && (
        <>
          {/* Risk alert */}
          {alerts.length > 0 && (
            <div className="bg-red-50 border border-l-4 border-l-red-500 border-red-200 rounded-xl p-4">
              <p className="text-xs font-bold text-red-700 uppercase tracking-wider mb-2">
                ⚠ High-Impact Alert
              </p>
              <ul className="space-y-1">
                {alerts.map((r, i) => (
                  <li key={i} className="text-sm text-red-800">
                    {r.one_line_summary}
                    <span className="ml-2 text-xs text-red-500">
                      [U{r.urgency}/10 · I{r.market_impact}/10]
                    </span>
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
                  {new Date(current.created_at).toLocaleString()} ·{" "}
                  {current.duration_minutes} min · {current.sources_count} sources
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleEmail}
                  disabled={emailLoading || emailSent}
                  className="btn-ghost text-xs"
                >
                  {emailSent ? "✓ Sent" : emailLoading ? "Sending…" : "📧 Email to me"}
                </button>
                {current.audio_url && (
                  <a
                    href={current.audio_url}
                    download
                    className="btn-ghost text-xs"
                  >
                    ↓ MP3
                  </a>
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
              {current.audio_url && <AudioPlayer audioUrl={current.audio_url} />}

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
                        <span
                          key={c.cluster_name}
                          className="text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-md px-2 py-0.5 font-medium"
                        >
                          {c.cluster_name}
                        </span>
                      ))}
                  </div>
                </div>
              </div>

              {/* Analytics highlights */}
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
                          <span className="text-xs text-slate-400 flex-shrink-0">
                            U{r.urgency} · I{r.market_impact}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Divider */}
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
