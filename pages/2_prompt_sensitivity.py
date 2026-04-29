import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import sys, os

# Adjusting path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from styles import inject_styles, render_sidebar, PLOTLY_LAYOUT
except ImportError:
    # Fallback if styles file is not found
    def inject_styles(): pass
    def render_sidebar(): st.sidebar.title("Navigation")
    PLOTLY_LAYOUT = {}

st.set_page_config(page_title="Prompt Sensitivity", layout="wide")
inject_styles()
render_sidebar()

DB_PATH = "data/news_vault.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# PAGE CONTENT
st.title("Experiment 3 — Prompt Sensitivity Analysis")
st.markdown("""
*Research Question: If I give the same AI the same article but change the 'lens' of the question, will it flip its verdict?*
""")
st.markdown("---")




p1, p2 = st.columns(2)

with p1:
    st.markdown("### Prompt 1: Framing Prompt")
    st.info('**Prompt:** "Does this article show political bias in its language or framing? Answer BIASED or NEUTRAL only."')
    

with p2:
    st.markdown("### Prompt 2: Fact-Checker Role")
    st.info('**Prompt:** "As a neutral fact-checker, evaluate if this text presents information fairly. Answer BIASED or NEUTRAL only."')
    

st.markdown("---")

# LOAD DATA (UPDATED QUERY)
try:
    conn = get_db_connection()
    # Note: prompt_a_label is removed from SELECT
    df = pd.read_sql_query("""
        SELECT outlet, lean, title,
               prompt_b_label, prompt_c_label
        FROM articles
        WHERE prompt_b_label IS NOT NULL AND prompt_c_label IS NOT NULL
        ORDER BY outlet
    """, conn)
    conn.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if df.empty:
    st.info("No prompt sensitivity data found for the new 2-prompt model. Run the AI experiments first.")
    st.stop()

# STABILITY CALCULATION (BINARY COMPARISON)
# Stability now means Prompt B and Prompt C gave the same answer
df["Is_Stable"] = (df["prompt_b_label"] == df["prompt_c_label"])
df["Status"] = df["Is_Stable"].map({True: "Stable", False: "Unstable"})

total    = len(df)
stable   = df["Is_Stable"].sum()
unstable = total - stable
rate     = round(stable / total * 100, 1)

# METRICS
m1, m2, m3, m4 = st.columns(4)
m1.metric("Articles Audited", total)
m2.metric("Stable Verdicts",  int(stable))
m3.metric("Unstable Verdicts", int(unstable))
m4.metric("Stability Rate",   f"{rate}%")

st.markdown("---")

# STABILITY BY OUTLET
st.subheader("Stability by News Outlet")
st.caption("Which outlets cause the most 'confusion' or inconsistency in the AI?")

outlet_stable = df.groupby(["outlet", "lean"]).agg(
    Total=("Is_Stable", "count"),
    Stable=("Is_Stable", "sum")
).reset_index()
outlet_stable["Stability Rate (%)"] = round(outlet_stable["Stable"] / outlet_stable["Total"] * 100, 1)

color_map = {"Left": "#3b82f6", "Right": "#ef4444", "Center": "#22c55e"}

fig1 = px.bar(
    outlet_stable,
    x="outlet", y="Stability Rate (%)",
    color="lean", color_discrete_map=color_map,
    title="Consistency Rate: Does the AI agree with itself?",
    text="Stability Rate (%)", height=400
)
fig1.update_traces(texttemplate='%{text}%', textposition='outside')
fig1.update_layout(yaxis_range=[0, 115], xaxis_title="Outlet", yaxis_title="Stability (%)")
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# BIAS RATE PER PROMPT
st.subheader("Bias Detection Rate: Framing vs. Fact-Checking")

prompt_rates = pd.DataFrame({
    "Methodology": ["Framing Lens", "Fact-Checker Lens"],
    "Bias Detection Rate (%)": [
        round((df["prompt_b_label"] == "BIASED").mean() * 100, 1),
        round((df["prompt_c_label"] == "BIASED").mean() * 100, 1),
    ]
})

fig2 = px.bar(
    prompt_rates,
    x="Methodology", y="Bias Detection Rate (%)",
    title="Does the Lens change the outcome?",
    text="Bias Detection Rate (%)",
    color="Methodology",
    color_discrete_sequence=["#636EFA", "#EF553B"],
    height=400
)
fig2.update_traces(texttemplate='%{text}%', textposition='outside')
fig2.update_layout(yaxis_range=[0, 110])
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# FULL RESULTS TABLE
st.subheader("Audit Log: Spotting Inconsistencies")
with st.expander("Show detailed results for every article"):
    display_df = df[["outlet", "lean", "title", "prompt_b_label", "prompt_c_label", "Status"]].copy()
    display_df.columns = ["Outlet", "Lean", "Headline", "Framing Result", "Fact-Check Result", "Stability Status"]
    
    # Highlight unstable rows in the dataframe
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")

# AUTOMATED INTERPRETATION
st.subheader("Research Finding")
gap = abs(prompt_rates["Bias Detection Rate (%)"].iloc[0] - prompt_rates["Bias Detection Rate (%)"].iloc[1])

if gap < 5:
    st.success(f"**Stable:** The AI is highly robust. The verdict remained consistent across different prompts (Gap: {gap}%).")
else:
    st.warning(f"**Variable:** The AI's sensitivity to prompt phrasing is notable. Changing the prompt shifted the bias detection rate by {gap}%.")

st.markdown("---")
st.caption("Ayushi Patel · MS Computer Science · Montclair State University · Spring 2026")