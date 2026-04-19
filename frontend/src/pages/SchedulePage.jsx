import { useEffect, useState } from "react";
import api from "../api/client";
import { FILTER_OPTIONS } from "../store/useArticleStore";

const VOICE_OPTIONS = [
  { label: "American", value: "us" },
  { label: "British", value: "co.uk" },
  { label: "Australian", value: "com.au" },
  { label: "Indian", value: "co.in" },
  { label: "Irish", value: "ie" },
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

export default function SchedulePage() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [cronPreset, setCronPreset] = useState("0 7 * * 1-5");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

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
    if (!form.cron_expression.trim()) { setError("Cron expression is required"); return; }
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await api.post("/schedules", form);
      setSuccess("Schedule created!");
      setShowForm(false);
      setForm(EMPTY_FORM);
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

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Scheduled Briefings</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Auto-generate and email briefings on a recurring schedule
          </p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">
          + New Schedule
        </button>
      </div>

      {/* New schedule form */}
      {showForm && (
        <div className="card p-5 space-y-4 border-blue-200 bg-blue-50">
          <p className="font-semibold text-slate-800">New schedule</p>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label block mb-1.5">Name</label>
              <input
                className="input"
                placeholder="e.g. Morning market briefing"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>

            <div>
              <label className="label block mb-1.5">Schedule preset</label>
              <select className="select" value={cronPreset} onChange={(e) => handlePreset(e.target.value)}>
                {CRON_PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label block mb-1.5">Cron expression</label>
              <input
                className="input font-mono"
                value={form.cron_expression}
                onChange={(e) => { setForm((f) => ({ ...f, cron_expression: e.target.value })); setCronPreset("custom"); }}
                placeholder="0 7 * * 1-5"
              />
              <p className="text-xs text-slate-400 mt-1">
                min hour day month weekday &nbsp;·&nbsp;
                <a href="https://crontab.guru" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                  crontab.guru
                </a>
              </p>
            </div>

            <div>
              <label className="label block mb-1.5">Filter preset</label>
              <select className="select" value={form.filter_preset} onChange={(e) => setForm((f) => ({ ...f, filter_preset: e.target.value }))}>
                {FILTER_OPTIONS.filter((f) => f !== "Manual Selection").map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label block mb-1.5">Duration: {form.duration_minutes} min</label>
              <input
                type="range" min={1} max={10} step={1}
                value={form.duration_minutes}
                onChange={(e) => setForm((f) => ({ ...f, duration_minutes: Number(e.target.value) }))}
                className="w-full accent-blue-600 mt-2"
              />
            </div>

            <div>
              <label className="label block mb-1.5">Voice accent</label>
              <select className="select" value={form.voice_accent} onChange={(e) => setForm((f) => ({ ...f, voice_accent: e.target.value }))}>
                {VOICE_OPTIONS.map((v) => (
                  <option key={v.value} value={v.value}>{v.label}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-3 col-span-2">
              <input
                type="checkbox"
                id="email_on_done"
                checked={form.email_on_done}
                onChange={(e) => setForm((f) => ({ ...f, email_on_done: e.target.checked }))}
                className="accent-blue-600"
              />
              <label htmlFor="email_on_done" className="text-sm text-slate-700 cursor-pointer">
                Send email when briefing is ready{" "}
                <span className="text-slate-400">(configure SMTP in Settings)</span>
              </label>
            </div>
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
          {success && <p className="text-sm text-green-600">{success}</p>}

          <div className="flex gap-2">
            <button onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? "Saving…" : "Save schedule"}
            </button>
            <button onClick={() => { setShowForm(false); setError(""); }} className="btn-ghost">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Schedules list */}
      {loading ? (
        <div className="card p-8 text-center text-slate-400">Loading…</div>
      ) : schedules.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-slate-400 mb-3">No schedules yet.</p>
          <p className="text-sm text-slate-500">
            Create a schedule to automatically generate and email your financial briefing every morning.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((s) => (
            <div key={s.id} className="card p-4 flex items-center gap-4">
              {/* Toggle */}
              <button
                onClick={() => handleToggle(s.id)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 ${
                  s.enabled ? "bg-blue-600" : "bg-slate-200"
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  s.enabled ? "translate-x-6" : "translate-x-1"
                }`} />
              </button>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-slate-800 truncate">{s.name}</p>
                  {!s.enabled && <span className="text-xs bg-slate-100 text-slate-400 px-2 rounded-full">Paused</span>}
                </div>
                <div className="flex flex-wrap gap-3 mt-1 text-xs text-slate-400">
                  <span className="font-mono bg-slate-100 px-2 py-0.5 rounded">{s.cron_expression}</span>
                  <span>{s.filter_preset}</span>
                  <span>{s.duration_minutes} min</span>
                  {s.email_on_done && <span>📧 email</span>}
                  {s.last_run_at && (
                    <span>Last run: {new Date(s.last_run_at).toLocaleString()}</span>
                  )}
                </div>
              </div>

              {/* Delete */}
              <button
                onClick={() => handleDelete(s.id)}
                className="btn-danger text-xs flex-shrink-0"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Info box */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <p className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-2">How it works</p>
        <ul className="text-sm text-amber-800 space-y-1">
          <li>• Schedules run in the background while the server is running</li>
          <li>• Articles are auto-fetched and filtered using the selected preset</li>
          <li>• The briefing is saved to your Archive automatically</li>
          <li>• Configure your SMTP settings in Settings → Email to receive it by email</li>
        </ul>
      </div>
    </div>
  );
}
