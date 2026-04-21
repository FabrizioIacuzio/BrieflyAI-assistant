import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { backendOrigin } from "../api/client";
import { useAuthStore } from "../store/useAuthStore";

const FEATURES = [
  { icon: "✉", title: "Smart Inbox", sub: "Live financial news auto-ranked by relevance" },
  { icon: "🎙", title: "AI Audio Briefings", sub: "Multi-step LLM pipeline clusters, ranks and narrates" },
  { icon: "📊", title: "Sentiment Analytics", sub: "Per-article sentiment, urgency & market impact" },
  { icon: "🗂", title: "Briefing Archive", sub: "Every briefing saved with full transcript and analytics" },
  { icon: "⏰", title: "Scheduled Delivery", sub: "Auto-generate briefings on a cron schedule" },
  { icon: "📧", title: "Email to Yourself", sub: "Receive full briefings with MP3 in your inbox" },
];

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
      <path d="M3.964 10.707A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  );
}

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/auth/login", { username, password });
      login(data.token, data.username);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left — login form */}
      <div className="w-full md:w-[420px] flex flex-col justify-center px-10 py-16 bg-white border-r border-slate-100">
        <div className="mb-8">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Welcome back</p>
          <h1 className="text-2xl font-black text-slate-900">Sign in to Briefly</h1>
          <p className="text-sm text-slate-500 mt-1">Your AI-powered financial briefing room</p>
        </div>

        {/* Google sign-in */}
        <a
          href={`${backendOrigin}/api/auth/google`}
          className="flex items-center justify-center gap-3 w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <GoogleIcon />
          Sign in with Google
        </a>

        {/* Divider */}
        <div className="flex items-center gap-3 my-2">
          <div className="flex-1 border-t border-slate-100" />
          <span className="text-xs text-slate-400">or</span>
          <div className="flex-1 border-t border-slate-100" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label block mb-1.5">Username</label>
            <input
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. demo"
              autoFocus
            />
          </div>
          <div>
            <label className="label block mb-1.5">Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-2.5 mt-2"
          >
            {loading ? "Signing in…" : "Sign in →"}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-100">
          <p className="label mb-2">Demo credentials</p>
          <div className="flex gap-4 text-sm text-slate-500">
            <span>User: <code className="bg-slate-100 px-2 py-0.5 rounded text-blue-700 font-semibold">demo</code></span>
            <span>Pass: <code className="bg-slate-100 px-2 py-0.5 rounded text-blue-700 font-semibold">demo123</code></span>
          </div>
        </div>
      </div>

      {/* Right — branding */}
      <div className="hidden md:flex flex-1 flex-col justify-center px-14 py-16 bg-[#0C1220]">
        <p className="text-5xl font-black text-white tracking-tight leading-none mb-3">
          Briefly <span className="text-blue-400">AI</span>
        </p>
        <p className="text-blue-300 text-base mb-10 leading-relaxed">
          Turn your financial inbox into a spoken briefing.
        </p>
        <div className="space-y-3">
          {FEATURES.map(({ icon, title, sub }) => (
            <div key={title} className="flex items-start gap-3 bg-white/5 rounded-xl px-4 py-3">
              <span className="text-xl mt-0.5">{icon}</span>
              <div>
                <p className="text-sm font-semibold text-white">{title}</p>
                <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-600 mt-8">
          Powered by Groq LLaMA 3.3 · gTTS · NewsAPI
        </p>
      </div>
    </div>
  );
}
