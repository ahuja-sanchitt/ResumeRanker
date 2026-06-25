import { useAnalysis } from "../AnalysisContext.jsx";
import Stepper from "./Stepper.jsx";

const TITLES = {
  new: "New analysis",
  report: "Match report",
  outreach: "Outreach",
};

export default function Topbar() {
  const { view, company, role } = useAnalysis();

  const crumbs = [company, role].filter((c) => c && c.trim());

  return (
    <header className="topbar">
      <div className="topbar__lead">
        {crumbs.length > 0 ? (
          <p className="crumbs">
            {crumbs.map((c, i) => (
              <span key={i}>
                {i > 0 && <span className="crumbs__sep">·</span>}
                <span className={i === 0 ? "crumbs__co" : ""}>{c}</span>
              </span>
            ))}
          </p>
        ) : (
          <p className="crumbs crumbs--empty">No role yet</p>
        )}
        <h1 className="topbar__title">{TITLES[view]}</h1>
      </div>
      <Stepper />
    </header>
  );
}
