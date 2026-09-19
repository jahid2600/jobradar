import { Filter, Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import OpportunityCard from "../components/OpportunityCard";

function OpportunitiesPage({ opportunities, loading, error, onRetry }) {
  const [query, setQuery] = useState("");
  const [qualifiedOnly, setQualifiedOnly] = useState(false);
  const [sort, setSort] = useState("relevance");

  const filteredOpportunities = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return [...opportunities]
      .filter(({ job = {}, qualification = {} }) => {
        const searchable = [job.title, job.company, job.location, job.description, job.source]
          .filter(Boolean).join(" ").toLowerCase();
        return (!normalizedQuery || searchable.includes(normalizedQuery))
          && (!qualifiedOnly || qualification.qualified);
      })
      .sort((left, right) => {
        if (sort === "company") return (left.job?.company || "").localeCompare(right.job?.company || "");
        return Number(right.qualification?.relevance_score || 0) - Number(left.qualification?.relevance_score || 0);
      });
  }, [opportunities, query, qualifiedOnly, sort]);

  return (
    <div className="page-content opportunities-page">
      <div className="page-heading-row">
        <div>
          <p className="eyebrow">DISCOVERY FEED</p>
          <h2>Opportunities worth your attention.</h2>
          <p className="page-lede">Every listing is normalized, deduplicated and evaluated against your target profile.</p>
        </div>
        <div className="result-count"><strong>{filteredOpportunities.length}</strong><span>visible matches</span></div>
      </div>

      <section className="filter-bar panel-surface">
        <label className="search-field">
          <Search size={17} />
          <span className="sr-only">Search opportunities</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title, company or skill" />
        </label>
        <label className="select-field">
          <SlidersHorizontal size={16} />
          <span className="sr-only">Sort opportunities</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="relevance">Sort: Relevance</option>
            <option value="company">Sort: Company</option>
          </select>
        </label>
        <label className={`filter-toggle ${qualifiedOnly ? "selected" : ""}`}>
          <input type="checkbox" checked={qualifiedOnly} onChange={(event) => setQualifiedOnly(event.target.checked)} />
          <Filter size={15} /> Qualified only
        </label>
      </section>

      {loading && <div className="state-panel panel-surface"><div className="loading-orb" /><h3>Loading opportunities</h3><p>Reading the latest qualified listings.</p></div>}
      {!loading && error && <div className="state-panel panel-surface"><div className="state-icon error"><Filter size={20} /></div><h3>Could not load opportunities</h3><p>{error}</p><button className="secondary-button" onClick={onRetry}>Try again</button></div>}
      {!loading && !error && !filteredOpportunities.length && <div className="state-panel panel-surface"><div className="state-icon"><Search size={20} /></div><h3>No matching opportunities</h3><p>Try clearing your search or run Radar to discover fresh listings.</p></div>}
      {!loading && !error && filteredOpportunities.length > 0 && (
        <div className="opportunity-grid">
          {filteredOpportunities.map((opportunity) => <OpportunityCard key={opportunity.job?.url || opportunity.job?.title} opportunity={opportunity} />)}
        </div>
      )}
    </div>
  );
}

export default OpportunitiesPage;
