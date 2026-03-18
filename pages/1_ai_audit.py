import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from styles import inject_styles, render_sidebar, PLOTLY_LAYOUT

st.set_page_config(page_title="AI Audit Results", layout="wide")
inject_styles()
render_sidebar()

DB_PATH = "data/news_vault.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# PAGE CONTENT

st.title("Experiments 1 & 2 — Dual Model Audit")
st.markdown("""
*Do a larger AI model (Llama3 8B) and a smaller AI model (Llama3.2 3B) agree
when detecting political bias in news articles?*
""")
st.markdown("---")

# LOAD DATA
try:
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT outlet, lean, title, label_8b, label_3b, reason_8b
        FROM articles
        WHERE label_8b IS NOT NULL AND label_3b IS NOT NULL
        ORDER BY outlet, id DESC
    """, conn)
    conn.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if df.empty:
    st.info("No audit data yet. Go to the Home page and run the AI experiments.")
    st.stop()

# AGREEMENT ANALYSIS
df["Agreement"]       = df["label_8b"] == df["label_3b"]
df["Agreement_Label"] = df["Agreement"].map({True: "Agree", False: "Disagree"})

total     = len(df)
agreed    = df["Agreement"].sum()
disagreed = total - agreed
rate      = round(agreed / total * 100, 1)

# METRIC CARDS
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Articles",    total)
m2.metric("Models Agreed",     int(agreed))
m3.metric("Models Disagreed",  int(disagreed))
m4.metric("Agreement Rate",    f"{rate}%")

st.markdown("---")

# AGREEMENT BY OUTLET
st.subheader("Agreement Rate by News Outlet")

outlet_agree = df.groupby(["outlet", "lean"]).agg(
    Total=("Agreement", "count"),
    Agreed=("Agreement", "sum")
).reset_index()
outlet_agree["Agreement Rate (%)"] = round(outlet_agree["Agreed"] / outlet_agree["Total"] * 100, 1)

color_map = {"Left": "#3b82f6", "Right": "#ef4444", "Center": "#22c55e"}

fig1 = px.bar(
    outlet_agree,
    x="outlet", y="Agreement Rate (%)",
    color="lean", color_discrete_map=color_map,
    title="Model Agreement Rate by Outlet — Do 8B and 3B Agree?",
    text="Agreement Rate (%)", height=400
)
fig1.update_traces(texttemplate='%{text}%', textposition='outside')
fig1.update_layout(
    **PLOTLY_LAYOUT,
    yaxis_range=[0, 115],
    xaxis_title="News Outlet",
    yaxis_title="Agreement Rate (%)"
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# VERDICT DISTRIBUTION
st.subheader("Verdict Distribution — What Did Each Model Decide?")

vc1, vc2 = st.columns(2)

verdict_colors = {"BIASED": "#ef4444", "NEUTRAL": "#22c55e", "UNCLEAR": "#f59e0b"}

with vc1:
    counts_8b = df["label_8b"].value_counts().reset_index()
    counts_8b.columns = ["Verdict", "Count"]
    fig2 = px.pie(
        counts_8b, names="Verdict", values="Count",
        title="Llama3 8B — Verdict Distribution",
        color="Verdict", color_discrete_map=verdict_colors
    )
    fig2.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)

with vc2:
    counts_3b = df["label_3b"].value_counts().reset_index()
    counts_3b.columns = ["Verdict", "Count"]
    fig3 = px.pie(
        counts_3b, names="Verdict", values="Count",
        title="Llama3.2 3B — Verdict Distribution",
        color="Verdict", color_discrete_map=verdict_colors
    )
    fig3.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")


# FULL RESULTS TABLE
st.subheader("Full Audit Results")

with st.expander("Show all audited articles"):
    display_df = df[["outlet", "lean", "title", "label_8b", "label_3b", "Agreement_Label"]].copy()
    display_df.columns = ["Outlet", "Lean", "Title", "8B Verdict", "3B Verdict", "Agreement"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")

# INTERPRETATION
st.subheader("Interpretation")

if rate >= 80:
    st.success(f"""
    **Finding:** With a {rate}% agreement rate, the two models show **high consistency**.
    This indicates that bias detection patterns are relatively stable across model sizes for this dataset.
    There is a {round(100-rate, 1)}% disagreement rate observed between the models.
    """)
elif rate >= 60:
    st.warning(f"""
    **Finding:** With a {rate}% agreement rate, the models show **moderate consistency**.
    Approximately 1 in 3 articles receives a different verdict depending on which model size is used.
    """)
else:
    st.info(f"""
    **Finding:** With a {rate}% agreement rate, the models show **low consistency**.
    This indicates that the bias detection results are highly model-dependent for this dataset.
    """)

st.markdown("---")
st.caption("Ayushi Patel · MS Computer Science · Montclair State University · Spring 2026")