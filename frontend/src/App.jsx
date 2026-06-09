import { useState } from "react";
import ResumeMatch from "./components/ResumeMatch.jsx";
import InterviewPrep from "./components/InterviewPrep.jsx";

const TABS = [
  { id: "match", label: "Résumé Match" },
  { id: "prep", label: "Interview Prep" },
];

export default function App() {
  const [tab, setTab] = useState("match");

  return (
    <div className="app">
      <header className="masthead">
        <h1>
          Resume Ranker <span className="accent">· Interview Co-Pilot</span>
        </h1>
        <p className="tagline">
          Score your résumé against a job description with grounded, explainable
          signals — then prep for the interview.
        </p>
      </header>

      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? "tab tab--active" : "tab"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="panel">
        {tab === "match" ? <ResumeMatch /> : <InterviewPrep />}
      </main>

      <footer className="footnote">
        Scores blend an objective embedding similarity with an LLM's judgement.
        Interview data is candidate-reported — a study aid, not gospel.
      </footer>
    </div>
  );
}
