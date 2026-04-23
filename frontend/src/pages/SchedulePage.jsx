import { useEffect, useState } from "react";
import api from "../api/client";
import { FILTER_OPTIONS } from "../store/useArticleStore";

const VOICE_OPTIONS = [
  { label: "American (en-US)", value: "us" },
  { label: "British (en-GB)", value: "co.uk" },
  { label: "Australian (en-AU)", value: "com.au" },
  { label: "Indian (en-IN)", value: "co.in" },
  { label: "Irish (en-IE)", value: "ie" },
];

const CRON_PRESETS = [
  { label: "Weekdays at 7:00 AM", value: "0 7 * * 1-5" },
  { label: "Weekdays at 8:00 AM", value: "0 8 * * 1-5" },
  { label: "Every day at 7:00 AM", value: "0 7 * * *" },
  { label: "Every day at 9:00 AM", value: "0 9 * * *" },
  { label: "Every hour",           value: "0 * * * *" },
  { label: "Custom…",              value: "custom" },
];

const EMPTY_FORM = {
  name: "",
  cron_expression: "0 7 * * 1-5",
  filter_preset: "Market Volatility",
  duration_minutes: 3,
  voice_accent: "us",
  email_on_done: true,
  enabled: true,
};

function cronLabel(expr) {
  const found = CRON_PRESETS.find((p) => p.value === expr);
  return found && found.value !== "custom" ? found.label : expr;
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 ${
        checked ? "bg-blue-600" : "bg-slate-200"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
          checked ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}

export default function SchedulePage() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [form, setForm]           = useState(EMPTY_FORM);
  const [cronPreset, setCronPreset] = useState("0 7 * * 1-5");
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/schedules");
      setSchedules(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handlePreset = (val) => {
    setCronPreset(val);
    if (val !== "custom") setForm((f) => ({ ...f, cron_expression: val }));
  };

  const handleSave = async () => {
    if (!form.name.trim()) { setError("Name is required"); return; }
    const cronParts = form.cron_expression.trim().split(/\s+/);
    if (cronParts.length !== 5) { setError("Cron expression must have exactly 5 fields: min hour dom mon dow"); return; }
    setSaving(true);
    setError("");
    try {
      await api.post("/schedules", form);
      setShowForm(false);
      setForm(EMPTY_FORM);
      setCronPreset("0 7 * * 1-5");
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (id) => {
    await api.post(`/schedules/${id}/toggle`);
    await load();
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this schedule?")) return;
    await api.delete(`/schedules/${id}`);
    await load();
  };

  const openForm = () => { setShowForm(true); setError(""); };
  const closeForm = () => { setShowForm(false); setError(""); };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-5">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Scheduled Briefings</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Auto-generate and deliver briefings on a recurring schedule
          </p>
        </div>
        {!showForm && (
          <button onClick={openForm} className="btn-primary">
            + New Schedule
          </button>
        )}
      </div>

      {/* ── New schedule form ── */}
      {showForm && (
        <div className="card p-6 space-y-5">
          <div className="pb-4 border-b border-slate-100">
            <p className="text-base font-semibold text-slate-800">New Schedule</p>
            <p className="text-sm text-slate-400 mt-0.5">
              Configure when and how your briefing is generated
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Name */}
            <div className="col-span-2">
              <label className="label block mb-1.5">Schedule name</label>
              <input
                className="input"
                placeholder="e.g. Morning market briefing"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>

            {/* Timing preset */}
            <div>
              <label className="label block mb-1.5">Timing</label>
              <select
                className="select"
                value={cronPreset}
                onChange={(e) => handlePreset(e.target.value)}
              >
                {CRON_PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>

            {/* Cron */}
            <div>
              <label className="label block mb-1.5">
                Cron expression
                <a
                  href="https://crontab.guru"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 normal-case font-normal text-blue-500 hover:underline text-xs"
                >
                  crontab.guru ↗
                </a>
              </label>
              <input
                className="input font-mono text-sm"
                value={form.cron_expression}
                onChange={(e) => {
                  setForm((f) => ({ ...f, cron_expression: e.target.value }));
                  setCronPreset("custom");
                }}
                placeholder="0 7 * * 1-5"
              />
            </div>

            {/* Filter */}
            <div>
              <label className="label block mb-1.5">News filter</label>
              <select
                className="select"
                value={form.filter_preset}
                onChange={(e) => setForm((f) => ({ ...f, filter_preset: e.target.value }))}
              >
                {FILTER_OPTIONS.filter((f) => f !== "Manual Selection").map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </div>

            {/* Voice */}
            <div>
              <label className="label block mb-1.5">Voice accent</label>
              <select
                className="select"
                value={form.voice_accent}
                onChange={(e) => setForm((f) => ({ ...f, voice_accent: e.target.value }))}
              >
                {VOICE_OPTIONS.map((v) => (
                  <option key={v.value} value={v.value}>{v.label}</option>
                ))}
              </select>
            </div>

            {/* Duration */}
            <div className="col-span-2">
              <label className="label block mb-2">
                Briefing duration —{" "}
                <span className="text-blue-600 normal-case font-semibold">
                  {form.duration_minutes} min
                </span>
              </label>
              <input
                type="range" min={1} max={10} step={1}
                value={form.duration_minutes}
                onChange={(e) =>
                  setForm((f) => ({ ...f, duration_minutes: Number(e.target.value) }))
                }
                className="w-full accent-blue-600"
              />
              <div className="flex justify-between text-xs text-slate-300 mt-1 select-none">
                <span>1 min</span><span>10 min</span>
              </div>
            </div>

            {/* Email toggle */}
            <div className="col-span-2 flex items-center gap-3 py-1">
              <Toggle
                checked={form.email_on_done}
                onChange={() => setForm((f) => ({ ...f, email_on_done: !f.email_on_done }))}
              />
              <p className="text-sm font-medium text-slate-700">Email when ready</p>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2.5">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? "Saving…" : "Save schedule"}
            </button>
            <button onClick={closeForm} className="btn-ghost">Cancel</button>
          </div>
        </div>
      )}

      {/* ── Schedules list ── */}
      {loading ? (
        <div className="card p-10 text-center text-slate-400 text-sm">Loading…</div>
      ) : schedules.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-4xl mb-3">⏰</p>
          <p className="text-base font-semibold text-slate-700 mb-1">No schedules yet</p>
          <p className="text-sm text-slate-400 max-w-sm mx-auto leading-relaxed">
            Create a schedule to automatically generate your financial briefing and deliver it to your inbox every morning.
          </p>
          <button onClick={openForm} className="btn-primary mt-5 mx-auto">
            + New Schedule
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((s) => (
            <div
              key={s.id}
              className={`card p-5 transition-opacity ${!s.enabled ? "opacity-55" : ""}`}
            >
              <div className="flex items-start gap-4">
                <Toggle checked={s.enabled} onChange={() => handleToggle(s.id)} />

                <div className="flex-1 min-w-0">
                  {/* Name + status */}
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-sm font-semibold text-slate-800">{s.name}</p>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        s.enabled
                          ? "bg-green-50 text-green-700"
                          : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      {s.enabled ? "Active" : "Paused"}
                    </span>
                  </div>

                  {/* Human-readable timing */}
                  <p className="text-xs text-slate-500 mb-3">{cronLabel(s.cron_expression)}</p>

                  {/* Metadata chips */}
                  <div className="flex flex-wrap gap-1.5">
                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                      {s.filter_preset}
                    </span>
                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                      {s.duration_minutes} min
                    </span>
                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                      {VOICE_OPTIONS.find((v) => v.value === s.voice_accent)?.label ?? s.voice_accent}
                    </span>
                    {s.email_on_done && (
                      <span className="text-xs bg-blue-50 text-blue-600 border border-blue-100 px-2 py-0.5 rounded">
                        Email delivery
                      </span>
                    )}
                  </div>

                  {s.last_run_at && (
                    <p className="text-xs text-slate-400 mt-2.5">
                      Last run: {new Date(s.last_run_at).toLocaleString()}
                    </p>
                  )}
                </div>

                <button
                  onClick={() => handleDelete(s.id)}
                  className="text-xs text-slate-300 hover:text-red-500 transition-colors flex-shrink-0 mt-0.5"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── How it works ── */}
      <div className="border border-slate-200 rounded-xl p-5">
        <p className="label mb-4">How it works</p>
        <div className="grid grid-cols-3 gap-5">
          {[
            ["1", "Trigger", "The server fires at the configured cron time automatically."],
            ["2", "Fetch & filter", "Articles are pulled and filtered by the selected preset."],
            ["3", "Deliver", "The briefing is archived and optionally emailed to you."],
          ].map(([n, title, desc]) => (
            <div key={n} className="flex gap-3">
              <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                {n}
              </span>
              <div>
                <p className="text-xs font-semibold text-slate-600">{title}</p>
                <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
