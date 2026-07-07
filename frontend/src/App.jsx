import React, { useEffect, useState } from "react";
import Landing from "./components/Landing.jsx";
import Contact from "./components/Contact.jsx";
import Auth from "./components/Auth.jsx";
import Onboarding from "./components/Onboarding.jsx";
import LivePanel from "./components/LivePanel.jsx";
import CallsDashboard from "./components/CallsDashboard.jsx";
import { api } from "./api.js";

const NAV = [
  { id: "setup", label: "Agent setup", icon: "⚙️" },
  { id: "live",  label: "Live monitor", icon: "🎧" },
  { id: "calls", label: "Call history", icon: "📊" },
];

export default function App() {
  const [email, setEmail] = useState(localStorage.getItem("vox_email") || "");
  // home | contact | auth | app (dashboard)
  const [view, setView] = useState(localStorage.getItem("vox_email") ? "app" : "home");
  const [tab, setTab] = useState("setup");
  const [business, setBusiness] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // returning from Google OAuth: /?business_id=..&google=connected
    const p = new URLSearchParams(location.search);
    const id = p.get("business_id") || localStorage.getItem("business_id");
    if (id) {
      api.getBusiness(id).then((b) => {
        setBusiness(b);
        localStorage.setItem("business_id", b.id);
      }).catch(() => localStorage.removeItem("business_id"))
        .finally(() => setReady(true));
    } else setReady(true);
    if (p.toString()) history.replaceState({}, "", "/");
  }, []);

  const onAuthed = ({ email, business }) => {
    localStorage.setItem("vox_email", email);
    setEmail(email);
    setView("app");
    if (business) {
      setBusiness(business);
      localStorage.setItem("business_id", business.id);
    }
  };

  // marketing-nav handler: if already logged in, "auth" means back to the dashboard
  const nav = (v) => setView(v === "auth" && email ? "app" : v);

  const logout = () => {
    localStorage.removeItem("vox_email");
    localStorage.removeItem("business_id");
    setEmail(""); setBusiness(null); setTab("setup"); setView("home");
  };

  if (!ready) return null;
  if (view === "auth" && !email) return <Auth onAuthed={onAuthed} onBack={() => setView("home")} />;
  if (view === "contact") return <Contact onNav={nav} />;
  if (view === "home" || !email) return <Landing onNav={nav} />;

  return (
    <div className="min-h-screen flex">
      {/* sidebar */}
      <aside className="w-60 shrink-0 border-r border-slate-800/70 bg-slate-950/80 flex flex-col">
        <button onClick={() => setView("home")} title="Go to home page"
                className="flex items-center gap-2.5 px-5 h-16 border-b border-slate-800/70 w-full
                           hover:bg-slate-900/60 transition group">
          <div className="h-8 w-8 rounded-lg bg-white
                          flex items-center justify-center text-black font-extrabold text-sm
                          group-hover:rotate-12 transition-transform duration-300">V</div>
          <span className="font-bold text-white tracking-tight">Voxsera</span>
        </button>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map((n) => (
            <button key={n.id} onClick={() => setTab(n.id)}
                    className={`w-full flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition
                      ${tab === n.id
                        ? "bg-brand-600/15 text-brand-400 border border-brand-600/30"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent"}`}>
              <span>{n.icon}</span>{n.label}
            </button>
          ))}
        </nav>
        {business?.twilio_number && (
          <div className="mx-3 mb-3 rounded-xl bg-slate-900 border border-slate-800 p-3.5">
            <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">Agent line</p>
            <p className="text-sm font-mono text-emerald-400 mt-1">{business.twilio_number}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {business.google_connected ? "● Google connected" : "○ Google not connected"}
            </p>
          </div>
        )}
        <div className="p-3 border-t border-slate-800/70 flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-300 truncate">{email}</p>
            <p className="text-[11px] text-slate-500 truncate">{business?.name || "No agent yet"}</p>
          </div>
          <button onClick={logout} title="Log out"
                  className="text-slate-500 hover:text-red-400 text-sm shrink-0 px-2 py-1 rounded hover:bg-slate-900">
            ⏻
          </button>
        </div>
      </aside>

      {/* main */}
      <main className="flex-1 overflow-y-auto">
        <header className="h-16 border-b border-slate-800/70 flex items-center justify-between px-8
                           bg-slate-950/60 backdrop-blur sticky top-0 z-10">
          <h1 className="font-semibold text-white">
            {NAV.find((n) => n.id === tab)?.label}
          </h1>
          {business && (
            <span className="text-sm text-slate-400">
              {business.name} · <span className="text-slate-500">{business.industry}</span>
            </span>
          )}
        </header>
        <div className="p-8 max-w-5xl">
          {tab === "setup" && (
            <Onboarding business={business} setBusiness={setBusiness} ownerEmail={email} />
          )}
          {tab === "live" && <LivePanel />}
          {tab === "calls" && <CallsDashboard business={business} ownerEmail={email} />}
        </div>
      </main>
    </div>
  );
}
