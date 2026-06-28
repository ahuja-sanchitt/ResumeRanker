import { useRef, useState } from "react";
import { analyzeResume, getInterviewPrep } from "../api.js";
import { useAnalysis } from "../AnalysisContext.jsx";

export default function NewAnalysis() {
  const {
    file,
    setFile,
    jd,
    setJd,
    company,
    setCompany,
    role,
    setRole,
    setAnalysis,
    setPrep,
    setView,
  } = useAnalysis();

  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const canSubmit =
    file && jd.trim().length >= 20 && company.trim() && role.trim() && !loading;

  function pickFile(f) {
    if (!f) return;
    const isPdf = f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setError("Please upload a PDF resume.");
      return;
    }
    setError("");
    setFile(f);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    pickFile(e.dataTransfer.files?.[0]);
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setError("");
    setLoading(true);
    setPrep(null);

    // Fire interview prep alongside analyze (D-004); don't let it block the report.
    const prepPromise = getInterviewPrep(company.trim(), role.trim()).catch(() => null);

    try {
      const result = await analyzeResume(file, jd);
      setAnalysis(result);
      setView("report");
      prepPromise.then((prep) => prep && setPrep(prep));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="analysis" onSubmit={onSubmit}>
      <p className="lede">
        Drop in your resume and the job description. Lodestar reads both, scores the
        fit, and shows you exactly where to sharpen before you apply. Takes about ten
        seconds.
      </p>

      <div className="cards2">
        {/* Resume card */}
        <section className="card">
          <h2 className="card__title">
            <span className="card__num">1</span> Your resume
          </h2>

          <div
            className={`dropzone${dragging ? " dropzone--over" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div className="dropzone__icon">↑</div>
            <p className="dropzone__title">Drag your PDF here</p>
            <p className="dropzone__sub">or browse - PDF up to 10 MB</p>
            <button
              type="button"
              className="btn btn--dark"
              onClick={() => inputRef.current?.click()}
            >
              Choose file
            </button>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              hidden
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
          </div>

          {file && (
            <div className="filechip">
              <span className="filechip__icon">▦</span>
              <span className="filechip__meta">
                <span className="filechip__name">{file.name}</span>
                <span className="filechip__sub">
                  {(file.size / 1024).toFixed(0)} KB / ready
                </span>
              </span>
              <span className="filechip__check">✓</span>
            </div>
          )}
        </section>

        {/* JD card */}
        <section className="card">
          <h2 className="card__title">
            <span className="card__num">2</span> Job description
          </h2>
          <textarea
            className="jd"
            rows={10}
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the full job description here..."
          />
        </section>
      </div>

      {/* Role context - drives the breadcrumb, interview prep, and outreach */}
      <section className="card">
        <h2 className="card__title">
          <span className="card__num">3</span> Role details
        </h2>
        <div className="fields2">
          <label className="field">
            <span className="field__label">Company</span>
            <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Helio" />
          </label>
          <label className="field">
            <span className="field__label">Role</span>
            <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Senior Product Designer" />
          </label>
        </div>
      </section>

      {error && <p className="error">{error}</p>}

      <div className="analysis__foot">
        <button className="btn btn--primary btn--lg" disabled={!canSubmit}>
          {loading ? "Analyzing..." : "✦ Analyze match"}
        </button>
      </div>
    </form>
  );
}
