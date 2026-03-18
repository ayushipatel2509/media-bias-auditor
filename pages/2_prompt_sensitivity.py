import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from styles import inject_styles, render_sidebar, PLOTLY_LAYOUT

st.set_page_config(page_title="Prompt Sensitivity", layout="wide")
inject_styles()
render_sidebar()

DB_PATH = "data/news_vault.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# PAGE CONTENT

st.title("Experiment 3 — Prompt Sensitivity Analysis")
st.markdown("""
*Does rephrasing the same question change the AI's bias verdict on the same article?*
""")
st.markdown("---")

# SHOW THE THREE PROMPTS
st.subheader("The Three Prompts Used")

p1, p2, p3 = st.columns(3)

with p1:
    st.markdown("**Prompt A — Direct**")
    st.info('"Is this article biased? Answer BIASED or NEUTRAL only."')

with p2:
    st.markdown("**Prompt B — Framing Focus**")
    st.info('"Does this article show political bias in its language or framing? Answer BIASED or NEUTRAL only."')

with p3:
    st.markdown("**Prompt C — Fact-Checker Role**")
    st.info('"As a neutral fact-checker, evaluate if this text presents information fairly. Answer BIASED or NEUTRAL only."')

st.markdown("---")

# LOAD DATA
try:
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT outlet, lean, title,
               label_8b as baseline,
               prompt_a_label, prompt_b_label, prompt_c_label
        FROM articles
        WHERE prompt_a_label IS NOT NULL
        ORDER BY outlet
    """, conn)
    conn.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if df.empty:
    st.info("No prompt sensitivity data yet. Run the AI experiments from the Home page.")
    st.stop()

# STABILITY CALCULATION
df["All_Same"] = (
    (df["prompt_a_label"] == df["prompt_b_label"]) &
    (df["prompt_b_label"] == df["prompt_c_label"])
)
df["Stable"] = df["All_Same"].map({True: "Stable", False: "Unstable"})

total    = len(df)
stable   = df["All_Same"].sum()
unstable = total - stable
rate     = round(stable / total * 100, 1)

# METRICS
m1, m2, m3, m4 = st.columns(4)
m1.metric("Articles Tested",   total)
m2.metric("Stable Verdicts",   int(stable))
m3.metric("Unstable Verdicts", int(unstable))
m4.metric("Stability Rate",    f"{rate}%")

st.markdown("---")

# STABILITY BY OUTLET
st.subheader("Prompt Stability by Outlet")
st.caption("Does rephrasing affect some outlets more than others?")

outlet_stable = df.groupby(["outlet", "lean"]).agg(
    Total=("All_Same", "count"),
    Stable=("All_Same", "sum")
).reset_index()
outlet_stable["Stability Rate (%)"] = round(outlet_stable["Stable"] / outlet_stable["Total"] * 100, 1)

color_map = {"Left": "#3b82f6", "Right": "#ef4444", "Center": "#22c55e"}

fig1 = px.bar(
    outlet_stable,
    x="outlet", y="Stability Rate (%)",
    color="lean", color_discrete_map=color_map,
    title="Prompt Stability Rate by Outlet — How Consistent is the AI?",
    text="Stability Rate (%)", height=400
)
fig1.update_traces(texttemplate='%{text}%', textposition='outside')
fig1.update_layout(
    **PLOTLY_LAYOUT,
    yaxis_range=[0, 115],
    xaxis_title="News Outlet",
    yaxis_title="Stability Rate (%)"
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# PROMPT COMPARISON CHART
st.subheader("Bias Rate Per Prompt — Does the Question Change the Answer?")

prompt_rates = pd.DataFrame({
    "Prompt": ["Prompt A (Direct)", "Prompt B (Framing)", "Prompt C (Fact-Checker)"],
    "Bias Rate (%)": [
        round((df["prompt_a_label"] == "BIASED").mean() * 100, 1),
        round((df["prompt_b_label"] == "BIASED").mean() * 100, 1),
        round((df["prompt_c_label"] == "BIASED").mean() * 100, 1),
    ]
})

fig2 = px.bar(
    prompt_rates,
    x="Prompt", y="Bias Rate (%)",
    title="Bias Detection Rate Changes With Prompt Wording",
    text="Bias Rate (%)",
    color="Bias Rate (%)",
    color_continuous_scale="RdYlGn_r",
    height=350
)
fig2.update_traces(texttemplate='%{text}%', textposition='outside')
fig2.update_layout(
    **PLOTLY_LAYOUT,
    yaxis_range=[0, 110],
    coloraxis_showscale=False
)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")


st.markdown("---")

# FULL TABLE
st.subheader("Full Prompt Sensitivity Results")
with st.expander("Show all results"):
    full_df = df[["outlet", "lean", "title", "prompt_a_label", "prompt_b_label", "prompt_c_label", "Stable"]].copy()
    full_df.columns = ["Outlet", "Lean", "Title", "Prompt A", "Prompt B", "Prompt C", "Stability"]
    st.dataframe(full_df, use_container_width=True, hide_index=True)

st.markdown("---")

# INTERPRETATION
st.subheader("Interpretation")

variance = abs(prompt_rates["Bias Rate (%)"].max() - prompt_rates["Bias Rate (%)"].min())

if variance < 5:
    st.success(f"""
    **Finding:** Bias detection rate varied by only {variance:.1f}% across the three prompts.
    This indicates relatively high prompt-stability for this dataset.
    """)
elif variance < 20:
    st.warning(f"""
    **Finding:** Bias detection rate varied by {variance:.1f}% across the three prompts.
    This indicates moderate variation in AI verdicts based on prompt phrasing.
    """)
else:
    st.info(f"""
    **Finding:** Bias detection rate varied by {variance:.1f}% across the three prompts.
    This indicates that a large portion of articles received different verdicts
    depending on the phrasing of the question.
    """)

st.markdown("---")
st.caption("Ayushi Patel · MS Computer Science · Montclair State University · Spring 2026")