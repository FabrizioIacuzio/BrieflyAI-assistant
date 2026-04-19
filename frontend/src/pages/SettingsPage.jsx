import { useEffect, useState } from "react";
import api from "../api/client";

const EMPTY_CONFIG = {
  smtp_host: "smtp.gmail.com",
  smtp_port: 587,
  smtp_user: "",
  smtp_password: "",
  from_address: "",
  to_address: "",
};

export default function SettingsPage() {
  const [config, setConfig] = useState(EMPTY_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [testMsg, setTestMsg] = useState("");

  useEffect(() => {
    api.get("/email-config").then(({ data }) => {
      setConfig(data);
      setLoading(false);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg("");
    try {
      await api.put("/email-config", config);
      setSaveMsg("✓ Settings saved");
    } catch (e) {
      setSaveMsg("Error: " + (e.response?.data?.detail || e.message));
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestMsg("");
    try {
      await api.post("/email-config/test");
      setTestMsg("✓ Test email sent — check your inbox");
    } catch (e) {
      setTestMsg("Error: " + (e.response?.data?.detail || e.message));
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">Configure email delivery for your briefings</p>
      </div>

      {loading ? (
        <div className="card p-8 text-center text-slate-400">Loading…</div>
      ) : (
        <div className="card p-6 space-y-5">
          <div>
            <p className="text-base font-semibold text-slate-800 mb-1">Email Configuration</p>
            <p className="text-sm text-slate-500">
              Used for manual "Email to me" and scheduled briefing delivery.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label block mb-1.5">SMTP host</label>
              <input
                className="input"
                value={config.smtp_host}
                onChange={(e) => setConfig((c) => ({ ...c, smtp_host: e.target.value }))}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div>
              <label className="label block mb-1.5">SMTP port</label>
              <input
                className="input"
                type="number"
                value={config.smtp_port}
                onChange={(e) => setConfig((c) => ({ ...c, smtp_port: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="label block mb-1.5">SMTP username</label>
              <input
                className="input"
                value={config.smtp_user}
                onChange={(e) => setConfig((c) => ({ ...c, smtp_user: e.target.value }))}
                placeholder="you@gmail.com"
              />
            </div>
            <div>
              <label className="label block mb-1.5">App password</label>
              <input
                className="input"
                type="password"
                value={config.smtp_password}
                onChange={(e) => setConfig((c) => ({ ...c, smtp_password: e.target.value }))}
                placeholder="Gmail App Password (16 chars)"
              />
            </div>
            <div>
              <label className="label block mb-1.5">From address</label>
              <input
                className="input"
                value={config.from_address}
                onChange={(e) => setConfig((c) => ({ ...c, from_address: e.target.value }))}
                placeholder="Briefly AI <you@gmail.com>"
              />
            </div>
            <div>
              <label className="label block mb-1.5">Send to</label>
              <input
                className="input"
                value={config.to_address}
                onChange={(e) => setConfig((c) => ({ ...c, to_address: e.target.value }))}
                placeholder="recipient@example.com"
              />
            </div>
          </div>

          {saveMsg && (
            <p className={`text-sm ${saveMsg.startsWith("✓") ? "text-green-600" : "text-red-600"}`}>
              {saveMsg}
            </p>
          )}

          <div className="flex gap-3">
            <button onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? "Saving…" : "Save settings"}
            </button>
            <button onClick={handleTest} disabled={testing} className="btn-ghost">
              {testing ? "Sending…" : "Send test email"}
            </button>
          </div>

          {testMsg && (
            <p className={`text-sm ${testMsg.startsWith("✓") ? "text-green-600" : "text-red-600"}`}>
              {testMsg}
            </p>
          )}
        </div>
      )}

      {/* Gmail instructions */}
      <div className="card p-5">
        <p className="text-sm font-semibold text-slate-700 mb-3">Gmail setup guide</p>
        <ol className="text-sm text-slate-600 space-y-2 list-decimal pl-4">
          <li>Enable 2-step verification on your Google account</li>
          <li>Go to <span className="font-mono text-xs bg-slate-100 px-1 rounded">myaccount.google.com → Security → App passwords</span></li>
          <li>Create a new app password (select "Mail" + "Other")</li>
          <li>Copy the 16-character password into the "App password" field above</li>
          <li>Use your full Gmail address as both the SMTP username and From address</li>
        </ol>
      </div>
    </div>
  );
}
