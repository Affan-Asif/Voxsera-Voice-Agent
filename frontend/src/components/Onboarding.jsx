import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const TIMEZONES = [
  "Asia/Kolkata", "America/New_York", "America/Chicago", "America/Los_Angeles",
  "Europe/London", "Europe/Berlin", "Asia/Dubai", "Asia/Singapore", "Australia/Sydney",
];
const INDUSTRIES = [
  "Dental clinic", "Medical clinic", "Salon & spa", "Physiotherapy",
  "Real estate", "Law firm", "Auto service", "Restaurant",
  "Fitness studio", "Veterinary clinic", "Tutoring center", "Other",
];
const STEPS = ["Business", "Personality", "Voice", "Integrations", "Go live"];

const inputCls =
  "w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm " +
  "placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent";
const labelCls = "block text-sm font-medium text-slate-300 mb-1.5 mt-4 first:mt-0";
const btnPrimary =
  "rounded-lg bg-white text-black hover:bg-zinc-200 " +
  "font-semibold px-5 py-2.5 text-sm transition disabled:opacity-40 shadow-[0_0_24px_rgba(255,255,255,0.12)]";
const btnGhost =
  "rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-900 font-medium px-5 py-2.5 text-sm transition";

function Card({ title, subtitle, children }) {
  return (
    <div className="rounded-2xl bg-slate-900/70 border border-slate-800 p-7">
      <h2 className="text-lg font-bold text-white">{title}</h2>
      {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
      <div className="mt-5">{children}</div>
    </div>
  );
}

export default function Onboarding({ business, setBusiness, ownerEmail }) {
  const [step, setStep] = useState(business ? 4 : 0);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  // step 0 — business info
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("Dental clinic");
  const [customIndustry, setCustomIndustry] = useState(false);
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [open, setOpen] = useState("09:00");
  const [close, setClose] = useState("18:00");
  const [days, setDays] = useState(["mon", "tue", "wed", "thu", "fri"]);

  // step 1 — persona
  const [agentName, setAgentName] = useState("Maya");
  const [language, setLanguage] = useState("en");
  const [friendliness, setFriendliness] = useState(8);
  const [formality, setFormality] = useState(5);
  const [verbosity, setVerbosity] = useState(3);
  const [customContext, setCustomContext] = useState("");

  // step 1 — auto-generate knowledge from website / PDF
  const [siteUrl, setSiteUrl] = useState("");
  const [genBusy, setGenBusy] = useState("");   // "" | "url" | "pdf"
  const [genErr, setGenErr] = useState("");
  const [genOk, setGenOk] = useState(false);

  const genFromUrl = async () => {
    if (!siteUrl.trim()) return;
    setGenBusy("url"); setGenErr(""); setGenOk(false);
    try {
      const res = await api.contextFromUrl(siteUrl.trim(), name, industry);
      setCustomContext(res.context);
      setGenOk(true);
    } catch (e) { setGenErr(String(e.message || e)); }
    setGenBusy("");
  };

  const genFromPdf = async (file) => {
    if (!file) return;
    setGenBusy("pdf"); setGenErr(""); setGenOk(false);
    try {
      const res = await api.contextFromPdf(file, name, industry);
      setCustomContext(res.context);
      setGenOk(true);
    } catch (e) { setGenErr(String(e.message || e)); }
    setGenBusy("");
  };

  // step 2 — voice
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("aura-2-thalia-en");
  const [playing, setPlaying] = useState("");

  // step 3 — integrations
  const [sheetUrl, setSheetUrl] = useState("");

  useEffect(() => { api.voices().then(setVoices).catch(() => {}); }, []);

  const toggleDay = (d) =>
    setDays((ds) => (ds.includes(d) ? ds.filter((x) => x !== d) : [...ds, d]));

  const playPreview = (id) => {
    setPlaying(id);
    const a = new Audio(api.previewUrl(id));
    a.onended = () => setPlaying("");
    a.onerror = () => { setPlaying(""); setErr("Preview failed — check DEEPGRAM_API_KEY"); };
    a.play().catch(() => setPlaying(""));
  };

  const createBusiness = async () => {
    setErr(""); setBusy(true);
    try {
      const row = await api.registerBusiness({
        name, industry, timezone,
        business_hours: { open, close, days },
        persona: { agent_name: agentName, language, friendliness, formality, verbosity, custom_context: customContext },
        voice_model: voice,
        owner_email: ownerEmail || "",
      });
      setBusiness(row);
      localStorage.setItem("business_id", row.id);
      setStep(3);
    } catch (e) { setErr(String(e.message || e)); }
    setBusy(false);
  };

  const connectGoogle = async () => {
    setErr("");
    try {
      if (sheetUrl) await api.patchBusiness(business.id, { google_sheet_id: sheetUrl });
      const { url } = await api.googleAuthUrl(business.id);
      window.location.href = url;
    } catch (e) { setErr(String(e.message || e)); }
  };

  const saveSheetOnly = async () => {
    setErr(""); setBusy(true);
    try {
      const row = await api.patchBusiness(business.id, { google_sheet_id: sheetUrl });
      setBusiness({ ...business, ...row });
    } catch (e) { setErr(String(e.message || e)); }
    setBusy(false);
  };

  return (
    <div className="space-y-6">
      {/* stepper */}
      <div className="flex items-center gap-0">
        {STEPS.map((s, i) => (
          <React.Fragment key={s}>
            <div className="flex items-center gap-2">
              <div className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold border
                ${step > i ? "bg-white border-white text-black"
                  : step === i ? "border-white text-white bg-white/10"
                  : "border-slate-700 text-slate-600"}`}>
                {step > i ? "✓" : i + 1}
              </div>
              <span className={`text-xs font-medium hidden sm:block
                ${step >= i ? "text-slate-200" : "text-slate-600"}`}>{s}</span>
            </div>
            {i < STEPS.length - 1 &&
              <div className={`flex-1 h-px mx-3 ${step > i ? "bg-white/70" : "bg-slate-800"}`} />}
          </React.Fragment>
        ))}
      </div>

      {step === 0 && (
        <Card title="Tell us about your business"
              subtitle="Your agent uses this to answer callers accurately.">
          <div className="grid md:grid-cols-2 gap-x-8">
            <div>
              <label className={labelCls}>Business name</label>
              <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)}
                     placeholder="Smile Dental Clinic" />
              <label className={labelCls}>Industry</label>
              <select className={inputCls}
                      value={customIndustry ? "Other" : industry}
                      onChange={(e) => {
                        if (e.target.value === "Other") { setCustomIndustry(true); setIndustry(""); }
                        else { setCustomIndustry(false); setIndustry(e.target.value); }
                      }}>
                {INDUSTRIES.map((ind) => <option key={ind} value={ind}>{ind}</option>)}
              </select>
              {customIndustry && (
                <input className={`${inputCls} mt-3`} autoFocus value={industry}
                       onChange={(e) => setIndustry(e.target.value)}
                       placeholder="Type your industry…" />
              )}
              <label className={labelCls}>Time zone</label>
              <select className={inputCls} value={timezone} onChange={(e) => setTimezone(e.target.value)}>
                {TIMEZONES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Opens</label>
                  <input type="time" className={inputCls} value={open} onChange={(e) => setOpen(e.target.value)} />
                </div>
                <div>
                  <label className={labelCls}>Closes</label>
                  <input type="time" className={inputCls} value={close} onChange={(e) => setClose(e.target.value)} />
                </div>
              </div>
              <label className={labelCls}>Working days</label>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((d) => (
                  <button key={d} onClick={() => toggleDay(d)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide border transition
                            ${days.includes(d)
                              ? "bg-brand-600/20 border-brand-500/50 text-brand-300"
                              : "border-slate-700 text-slate-500 hover:border-slate-500"}`}>
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-7">
            <button className={btnPrimary} disabled={!name.trim()} onClick={() => setStep(1)}>Continue →</button>
          </div>
        </Card>
      )}

      {step === 1 && (
        <Card title="Design your agent's personality"
              subtitle="How should it sound on the phone?">
          <div className="grid md:grid-cols-2 gap-x-8">
            <div>
              <label className={labelCls}>Agent name</label>
              <input className={inputCls} value={agentName} onChange={(e) => setAgentName(e.target.value)} />
              <label className={labelCls}>Call language</label>
              <select className={inputCls} value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="en">English</option>
                <option value="hi">Hindi (हिन्दी)</option>
              </select>
              {language === "hi" && (
                <p className="text-xs text-slate-500 mt-1.5">
                  Hindi works best with an Indian-accent (Sarvam) voice — pick one in the next step.
                </p>
              )}
              {[["Friendliness", friendliness, setFriendliness],
                ["Formality", formality, setFormality],
                ["Talkativeness", verbosity, setVerbosity]].map(([label, val, set]) => (
                <div key={label}>
                  <label className={labelCls}>
                    {label} <span className="text-brand-400 font-semibold">{val}/10</span>
                  </label>
                  <input type="range" min="1" max="10" value={val}
                         onChange={(e) => set(+e.target.value)}
                         className="w-full accent-indigo-500" />
                </div>
              ))}
            </div>
            <div>
              {/* AI prompt generator */}
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 mt-4">
                <p className="text-sm font-semibold text-white">✦ Auto-generate with AI</p>
                <p className="text-xs text-slate-500 mt-1">
                  Paste your website or upload a brochure/price-list PDF — we'll read it and
                  draft the receptionist's knowledge for you.
                </p>
                <div className="flex gap-2 mt-3">
                  <input className={inputCls} value={siteUrl}
                         onChange={(e) => setSiteUrl(e.target.value)}
                         placeholder="https://yourclinic.com" />
                  <button type="button" onClick={genFromUrl}
                          disabled={!!genBusy || !siteUrl.trim()}
                          className="shrink-0 rounded-lg bg-white text-black text-xs font-semibold px-4
                                     hover:bg-zinc-200 transition disabled:opacity-40">
                    {genBusy === "url" ? "Reading…" : "Generate"}
                  </button>
                </div>
                <label className="mt-2.5 flex items-center gap-2 text-xs text-slate-400 cursor-pointer
                                  hover:text-slate-200 transition w-fit">
                  <span className="rounded-lg border border-slate-700 px-3 py-1.5">
                    {genBusy === "pdf" ? "Extracting…" : "📄 Upload PDF instead"}
                  </span>
                  <input type="file" accept="application/pdf" className="hidden"
                         disabled={!!genBusy}
                         onChange={(e) => { genFromPdf(e.target.files?.[0]); e.target.value = ""; }} />
                </label>
                {genErr && <p className="text-xs text-red-400 mt-2">{genErr}</p>}
                {genOk && <p className="text-xs text-emerald-400 mt-2">✓ Draft ready below — review and edit before continuing.</p>}
              </div>

              <label className={labelCls}>Business knowledge (services, prices, policies…)</label>
              <textarea rows={9} className={inputCls}
                        value={customContext} onChange={(e) => setCustomContext(e.target.value)}
                        placeholder="We offer cleaning, root canal, braces. New patients should arrive 10 minutes early…" />
            </div>
          </div>
          <div className="mt-7 flex gap-3">
            <button className={btnGhost} onClick={() => setStep(0)}>← Back</button>
            <button className={btnPrimary} onClick={() => setStep(2)}>Continue →</button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card title="Choose a voice"
              subtitle="English accent (Deepgram) or Indian accent with multilingual support (Sarvam) — tap ▶ to preview.">
          {[["deepgram", "English accent", "Deepgram Aura"],
            ["sarvam", "Indian accent · multilingual", "Sarvam Bulbul"]].map(([prov, title, sub]) => (
            <div key={prov} className="mb-6 last:mb-0">
              <div className="flex items-baseline gap-2 mb-3">
                <h3 className="text-sm font-bold text-white">{title}</h3>
                <span className="text-[11px] text-slate-500 font-mono uppercase tracking-wider">{sub}</span>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {voices.filter((v) => (v.provider || "deepgram") === prov).map((v) => (
                  <div key={v.id} onClick={() => setVoice(v.id)}
                       className={`rounded-xl border p-4 cursor-pointer transition
                         ${voice === v.id
                           ? "border-brand-500 bg-brand-600/10 ring-1 ring-brand-500/40"
                           : "border-slate-800 bg-slate-950/60 hover:border-slate-600"}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">{v.name}</span>
                      <span className="text-[11px] uppercase tracking-wide text-slate-500">{v.gender}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{v.style}</p>
                    <button onClick={(e) => { e.stopPropagation(); playPreview(v.id); }}
                            className="mt-3 text-xs font-semibold text-brand-400 hover:text-brand-300">
                      {playing === v.id ? "◉ Playing…" : "▶ Preview"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div className="mt-7 flex gap-3">
            <button className={btnGhost} onClick={() => setStep(1)}>← Back</button>
            <button className={btnPrimary} disabled={busy} onClick={createBusiness}>
              {busy ? "Creating agent…" : "Create my agent →"}
            </button>
          </div>
        </Card>
      )}

      {step === 3 && business && (
        <Card title="Connect Google"
              subtitle="One click — zero setup. We create a single spreadsheet in your Drive that powers
                        everything: bookings, call logs, and outbound reminders.">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 mb-4">
            <p className="text-sm font-semibold text-white">Fully automatic</p>
            <ul className="text-xs text-slate-400 mt-2 space-y-1.5 list-none">
              <li>· Availability is read from your Google Calendar; bookings are added to it</li>
              <li>· A sheet <span className="text-slate-300">"Voxsera — {business.name}"</span> is created
                  with an <span className="text-slate-300">Appointments</span> tab (bookings) and a{" "}
                  <span className="text-slate-300">Calls</span> tab (transcript log)</li>
              <li>· Outbound reminders read the same Appointments tab — every booking made on an
                  inbound call is automatically reminder-called 30 min before, or instantly via Call now</li>
            </ul>
          </div>
          <details className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <summary className="text-xs font-semibold text-slate-400 cursor-pointer hover:text-slate-200">
              Advanced: use an existing appointments sheet instead (optional)
            </summary>
            <input className={`${inputCls} mt-3`} value={sheetUrl}
                   onChange={(e) => setSheetUrl(e.target.value)}
                   placeholder="https://docs.google.com/spreadsheets/d/…" />
            {business.google_connected && (
              <button className={`${btnGhost} mt-3`} disabled={busy || !sheetUrl} onClick={saveSheetOnly}>
                Save custom sheet
              </button>
            )}
          </details>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button className={btnPrimary} onClick={connectGoogle}>
              {business.google_connected ? "Reconnect Google" : "Connect Google account"}
            </button>
            <button className={btnGhost} onClick={() => setStep(4)}>
              {business.google_connected ? "Continue →" : "Skip for now"}
            </button>
          </div>
          {business.google_connected && (
            <p className="mt-4 text-sm text-emerald-400">
              ✓ Google connected — calendar, workspace sheet and reminders are live.</p>
          )}
        </Card>
      )}

      {step === 4 && business && (
        <Card title="Your agent is live 🎉" subtitle="Share this number — the AI answers instantly, 24/7.">
          <div className="rounded-2xl bg-gradient-to-r from-brand-600/20 to-violet-600/20
                          border border-brand-500/30 p-6 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-400 font-semibold">Your AI agent number</p>
            <p className="text-3xl font-extrabold text-white font-mono mt-2">
              {business.twilio_number || "No Twilio number in .env"}
            </p>
          </div>
          <div className="grid sm:grid-cols-3 gap-3 mt-4 text-sm">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-slate-500 text-xs">Google</p>
              <p className={business.google_connected ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                {business.google_connected ? "Connected" : "Not connected"}
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-slate-500 text-xs">Voice</p>
              <p className="text-white font-semibold">{business.voice_model?.replace("aura-2-", "").replace("-en", "")}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-slate-500 text-xs">Agent</p>
              <p className="text-white font-semibold">{(business.persona || {}).agent_name || "Maya"}</p>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-4">
            Outbound: rows in your reminder sheet due within 30 minutes are called automatically.
            Booking confirmations are emailed to {ownerEmail || "your account email"}.
          </p>
          <div className="mt-6">
            <button className={btnGhost} onClick={() => setStep(3)}>← Back to integrations</button>
          </div>
        </Card>
      )}

      {err && (
        <p className="text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-lg px-4 py-3">{err}</p>
      )}
    </div>
  );
}
