const j = (r) => {
  if (!r.ok) return r.text().then((t) => {
    let msg = t || r.statusText;
    try { msg = JSON.parse(t).detail || msg; } catch {}
    throw new Error(msg);
  });
  return r.json();
};

const post = (url, body) =>
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(j);

export const api = {
  // auth
  signup: (email, password) => post("/api/auth/signup", { email, password }),
  login: (email, password) => post("/api/auth/login", { email, password }),

  // business
  registerBusiness: (body) => post("/api/businesses", body),
  patchBusiness: (id, body) =>
    fetch(`/api/businesses/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j),
  getBusiness: (id) => fetch(`/api/businesses/${id}`).then(j),
  listBusinesses: () => fetch("/api/businesses").then(j),

  // voices
  voices: () => fetch("/api/voices").then(j),
  previewUrl: (voiceId) => `/api/voices/${voiceId}/preview`,

  // google
  googleAuthUrl: (businessId) =>
    fetch(`/api/google/auth?business_id=${businessId}`).then(j),

  // AI prompt generation
  contextFromUrl: (url, business_name, industry) =>
    post("/api/context/from-url", { url, business_name, industry }),
  contextFromPdf: (file, business_name, industry) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("business_name", business_name || "");
    fd.append("industry", industry || "");
    return fetch("/api/context/from-pdf", { method: "POST", body: fd }).then(j);
  },

  // outbound reminders
  appointments: (businessId) =>
    fetch(`/api/appointments?business_id=${businessId}`).then(j),
  callNow: (businessId, row) =>
    post("/api/outbound/call-now", { business_id: businessId, row }),

  // calls — scoped to the logged-in owner's businesses
  calls: (ownerEmail, direction) => {
    const p = new URLSearchParams();
    if (ownerEmail) p.set("owner_email", ownerEmail);
    if (direction) p.set("direction", direction);
    return fetch(`/api/calls?${p}`).then(j);
  },
  health: () => fetch("/api/health").then(j),
};
