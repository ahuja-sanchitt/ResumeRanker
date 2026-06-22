import { useAnalysis } from "../AnalysisContext.jsx";

const WORKSPACE = [
  { id: "new", label: "New analysis", icon: "↑" },
  { id: "report", label: "Match report", icon: "◷" },
  { id: "outreach", label: "Outreach", icon: "✉" },
];

const LIBRARY = [
  { label: "Saved roles", icon: "❏", tag: "soon" },
  { label: "Email templates", icon: "≣", tag: "soon" },
];

export default function Sidebar() {
  const { view, setView, hasAnalysis } = useAnalysis();

  function go(id) {
    // Match/Outreach are gated until there's an analysis (D-003).
    if ((id === "report" || id === "outreach") && !hasAnalysis) return;
    setView(id);
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand__mark">★</span>
        <span className="brand__name">Lodestar</span>
      </div>

      <nav className="nav">
        <p className="nav__group">Workspace</p>
        {WORKSPACE.map((item) => {
          const locked = (item.id === "report" || item.id === "outreach") && !hasAnalysis;
          return (
            <button
              key={item.id}
              className={`nav__item${view === item.id ? " nav__item--active" : ""}${
                locked ? " nav__item--locked" : ""
              }`}
              onClick={() => go(item.id)}
              disabled={locked}
              title={locked ? "Run an analysis first" : undefined}
            >
              <span className="nav__icon">{item.icon}</span>
              {item.label}
            </button>
          );
        })}

        <p className="nav__group">Library</p>
        {LIBRARY.map((item) => (
          <button key={item.label} className="nav__item nav__item--locked" disabled>
            <span className="nav__icon">{item.icon}</span>
            {item.label}
            <span className="nav__tag">{item.tag}</span>
          </button>
        ))}
      </nav>

      <div className="user">
        <span className="user__avatar">AR</span>
        <div className="user__meta">
          <span className="user__name">Alex Rivera</span>
          <span className="user__sub">Pro · job hunt</span>
        </div>
      </div>
    </aside>
  );
}
