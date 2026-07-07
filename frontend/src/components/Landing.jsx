import React, { useEffect, useState } from "react";
import Beams from "./Beams.jsx";

/* thin-line icon set (heroicons outline paths) — no emoji stickers */
const Icon = ({ d, className = "h-7 w-7" }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5}
       stroke="currentColor" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d={d} />
  </svg>
);
const ICONS = {
  phone: "M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z",
  calendar: "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6 2.25 2.25L18.75 10.5",
  link: "M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244",
  sliders: "M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75",
  wave: "M3 12h2.25m3-6v12m3.75-9v6m3.75-10.5v15M18.75 9v6M21 12h.008",
  bell: "M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0",
};

/* ---------- shared marketing nav + footer ---------- */

export function MarketingNav({ onNav, active }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const link = "text-sm transition font-medium " +
    (scrolled ? "text-slate-400 hover:text-white" : "text-slate-300 hover:text-white");

  return (
    <nav className={`fixed top-0 inset-x-0 z-50 transition-all duration-500 ${scrolled ? "pt-3 px-4" : "pt-0 px-0"}`}>
      <div className={`mx-auto flex items-center justify-between transition-all duration-500
        ${scrolled
          ? "max-w-4xl h-14 px-5 rounded-2xl border border-slate-700/60 bg-slate-900/75 backdrop-blur-xl shadow-2xl shadow-black/50"
          : "max-w-6xl h-20 px-6 border border-transparent bg-transparent"}`}>
        <button onClick={() => onNav("home")} className="flex items-center gap-2.5 group">
          <div className="h-8 w-8 rounded-lg bg-white
                          flex items-center justify-center text-black font-extrabold text-sm
                          group-hover:rotate-12 transition-transform duration-300">V</div>
          <span className="font-bold text-white tracking-tight text-lg">Voxsera</span>
        </button>
        <div className="hidden md:flex items-center gap-1">
          {[["#features", "Features"], ["#pricing", "Pricing"], ["#faq", "FAQ"]].map(([href, label]) => (
            <a key={href} href={href} onClick={() => onNav("home")}
               className={`${link} px-3.5 py-2 rounded-full hover:bg-white/5`}>{label}</a>
          ))}
          <button onClick={() => onNav("contact")}
                  className={`${link} px-3.5 py-2 rounded-full hover:bg-white/5 ${active === "contact" ? "text-white bg-white/5" : ""}`}>
            Contact
          </button>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => onNav("auth")} className="text-sm font-medium text-slate-300 hover:text-white px-3 py-2">
            Log in
          </button>
          <button onClick={() => onNav("auth")}
                  className="rounded-full bg-white text-black text-sm font-semibold px-5 py-2 transition
                             hover:bg-zinc-200 shadow-[0_0_24px_rgba(255,255,255,0.18)] hover:scale-[1.03]">
            Get started free
          </button>
        </div>
      </div>
    </nav>
  );
}

export function MarketingFooter({ onNav }) {
  return (
    <footer className="border-t border-slate-800/60 bg-slate-950">
      <div className="max-w-6xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-white
                            flex items-center justify-center text-black font-extrabold text-sm">V</div>
            <span className="font-bold text-white text-lg">Voxsera</span>
          </div>
          <p className="text-sm text-slate-500 mt-4 max-w-sm">
            AI voice agents that answer every call, book appointments, and call your
            customers back — so your business never misses revenue again.
          </p>
        </div>
        <div>
          <p className="text-sm font-semibold text-white mb-4">Product</p>
          <ul className="space-y-2.5 text-sm text-slate-500">
            <li><a href="#features" onClick={() => onNav("home")} className="hover:text-slate-300">Features</a></li>
            <li><a href="#pricing" onClick={() => onNav("home")} className="hover:text-slate-300">Pricing</a></li>
            <li><a href="#faq" onClick={() => onNav("home")} className="hover:text-slate-300">FAQ</a></li>
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold text-white mb-4">Company</p>
          <ul className="space-y-2.5 text-sm text-slate-500">
            <li><button onClick={() => onNav("contact")} className="hover:text-slate-300">Contact us</button></li>
            <li><a href="mailto:voxsera.ai@gmail.com" className="hover:text-slate-300">voxsera.ai@gmail.com</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-slate-800/60">
        <div className="max-w-6xl mx-auto px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-slate-600">© 2026 Voxsera. All rights reserved.</p>
          <p className="text-xs text-slate-600">Driven by vision, designed by data.</p>
        </div>
      </div>
    </footer>
  );
}

/* ---------- data ---------- */

const FEATURES = [
  { icon: ICONS.phone, tag: "Always on", title: "24/7 call support",
    desc: "Your AI agent answers every call instantly — nights, weekends and holidays. No hold music, no missed customers, no voicemail black hole." },
  { icon: ICONS.calendar, tag: "Zero admin", title: "Auto appointment booking",
    desc: "The agent checks real availability, offers open slots, and books directly into your calendar mid-call — confirmations included." },
  { icon: ICONS.link, tag: "Plug & play", title: "Google integrations",
    desc: "Native Calendar and Sheets sync. Bookings land on your calendar, every call is logged to a spreadsheet in your Drive automatically." },
  { icon: ICONS.sliders, tag: "Your brand", title: "Custom voice personality",
    desc: "Pick a voice, tune friendliness, formality and talkativeness, and feed it your services and policies — it sounds like your best receptionist." },
  { icon: ICONS.wave, tag: "Feels human", title: "Full-duplex conversations",
    desc: "Callers can interrupt mid-sentence and the agent adapts instantly — sub-second barge-in makes it feel human, not IVR." },
  { icon: ICONS.bell, tag: "No-show killer", title: "Outbound reminders",
    desc: "30 minutes before every appointment, the agent calls the customer to confirm — slashing no-shows without lifting a finger." },
];

const PLANS = [
  {
    name: "Starter", price: "3,999", tagline: "For solo clinics & shops getting started",
    highlight: false,
    features: ["300 minutes / month", "1 phone number", "3 voice options",
               "Google Calendar sync", "Google Sheets sync", "Email support"],
  },
  {
    name: "Growth", price: "7,999", tagline: "For busy practices that live on the phone",
    highlight: true,
    features: ["600 minutes / month", "2 phone numbers", "3 voice options",
               "Google Calendar sync", "Google Sheets sync", "Email support"],
  },
  {
    name: "Scale", price: "14,999", tagline: "For multi-location businesses & franchises",
    highlight: false,
    features: ["2,000 minutes / month", "5 phone numbers", "8 custom voice options",
               "Google Calendar sync", "Google Sheets sync", "Email support"],
  },
];

const FAQS = [
  { q: "How long does setup take?",
    a: "About 5 minutes. Enter your business details, pick a voice, connect your Google account, and your agent is live on a real phone number — no code, no telephony knowledge needed." },
  { q: "Do I get a real phone number?",
    a: "Yes. Every plan includes at least one dedicated phone number. Forward your existing business number to it, or print it directly on your storefront and ads." },
  { q: "What happens if the AI can't answer a question?",
    a: "The agent politely steers the conversation back to what it knows, and every full transcript is logged to your dashboard and Google Sheet so you can follow up personally on anything it couldn't resolve." },
  { q: "How are minutes counted?",
    a: "Only connected talk-time counts — ring time and missed calls are free. Unused minutes don't roll over, and you can upgrade mid-month anytime." },
  { q: "Can the agent handle appointment changes?",
    a: "Yes. It checks your live Google Calendar availability, books new appointments, and confirms or reschedules existing ones during outbound reminder calls." },
  { q: "Is my customer data secure?",
    a: "Call logs and transcripts are stored encrypted, Google access uses OAuth (we never see your password), and you can disconnect integrations and export your data at any time." },
];

/* ---------- page ---------- */

export default function Landing({ onNav }) {
  const [openFaq, setOpenFaq] = useState(0);

  return (
    <div className="min-h-screen bg-slate-950">
      <MarketingNav onNav={onNav} active="home" />

      {/* hero */}
      <section className="relative overflow-hidden">
        {/* monochrome light beams */}
        <div className="absolute inset-0 pointer-events-none">
          <Beams
            beamWidth={2.2}
            beamHeight={18}
            beamNumber={13}
            lightColor="#ffffff"
            speed={1.6}
            noiseIntensity={1.6}
            scale={0.2}
            rotation={32}
          />
        </div>
        {/* dark scrim behind the copy for contrast */}
        <div className="absolute inset-0 pointer-events-none
                        bg-[radial-gradient(ellipse_55%_60%_at_center,rgba(0,0,0,0.72),rgba(0,0,0,0.25)_60%,transparent_100%)]" />
        {/* soft fade so lines melt into the page below */}
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-950 to-transparent pointer-events-none" />
        <div className="relative max-w-6xl mx-auto px-6 pt-40 pb-28 text-center">
          <span className="inline-flex items-center gap-2.5 rounded-full border border-brand-500/30 bg-brand-600/10
                           px-4 py-1.5 text-xs font-semibold text-brand-300">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-400" />
            </span>
            Full-duplex AI voice agents for SMBs
          </span>
          <h1 className="mt-7 text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-[1.1]
                         drop-shadow-[0_4px_24px_rgba(0,0,0,0.9)]">
            Never miss a customer<br />
            <span className="bg-gradient-to-r from-brand-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent
                             drop-shadow-[0_4px_24px_rgba(0,0,0,0.9)]">
              call again.
            </span>
          </h1>
          <p className="mt-6 text-lg text-slate-300 max-w-2xl mx-auto drop-shadow-[0_2px_12px_rgba(0,0,0,0.9)]">
            Voxsera answers your business line 24/7 with a natural AI voice, books appointments
            straight into Google Calendar, and calls customers back with reminders — while you
            focus on the work that pays.
          </p>
          <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button onClick={() => onNav("auth")}
                    className="rounded-xl bg-white text-black font-semibold px-8 py-3.5 transition text-base
                               hover:bg-zinc-200 shadow-[0_0_40px_rgba(255,255,255,0.22)]">
              Create your agent — free
            </button>
            <a href="#pricing"
               className="rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-900 hover:text-white
                          font-semibold px-8 py-3.5 transition text-base">
              View pricing
            </a>
          </div>
          <div className="mt-14 flex flex-wrap justify-center gap-x-10 gap-y-4 text-sm text-slate-400">
            {["Sub-second responses", "Callers can interrupt naturally",
              "Live transcripts & sentiment", "OAuth-secured Google access"].map((t) => (
              <span key={t} className="flex items-center gap-2.5">
                <span className="h-1 w-4 rounded-full bg-gradient-to-r from-brand-500 to-violet-500" />
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* features — scroll-stacking cards */}
      <section id="features" className="max-w-4xl mx-auto px-6 py-24 scroll-mt-16">
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-sm font-bold text-brand-400 uppercase tracking-widest">Features</p>
          <h2 className="mt-3 text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            A receptionist that never sleeps, never sighs, never quits
          </h2>
          <p className="mt-4 text-sm text-slate-500">Keep scrolling — the cards stack up.</p>
        </div>
        {/* CSS sticky stack — compositor-driven, zero jank */}
        <div className="mt-12 pb-24">
          {FEATURES.map((f, i) => (
            <div key={f.title} className="sticky mb-8"
                 style={{ top: `${104 + i * 30}px`, zIndex: i + 1 }}>
              <div className="group rounded-3xl border border-slate-700/60 p-8 sm:p-10
                              shadow-[0_24px_60px_rgba(0,0,0,0.55)]
                              transition-colors duration-300 hover:border-brand-500/50"
                   style={{
                     background:
                       "radial-gradient(120% 160% at 100% 0%, rgba(255,255,255,0.06), transparent 50%)," +
                       "linear-gradient(165deg, #16161a 0%, #0c0c0f 100%)",
                   }}>
                <div className="flex flex-col sm:flex-row sm:items-start gap-6 sm:gap-10">
                  <div className="shrink-0 flex sm:flex-col items-center sm:items-start gap-4">
                    <span className="font-mono text-sm text-slate-600 tracking-widest">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div className="h-14 w-14 rounded-2xl border border-slate-700/80 bg-slate-950/80
                                    flex items-center justify-center text-brand-400
                                    transition-all duration-300 group-hover:scale-110 group-hover:text-brand-300
                                    group-hover:border-brand-500/50">
                      <Icon d={f.icon} />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-mono uppercase tracking-[0.3em] text-brand-400/80">{f.tag}</p>
                    <h3 className="mt-2 text-2xl sm:text-3xl font-bold text-white tracking-tight">{f.title}</h3>
                    <p className="mt-3 text-slate-400 leading-relaxed max-w-2xl">{f.desc}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* pricing */}
      <section id="pricing" className="max-w-6xl mx-auto px-6 py-24 scroll-mt-16">
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-sm font-bold text-brand-400 uppercase tracking-widest">Pricing</p>
          <h2 className="mt-3 text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Costs less than one missed customer a month
          </h2>
          <p className="mt-4 text-slate-400">Simple monthly plans. No setup fees. Cancel anytime.</p>
        </div>
        <div className="mt-14 grid md:grid-cols-3 gap-6 items-stretch">
          {PLANS.map((p) => (
            <div key={p.name}
                 className={`relative rounded-2xl p-7 flex flex-col border transition
                   ${p.highlight
                     ? "bg-gradient-to-b from-brand-950/80 to-slate-900 border-brand-500/60 shadow-2xl shadow-brand-600/20 md:-my-3 md:py-10"
                     : "bg-slate-900/60 border-slate-800 hover:border-slate-600"}`}>
              {p.highlight && (
                <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-white
                                 text-black text-xs font-bold px-4 py-1.5 shadow-[0_0_20px_rgba(255,255,255,0.25)]">
                  MOST POPULAR
                </span>
              )}
              <h3 className="font-bold text-white text-lg">{p.name}</h3>
              <p className="text-xs text-slate-500 mt-1">{p.tagline}</p>
              <div className="mt-5 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-white">₹{p.price}</span>
                <span className="text-slate-500 text-sm">/month</span>
              </div>
              <ul className="mt-6 space-y-3 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                    <span className="text-emerald-400 mt-0.5">✓</span>{f}
                  </li>
                ))}
              </ul>
              <button onClick={() => onNav("auth")}
                      className={`mt-7 w-full rounded-lg font-semibold py-2.5 text-sm transition
                        ${p.highlight
                          ? "bg-white text-black hover:bg-zinc-200 shadow-[0_0_24px_rgba(255,255,255,0.2)]"
                          : "border border-slate-700 text-slate-200 hover:bg-slate-800"}`}>
                Start with {p.name}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="max-w-3xl mx-auto px-6 py-24 scroll-mt-16">
        <div className="text-center">
          <p className="text-sm font-bold text-brand-400 uppercase tracking-widest">FAQ</p>
          <h2 className="mt-3 text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Frequently asked questions
          </h2>
        </div>
        <div className="mt-12 space-y-3">
          {FAQS.map((f, i) => (
            <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
              <button onClick={() => setOpenFaq(openFaq === i ? -1 : i)}
                      className="w-full flex items-center justify-between px-5 py-4 text-left">
                <span className="font-semibold text-white text-sm sm:text-base">{f.q}</span>
                <span className={`text-brand-400 text-xl leading-none transition-transform duration-200
                  ${openFaq === i ? "rotate-45" : ""}`}>+</span>
              </button>
              {openFaq === i && (
                <p className="px-5 pb-5 text-sm text-slate-400 leading-relaxed">{f.a}</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="rounded-3xl bg-gradient-to-r from-brand-600/20 via-violet-600/20 to-fuchsia-600/20
                        border border-brand-500/30 p-10 sm:p-14 text-center">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Your next customer is calling.
          </h2>
          <p className="mt-3 text-slate-400 max-w-xl mx-auto">
            Set up your AI voice agent in 5 minutes — no credit card required.
          </p>
          <button onClick={() => onNav("auth")}
                  className="mt-7 rounded-xl bg-white text-black font-semibold px-8 py-3.5 transition
                             hover:bg-zinc-200 shadow-[0_0_40px_rgba(255,255,255,0.2)]">
            Get started free →
          </button>
        </div>
      </section>

      <MarketingFooter onNav={onNav} />
    </div>
  );
}
