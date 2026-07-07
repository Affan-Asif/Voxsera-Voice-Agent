import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const fmt = (ts) => (ts ? new Date(ts).toLocaleString() : "—");

const OUTCOME_STYLE = {
  booked:    "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  info:      "bg-sky-500/15 text-sky-400 border-sky-500/30",
  reminded:  "bg-violet-500/15 text-violet-400 border-violet-500/30",
  no_answer: "bg-slate-600/20 text-slate-400 border-slate-600/40",
};

export default function CallsDashboard({ business, ownerEmail }) {
  const [direction, setDirection] = useState("inbound");
  const [calls, setCalls] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);

  // outbound: appointments from the reminder sheet + call-now
  const [appts, setAppts] = useState([]);
  const [apptsErr, setApptsErr] = useState("");
  const [callingRow, setCallingRow] = useState(null);
  const [callMsg, setCallMsg] = useState("");

  const loadAppts = () => {
    if (!business?.id) return;
    setApptsErr("");
    api.appointments(business.id)
      .then(setAppts)
      .catch((e) => { setAppts([]); setApptsErr(String(e.message || e)); });
  };

  useEffect(() => { if (direction === "outbound") loadAppts(); }, [direction, business?.id]);

  const callNow = async (row) => {
    setCallingRow(row); setCallMsg(""); setApptsErr("");
    try {
      const res = await api.callNow(business.id, row);
      setCallMsg(`Calling ${res.name || ""} at ${res.phone}… watch it live in the Live monitor.`);
      loadAppts();
    } catch (e) { setApptsErr(String(e.message || e)); }
    setCallingRow(null);
  };

  const load = () => {
    setLoading(true);
    // scoped to this owner's account (covers all their business rows)
    api.calls(ownerEmail, direction)
      .then(setCalls)
      .catch(() => setCalls([]))
      .finally(() => setLoading(false));
  };

  useEffect(load, [direction, business?.id]);

  const stats = {
    total: calls.length,
    booked: calls.filter((c) => c.outcome === "booked").length,
    avgSent: calls.length
      ? (calls.reduce((s, c) => s + (c.sentiment || 0), 0) / calls.length)
      : 0,
    avgDur: calls.length
      ? Math.round(calls.reduce((s, c) => s + (c.duration_sec || 0), 0) / calls.length)
      : 0,
  };

  return (
    <div className="space-y-6">
      {/* toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex rounded-lg border border-slate-800 bg-slate-900/70 p-1">
          {["inbound", "outbound"].map((d) => (
            <button key={d}
                    onClick={() => { setDirection(d); setSelected(null); }}
                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition
                      ${direction === d ? "bg-brand-600/20 text-brand-300" : "text-slate-400 hover:text-slate-200"}`}>
              {d === "inbound" ? "📥 Inbound" : "📤 Outbound"}
            </button>
          ))}
        </div>
        <button onClick={load}
                className="text-sm text-slate-400 hover:text-white border border-slate-800 rounded-lg px-3.5 py-1.5 hover:bg-slate-900 transition">
          ↻ Refresh
        </button>
      </div>

      {/* stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[["Total calls", stats.total],
          ["Bookings", stats.booked],
          ["Avg sentiment", stats.avgSent.toFixed(2)],
          ["Avg duration", `${stats.avgDur}s`]].map(([label, val]) => (
          <div key={label} className="rounded-xl bg-slate-900/70 border border-slate-800 p-4">
            <p className="text-xs text-slate-500">{label}</p>
            <p className="text-2xl font-bold text-white mt-1">{val}</p>
          </div>
        ))}
      </div>

      {/* outbound: appointment sheet + call-now */}
      {direction === "outbound" && (
        <div className="rounded-2xl bg-slate-900/70 border border-slate-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-bold text-white">Upcoming appointments</h2>
              <p className="text-xs text-slate-500 mt-1">
                From your reminder sheet. Auto-called 30 min before start — or call instantly.
              </p>
            </div>
            <button onClick={loadAppts}
                    className="text-sm text-slate-400 hover:text-white border border-slate-800 rounded-lg px-3 py-1.5 hover:bg-slate-800 transition">
              ↻ Reload sheet
            </button>
          </div>
          {apptsErr && (
            <p className="mt-4 text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-lg px-3 py-2">{apptsErr}</p>
          )}
          {callMsg && (
            <p className="mt-4 text-sm text-emerald-400 bg-emerald-950/30 border border-emerald-900/50 rounded-lg px-3 py-2">{callMsg}</p>
          )}
          {appts.length === 0 && !apptsErr ? (
            <p className="mt-4 text-sm text-slate-500">No rows found in the Appointments tab of your sheet.</p>
          ) : appts.length > 0 && (
            <table className="w-full text-sm mt-4">
              <thead>
                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2.5 font-semibold">Name</th>
                  <th className="px-3 py-2.5 font-semibold">Phone</th>
                  <th className="px-3 py-2.5 font-semibold">Date</th>
                  <th className="px-3 py-2.5 font-semibold">Time</th>
                  <th className="px-3 py-2.5 font-semibold">Reason</th>
                  <th className="px-3 py-2.5 font-semibold">Reminded</th>
                  <th className="px-3 py-2.5 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {appts.map((a) => (
                  <tr key={a.row} className="border-b border-slate-800/60 last:border-0">
                    <td className="px-3 py-3 text-slate-200">{a.name || "—"}</td>
                    <td className="px-3 py-3 font-mono text-slate-300">{a.phone || "—"}</td>
                    <td className="px-3 py-3 text-slate-400">{a.date}</td>
                    <td className="px-3 py-3 text-slate-400">{a.time}</td>
                    <td className="px-3 py-3 text-slate-400">{a.reason || "—"}</td>
                    <td className="px-3 py-3">
                      {(a.reminder_sent || "").toUpperCase() === "YES"
                        ? <span className="text-emerald-400 text-xs font-semibold">YES</span>
                        : <span className="text-slate-500 text-xs">—</span>}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <button onClick={() => callNow(a.row)}
                              disabled={callingRow === a.row || !a.phone}
                              className="rounded-lg bg-white text-black text-xs font-semibold px-3.5 py-1.5
                                         hover:bg-zinc-200 transition disabled:opacity-40">
                        {callingRow === a.row ? "Dialing…" : "Call now"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* table */}
      <div className="rounded-2xl bg-slate-900/70 border border-slate-800 overflow-hidden">
        {loading ? (
          <p className="p-8 text-sm text-slate-500 text-center">Loading…</p>
        ) : calls.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-3xl mb-2">☎️</div>
            <p className="text-slate-400 text-sm">No {direction} calls yet.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3.5 font-semibold">When</th>
                <th className="px-5 py-3.5 font-semibold">Phone</th>
                <th className="px-5 py-3.5 font-semibold">Outcome</th>
                <th className="px-5 py-3.5 font-semibold">Sentiment</th>
                <th className="px-5 py-3.5 font-semibold">Turns</th>
                <th className="px-5 py-3.5 font-semibold">Duration</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id} onClick={() => setSelected(c)}
                    className="border-b border-slate-800/60 last:border-0 cursor-pointer hover:bg-slate-800/40 transition">
                  <td className="px-5 py-3.5 text-slate-300">{fmt(c.started_at || c.created_at)}</td>
                  <td className="px-5 py-3.5 font-mono text-slate-300">{c.phone}</td>
                  <td className="px-5 py-3.5">
                    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium
                      ${OUTCOME_STYLE[c.outcome] || OUTCOME_STYLE.no_answer}`}>
                      {c.outcome}
                    </span>
                  </td>
                  <td className={`px-5 py-3.5 font-semibold
                    ${c.sentiment > 0.15 ? "text-emerald-400" : c.sentiment < -0.15 ? "text-red-400" : "text-amber-400"}`}>
                    {(c.sentiment ?? 0).toFixed(2)}
                  </td>
                  <td className="px-5 py-3.5 text-slate-400">{c.turns}</td>
                  <td className="px-5 py-3.5 text-slate-400">{Math.round(c.duration_sec || 0)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* transcript drawer */}
      {selected && (
        <div className="rounded-2xl bg-slate-900/70 border border-slate-800 p-7">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Transcript · {selected.phone}</h2>
              <p className="text-xs text-slate-500 mt-1">
                {fmt(selected.started_at)} · {selected.direction} · {selected.outcome} · {selected.notes}
              </p>
            </div>
            <button onClick={() => setSelected(null)}
                    className="text-slate-500 hover:text-white text-xl leading-none px-2">×</button>
          </div>
          <div className="mt-5 max-h-96 overflow-y-auto space-y-3 pr-2">
            {(selected.transcript || []).map((t, i) => (
              <div key={i} className={`flex ${t.role === "USER" ? "justify-start" : "justify-end"}`}>
                <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm
                  ${t.role === "USER"
                    ? "bg-slate-800 text-slate-200 rounded-bl-sm"
                    : "bg-gradient-to-r from-brand-600/30 to-violet-600/30 border border-brand-500/20 text-slate-100 rounded-br-sm"}`}>
                  <p className={`text-[10px] uppercase tracking-wider font-bold mb-1
                    ${t.role === "USER" ? "text-slate-500" : "text-brand-400"}`}>
                    {t.role === "USER" ? "Caller" : "Agent"}
                  </p>
                  {t.text}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
