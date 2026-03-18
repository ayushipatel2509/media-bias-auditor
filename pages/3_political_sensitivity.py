import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from styles import inject_styles, render_sidebar, PLOTLY_LAYOUT

st.set_page_config(page_title="Political Symmetry", layout="wide")
inject_styles()
render_sidebar()

DB_PATH = "data/news_vault.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# PAGE CONTENT

st.title("Experiment 4 — Political Symmetry Test")
st.markdown("""
*Does the AI label Left-leaning and Right-leaning news articles as BIASED
at the same rate?*
""")

st.markdown("""
| Finding | Interpretation |
|---|---|
| Left rate >> Right rate | AI has **Right-leaning bias** — harder on Left outlets |
| Right rate >> Left rate | AI has **Left-leaning bias** — harder on Right outlets |
| Rates approximately equal | AI is **politically symmetric** |
""")
st.markdown("---")

# LOAD DATA
try:
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT outlet, lean, title, label_8b, label_3b
        FROM articles
        WHERE label_8b IS NOT NULL
        ORDER BY lean, outlet
    """, conn)
    conn.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if df.empty:
    st.info("No audit data yet. Run the AI experiments from the Home page.")
    st.stop()

# CALCULATE RATES BY LEAN
lean_stats = df.groupby("lean").agg(
    Total=("label_8b", "count"),
    Biased=("label_8b", lambda x: (x == "BIASED").sum()),
    Neutral=("label_8b", lambda x: (x == "NEUTRAL").sum())
).reset_index()
lean_stats["Bias Rate (%)"] = round(lean_stats["Biased"] / lean_stats["Total"] * 100, 1)

# GAUGE CHARTS
st.subheader("Bias Detection Rate — Left vs Right vs Center")

left_row   = lean_stats[lean_stats["lean"] == "Left"]
right_row  = lean_stats[lean_stats["lean"] == "Right"]
center_row = lean_stats[lean_stats["lean"] == "Center"]

left_rate   = float(left_row["Bias Rate (%)"].values[0])   if not left_row.empty   else 0
right_rate  = float(right_row["Bias Rate (%)"].values[0])  if not right_row.empty  else 0
center_rate = float(center_row["Bias Rate (%)"].values[0]) if not center_row.empty else 0

def make_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 13, "family": "Inter"}},
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar":  {"color": color},
            "steps": [
                {"range": [0,  33], "color": "#dcfce7"},
                {"range": [33, 66], "color": "#fef9c3"},
                {"range": [66,100], "color": "#fee2e2"}
            ],
            "threshold": {
                "line": {"color": "#64748b", "width": 2},
                "thickness": 0.75,
                "value": 50
            }
        }
    ))
    fig.update_layout(
        height=260,
        margin=dict(t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter")
    )
    return fig

g1, g2, g3 = st.columns(3)

with g1:
    st.plotly_chart(
        make_gauge(left_rate, "Left-Leaning Outlets — % Labeled BIASED", "#3b82f6"),
        use_container_width=True
    )
    st.caption(f"Left outlets: {int(left_row['Total'].values[0]) if not left_row.empty else 0} articles analyzed")

with g2:
    st.plotly_chart(
        make_gauge(right_rate, "Right-Leaning Outlets — % Labeled BIASED", "#ef4444"),
        use_container_width=True
    )
    st.caption(f"Right outlets: {int(right_row['Total'].values[0]) if not right_row.empty else 0} articles analyzed")

with g3:
    st.plotly_chart(
        make_gauge(center_rate, "Center Outlets — % Labeled BIASED", "#22c55e"),
        use_container_width=True
    )
    st.caption(f"Center outlets: {int(center_row['Total'].values[0]) if not center_row.empty else 0} articles analyzed")

st.markdown("---")

# SYMMETRY VERDICT
st.subheader("Symmetry Analysis Verdict")

diff = abs(left_rate - right_rate)

if diff < 10:
    st.success(f"""
    **AI Appears Politically Symmetric**

    Left bias rate: {left_rate}% · Right bias rate: {right_rate}% · Difference: {diff:.1f}%

    The AI labels Left and Right leaning articles as biased at approximately the same rate
    (within 10% threshold). This suggests the model does not have a significant political lean
    in its bias detection.
    """)
elif left_rate > right_rate:
    st.error(f"""
    **AI Shows Potential Right-Leaning Bias**

    Left bias rate: {left_rate}% · Right bias rate: {right_rate}% · Difference: {diff:.1f}%

    The AI labels Left-leaning articles as BIASED {diff:.1f}% more often than Right-leaning articles.
    This asymmetry suggests the model may have internalized patterns that make it
    more critical of left-leaning language and framing.
    """)
else:
    st.error(f"""
    **AI Shows Potential Left-Leaning Bias**

    Left bias rate: {left_rate}% · Right bias rate: {right_rate}% · Difference: {diff:.1f}%

    The AI labels Right-leaning articles as BIASED {diff:.1f}% more often than Left-leaning articles.
    This asymmetry suggests the model may have internalized patterns that make it
    more critical of right-leaning language and framing.
    """)

st.markdown("---")

# OUTLET BY OUTLET BREAKDOWN
st.subheader("Bias Detection Rate — Outlet by Outlet")
st.caption("Individual outlet analysis reveals which sources the AI treats most harshly")

outlet_stats = df.groupby(["outlet", "lean"]).agg(
    Total=("label_8b", "count"),
    Biased=("label_8b", lambda x: (x == "BIASED").sum())
).reset_index()
outlet_stats["Bias Rate (%)"] = round(outlet_stats["Biased"] / outlet_stats["Total"] * 100, 1)
outlet_stats = outlet_stats.sort_values("Bias Rate (%)", ascending=False)

color_map = {"Left": "#3b82f6", "Right": "#ef4444", "Center": "#22c55e"}

fig_outlets = px.bar(
    outlet_stats,
    x="outlet", y="Bias Rate (%)",
    color="lean", color_discrete_map=color_map,
    title="AI-Detected Bias Rate by Individual Outlet",
    text="Bias Rate (%)", height=420,
    category_orders={"outlet": outlet_stats["outlet"].tolist()}
)
fig_outlets.update_traces(texttemplate='%{text}%', textposition='outside')
fig_outlets.update_layout(
    **PLOTLY_LAYOUT,
    yaxis_range=[0, 115],
    xaxis_title="News Outlet",
    yaxis_title="% of Articles Labeled BIASED by AI"
)
st.plotly_chart(fig_outlets, use_container_width=True)

st.markdown("---")

# LEFT VS RIGHT DIRECT COMPARISON
st.subheader("Left vs Right — Direct Comparison")

fig_compare = px.bar(
    lean_stats[lean_stats["lean"].isin(["Left", "Right"])],
    x="lean", y="Bias Rate (%)",
    color="lean", color_discrete_map=color_map,
    title="Direct Comparison: Bias Rate for Left vs Right Outlets",
    text="Bias Rate (%)", height=350, barmode="group"
)
fig_compare.update_traces(texttemplate='%{text}%', textposition='outside')
fig_compare.update_layout(
    **PLOTLY_LAYOUT,
    yaxis_range=[0, 115],
    showlegend=False
)
st.plotly_chart(fig_compare, use_container_width=True)

st.markdown("---")



# MODEL SIZE COMPARISON
st.subheader("Does Model Size Affect Political Symmetry?")
st.caption("Comparing 8B vs 3B model bias rates for Left and Right outlets")

model_compare = []
for lean in ["Left", "Right", "Center"]:
    subset = df[df["lean"] == lean]
    if not subset.empty:
        rate_8b = round((subset["label_8b"] == "BIASED").mean() * 100, 1)
        rate_3b = round((subset["label_3b"] == "BIASED").mean() * 100, 1)
        model_compare.append({"Lean": lean, "Model": "Llama3 8B",   "Bias Rate (%)": rate_8b})
        model_compare.append({"Lean": lean, "Model": "Llama3.2 3B", "Bias Rate (%)": rate_3b})

if model_compare:
    df_model = pd.DataFrame(model_compare)
    fig_model = px.bar(
        df_model,
        x="Lean", y="Bias Rate (%)",
        color="Model", barmode="group",
        title="Political Bias Rate by Model Size — Does a Larger Model Show Less Bias?",
        text="Bias Rate (%)", height=380,
        color_discrete_map={"Llama3 8B": "#8b5cf6", "Llama3.2 3B": "#f59e0b"}
    )
    fig_model.update_traces(texttemplate='%{text}%', textposition='outside')
    fig_model.update_layout(**PLOTLY_LAYOUT, yaxis_range=[0, 115])
    st.plotly_chart(fig_model, use_container_width=True)

st.markdown("---")
st.caption("Ayushi Patel · MS Computer Science · Montclair State University · Spring 2026")