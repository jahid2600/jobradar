import {
  Brain,
  Circle,
  Radar,
  RefreshCw,
  Target,
} from "lucide-react";

const pipelineSteps = [
  { id: "generating_strategy", label: "Generating search strategy" },
  { id: "searching", label: "Expanding / searching" },
  { id: "normalizing", label: "Normalizing" },
  { id: "filtering", label: "Filtering" },
  { id: "deduplicating", label: "Removing duplicates" },
  { id: "qualifying", label: "Evaluating with Bedrock" },
  { id: "persisting", label: "Persisting opportunities" },
  { id: "completed", label: "Completed" },
];

function StatCard({ label, value, accent }) {
  return (
    <div className={`stat-card ${accent ? "accent" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RadarPage({ stats, running, statusError, onRun, onRetry }) {
  const statusLabel = stats.status === "error" ? "SCAN ERROR" : running ? "RADAR RUNNING" : "RADAR STATUS";
  const currentStageIndex = pipelineSteps.findIndex((item) => item.id === stats.current_stage);
  const completedStageIndex = stats.status === "completed" ? pipelineSteps.length : currentStageIndex;

  return (
    <div className="page-content">
      <section className={`hero ${running ? "scanning" : ""}`}>
        <div className="hero-content">
          <div className="radar-symbol"><Radar size={42} /></div>
          <div>
            <p className="hero-label">{statusLabel}</p>
            <h2>{running ? "Scanning the job market..." : stats.status === "error" ? "Radar needs attention." : "Ready to discover."}</h2>
            <p className="hero-text">
              {running
                ? "JobRadar is discovering, filtering and qualifying new opportunities."
                : stats.status === "error"
                  ? stats.error || "The last scan could not be completed."
                  : "JobRadar continuously finds, qualifies and deduplicates opportunities matching your target."}
            </p>
          </div>
        </div>
        <button className="run-button" onClick={onRun} disabled={running}>
          {running ? <RefreshCw className="spin" size={18} /> : <Radar size={18} />}
          {running ? "Running..." : "Run JobRadar"}
        </button>
      </section>

      {statusError && (
        <div className="inline-alert error-alert">
          <span>{statusError}</span>
          <button className="text-button" onClick={onRetry}>Retry status check</button>
        </div>
      )}

      {running && (
        <section className="scan-panel panel-surface">
          <div className="scan-header">
            <div>
              <p className="eyebrow">LIVE PIPELINE</p>
              <h3>JobRadar intelligence engine</h3>
            </div>
            <span className="live-badge"><span className="live-dot" /> LIVE</span>
          </div>
          <div className="scan-steps">
            {pipelineSteps.map((item, index) => {
              const isComplete = index < completedStageIndex;
              const isCurrent = running && index === currentStageIndex;
              return (
              <div className={`scan-step ${isComplete ? "complete" : ""} ${isCurrent ? "current" : ""}`} key={item.id}>
                <div className="step-icon">{isComplete ? "✓" : isCurrent ? <span className="pulse" /> : <Circle size={10} />}</div>
                <span>{item.label}</span>
                {isCurrent && stats.stage_progress !== null && <small>{stats.stage_progress}%</small>}
              </div>
              );
            })}
          </div>
        </section>
      )}

      <section className="stats">
        <StatCard label="Opportunities found" value={running ? "..." : stats.discovered ?? 0} />
        <StatCard label="Relevant matches" value={stats.relevant ?? 0} accent />
        <StatCard label="Duplicates removed" value={stats.duplicates ?? 0} />
        <StatCard label="New opportunities" value={stats.new_opportunities ?? 0} accent />
      </section>

      <section className="content-grid">
        <div className="panel-surface panel">
          <div className="panel-header">
            <div><p className="eyebrow">TARGET</p><h3>What JobRadar is looking for</h3></div>
            <Target size={20} />
          </div>
          <div className="target-tags">
            <span>Bengaluru</span><span>0–1 years</span><span>AWS</span><span>Cloud</span><span>DevOps</span>
          </div>
        </div>
        <div className="panel-surface panel">
          <div className="panel-header">
            <div><p className="eyebrow">SYSTEM</p><h3>How it works</h3></div>
            <Brain size={20} />
          </div>
          <div className="pipeline">
            <span>Discover</span><span>→</span><span>Normalize</span><span>→</span><span>Deduplicate</span><span>→</span><span>Bedrock</span>
          </div>
        </div>
      </section>
    </div>
  );
}

export default RadarPage;
