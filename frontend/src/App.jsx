import { AnalysisProvider, useAnalysis } from "./AnalysisContext.jsx";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import NewAnalysis from "./components/NewAnalysis.jsx";
import MatchReport from "./components/MatchReport.jsx";
import Outreach from "./components/Outreach.jsx";

function Workspace() {
  const { view } = useAnalysis();
  return (
    <div className="workspace">
      <Sidebar />
      <main className="main">
        <Topbar />
        <div className="view">
          {view === "new" && <NewAnalysis />}
          {view === "report" && <MatchReport />}
          {view === "outreach" && <Outreach />}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AnalysisProvider>
      <Workspace />
    </AnalysisProvider>
  );
}
