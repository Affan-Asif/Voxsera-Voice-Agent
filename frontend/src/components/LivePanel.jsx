import React, { useEffect, useRef, useState } from "react";

export default function LivePanel() {
  const [connected, setConnected] = useState(false);
  const [callInfo, setCallInfo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [interim, setInterim] = useState("");
  const [sentiment, setSentiment] = useState(0);
  const boxRef = useRef(null);

  useEffect(() => {
    let ws, closed = false;
    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}/live`);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => { setConnected(false); if (!closed) setTimeout(connect, 2000); };
      ws.onmessage = (e) => {
        const ev = JSON.parse(e.data);
        if (ev.type === "call_start") {
          setCallInfo(ev); setMessages([]); setInterim(""); setSentiment(0);
        } else if (ev.type === "agent_speak") {
          setMessages((m) => [...m, { role: "AGENT", text: ev.text }]);
        } else if (ev.type === "user_final") {
          setInterim("");
          setMessages((m) => [...m, { role: "USER", text: ev.text }]);
        } else if (ev.type === "user_interim") {
          setInterim(ev.text);
        } else if (ev.type === "state") {
          setSentiment(ev.sentiment ?? 0);
        } else if (ev.type === "barge_in") {
          setMessages((m) => [...m, { role: "SYS", text: "⚡ Barge-in — caller interrupted, agent stopped talking" }]);
        } else if (ev.type === "call_end") {
          setMessages((m) => [...m, {
            role: "SYS",
            text: `📞 Call ended · ${ev.direction} · outcome: ${ev.outcome} · ${Math.round(ev.duration_sec)}s`,
          }]);
          setCallInfo(null); setInterim("");
        }
      };
    };
    connect();
    return () => { closed = true; ws && ws.close(); };
  }, []);

  useEffect(() => {
    boxRef.current && (boxRef.current.scrollTop = boxRef.current.scrollHeight);
  }, [messages, interim]);

  const pct = Math.round(((sentiment + 1) / 2) * 100);
  const barColor = sentiment > 0.15 ? "bg-emerald-500" : sentiment < -0.15 ? "bg-red-500" : "bg-amber-500";

  return (
    <div className="rounded-2xl bg-slate-900/70 border border-slate-800 p-7">
      {/* header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`h-2.5 w-2.5 rounded-full ${connected ? "bg-emerald-500 animate-pulseDot" : "bg-slate-600"}`} />
          <h2 className="text-lg font-bold text-white">Live call monitor</h2>
        </div>
        {callInfo ? (
          <span className="text-xs font-medium rounded-full bg-red-500/15 text-red-400 border border-red-500/30 px-3 py-1">
            ● LIVE · {callInfo.direction} · {callInfo.phone}
          </span>
        ) : (
          <span className="text-xs text-slate-500">{connected ? "Idle — waiting for a call" : "Reconnecting…"}</span>
        )}
      </div>

      {/* sentiment */}
      <div className="mt-5">
        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>Caller sentiment</span>
          <span className={sentiment > 0.15 ? "text-emerald-400" : sentiment < -0.15 ? "text-red-400" : "text-amber-400"}>
            {sentiment.toFixed(2)}
          </span>
        </div>
        <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* transcript */}
      <div ref={boxRef} className="mt-6 h-[26rem] overflow-y-auto space-y-3 pr-2">
        {messages.length === 0 && !interim && (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="text-4xl mb-3">🎧</div>
            <p className="text-slate-400 text-sm font-medium">Waiting for a call…</p>
            <p className="text-slate-600 text-xs mt-1">Live transcripts, sentiment and barge-ins appear here in real time.</p>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "SYS" ? (
            <p key={i} className="text-center text-xs text-slate-500 py-1">{m.text}</p>
          ) : (
            <div key={i} className={`flex ${m.role === "USER" ? "justify-start" : "justify-end"}`}>
              <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
                ${m.role === "USER"
                  ? "bg-slate-800 text-slate-200 rounded-bl-sm"
                  : "bg-gradient-to-r from-brand-600/30 to-violet-600/30 border border-brand-500/20 text-slate-100 rounded-br-sm"}`}>
                <p className={`text-[10px] uppercase tracking-wider font-bold mb-1
                  ${m.role === "USER" ? "text-slate-500" : "text-brand-400"}`}>
                  {m.role === "USER" ? "Caller" : "Agent"}
                </p>
                {m.text}
              </div>
            </div>
          )
        )}
        {interim && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm bg-slate-800/50
                            border border-dashed border-slate-700 text-slate-400 italic">
              {interim}…
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
