import streamlit as st
import sqlite3
import subprocess
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analyzer import get_audit_summary, calculate_convergence, run_political_symmetry

# PAGE CONFIG

st.set_page_config(
    page_title="Media Bias AI Auditor",
    layout="wide",
    initial_sidebar_state="collapsed"
)

import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from styles import inject_styles, render_sidebar, PLOTLY_LAYOUT

inject_styles()

DB_PATH = "data/news_vault.db"

# HELPERS

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_article_count():
    try:
        conn  = get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def get_processed_count():
    try:
        conn  = get_db_connection()
        count = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE label_8b IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

# SIDEBAR

render_sidebar()
# HEADER

st.title("Media Bias AI Auditor")
st.markdown("#### Auditing the Auditors — Do LLMs Show Political Bias?")
st.markdown(
    "This project investigates whether Large Language Models (LLMs) themselves exhibit "
    "political bias when tasked with detecting bias in news articles. We run **four controlled experiments** "
    "across articles from politically diverse news outlets scraped in real time."
)
st.markdown("---")

# DATA PIPELINE

st.subheader("Data Pipeline")
st.caption("Run these two steps to collect fresh news and analyze them with AI")

total     = get_article_count()
processed = get_processed_count()

pipe_col1, pipe_col2, pipe_col3 = st.columns([2, 2, 3])

with pipe_col1:
    if st.button("Step 1 — Scrape Latest News", use_container_width=True, type="primary"):
        with st.spinner("Scraping news articles from RSS feeds... (2–3 min)"):
            result = subprocess.run(
                ["python", "scraper.py"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                st.success("Articles scraped successfully.")
            else:
                st.error(f"Error: {result.stderr[:200]}")
        st.rerun()

with pipe_col2:
    if st.button("Step 2 — Run AI Experiments", use_container_width=True, type="primary"):
        with st.spinner("Running AI experiments... (5–15 min depending on article count)"):
            result = subprocess.run(
                ["python", "analyzer.py"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                st.success("Experiments complete.")
            else:
                st.error(f"Error: {result.stderr[:200]}")
        st.rerun()

with pipe_col3:
    pct = int(processed / total * 100) if total > 0 else 0
    st.markdown(
        f"<div style='padding: 0.6rem 1rem; border-radius: 8px; background:#0f172a; "
        f"border: 1px solid #1e293b; font-size: 0.875rem; color: #cbd5e1;'>"
        f"<b>{total}</b> total articles &nbsp;·&nbsp; "
        f"<b>{processed}</b> AI audited &nbsp;·&nbsp; "
        f"<b>{pct}%</b> complete</div>",
        unsafe_allow_html=True
    )
    if total > 0:
        st.progress(processed / total)

st.markdown("---")

# KEY METRICS

summary = get_audit_summary()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Articles Audited", summary["total_audited"],
              help="Total articles analyzed by AI models")
with col2:
    st.metric("Model Agreement", f"{summary['agreement_rate']}%",
              help="How often Llama3 8B and Llama3.2 3B agree on bias verdict")
with col3:
    st.metric("Prompt Stability", f"{summary['stability_rate']}%",
              help="How often the same model gives same verdict with different prompts")
with col4:
    outlets_avail = [o[0] for o in summary["outlet_stats"]] if summary["outlet_stats"] else []
    default_a = "CNN"     if "CNN"     in outlets_avail else (outlets_avail[0] if outlets_avail else "CNN")
    default_b = "Fox News" if "Fox News" in outlets_avail else (outlets_avail[1] if len(outlets_avail) > 1 else "Fox")
    conv = calculate_convergence(default_a, default_b)
    conv_display = f"{conv:.2f}" if conv else "N/A"
    st.metric(f"{default_a} vs {default_b}", conv_display,
              help="Semantic similarity (1.0 = identical narratives, 0.0 = completely different)")

st.markdown("---")


# SECTION 5 — RESEARCH METHODOLOGY

st.subheader("Research Methodology")
st.markdown(
    "This project employs a multi-tiered approach to audit LLMs for systemic political bias. "
    "By running controlled experiments on live news data, we evaluate the models' objectivity, "
    "consistency, and resilience to prompt framing."
)

col_meth1, col_meth2 = st.columns(2)

with col_meth1:
    with st.container(border=True):
        st.markdown("##### Experiments 1 & 2 — Model Audit")
        st.caption("Do different AI models agree on bias?")
        st.write("We send the same article to Llama3 8B and Llama3.2 3B. Disagreements show that bias detection is model-dependent and subjective.")
        st.page_link("pages/1_ai_audit.py", label="View Full AI Audit Results")

    with st.container(border=True):
        st.markdown("##### Experiment 3 — Prompt Sensitivity")
        st.caption("Does rephrasing change the answer?")
        st.write("We test each article with three differently worded prompts. If verdicts change, the AI is responding to framing rather than content.")
        st.page_link("pages/2_prompt_sensitivity.py", label="View Prompt Sensitivity Results")

with col_meth2:
    with st.container(border=True):
        st.markdown("##### Experiment 4 — Political Symmetry")
        st.caption("Are Left and Right treated equally?")
        st.write("We compare AI bias detection rates across left and right leaning outlets. Asymmetry reveals political bias embedded in the model's training data.")
        st.page_link("pages/3_political_sensitivity.py", label="View Political Symmetry Results")

    with st.container(border=True):
        st.markdown("##### Live Article Analyzer")
        st.caption("Test any article in real time")
        st.write("Paste any news article or URL and get instant bias analysis from both AI models, with reasoning, trigger words, and database comparison.")
        st.page_link("pages/4_live_analyser.py", label="Open Live Analyzer")

st.markdown("---")

# SECTION 4 — CONVERGENCE

st.subheader("Media Convergence Analysis")
st.caption("Semantic similarity between outlets — how similar are their narratives?")

try:
    conn = get_db_connection()
    outlets_df = pd.read_sql_query("SELECT DISTINCT outlet FROM articles ORDER BY outlet", conn)
    conn.close()
    available_outlets = outlets_df['outlet'].tolist()
except Exception:
    available_outlets = []

if len(available_outlets) >= 2:
    col_a, col_b = st.columns(2)
    with col_a:
        outlet_1 = st.selectbox("First Outlet", available_outlets, index=0)
    with col_b:
        outlet_2 = st.selectbox("Second Outlet", available_outlets,
                                index=1 if len(available_outlets) > 1 else 0)

    if outlet_1 != outlet_2:
        with st.spinner("Calculating semantic similarity..."):
            score = calculate_convergence(outlet_1, outlet_2)

        if score is not None:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score * 100,
                title={"text": f"Narrative Convergence — {outlet_1} vs {outlet_2}",
                       "font": {"size": 13, "family": "Inter"}},
                number={"suffix": "%"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#4f46e5"},
                    "steps": [
                        {"range": [0,  33], "color": "#fee2e2"},
                        {"range": [33, 66], "color": "#fef9c3"},
                        {"range": [66,100], "color": "#dcfce7"}
                    ],
                }
            ))
            fig_gauge.update_layout(
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter")
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

            if score > 0.75:
                st.success(f"**High Convergence** — {outlet_1} and {outlet_2} show highly similar narratives.")
            elif score > 0.45:
                st.warning(f"**Moderate Convergence** — {outlet_1} and {outlet_2} share some overlap but differ significantly.")
            else:
                st.error(f"**Low Convergence** — {outlet_1} and {outlet_2} present noticeably distinct narratives.")
    else:
        st.warning("Please select two different outlets.")
else:
    st.info("Run the scraper first to populate outlets.")

st.markdown("---")



st.caption("Ayushi Patel · MS Computer Science · Montclair State University · Spring 2026")