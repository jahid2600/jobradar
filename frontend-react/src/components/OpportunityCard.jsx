import {
  ArrowUpRight,
  BriefcaseBusiness,
  Check,
  CircleAlert,
  MapPin,
  Sparkles,
  Wrench,
} from "lucide-react";

function List({ items, tone = "default" }) {
  if (!items?.length) {
    return <span className="muted-copy">None identified</span>;
  }

  return (
    <div className={`detail-list ${tone}`}>
      {items.map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}

function OpportunityCard({ opportunity }) {
  const { job = {}, qualification = {} } = opportunity;
  const isQualified = Boolean(qualification.qualified);
  const score = Number(qualification.relevance_score || 0);
  const isUnverified = !job.url || job.source === "mock";

  return (
    <article className="opportunity-card">
      <div className="opportunity-card-topline">
        <div className="opportunity-source">
          <span className="source-mark"><BriefcaseBusiness size={15} /></span>
          <span>{job.source || "Unknown source"}</span>
          {isUnverified && (
            <span className="verification-warning" title="This listing could not be fully verified">
              <CircleAlert size={14} /> Verification needed
            </span>
          )}
        </div>
        <span className={`qualification-badge ${isQualified ? "qualified" : "review"}`}>
          {isQualified ? <Check size={13} /> : <CircleAlert size={13} />}
          {isQualified ? "Qualified" : "Review"}
        </span>
      </div>

      <div className="opportunity-heading">
        <div>
          <h3>{job.title || "Untitled opportunity"}</h3>
          <p>{job.company || "Company not identified"}</p>
        </div>
        <div className="score-block">
          <strong>{score}</strong>
          <span>match</span>
        </div>
      </div>

      <div className="opportunity-meta">
        <span><MapPin size={14} />{job.location || "Location not identified"}</span>
        <span><BriefcaseBusiness size={14} />{job.experience || "Experience not identified"}</span>
      </div>

      <div className="opportunity-insights">
        <div className="insight-block">
          <div className="insight-label"><Sparkles size={14} /> Matched requirements</div>
          <List items={qualification.matched_requirements} tone="positive" />
        </div>
        <div className="insight-block">
          <div className="insight-label"><Wrench size={14} /> Skill gaps</div>
          <List items={qualification.skill_gaps} tone="neutral" />
        </div>
      </div>

      {qualification.reason && (
        <div className="reason-block">
          <span className="insight-label">Bedrock explanation</span>
          <p>{qualification.reason}</p>
        </div>
      )}

      <div className="opportunity-footer">
        <span className="source-note">Source: {job.source || "Not identified"}</span>
        {job.url ? (
          <a href={job.url} target="_blank" rel="noreferrer" className="link-button">
            View original <ArrowUpRight size={15} />
          </a>
        ) : (
          <span className="muted-copy">No original link</span>
        )}
      </div>
    </article>
  );
}

export default OpportunityCard;