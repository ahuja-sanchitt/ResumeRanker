import { useState } from "react";
import { getContacts, draftColdEmail, createGmailDraft, googleLogout, googleLoginUrl } from "../api.js";
import { useAnalysis } from "../AnalysisContext.jsx";

function contactName(c) {
  return [c.first_name, c.last_name].filter(Boolean).join(" ") || c.email;
}

export default function Outreach() {
  const {
    file,
    jd,
    company,
    role,
    gmailSession,
    setGmailSession,
    gmailEmail,
    gmailConnected,
  } = useAnalysis();

  // --- contact discovery ---
  const [contacts, setContacts] = useState(null); // null = not searched
  const [contactsState, setContactsState] = useState({ loading: false, error: "", configured: true });
  const [selected, setSelected] = useState(null); // chosen Contact or manual {name,email,role}

  // --- manual contact ---
  const [manual, setManual] = useState({ name: "", email: "", role: "" });

  // --- draft ---
  const [draft, setDraft] = useState(null); // {subject, body}
  const [draftState, setDraftState] = useState({ loading: false, error: "" });
  const [to, setTo] = useState("");

  // --- gmail --- (connection status itself lives in AnalysisContext — see Sidebar)
  const [gmailState, setGmailState] = useState({ loading: false, error: "", result: null });

  async function findContacts() {
    setContactsState({ loading: true, error: "", configured: true });
    try {
      const res = await getContacts(company.trim());
      setContacts(res.contacts || []);
      setContactsState({ loading: false, error: "", configured: true });
    } catch (err) {
      setContacts([]);
      setContactsState({
        loading: false,
        error: err.message,
        configured: err.status !== 503,
      });
    }
  }

  function chooseContact(c) {
    setSelected({ name: contactName(c), email: c.email, role: c.position });
    setTo(c.email);
    setDraft(null);
    setGmailState((s) => ({ ...s, result: null }));
  }

  function useManual() {
    if (!manual.email.trim()) return;
    setSelected({ name: manual.name.trim(), email: manual.email.trim(), role: manual.role.trim() });
    setTo(manual.email.trim());
    setDraft(null);
    setGmailState((s) => ({ ...s, result: null }));
  }

  async function generateDraft() {
    if (!file) {
      setDraftState({ loading: false, error: "Re-run the analysis — the résumé file isn't loaded." });
      return;
    }
    setDraftState({ loading: true, error: "" });
    try {
      const res = await draftColdEmail(file, company.trim(), selected.name, selected.role, jd);
      setDraft({ subject: res.subject, body: res.body });
      setDraftState({ loading: false, error: "" });
    } catch (err) {
      setDraftState({ loading: false, error: err.message });
    }
  }

  async function saveToGmail() {
    setGmailState({ loading: true, error: "", result: null });
    try {
      const res = await createGmailDraft(
        { to: to.trim(), subject: draft.subject, body: draft.body },
        gmailSession
      );
      setGmailState({ loading: false, error: "", result: res });
    } catch (err) {
      setGmailState({ loading: false, error: err.message, result: null });
    }
  }

  async function disconnect() {
    await googleLogout(gmailSession);
    setGmailSession(""); // AnalysisContext's status effect picks this up and clears connected/email
  }

  return (
    <div className="outreach">
      <p className="lede">
        Find a relevant engineer or hiring manager at <strong>{company || "the company"}</strong>,
        let Lodestar draft a tailored note from your résumé, then save it to Gmail —
        you review and send it yourself. Nothing is ever sent automatically.
      </p>

      {/* STEP A — contact */}
      <section className="card">
        <h2 className="card__title"><span className="card__num">1</span> Pick a contact</h2>

        <div className="outreach__discover">
          <button className="btn btn--dark" onClick={findContacts} disabled={contactsState.loading || !company}>
            {contactsState.loading ? "Searching…" : `Find contacts at ${company || "company"}`}
          </button>
          {!company && <span className="muted small">Add a company on the upload step first.</span>}
        </div>

        {contacts !== null && !contactsState.configured && (
          <div className="notice">
            <strong>Contact discovery isn’t configured.</strong> Add a{" "}
            <code>HUNTER_API_KEY</code> to the backend (see <code>docs/COLD_EMAIL_SETUP.md</code>),
            or enter a contact manually below.
          </div>
        )}

        {contacts !== null && contactsState.configured && contactsState.error && (
          <p className="error">{contactsState.error}</p>
        )}

        {contacts !== null && contactsState.configured && contacts.length === 0 && !contactsState.error && (
          <p className="muted">No contacts found — enter one manually below.</p>
        )}

        {contacts && contacts.length > 0 && (
          <ul className="contacts">
            {contacts.map((c, i) => (
              <li key={i}>
                <button
                  className={`contact${selected?.email === c.email ? " contact--on" : ""}`}
                  onClick={() => chooseContact(c)}
                >
                  <span className="contact__name">{contactName(c)}</span>
                  <span className="contact__role">{c.position || "—"}</span>
                  <span className="contact__tags">
                    {c.seniority && <span className="tag">{c.seniority}</span>}
                    {c.department && <span className="tag">{c.department}</span>}
                    {c.confidence > 0 && <span className="tag tag--num">{c.confidence}%</span>}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <details className="manual">
          <summary>Or enter a contact manually</summary>
          <div className="fields3">
            <label className="field">
              <span className="field__label">Name</span>
              <input value={manual.name} onChange={(e) => setManual({ ...manual, name: e.target.value })} placeholder="Jordan Lee" />
            </label>
            <label className="field">
              <span className="field__label">Email</span>
              <input value={manual.email} onChange={(e) => setManual({ ...manual, email: e.target.value })} placeholder="jordan@company.com" />
            </label>
            <label className="field">
              <span className="field__label">Role</span>
              <input value={manual.role} onChange={(e) => setManual({ ...manual, role: e.target.value })} placeholder="Engineering Manager" />
            </label>
          </div>
          <button className="btn btn--ghost" onClick={useManual} disabled={!manual.email.trim()} type="button">
            Use this contact
          </button>
        </details>
      </section>

      {/* STEP B — draft */}
      {selected && (
        <section className="card">
          <h2 className="card__title"><span className="card__num">2</span> Draft the email</h2>
          <p className="muted small">
            To: <strong>{selected.name || selected.email}</strong>
            {selected.role ? ` · ${selected.role}` : ""}
          </p>

          {!draft && (
            <button className="btn btn--primary" onClick={generateDraft} disabled={draftState.loading}>
              {draftState.loading ? "Writing…" : "✦ Generate draft"}
            </button>
          )}
          {draftState.error && <p className="error">{draftState.error}</p>}

          {draft && (
            <div className="draft">
              <label className="field">
                <span className="field__label">To</span>
                <input value={to} onChange={(e) => setTo(e.target.value)} placeholder="name@company.com" />
              </label>
              <label className="field">
                <span className="field__label">Subject</span>
                <input value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })} />
              </label>
              <label className="field">
                <span className="field__label">Body</span>
                <textarea rows={12} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} />
              </label>
              <button className="btn btn--ghost" type="button" onClick={generateDraft} disabled={draftState.loading}>
                {draftState.loading ? "Rewriting…" : "↻ Regenerate"}
              </button>
            </div>
          )}
        </section>
      )}

      {/* STEP C — gmail */}
      {draft && (
        <section className="card">
          <h2 className="card__title"><span className="card__num">3</span> Save to Gmail</h2>

          {!gmailConnected ? (
            <div className="gmail__connect">
              <p className="muted small">
                Connect Gmail to save this as a draft in your account. We only request
                permission to <strong>compose</strong> drafts — never to send.
              </p>
              <a className="btn btn--dark" href={googleLoginUrl()}>
                Connect Gmail
              </a>
            </div>
          ) : (
            <>
              <p className="muted small">
                Connected as <strong>{gmailEmail}</strong> ·{" "}
                <button className="linkbtn" onClick={disconnect}>disconnect</button>
              </p>
              <button className="btn btn--primary" onClick={saveToGmail} disabled={gmailState.loading || !to.trim()}>
                {gmailState.loading ? "Saving…" : "Create Gmail draft"}
              </button>
              {gmailState.error && <p className="error">{gmailState.error}</p>}
              {gmailState.result && (
                <div className="notice notice--ok">
                  Draft created in your Gmail.{" "}
                  <a href={gmailState.result.drafts_url} target="_blank" rel="noreferrer">
                    Open it →
                  </a>{" "}
                  Review and send it yourself.
                </div>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
