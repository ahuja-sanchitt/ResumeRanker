import { useState } from "react";
import { useAnalysis } from "../AnalysisContext.jsx";
import Donut from "./Donut.jsx";

function headlineFor(score) {
  if (score >= 80)
    return ["Strong fit — apply with confidence.", "You clear the bar comfortably. Tighten the few gaps below to stand out."];
  if (score >= 60)
    return ["Solid fit — worth applying, with a few sharpening moves.", "You clear the core bar. Closing the gaps below would push you into the top tier of applicants."];
  if (score >= 40)
    return ["Partial fit — close some gaps before you apply.", "There's a real foundation here, but a few requirements need addressing to be competitive."];
  return ["Stretch fit — significant gaps to close.", "This role asks for more than the résumé currently shows. Focus on the gaps below."];
}

function Bar({ label, value, tone }) {
  return (
    <div className="bar">
      <div className="bar__head">
        <span>{label}</span>
        <span className="bar__val">{value}</span>
      </div>
      <div className="bar__track">
        <div className={`bar__fill bar__fill--${tone}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export default function MatchReport() {
  const { analysis, prep, setView } = useAnalysis();
  const [tab, setTab] = useState("gauge"); // gauge | breakdown

  if (!analysis) return null;

  const {
    final_score,
    embedding_score,
    llm_fit_score,
    strengths = [],
    gaps = [],
    matched_skills = [],
    missing_skills = [],
    feedback,
    cached,
  } = analysis;

  const [headline, sub] = headlineFor(final_score);
  const questions = prep?.frequent_question_types?.length
    ? prep.frequent_question_types
    : prep?.topics_to_focus || [];

  return (
    <div className="report">
      <div className="report__bar">
        <span className="report__overview">Match overview</span>
        <div className="toggle">
          <button
            className={`toggle__btn${tab === "gauge" ? " toggle__btn--on" : ""}`}
            onClick={() => setTab("gauge")}
          >
            Gauge
          </button>
          <button
            className={`toggle__btn${tab === "breakdown" ? " toggle__btn--on" : ""}`}
            onClick={() => setTab("breakdown")}
          >
            Breakdown
          </button>
        </div>
      </div>

      {tab === "gauge" ? (
        <>
          <div className="report__hero">
            <div className="report__gauge">
              <Donut value={final_score} label="Match score" />
              {cached && <span className="badge">cached</span>}
            </div>
            <div className="report__lead">
              <h2 className="report__headline">{headline}</h2>
              <p className="report__sub">{sub}</p>
              <div className="pillrow">
                <span className="pill pill--good">{strengths.length} standout strengths</span>
                <span className="pill pill--bad">{gaps.length} gaps to close</span>
                {questions.length > 0 && (
                  <span className="pill pill--warn">{questions.length} likely interview topics</span>
                )}
              </div>
            </div>
          </div>

          <div className="cols2">
            <section className="card card--good">
              <h3 className="col__title col__title--good">✓ Where you're strong</h3>
              {strengths.length ? (
                <ul className="findings">
                  {strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted">None identified.</p>
              )}
              {matched_skills.length > 0 && (
                <>
                  <p className="col__sub">Matched skills</p>
                  <div className="chips">
                    {matched_skills.map((s, i) => (
                      <span key={i} className="chip chip--good">{s}</span>
                    ))}
                  </div>
                </>
              )}
            </section>

            <section className="card card--bad">
              <h3 className="col__title col__title--bad">⚠ Where you lack</h3>
              {gaps.length ? (
                <ul className="findings">
                  {gaps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No major gaps.</p>
              )}
              {missing_skills.length > 0 && (
                <>
                  <p className="col__sub">Missing keywords</p>
                  <div className="chips">
                    {missing_skills.map((s, i) => (
                      <span key={i} className="chip chip--bad">{s}</span>
                    ))}
                  </div>
                </>
              )}
            </section>
          </div>

          <section className="card">
            <div className="qhead">
              <h3 className="col__title">
                <span className="qhead__q">?</span> Likely interview questions
              </h3>
              <span className="qhead__note">Tailored to this role &amp; your gaps</span>
            </div>
            {questions.length > 0 ? (
              <div className="qgrid">
                {questions.map((q, i) => (
                  <div key={i} className="qcard">
                    <span className="qcard__n">{String(i + 1).padStart(2, "0")}</span>
                    <span className="qcard__text">{q}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">
                {prep === null
                  ? "Fetching interview signals for this company…"
                  : "No interview data found for this company yet."}
              </p>
            )}
            {prep?.sources?.length > 0 && (
              <p className="qsources">
                Sources:{" "}
                {prep.sources.slice(0, 3).map((s, i) => (
                  <a key={i} href={s} target="_blank" rel="noreferrer">
                    [{i + 1}]
                  </a>
                ))}
              </p>
            )}
          </section>

          {feedback && (
            <section className="card">
              <h3 className="col__title">Overall read</h3>
              <p className="feedback">{feedback}</p>
            </section>
          )}

          <div className="report__foot">
            <span className="muted">Fit looks good — the next move is getting in front of a human.</span>
            <button className="btn btn--primary" onClick={() => setView("outreach")}>
              Draft outreach to recruiters →
            </button>
          </div>
        </>
      ) : (
        <div className="card">
          <h3 className="col__title">How the score is built</h3>
          <p className="muted breakdown__note">
            The final score blends an objective embedding similarity (grounds the number
            in the text) with the LLM's holistic fit judgement (adds nuance). Both are
            shown so the result is never a black box.
          </p>
          <div className="bars">
            <Bar label="Embedding similarity (objective)" value={embedding_score} tone="blue" />
            <Bar label="LLM fit judgement" value={llm_fit_score} tone="violet" />
            <Bar label="Final blended score" value={final_score} tone="accent" />
          </div>
        </div>
      )}
    </div>
  );
}
