import React, { useState } from "react";
import { api } from "../api.js";

export default function Auth({ onAuthed, onBack }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const res = mode === "login"
        ? await api.login(email, password)
        : await api.signup(email, password);
      onAuthed(res);
    } catch (ex) { setErr(String(ex.message || ex)); }
    setBusy(false);
  };

  return (
    <div className="min-h-screen flex">
      {/* left brand panel */}
      <div className="hidden lg:flex w-1/2 flex-col justify-between p-12
                      bg-gradient-to-br from-indigo-950 via-slate-950 to-slate-950
                      border-r border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-white
                          flex items-center justify-center text-black font-extrabold">V</div>
          <span className="text-xl font-bold text-white tracking-tight">Voxsera</span>
        </div>
        <div>
          <h1 className="text-4xl xl:text-5xl font-extrabold text-white leading-tight tracking-tight">
            Your business never<br />
            <span className="bg-gradient-to-r from-brand-400 to-violet-400 bg-clip-text text-transparent">
              misses a call again.
            </span>
          </h1>
          <p className="mt-5 text-slate-400 text-lg max-w-md">
            Full-duplex AI voice agents that answer, book appointments into Google
            Calendar, and call customers back with reminders — live in 5 minutes.
          </p>
          <div className="mt-8 flex gap-8 text-sm">
            <div><div className="text-2xl font-bold text-white">&lt;1s</div><div className="text-slate-500">response latency</div></div>
            <div><div className="text-2xl font-bold text-white">24/7</div><div className="text-slate-500">availability</div></div>
            <div><div className="text-2xl font-bold text-white">2-way</div><div className="text-slate-500">inbound + outbound</div></div>
          </div>
        </div>
        <p className="text-xs text-slate-600">© 2026 Voxsera · Built at VYNEDAM Talent Hunt 2K26</p>
      </div>

      {/* right form panel */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {onBack && (
            <button onClick={onBack}
                    className="mb-6 text-sm text-slate-500 hover:text-slate-300 transition">
              ← Back to home
            </button>
          )}
          <div className="lg:hidden flex items-center gap-2.5 mb-8 justify-center">
            <div className="h-9 w-9 rounded-xl bg-white
                            flex items-center justify-center text-black font-extrabold">V</div>
            <span className="text-xl font-bold text-white">Voxsera</span>
          </div>
          <h2 className="text-2xl font-bold text-white">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            {mode === "login" ? "Log in to manage your AI voice agent."
                              : "Set up an AI receptionist for your business."}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Work email</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                     placeholder="you@business.com"
                     className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3.5 py-2.5 text-sm
                                placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
              <input type="password" required minLength={6} value={password}
                     onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
                     className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3.5 py-2.5 text-sm
                                placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent" />
            </div>
            {err && <p className="text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-lg px-3 py-2">{err}</p>}
            <button disabled={busy}
                    className="w-full rounded-lg bg-white text-black font-semibold py-2.5 text-sm transition
                               hover:bg-zinc-200 disabled:opacity-50 shadow-[0_0_24px_rgba(255,255,255,0.15)]">
              {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
            </button>
          </form>

          <p className="mt-6 text-sm text-slate-400 text-center">
            {mode === "login" ? "New to Voxsera? " : "Already have an account? "}
            <button onClick={() => { setMode(mode === "login" ? "signup" : "login"); setErr(""); }}
                    className="text-brand-400 hover:text-brand-300 font-medium">
              {mode === "login" ? "Create an account" : "Log in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
