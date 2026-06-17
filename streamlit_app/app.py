"""
app.py — SiteSignal: Job Site Performance Dashboard (local / Streamlit Cloud version)
---------------------------------------------------------------------------------------
Connects to Snowflake using credentials from st.secrets (works locally via
.streamlit/secrets.toml, and on Streamlit Community Cloud via the app's
Secrets settings).

Cortex Analyst chat uses the external REST API with a Programmatic Access
Token (PAT) for authentication.

Run locally:
    streamlit run app.py

Deploy:
    Push this folder to a GitHub repo, then deploy on share.streamlit.io.
    Add the contents of .streamlit/secrets.toml to the app's Secrets settings
    (do NOT commit secrets.toml to the repo).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import snowflake.connector

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="SiteSignal · Job Site Performance", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
  [data-testid="stMetricValue"] { font-size: 1.9rem; }
  .section-header {
    font-size: 1.05rem; font-weight: 600; color: #6366f1;
    border-bottom: 2px solid #6366f1; padding-bottom: 4px; margin-bottom: 14px;
  }
</style>
""", unsafe_allow_html=True)

COLORS = {
    "PRE_FILING": "#94a3b8", "IN_REVIEW": "#f59e0b", "APPROVED": "#3b82f6",
    "PERMIT_ISSUED": "#8b5cf6", "COMPLETED": "#10b981",
    "DISAPPROVED": "#ef4444", "SUSPENDED": "#64748b",
}

VIEW_NAME = "JOB_SITE_PERFORMANCE"   # database.schema.view set via secrets below
SEMANTIC_MODEL_FILE = st.secrets["cortex"]["semantic_model_file"]  # e.g. "@DB.SCHEMA.STAGE/job_site_performance.yaml"

# ── Snowflake connection ──────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"].get("role"),
    )

def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        return cur.fetch_pandas_all()
    finally:
        cur.close()

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_summary():
    return run_query(f"""
        select
            count(*)                                              as total_jobs,
            sum(case when is_at_risk then 1 else 0 end)           as at_risk_jobs,
            avg(case when is_at_risk then 1.0 else 0.0 end) * 100  as at_risk_rate,
            avg(case when is_approved then 1.0 else 0.0 end) * 100 as approval_rate,
            avg(days_in_review)                                   as avg_days_in_review,
            avg(case when is_approved then days_to_approval end)  as avg_days_to_approval,
            sum(initial_cost)                                     as total_value,
            avg(initial_cost)                                     as avg_value
        from {VIEW_NAME}
    """)

@st.cache_data
def load_stage_counts():
    return run_query(f"""
        select stage_group, count(*) as job_count
        from {VIEW_NAME}
        group by stage_group
        order by job_count desc
    """)

@st.cache_data
def load_borough_summary():
    return run_query(f"""
        select
            borough,
            count(*)                                       as total_jobs,
            sum(case when is_at_risk then 1 else 0 end)    as at_risk_jobs,
            avg(days_in_review)                            as avg_days_in_review,
            sum(initial_cost)                              as total_value
        from {VIEW_NAME}
        where borough is not null
        group by borough
        order by total_jobs desc
    """)

@st.cache_data
def load_job_type_summary():
    return run_query(f"""
        select
            job_type_description,
            count(*)                                       as total_jobs,
            avg(days_in_review)                            as avg_days_in_review,
            avg(case when is_at_risk then 1.0 else 0.0 end) * 100 as at_risk_rate
        from {VIEW_NAME}
        where job_type_description is not null
        group by job_type_description
        order by total_jobs desc
    """)

@st.cache_data
def load_monthly_trend():
    return run_query(f"""
        select
            filing_month,
            count(*)                              as jobs_filed,
            avg(days_in_review)                   as avg_days_in_review
        from {VIEW_NAME}
        where filing_month >= dateadd(year, -2, current_date())
        group by filing_month
        order by filing_month
    """)

@st.cache_data
def load_map_data():
    return run_query(f"""
        select
            job_id, borough, stage_group, is_at_risk,
            initial_cost, latitude, longitude
        from {VIEW_NAME}
        where latitude is not null and longitude is not null
        limit 5000
    """)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏗️ SiteSignal — Job Site Performance Dashboard")
st.caption("NYC DOB job application filings · Semantic layer powered by Snowflake Cortex Analyst")
st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────
summary = load_summary().iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total jobs", f"{int(summary['TOTAL_JOBS']):,}")
c2.metric("At-risk jobs", f"{int(summary['AT_RISK_JOBS']):,}",
          delta=f"{summary['AT_RISK_RATE']:.1f}% of total", delta_color="inverse")
c3.metric("Approval rate", f"{summary['APPROVAL_RATE']:.1f}%")
c4.metric("Avg days in review", f"{summary['AVG_DAYS_IN_REVIEW']:.0f}")
c5.metric("Total pipeline value", f"${float(summary['TOTAL_VALUE'])/1e9:.2f}B")

st.divider()

# ── Stage funnel + Borough breakdown ────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-header">Pipeline by stage</div>', unsafe_allow_html=True)
    stages = load_stage_counts()
    fig_stage = px.bar(
        stages, x="JOB_COUNT", y="STAGE_GROUP", orientation="h",
        color="STAGE_GROUP", color_discrete_map=COLORS,
        labels={"JOB_COUNT": "Number of jobs", "STAGE_GROUP": ""},
    )
    fig_stage.update_layout(showlegend=False, height=340, margin=dict(l=0, r=10, t=10, b=30))
    st.plotly_chart(fig_stage, use_container_width=True)

with col2:
    st.markdown('<div class="section-header">Jobs &amp; risk by borough</div>', unsafe_allow_html=True)
    boroughs = load_borough_summary()
    fig_boro = px.bar(
        boroughs, x="BOROUGH", y="TOTAL_JOBS",
        color="AT_RISK_JOBS", color_continuous_scale="Oranges",
        labels={"TOTAL_JOBS": "Total jobs", "BOROUGH": "", "AT_RISK_JOBS": "At-risk jobs"},
    )
    fig_boro.update_layout(height=340, margin=dict(l=0, r=10, t=10, b=30))
    st.plotly_chart(fig_boro, use_container_width=True)

st.divider()

# ── Job type performance + Monthly trend ────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="section-header">Performance by job type</div>', unsafe_allow_html=True)
    jt = load_job_type_summary()
    fig_jt = px.scatter(
        jt, x="AVG_DAYS_IN_REVIEW", y="AT_RISK_RATE",
        size="TOTAL_JOBS", color="JOB_TYPE_DESCRIPTION",
        hover_name="JOB_TYPE_DESCRIPTION", size_max=40,
        labels={"AVG_DAYS_IN_REVIEW": "Avg days in review", "AT_RISK_RATE": "At-risk rate (%)"},
    )
    fig_jt.update_layout(height=340, margin=dict(l=0, r=10, t=10, b=30))
    st.plotly_chart(fig_jt, use_container_width=True)

with col4:
    st.markdown('<div class="section-header">Filing volume &amp; review time trend</div>', unsafe_allow_html=True)
    trend = load_monthly_trend()
    fig_trend = px.line(
        trend, x="FILING_MONTH", y="AVG_DAYS_IN_REVIEW",
        labels={"FILING_MONTH": "", "AVG_DAYS_IN_REVIEW": "Avg days in review"},
        markers=True,
    )
    fig_trend.update_layout(height=340, margin=dict(l=0, r=10, t=10, b=30))
    st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# ── Map ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Job site map</div>', unsafe_allow_html=True)
map_df = load_map_data()
fig_map = px.scatter_mapbox(
    map_df, lat="LATITUDE", lon="LONGITUDE",
    color="STAGE_GROUP", color_discrete_map=COLORS,
    size="INITIAL_COST", size_max=18,
    hover_data=["JOB_ID", "BOROUGH", "IS_AT_RISK"],
    zoom=9.5, height=460,
    mapbox_style="carto-positron",
)
fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# ── Ask SiteSignal — Cortex Analyst chat (external REST API) ────────────────
st.markdown('<div class="section-header">💬 Ask SiteSignal</div>', unsafe_allow_html=True)
st.caption("Ask a question in plain English. Powered by Cortex Analyst + the semantic model.")

if "messages" not in st.session_state:
    st.session_state.messages = []

def call_cortex_analyst(prompt: str) -> dict:
    """Send a question to Cortex Analyst's REST API and return the parsed response."""
    account = st.secrets["snowflake"]["account"]
    # account identifier like "abc12345.us-east-1" -> hostname form
    host = account.replace("_", "-").lower()
    url = f"https://{host}.snowflakecomputing.com/api/v2/cortex/analyst/message"

    headers = {
        "Authorization": f"Bearer {st.secrets['cortex']['pat_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
        "semantic_model_file": SEMANTIC_MODEL_FILE,
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Cortex Analyst request failed ({resp.status_code}): {resp.text}")
    return resp.json()

def render_cortex_response(content_items):
    """Render the content blocks returned by Cortex Analyst (text, sql, suggestions)."""
    sql_to_run = None
    for item in content_items:
        if item["type"] == "text":
            st.markdown(item["text"])
        elif item["type"] == "sql":
            sql_to_run = item["statement"]
            with st.expander("View generated SQL"):
                st.code(sql_to_run, language="sql")
        elif item["type"] == "suggestions":
            st.write("You could also ask:")
            for s in item.get("suggestions", []):
                st.write(f"- {s}")

    if sql_to_run:
        try:
            result_df = run_query(sql_to_run)
            st.dataframe(result_df, use_container_width=True)

            if result_df.shape[1] == 2 and result_df.shape[0] > 1:
                col_a, col_b = result_df.columns[0], result_df.columns[1]
                if pd.api.types.is_numeric_dtype(result_df[col_b]):
                    fig = px.bar(result_df, x=col_a, y=col_b)
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Couldn't run the generated SQL: {e}")

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_cortex_response(msg["content"])

# Suggested starter questions
st.write("Try asking:")
example_cols = st.columns(4)
examples = [
    "Which borough has the most at-risk jobs?",
    "Avg review time for new buildings, Brooklyn vs Manhattan?",
    "Show large projects pending over 6 months",
    "What % of large jobs get approved within 90 days?",
]
for col, ex in zip(example_cols, examples):
    if col.button(ex, use_container_width=True):
        st.session_state.pending_prompt = ex

# Chat input
prompt = st.chat_input("Ask a question about job site performance...")
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = call_cortex_analyst(prompt)
                content_items = response["message"]["content"]
                render_cortex_response(content_items)
                st.session_state.messages.append({"role": "assistant", "content": content_items})
            except Exception as e:
                error_text = f"Sorry, I couldn't process that: {e}"
                st.error(error_text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": error_text}]
                })

st.divider()
st.caption("Data: NYC DOB Job Application Filings · Semantic model: job_site_performance.yaml · Built with Streamlit + Snowflake Cortex Analyst")