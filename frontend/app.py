import streamlit as st

from backend.aws_client import dynamodb
from backend.config import (
    TARGET_LOCATION,
    TARGET_EXPERIENCE,
    TARGET_ROLES,
    TARGET_SKILLS,
    PREFERRED_COMPANY_TYPES,
)

TABLE_NAME = "jobradar-jobs"


# ---------------------------------------------------------
# Page
# ---------------------------------------------------------

st.set_page_config(
    page_title="JobRadar",
    page_icon="🎯",
    layout="wide",
)


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1400px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .hero-title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .hero-subtitle {
            font-size: 1.15rem;
            opacity: 0.7;
            margin-bottom: 1rem;
        }

        .status {
            display: inline-block;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            background: rgba(46, 204, 113, 0.15);
            color: #2ecc71;
        }

        .job-card {
            padding: 1.4rem;
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 16px;
            margin-bottom: 1rem;
        }

        .job-title {
            font-size: 1.35rem;
            font-weight: 750;
        }

        .company {
            opacity: 0.7;
            margin-top: 0.25rem;
        }

        .score {
            font-size: 2rem;
            font-weight: 800;
        }

        .section-title {
            font-size: 1.45rem;
            font-weight: 750;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------

def load_jobs():
    response = dynamodb.scan(TableName=TABLE_NAME)

    jobs = []

    for item in response.get("Items", []):
        jobs.append(
            {
                "title": item.get("title", {}).get("S", ""),
                "company": item.get("company", {}).get("S", ""),
                "location": item.get("location", {}).get("S", ""),
                "url": item.get("url", {}).get("S", ""),
                "source": item.get("source", {}).get("S", ""),
                "experience": item.get("experience", {}).get("S", ""),
                "qualified": item.get("qualified", {}).get("BOOL", False),
                "score": int(item.get("relevance_score", {}).get("N", "0")),
                "reason": item.get("reason", {}).get("S", ""),
                "description": item.get("description", {}).get("S", ""),
            }
        )

    return sorted(
        jobs,
        key=lambda job: job["score"],
        reverse=True,
    )


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    """
    <div class="hero-title">🎯 JobRadar</div>

    <div class="hero-subtitle">
        Autonomous job discovery and opportunity intelligence
    </div>

    <span class="status">● RADAR ACTIVE</span>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Never search for the same job twice. "
    "JobRadar discovers, evaluates, deduplicates and explains opportunities."
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    st.header("🎯 Target Profile")

    st.write(f"**Location:** {TARGET_LOCATION}")
    st.write(f"**Experience:** {TARGET_EXPERIENCE}")

    st.write("**Target roles**")

    for role in TARGET_ROLES:
        st.caption(f"• {role}")

    st.write("**Skills**")
    st.caption(", ".join(TARGET_SKILLS))

    st.write("**Preferences**")

    for preference in PREFERRED_COMPANY_TYPES:
        st.caption(f"• {preference}")

    st.divider()

    if st.button(
        "🔄 Run JobRadar",
        use_container_width=True,
    ):
        with st.spinner("JobRadar is scanning the web and evaluating opportunities..."):
            from backend.pipeline import run_pipeline

        run_pipeline("AWS Cloud Engineer Bengaluru fresher")

    st.success("Radar scan completed. Refreshing opportunities...")
    st.rerun()


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

st.write("DEBUG: before DynamoDB")
jobs = load_jobs()
st.write(f"DEBUG: after DynamoDB - {len(jobs)} jobs")

total_jobs = len(jobs)
qualified_jobs = sum(
    1 for job in jobs if job["qualified"]
)

average_score = (
    round(
        sum(job["score"] for job in jobs) / total_jobs
    )
    if total_jobs
    else 0
)


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">Radar Overview</div>',
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Opportunities found",
        total_jobs,
    )

with col2:
    st.metric(
        "Qualified",
        qualified_jobs,
    )

with col3:
    st.metric(
        "Duplicates removed",
        "—",
    )

with col4:
    st.metric(
        "Average match",
        f"{average_score}%",
    )


# ---------------------------------------------------------
# Intelligence
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">🧠 JobRadar Intelligence</div>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        "**Discovery**\n\n"
        "Bedrock expands your target into related roles, "
        "keywords and search strategies."
    )

with col2:
    st.success(
        "**Qualification**\n\n"
        "Bedrock evaluates how closely each opportunity "
        "matches your profile."
    )

with col3:
    st.warning(
        "**Deduplication**\n\n"
        "Repeated listings are normalized so the same "
        "opportunity is not shown multiple times."
    )


# ---------------------------------------------------------
# Opportunities
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">🔥 Qualified Opportunities</div>',
    unsafe_allow_html=True,
)

if not jobs:

    st.warning(
        "No opportunities have been discovered yet."
    )

else:

    for job in jobs:

        st.markdown(
            f"""
            <div class="job-card">

                <div class="job-title">
                    {job["title"]}
                </div>

                <div class="company">
                    {job["company"] or "Company not identified"}
                    ·
                    {job["location"] or "Location not identified"}
                    ·
                    {job["experience"] or "Experience not identified"}
                </div>

                <br>

                <div class="score">
                    {job["score"]}% Match
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Why JobRadar found this**")

        st.write(job["reason"])

        with st.expander("🔍 View opportunity details"):

            st.write(
                f"**Source:** {job['source']}"
            )

            st.write(
                f"**Experience:** {job['experience'] or 'Not identified'}"
            )

            if job["description"]:
                st.write("**Job intelligence input**")
                st.write(
                    job["description"][:1200]
                )

        if job["url"]:
            st.link_button(
                "View original opportunity ↗",
                job["url"],
            )

        st.divider()


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.caption(
    "JobRadar · AWS + Amazon Bedrock powered "
    "job intelligence · Applications remain user-controlled."
)