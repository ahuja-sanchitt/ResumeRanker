import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { readGmailSessionFromUrl } from "./api.js";

const GMAIL_SESSION_KEY = "lodestar_gmail_session";

const AnalysisContext = createContext(null);

/**
 * The shared "analysis session" that the whole Lodestar flow reads from.
 * Upload → Match report → Outreach are three views over one session, so the
 * résumé, JD, company/role, and both API results live here (see D-003).
 */
export function AnalysisProvider({ children }) {
  const [view, setView] = useState("new"); // new | report | outreach

  // Upload inputs
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");

  // Results
  const [analysis, setAnalysis] = useState(null); // /analyze response
  const [prep, setPrep] = useState(null); // /interview-prep response (may load after analysis)

  // Gmail OAuth session token (persisted; handed off via the callback redirect)
  const [gmailSession, setGmailSession] = useState(
    () => localStorage.getItem(GMAIL_SESSION_KEY) || ""
  );

  // On mount: if the OAuth callback bounced us back with a session token, capture it.
  useEffect(() => {
    const fromUrl = readGmailSessionFromUrl();
    if (fromUrl) {
      localStorage.setItem(GMAIL_SESSION_KEY, fromUrl);
      setGmailSession(fromUrl);
      setView("outreach"); // they were mid-outreach when they went to connect Gmail
    }
  }, []);

  function persistGmailSession(token) {
    if (token) localStorage.setItem(GMAIL_SESSION_KEY, token);
    else localStorage.removeItem(GMAIL_SESSION_KEY);
    setGmailSession(token || "");
  }

  function resetSession() {
    setFile(null);
    setJd("");
    setCompany("");
    setRole("");
    setLocation("");
    setAnalysis(null);
    setPrep(null);
    setView("new");
  }

  const hasAnalysis = Boolean(analysis);

  const value = useMemo(
    () => ({
      view,
      setView,
      file,
      setFile,
      jd,
      setJd,
      company,
      setCompany,
      role,
      setRole,
      location,
      setLocation,
      analysis,
      setAnalysis,
      prep,
      setPrep,
      gmailSession,
      setGmailSession: persistGmailSession,
      resetSession,
      hasAnalysis,
    }),
    [view, file, jd, company, role, location, analysis, prep, gmailSession, hasAnalysis]
  );

  return <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>;
}

export function useAnalysis() {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within AnalysisProvider");
  return ctx;
}
