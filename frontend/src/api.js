const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function parseError(res) {
  try {
    const body = await res.json();
    return body.detail || JSON.stringify(body);
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function analyzeResume(file, jd) {
  const form = new FormData();
  form.append("resume", file);
  form.append("jd", jd);
  const res = await fetch(`${BASE}/analyze`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getInterviewPrep(companyName, role, forceRefresh = false) {
  const res = await fetch(`${BASE}/interview-prep`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_name: companyName, role, force_refresh: forceRefresh }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

// ---------- Outreach: contact discovery (Hunter.io) ----------

export async function getContacts(company) {
  const res = await fetch(`${BASE}/contacts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company }),
  });
  if (!res.ok) {
    const err = new Error(await parseError(res));
    err.status = res.status; // 503 = Hunter not configured, surfaced distinctly in the UI
    throw err;
  }
  return res.json();
}

// ---------- Outreach: AI draft (multipart, re-sends the resume) ----------

export async function draftColdEmail(file, company, contactName, contactRole, jd) {
  const form = new FormData();
  form.append("resume", file);
  form.append("company", company);
  form.append("contact_name", contactName || "");
  form.append("contact_role", contactRole || "");
  form.append("jd", jd || "");
  const res = await fetch(`${BASE}/cold-email/draft`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

// ---------- Outreach: Gmail (draft only, never sends) ----------

export function googleLoginUrl() {
  return `${BASE}/auth/google/login`;
}

export async function gmailStatus(session) {
  const res = await fetch(`${BASE}/auth/google/status`, {
    headers: session ? { "X-Gmail-Session": session } : {},
  });
  if (!res.ok) {
    const err = new Error(await parseError(res));
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function createGmailDraft({ to, subject, body }, session) {
  const res = await fetch(`${BASE}/gmail/draft`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(session ? { "X-Gmail-Session": session } : {}),
    },
    body: JSON.stringify({ to, subject, body }),
  });
  if (!res.ok) {
    const err = new Error(await parseError(res));
    err.status = res.status; // 401 = connect Gmail first, 503 = OAuth unconfigured
    throw err;
  }
  return res.json();
}

export async function googleLogout(session) {
  await fetch(`${BASE}/auth/google/logout`, {
    method: "POST",
    headers: session ? { "X-Gmail-Session": session } : {},
  });
}

// ---------- Gmail session token handoff ----------
// The OAuth callback redirects back to the SPA with ?gmail_session=... in the URL.
// Pull it out (if present), and let the caller persist it; then strip it from the
// address bar so it isn't left lying around or re-read on reload.

export function readGmailSessionFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const session = params.get("gmail_session");
  if (!session) return null;
  params.delete("gmail_session");
  const qs = params.toString();
  const clean = window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash;
  window.history.replaceState({}, "", clean);
  return session;
}
