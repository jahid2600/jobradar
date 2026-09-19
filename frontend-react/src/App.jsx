import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bell,
  Brain,
  BriefcaseBusiness,
  Radar,
  Search,
  Target,
} from "lucide-react";
import { fetchApi } from "./lib/api";
import IntelligencePage from "./pages/IntelligencePage";
import OpportunitiesPage from "./pages/OpportunitiesPage";
import RadarPage from "./pages/RadarPage";
import TargetPage from "./pages/TargetPage";
import "./App.css";

const initialStatus = {
  status: "idle",
  discovered: 0,
  relevant: 0,
  duplicates: 0,
  new_opportunities: 0,
};

const navigation = [
  { id: "radar", label: "Radar", icon: Radar },
  { id: "opportunities", label: "Opportunities", icon: BriefcaseBusiness },
  { id: "intelligence", label: "Intelligence", icon: Brain },
  { id: "target", label: "Target", icon: Target },
];

const pageHeadings = {
  radar: "Your job search searches for you.",
  opportunities: "A better shortlist starts here.",
  intelligence: "Understand the signal behind every match.",
  target: "Your target, made explicit.",
};

function App() {
  const [activePage, setActivePage] = useState("radar");
  const [status, setStatus] = useState(initialStatus);
  const [statusError, setStatusError] = useState("");
  const [opportunities, setOpportunities] = useState([]);
  const [opportunitiesLoading, setOpportunitiesLoading] = useState(true);
  const [opportunitiesError, setOpportunitiesError] = useState("");
  const previousStatus = useRef(null);

  const loadOpportunities = useCallback(async () => {
    setOpportunitiesLoading(true);
    try {
      const data = await fetchApi("/api/opportunities");
      setOpportunities(Array.isArray(data) ? data : []);
      setOpportunitiesError("");
    } catch (error) {
      setOpportunitiesError(error.message || "Could not load opportunities.");
    } finally {
      setOpportunitiesLoading(false);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await fetchApi("/api/radar/status");
      setStatus(data);
      setStatusError("");

      if (data.status === "completed" && previousStatus.current !== "completed") {
        await loadOpportunities();
      }

      previousStatus.current = data.status;
    } catch (error) {
      setStatusError(error.message || "Could not reach the Radar status endpoint.");
    }
  }, [loadOpportunities]);

  useEffect(() => {
    refreshStatus();
    const poll = setInterval(refreshStatus, 1500);
    return () => clearInterval(poll);
  }, [refreshStatus]);

  useEffect(() => {
    loadOpportunities();
  }, [loadOpportunities]);

  const runRadar = async () => {
    if (status.status === "running") return;

    try {
      await fetchApi("/api/radar/run", { method: "POST" });
      previousStatus.current = "running";
      setStatus((current) => ({ ...current, status: "running", error: undefined }));
      setStatusError("");
    } catch (error) {
      setStatus((current) => ({ ...current, status: "error", error: error.message }));
    }
  };

  const renderPage = () => {
    if (activePage === "opportunities") {
      return (
        <OpportunitiesPage
          opportunities={opportunities}
          loading={opportunitiesLoading}
          error={opportunitiesError}
          onRetry={loadOpportunities}
        />
      );
    }

    if (activePage === "intelligence") return <IntelligencePage />;
    if (activePage === "target") return <TargetPage />;

    return (
      <RadarPage
        stats={status}
        running={status.status === "running"}
        statusError={statusError}
        onRun={runRadar}
        onRetry={refreshStatus}
      />
    );
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Radar size={22} /></div>
          <span>JobRadar</span>
        </div>

        <nav aria-label="Primary navigation">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              className={`nav-item ${activePage === id ? "active" : ""}`}
              key={id}
              onClick={() => setActivePage(id)}
            >
              <Icon size={18} /> <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="status-dot" />
          <span>Autonomous system online</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">AUTONOMOUS JOB DISCOVERY</p>
            <h1>{pageHeadings[activePage]}</h1>
          </div>
          <div className="top-actions">
            <button title="Search" aria-label="Search"><Search size={18} /></button>
            <button title="Notifications" aria-label="Notifications"><Bell size={18} /></button>
            <div className="avatar">JA</div>
          </div>
        </header>

        {renderPage()}
      </main>
    </div>
  );
}

export default App;
