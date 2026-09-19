import {
  BellRing,
  Brain,
  CheckCircle2,
  CircleDot,
  Database,
  Filter,
  Globe2,
  SearchCheck,
  Sparkles,
  UserRound,
} from "lucide-react";

const stages = [
  { icon: UserRound, label: "Candidate Profile", detail: "Your location, experience, target roles, skills and preferred company types define the signal." },
  { icon: Sparkles, label: "Search Strategy", detail: "The project includes a Bedrock search-strategy module for vocabulary expansion; the active Radar run currently uses its configured target query." },
  { icon: Globe2, label: "Web Discovery", detail: "Tavily searches the web for fresh job listings using the active discovery query." },
  { icon: SearchCheck, label: "Normalization", detail: "Provider-specific results become one consistent JobRadar opportunity schema." },
  { icon: Filter, label: "Deduplication", detail: "Repeated listings are removed by normalized job URL before evaluation." },
  { icon: Brain, label: "Bedrock Qualification", detail: "Amazon Bedrock evaluates role fit, skills, location, experience and explains the match." },
  { icon: Database, label: "Opportunity Storage", detail: "Qualified results are persisted to DynamoDB for the product feed." },
  { icon: BellRing, label: "Alert", detail: "The alert layer is prepared for future notification delivery; no alert is sent by this UI yet." },
];

function IntelligencePage() {
  return (
    <div className="page-content intelligence-page">
      <div className="page-heading-row">
        <div><p className="eyebrow">SYSTEM INTELLIGENCE</p><h2>From profile signal to opportunity.</h2><p className="page-lede">A transparent pipeline that turns a narrow target into explainable job intelligence.</p></div>
        <div className="architecture-badge"><Brain size={17} /><span>Bedrock-powered qualification</span></div>
      </div>

      <section className="architecture-flow panel-surface">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <div className="architecture-stage" key={stage.label}>
              <div className={`stage-icon ${stage.label === "Bedrock Qualification" ? "highlight" : ""}`}><Icon size={19} /></div>
              <div className="stage-copy"><span className="stage-number">0{index + 1}</span><h3>{stage.label}</h3><p>{stage.detail}</p></div>
              {index < stages.length - 1 && <div className="stage-connector"><CircleDot size={12} /></div>}
            </div>
          );
        })}
      </section>

      <section className="intelligence-callout">
        <div className="callout-icon"><CheckCircle2 size={22} /></div>
        <div><p className="eyebrow">EXPLAINABILITY BY DESIGN</p><h3>Every match comes with a reason.</h3><p>Bedrock returns a relevance score, matched requirements, skill gaps and concerns so the shortlist stays understandable and user-controlled.</p></div>
      </section>
    </div>
  );
}

export default IntelligencePage;
