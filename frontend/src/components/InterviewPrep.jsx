import { useState } from "react";
import { getInterviewPrep } from "../api.js";

function Chips({ items }) {
  if (!items?.length) return null;
  return (
    <div className="chips">
      {items.map((s, i) => <span key={i} className="chip chip--neutral">{s}</span>)}
    </div>
  );
}

export default function InterviewPrep() {
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const canSubmit = company.trim() && role.trim() && !loading;

  async function run(forceRefresh) {
    setError("");
    setLoading(true);
    try {
      setData(await getInterviewPrep(company, role, forceRefresh));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); if (canSubmit) run(false); }} className="form">
        <div className="grid2">
          <label className="field">
            <span className="field__label">Company</span>
            <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Amazon" />
          </label>
          <label className="field">
            <span className="field__label">Role</span>
            <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. SDE 1 / Associate Software Engineer" />
          </label>
        </div>
        <button className="btn" disabled={!canSubmit}>
          {loading ? "Searching…" : "Get interview prep"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {data && (
        <div className="result">
          <div className="prep__meta">
            <span className="badge badge--level">{data.seniority}</span>
            {data.num_rounds > 0 && <span className="muted">{data.num_rounds} round(s)</span>}
            {data.cached && <span className="badge">cached</span>}
            {data.last_updated && (
              <span className="muted small">updated {new Date(data.last_updated).toLocaleDateString()}</span>
            )}
            <button className="btn btn--ghost" disabled={loading} onClick={() => run(true)}>
              Refresh
            </button>
          </div>

          {data.rounds?.length > 0 && (
            <section>
              <h3>Rounds</h3>
              <ol className="rounds">
                {data.rounds.map((r, i) => (
                  <li key={i}><strong>{r.name}</strong>{r.description ? ` — ${r.description}` : ""}</li>
                ))}
              </ol>
            </section>
          )}

          {data.frequent_question_types?.length > 0 && (
            <section>
              <h3>Frequently asked</h3>
              <Chips items={data.frequent_question_types} />
            </section>
          )}

          {data.topics_to_focus?.length > 0 && (
            <section>
              <h3>Topics to focus on</h3>
              <Chips items={data.topics_to_focus} />
            </section>
          )}

          {data.difficulty_notes && (
            <section>
              <h3>Notes</h3>
              <p className="feedback">{data.difficulty_notes}</p>
            </section>
          )}

          {data.sources?.length > 0 && (
            <section>
              <h3>Sources</h3>
              <ul className="list sources">
                {data.sources.map((s, i) => (
                  <li key={i}><a href={s} target="_blank" rel="noreferrer">{s}</a></li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
