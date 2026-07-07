import React, { useState } from "react";
import { MarketingNav, MarketingFooter } from "./Landing.jsx";

const inputCls =
  "w-full rounded-lg bg-slate-900 border border-slate-700 px-3.5 py-2.5 text-sm " +
  "placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent";

export default function Contact({ onNav }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    // demo: open the user's mail client pre-filled; also show success state
    const body = encodeURIComponent(`Name: ${name}\nCompany: ${company}\n\n${message}`);
    window.open(`mailto:voxsera.ai@gmail.com?subject=${encodeURIComponent(
      "Voxsera enquiry — " + (company || name))}&body=${body}`, "_blank");
    setSent(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      <MarketingNav onNav={onNav} active="contact" />

      <div className="flex-1 max-w-6xl mx-auto px-6 pt-36 pb-20 w-full">
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-sm font-bold text-brand-400 uppercase tracking-widest">Contact</p>
          <h1 className="mt-3 text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Talk to a human. <span className="text-slate-500">(We have those too.)</span>
          </h1>
          <p className="mt-4 text-slate-400">
            Questions about plans, custom voices, or high-volume deployments — we reply within one business day.
          </p>
        </div>

        <div className="mt-16 grid lg:grid-cols-5 gap-8">
          {/* info cards */}
          <div className="lg:col-span-2 space-y-4">
            {[
              ["📧", "Email us", "voxsera.ai@gmail.com", "mailto:voxsera.ai@gmail.com"],
              ["💬", "Sales & demos", "Book a 15-min walkthrough of your own agent", null],
              ["🛟", "Support", "Existing customers get priority email support on every plan", null],
            ].map(([icon, title, desc, href]) => (
              <div key={title} className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6">
                <div className="text-2xl">{icon}</div>
                <h3 className="mt-3 font-bold text-white">{title}</h3>
                {href ? (
                  <a href={href} className="mt-1 block text-sm text-brand-400 hover:text-brand-300">{desc}</a>
                ) : (
                  <p className="mt-1 text-sm text-slate-400">{desc}</p>
                )}
              </div>
            ))}
          </div>

          {/* form */}
          <div className="lg:col-span-3 rounded-2xl bg-slate-900/60 border border-slate-800 p-8">
            {sent ? (
              <div className="h-full flex flex-col items-center justify-center text-center py-16">
                <div className="text-5xl mb-4">✅</div>
                <h3 className="text-xl font-bold text-white">Message ready!</h3>
                <p className="text-slate-400 text-sm mt-2 max-w-sm">
                  Your email draft has been opened. Hit send and we'll get back to you
                  within one business day.
                </p>
                <button onClick={() => setSent(false)}
                        className="mt-6 text-sm text-brand-400 hover:text-brand-300 font-medium">
                  Send another message
                </button>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">Your name</label>
                    <input required className={inputCls} value={name}
                           onChange={(e) => setName(e.target.value)} placeholder="Aisha Khan" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">Work email</label>
                    <input type="email" required className={inputCls} value={email}
                           onChange={(e) => setEmail(e.target.value)} placeholder="aisha@clinic.com" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Business name</label>
                  <input className={inputCls} value={company}
                         onChange={(e) => setCompany(e.target.value)} placeholder="Smile Dental Clinic" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">How can we help?</label>
                  <textarea required rows={6} className={inputCls} value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            placeholder="We get ~40 calls a day and miss half of them after 6pm…" />
                </div>
                <button className="w-full rounded-lg bg-white text-black font-semibold py-3
                                   text-sm transition hover:bg-zinc-200 shadow-[0_0_24px_rgba(255,255,255,0.15)]">
                  Send message →
                </button>
              </form>
            )}
          </div>
        </div>
      </div>

      <MarketingFooter onNav={onNav} />
    </div>
  );
}
