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

# SECTION 1 — BIAS RATE BY OUTLET

sec1_col, btn1_col = st.columns([6, 1])
with sec1_col:
    st.subheader("Bias Detection Rate by News Outlet")
    st.caption("How often does the AI label each outlet's articles as BIASED?")
with btn1_col:
    st.markdown("<br>", unsafe_allow_html=True)
    st.page_link("pages/1_ai_audit.py", label="Full AI Audit")

if summary["outlet_stats"]:
    outlet_data = []
    for outlet, lean, total_art, biased_art in summary["outlet_stats"]:
        if total_art > 0:
            bias_rate = round(biased_art / total_art * 100, 1)
            outlet_data.append({
                "Outlet": outlet, "Lean": lean,
                "Total Articles": total_art,
                "Biased": biased_art,
                "Bias Rate (%)": bias_rate
            })

    if outlet_data:
        df_outlets = pd.DataFrame(outlet_data)
        color_map  = {"Left": "#3b82f6", "Right": "#ef4444", "Center": "#22c55e"}

        fig = px.bar(
            df_outlets, x="Outlet", y="Bias Rate (%)",
            color="Lean", color_discrete_map=color_map,
            title="AI-Detected Bias Rate by News Outlet",
            text="Bias Rate (%)", height=380
        )
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter"),
            showlegend=True,
            xaxis_title="News Outlet", yaxis_title="Bias Rate (%)",
            yaxis_range=[0, 115]
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df_outlets[["Outlet", "Lean", "Total Articles", "Biased", "Bias Rate (%)"]],
            use_container_width=True, hide_index=True
        )
else:
    st.info("Run Step 1 and Step 2 above to generate results.")

st.markdown("---")

# SECTION 2 — POLITICAL SYMMETRY

sec2_col, btn2_col = st.columns([6, 1])
with sec2_col:
    st.subheader("Political Symmetry — Does AI Treat Left and Right Equally?")
    st.caption("If the AI labels one side as BIASED more often, the AI itself has a political lean.")
with btn2_col:
    st.markdown("<br>", unsafe_allow_html=True)
    st.page_link("pages/3_political_sensitivity.py", label="Full Analysis")

sym           = run_political_symmetry()
left_biased   = sym["Left"]["BIASED"]
left_neutral  = sym["Left"]["NEUTRAL"]
right_biased  = sym["Right"]["BIASED"]
right_neutral = sym["Right"]["NEUTRAL"]
left_total    = left_biased  + left_neutral
right_total   = right_biased + right_neutral

if left_total > 0 and right_total > 0:
    left_rate  = round(left_biased  / left_total  * 100, 1)
    right_rate = round(right_biased / right_total * 100, 1)

    sym_col1, sym_col2 = st.columns(2)

    def make_gauge(value, title, color):
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=value,
            title={"text": title, "font": {"size": 13, "family": "Inter", "color": "#f8fafc"}},
            number={"suffix": "%", "font": {"color": "#f8fafc"}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0,  33], "color": "#064e3b"},
                    {"range": [33, 66], "color": "#78350f"},
                    {"range": [66,100], "color": "#7f1d1d"}
                ],
                "threshold": {
                    "line": {"color": "#94a3b8", "width": 2},
                    "thickness": 0.75, "value": 50
                }
            }
        ))
        fig.update_layout(
            height=260,
            margin=dict(t=50, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#f8fafc")
        )
        return fig

    with sym_col1:
        st.plotly_chart(
            make_gauge(left_rate, "Left-Leaning Outlets — % Labeled BIASED", "#3b82f6"),
            use_container_width=True
        )
    with sym_col2:
        st.plotly_chart(
            make_gauge(right_rate, "Right-Leaning Outlets — % Labeled BIASED", "#ef4444"),
            use_container_width=True
        )

    diff = abs(left_rate - right_rate)
    if diff < 10:
        st.success(f"**AI appears POLITICALLY SYMMETRIC** — Difference: {diff:.1f}% (within 10% threshold)")
    elif left_rate > right_rate:
        st.error(f"**AI shows RIGHT-LEANING BIAS** — Labels Left outlets as biased {diff:.1f}% more often")
    else:
        st.error(f"**AI shows LEFT-LEANING BIAS** — Labels Right outlets as biased {diff:.1f}% more often")
else:
    st.info("Run the AI experiments first to see political symmetry results.")

st.markdown("---")

# SECTION 3 — PROMPT SENSITIVITY SUMMARY

sec3_col, btn3_col = st.columns([6, 1])
with sec3_col:
    st.subheader("Prompt Sensitivity Summary")
    st.caption("Does rephrasing the question change the AI's verdict on the same article?")
with btn3_col:
    st.markdown("<br>", unsafe_allow_html=True)
    st.page_link("pages/2_prompt_sensitivity.py", label="Full Analysis")

try:
    conn = get_db_connection()
    prompt_df = pd.read_sql_query("""
        SELECT prompt_a_label, prompt_b_label, prompt_c_label
        FROM articles WHERE prompt_a_label IS NOT NULL
    """, conn)
    conn.close()

    if not prompt_df.empty:
        prompt_rates = pd.DataFrame({
            "Prompt": ["Prompt A (Direct)", "Prompt B (Framing)", "Prompt C (Fact-Checker)"],
            "Bias Rate (%)": [
                round((prompt_df["prompt_a_label"] == "BIASED").mean() * 100, 1),
                round((prompt_df["prompt_b_label"] == "BIASED").mean() * 100, 1),
                round((prompt_df["prompt_c_label"] == "BIASED").mean() * 100, 1),
            ]
        })

        fig_prompt = px.bar(
            prompt_rates, x="Prompt", y="Bias Rate (%)",
            title="Bias Detection Rate Changes With Prompt Wording — Same Article, Different Question",
            text="Bias Rate (%)",
            color="Bias Rate (%)",
            color_continuous_scale="RdYlGn_r",
            height=320
        )
        fig_prompt.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_prompt.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter"),
            yaxis_range=[0, 115], coloraxis_showscale=False
        )
        st.plotly_chart(fig_prompt, use_container_width=True)

        variance = abs(prompt_rates["Bias Rate (%)"].max() - prompt_rates["Bias Rate (%)"].min())
        if variance >= 20:
            st.error(f"**Large variation ({variance:.1f}%)** — Verdict changes significantly with prompt wording.")
        elif variance >= 5:
            st.warning(f"**Moderate variation ({variance:.1f}%)** — Some prompt sensitivity detected.")
        else:
            st.success(f"**Low variation ({variance:.1f}%)** — AI is relatively prompt-stable.")
    else:
        st.info("Run AI experiments to see prompt sensitivity data.")
except Exception:
    st.info("Run AI experiments to see prompt sensitivity data.")

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
st.caption("Ayushi Patel · MS Computer Science · Montclair State University · Spring 2026")