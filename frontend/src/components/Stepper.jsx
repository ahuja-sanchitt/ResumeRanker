import { useAnalysis } from "../AnalysisContext.jsx";

const STEPS = [
  { id: "new", n: 1, label: "Upload" },
  { id: "report", n: 2, label: "Match report" },
  { id: "outreach", n: 3, label: "Outreach" },
];

export default function Stepper() {
  const { view, setView, hasAnalysis } = useAnalysis();
  const activeIndex = STEPS.findIndex((s) => s.id === view);

  function go(step, idx) {
    if ((step.id === "report" || step.id === "outreach") && !hasAnalysis) return;
    setView(step.id);
  }

  return (
    <ol className="stepper">
      {STEPS.map((step, idx) => {
        const state =
          view === step.id ? "active" : idx < activeIndex ? "done" : "upcoming";
        const locked = (step.id === "report" || step.id === "outreach") && !hasAnalysis;
        return (
          <li key={step.id} className="stepper__item">
            <button
              className={`stepper__btn stepper__btn--${state}`}
              onClick={() => go(step, idx)}
              disabled={locked}
            >
              <span className="stepper__num">{step.n}</span>
              <span className="stepper__label">{step.label}</span>
            </button>
            {idx < STEPS.length - 1 && <span className="stepper__rule" />}
          </li>
        );
      })}
    </ol>
  );
}
