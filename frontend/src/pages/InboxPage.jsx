import { useState } from "react";
import { backendOrigin } from "../api/client";
import { useArticleStore, FILTER_OPTIONS } from "../store/useArticleStore";
import { useBriefingStore } from "../store/useBriefingStore";
import BriefingPanel from "../components/BriefingPanel";

const VOICE_OPTIONS = [
  { label: "American (en-US)", value: "us" },
  { label: "British (en-GB)", value: "co.uk" },
  { label: "Australian (en-AU)", value: "com.au" },
  { label: "Indian (en-IN)", value: "co.in" },
  { label: "Irish (en-IE)", value: "ie" },
];

const TOPIC_COLORS = {
  "AI & Tech": "bg-purple-100 text-purple-700",
  "Energy": "bg-amber-100 text-amber-700",
  "Central Banks": "bg-blue-100 text-blue-700",
  "Equities": "bg-green-100 text-green-700",
  "Commodities": "bg-orange-100 text-orange-700",
  "Macro": "bg-slate-100 text-slate-700",
  "Crypto": "bg-yellow-100 text-yellow-700",
  "Retail": "bg-pink-100 text-pink-700",
  "Other": "bg-slate-100 text-slate-500",
};

const URGENCY_COLORS = {
  9: "bg-red-100 text-red-700",
  8: "bg-red-100 text-red-700",
  7: "bg-orange-100 text-orange-700",
  5: "bg-amber-100 text-amber-700",
  3: "bg-slate-100 text-slate-500",
  2: "bg-slate-100 text-slate-400",
};

function urgencyColor(u) {
  if (u >= 8) return URGENCY_COLORS[9];
  if (u >= 6) return URGENCY_COLORS[7];
  if (u >= 4) return URGENCY_COLORS[5];
  return URGENCY_COLORS[2];
}

export default function InboxPage() {
  const {
    articles, loading, error, source, isGmail, filter, duration, voiceAccent,
    selectedIds, starredIds, search,
    applyFilter, toggleSelected, toggleStar, refreshArticles,
    setSearch, setDuration, setVoiceAccent, filteredArticles, getSelectedArticles,
  } = useArticleStore();

  const { startGeneration, startGenerationRaw, generating, current } = useBriefingStore();
  const [expandedId, setExpandedId] = useState(null);
  const [starredOnly, setStarredOnly] = useState(false);

  const displayed = filteredArticles().filter((a) =>
    starredOnly ? starredIds.has(a.ID) : true
  );

  const financial = displayed.filter((a) => a.is_financial);
  const noise = displayed.filter((a) => !a.is_financial);

  const handleGenerate = () => {
    if (isGmail) {
      const selected = getSelectedArticles();
      startGenerationRaw(selected, { duration, voiceAccent });
    } else {
      startGeneration(Array.from(selectedIds), { duration, voiceAccent, filterUsed: filter });
    }
  };

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Inbox</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {source && <span className="font-medium text-blue-600">{source} · </span>}
            {financial.length} financial · {noise.length} other · {selectedIds.size} selected
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={refreshArticles} className="btn-ghost text-xs">
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Controls row */}
      <div className="card p-4 flex flex-wrap gap-4 items-end">
        {/* Filter */}
        <div className="flex-1 min-w-[180px]">
          <label className="label block mb-1.5">Auto-select filter</label>
          <select
            className="select"
            value={filter}
            onChange={(e) => applyFilter(e.target.value)}
          >
            {FILTER_OPTIONS.map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
        </div>

        {/* Duration */}
        <div className="w-32">
          <label className="label block mb-1.5">Duration: {duration} min</label>
          <input
            type="range" min={1} max={10} step={1}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
        </div>

        {/* Voice */}
        <div className="w-44">
          <label className="label block mb-1.5">Voice accent</label>
          <select
            className="select"
            value={voiceAccent}
            onChange={(e) => setVoiceAccent(e.target.value)}
          >
            {VOICE_OPTIONS.map((v) => (
              <option key={v.value} value={v.value}>{v.label}</option>
            ))}
          </select>
        </div>

        {/* Search */}
        <div className="flex-1 min-w-[160px]">
          <label className="label block mb-1.5">Search</label>
          <input
            className="input"
            placeholder="Subject or sender…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Starred toggle */}
        <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer pb-0.5">
          <input
            type="checkbox"
            checked={starredOnly}
            onChange={(e) => setStarredOnly(e.target.checked)}
            className="accent-blue-600"
          />
          Starred only
        </label>
      </div>

      {/* Gmail reconnect prompt */}
      {error === "gmail_auth" && (
        <div className="card p-5 border-amber-200 bg-amber-50 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-amber-800">Gmail not connected</p>
            <p className="text-xs text-amber-600 mt-0.5">Sign out and sign back in with Google to load your inbox.</p>
          </div>
          <a href={`${backendOrigin}/api/auth/google`} className="btn-primary text-sm px-4 py-2">
            Reconnect Gmail →
          </a>
        </div>
      )}

      {/* Article table */}
      {loading ? (
        <div className="card p-10 text-center text-slate-400">Loading Gmail inbox…</div>
      ) : (
        <div className="card overflow-hidden">
          {/* Financial */}
          {financial.length > 0 && (
            <>
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-100">
                <span className="label">Financial ({financial.length})</span>
              </div>
              <ArticleList
                articles={financial}
                selectedIds={selectedIds}
                starredIds={starredIds}
                expandedId={expandedId}
                onToggle={toggleSelected}
                onStar={toggleStar}
                onExpand={setExpandedId}
              />
            </>
          )}
          {/* Noise */}
          {noise.length > 0 && (
            <>
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 border-t">
                <span className="label">Other ({noise.length})</span>
              </div>
              <ArticleList
                articles={noise}
                selectedIds={selectedIds}
                starredIds={starredIds}
                expandedId={expandedId}
                onToggle={() => {}}   // noise cannot be selected
                onStar={toggleStar}
                onExpand={setExpandedId}
                dimmed
              />
            </>
          )}
        </div>
      )}

      {/* Generate button */}
      <div className="flex justify-end">
        <button
          onClick={handleGenerate}
          disabled={selectedIds.size === 0 || generating}
          className="btn-primary px-8 py-3 text-base"
        >
          {generating ? "Generating…" : `Generate Audio Brief (${selectedIds.size} selected)`}
        </button>
      </div>

      {/* Briefing panel */}
      {(generating || current) && <BriefingPanel />}
    </div>
  );
}

function ArticleList({ articles, selectedIds, starredIds, expandedId, onToggle, onStar, onExpand, dimmed }) {
  return (
    <div>
      {articles.map((a, i) => {
        const isExpanded = expandedId === a.ID;
        const isSelected = selectedIds.has(a.ID);
        const isStarred = starredIds.has(a.ID);

        return (
          <div
            key={a.ID}
            className={`border-b border-slate-50 last:border-0 ${dimmed ? "opacity-60" : ""}`}
          >
            <div
              className={`flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors ${
                isSelected ? "bg-blue-50" : ""
              }`}
            >
              {/* Checkbox */}
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggle(a.ID)}
                disabled={dimmed}
                className="accent-blue-600 flex-shrink-0"
              />

              {/* Star */}
              <button
                onClick={() => onStar(a.ID)}
                className={`text-lg flex-shrink-0 transition-colors ${
                  isStarred ? "text-amber-400" : "text-slate-200 hover:text-amber-300"
                }`}
              >
                ★
              </button>

              {/* Sender */}
              <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0">
                {a.Sender}
              </span>

              {/* Subject */}
              <button
                className={`text-sm text-left flex-1 truncate ${
                  a.is_financial ? "font-medium text-slate-800" : "text-slate-500"
                }`}
                onClick={() => onExpand(isExpanded ? null : a.ID)}
              >
                {a.Subject}
              </button>

              {/* Date */}
              <span className="text-xs text-slate-400 flex-shrink-0">{a.Date}</span>

              {/* Topic pill */}
              {a.topic && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${
                    TOPIC_COLORS[a.topic] || TOPIC_COLORS["Other"]
                  }`}
                >
                  {a.topic}
                </span>
              )}

              {/* Urgency */}
              {a.urgency_kw >= 5 && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-semibold flex-shrink-0 ${urgencyColor(
                    a.urgency_kw
                  )}`}
                >
                  U{a.urgency_kw}
                </span>
              )}
            </div>

            {/* Expanded content */}
            {isExpanded && (
              <div className="px-14 pb-4 pt-1 bg-slate-50 border-t border-slate-100">
                <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                  {a.Content || "No content available."}
                </p>
                {a.URL && (
                  <a
                    href={a.URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline mt-2 block"
                  >
                    Read full article →
                  </a>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
