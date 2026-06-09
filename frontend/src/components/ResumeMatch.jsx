import { useState } from "react";
import { analyzeResume } from "../api.js";
import ScoreBreakdown from "./ScoreBreakdown.jsx";

export default function ResumeMatch() {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const canSubmit = file && jd.trim().length >= 20 && !loading;

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      setResult(await analyzeResume(file, jd));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={onSubmit} className="form">
        <label className="field">
          <span className="field__label">Résumé (PDF)</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file && <span className="muted small">{file.name}</span>}
        </label>

        <label className="field">
          <span className="field__label">Job description</span>
          <textarea
            rows={8}
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the full job description here…"
          />
        </label>

        <button className="btn" disabled={!canSubmit}>
          {loading ? "Analyzing…" : "Analyze match"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {result && <ScoreBreakdown result={result} />}
    </div>
  );
}
