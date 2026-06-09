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
