import { googleLoginUrl } from "../api.js";
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
  const { view, setView, hasAnalysis, gmailConnected, gmailEmail } = useAnalysis();

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

      {/* There's no separate Lodestar account - the connected Gmail (used for
          drafting outreach) is the only identity this app has, so it doubles
          as the "who's signed in" footer. */}
      {gmailConnected ? (
        <div className="user">
          <span className="user__avatar">{gmailEmail.charAt(0).toUpperCase()}</span>
          <div className="user__meta">
            <span className="user__name">{gmailEmail}</span>
            <span className="user__sub user__sub--connected">Connected</span>
          </div>
        </div>
      ) : (
        <a className="user user--link" href={googleLoginUrl()}>
          <span className="user__avatar user__avatar--ghost">G</span>
          <div className="user__meta">
            <span className="user__name">Sign in with Google</span>
            <span className="user__sub">Connect Gmail to send outreach</span>
          </div>
        </a>
      )}
    </aside>
  );
}
