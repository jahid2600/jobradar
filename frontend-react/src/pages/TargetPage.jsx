import { Check, RotateCcw, Save, Target } from "lucide-react";
import { useState } from "react";

const initialProfile = {
  location: "Bengaluru",
  experience: "0-1 years",
  roles: ["AWS Cloud Engineer", "AWS Cloud Support Engineer", "Cloud Support Associate", "Cloud Operations Engineer", "Cloud Infrastructure Engineer", "Junior DevOps Engineer", "Cloud Administrator", "Entry-level SRE", "DevOps Intern", "Cloud Intern"],
  skills: ["AWS", "Linux", "Docker", "Git", "Python", "Terraform", "CI/CD"],
  companyTypes: ["MNC", "Startup", "Internship", "Entry-level"],
};

function TagEditor({ label, values, onChange }) {
  const [draft, setDraft] = useState("");
  const addValue = (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const value = draft.trim();
    if (value && !values.includes(value)) onChange([...values, value]);
    setDraft("");
  };

  return (
    <div className="field-group">
      <label>{label}</label>
      <div className="editable-tags">
        {values.map((value) => <button type="button" className="editable-tag" key={value} onClick={() => onChange(values.filter((item) => item !== value))}>{value}<span>×</span></button>)}
        <input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={addValue} placeholder="Add and press Enter" aria-label={`Add ${label}`} />
      </div>
    </div>
  );
}

function TargetPage() {
  const [profile, setProfile] = useState(initialProfile);
  const [saved, setSaved] = useState(false);
  const update = (key, value) => { setProfile((current) => ({ ...current, [key]: value })); setSaved(false); };

  const saveProfile = () => setSaved(true);
  const resetProfile = () => { setProfile(initialProfile); setSaved(false); };

  return (
    <div className="page-content target-page">
      <div className="page-heading-row">
        <div><p className="eyebrow">TARGET PROFILE</p><h2>Give the radar a sharper signal.</h2><p className="page-lede">This local profile is initialized from the current backend configuration. Editing is session-only until a profile API exists.</p></div>
        <div className="profile-status"><span className="status-dot" /> Active profile</div>
      </div>

      <section className="target-layout">
        <div className="panel-surface profile-form">
          <div className="form-header"><div className="panel-icon"><Target size={18} /></div><div><h3>Candidate profile</h3><p>Used as the qualification target for Radar runs.</p></div></div>
          <div className="form-grid">
            <div className="field-group"><label htmlFor="location">Location</label><input id="location" value={profile.location} onChange={(event) => update("location", event.target.value)} /></div>
            <div className="field-group"><label htmlFor="experience">Experience range</label><select id="experience" value={profile.experience} onChange={(event) => update("experience", event.target.value)}><option>0-1 years</option><option>1-2 years</option><option>Internship</option><option>Graduate</option></select></div>
          </div>
          <TagEditor label="Target roles" values={profile.roles} onChange={(value) => update("roles", value)} />
          <TagEditor label="Skills" values={profile.skills} onChange={(value) => update("skills", value)} />
          <TagEditor label="Preferred company types" values={profile.companyTypes} onChange={(value) => update("companyTypes", value)} />
          <div className="form-actions"><button className="secondary-button" onClick={resetProfile}><RotateCcw size={15} /> Reset</button><button className="run-button" onClick={saveProfile}><Save size={15} /> Save profile</button></div>
          {saved && <div className="saved-note"><Check size={15} /> Profile saved for this session. Backend configuration remains unchanged.</div>}
        </div>
        <aside className="profile-summary panel-surface"><p className="eyebrow">ACTIVE SIGNAL</p><h3>{profile.location}</h3><p>{profile.experience} · {profile.roles.length} roles · {profile.skills.length} skills</p><div className="summary-line" /><span>Radar qualification uses the backend profile until profile persistence is implemented.</span></aside>
      </section>
    </div>
  );
}

export default TargetPage;
