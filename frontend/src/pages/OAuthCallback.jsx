/**
 * OAuthCallback — landing page after Google redirects back.
 *
 * Google → backend callback → redirect here with:
 *   ?token=xxx&username=Fabrizio&email=fab@gmail.com&picture=https://...
 *
 * We read the params, log the user in, clean the URL, then go to the dashboard.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/useAuthStore";

export default function OAuthCallback() {
  const [error, setError] = useState("");
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token    = params.get("token");
    const username = params.get("username");
    const email    = params.get("email");
    const picture  = params.get("picture");

    if (!token || !username) {
      setError("OAuth failed: missing token or username from Google callback.");
      return;
    }

    login(token, username, { email, picture });

    // Remove the sensitive params from the browser history
    window.history.replaceState({}, "", "/");
    navigate("/", { replace: true });
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="card p-8 max-w-sm text-center space-y-4">
          <p className="text-red-600 font-medium">{error}</p>
          <a href="/login" className="btn-primary inline-block px-6 py-2">
            Back to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-slate-500 text-sm">Signing you in…</p>
      </div>
    </div>
  );
}
