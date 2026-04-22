import { useEffect, useState } from "react";
import { Routes, Route, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/useAuthStore";
import { useArticleStore } from "../store/useArticleStore";
import { useBriefingStore } from "../store/useBriefingStore";
import InboxPage from "./InboxPage";
import ArchivePage from "./ArchivePage";
import SchedulePage from "./SchedulePage";
import SettingsPage from "./SettingsPage";
import api from "../api/client";

const NAV_ITEMS = [
  { to: "/",         label: "Inbox",    icon: "✉" },
  { to: "/archive",  label: "Archive",  icon: "🗂" },
  { to: "/schedule", label: "Schedule", icon: "⏰" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

export default function Dashboard() {
  const { username, email, picture, logout } = useAuthStore();
  const { fetchArticles, source } = useArticleStore();
  const { fetchArchive } = useBriefingStore();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    fetchArticles();
    fetchArchive();
  }, []);

  const handleLogout = async () => {
    try { await api.post("/auth/logout"); } catch (_) {}
    logout();
    navigate("/login");
  };

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-[#0C1220] flex flex-col border-r border-[#1E293B]">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-[#1E293B]">
          <p className="text-xl font-black text-white tracking-tight">
            Briefly <span className="text-blue-400">AI</span>
          </p>
          {source && (
            <p className="text-xs text-slate-500 mt-1">{source}</p>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`
              }
            >
              <span className="text-base">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="px-4 py-4 border-t border-[#1E293B]">
          <div className="flex items-center gap-2.5 mb-3">
            {picture ? (
              <img
                src={picture}
                alt={username}
                className="w-7 h-7 rounded-full ring-1 ring-white/10 flex-shrink-0"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                {username?.[0]?.toUpperCase() ?? "?"}
              </div>
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-300 truncate">{username}</p>
              {email && <p className="text-xs text-slate-500 truncate">{email}</p>}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Sign out →
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div key={location.pathname} className="page-enter">
          <Routes>
            <Route path="/" element={<InboxPage />} />
            <Route path="/archive" element={<ArchivePage />} />
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
