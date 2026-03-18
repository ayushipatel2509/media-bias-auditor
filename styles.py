"""
Shared style injection for all pages.
Import and call inject_styles() at the top of each page.
"""

import streamlit as st

SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Reset and box-sizing to prevent overlap */
* {
    box-sizing: border-box !important;
}

/* Force dark mode */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background-color: #020617 !important; /* slate-950 */
    color: #f8fafc !important; /* slate-50 */
}
.stApp { 
    background-color: #020617 !important; 
}
[data-testid="stHeader"] { 
    background-color: transparent !important; 
}

/* Typography */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0f172a !important; /* slate-900 */
    border-right: 1px solid #1e293b !important; /* slate-800 */
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; /* slate-300 */ }
[data-testid="stSidebar"] strong { color: #f8fafc !important; }
[data-testid="stSidebar"] hr { border-color: #1e293b !important; margin: 1.5rem 0 !important; }

/* Page link nav items */
div.stPageLink > a {
    display: flex;
    align-items: center;
    padding: 0.5rem 0.875rem;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 500;
    color: #cbd5e1 !important;
    text-decoration: none !important;
    transition: all 0.2s ease;
    background: transparent;
    width: 100%;
    margin-bottom: 0.25rem;
    border: 1px solid transparent;
}
div.stPageLink > a:hover {
    background: #1e293b !important;
    color: #818cf8 !important; /* indigo-400 */
    border: 1px solid #334155 !important;
}

/* Metric cards (Fixing Overlap) */
[data-testid="stMetric"] {
    background: #0f172a !important; /* slate-900 */
    border: 1px solid #1e293b !important; /* slate-800 */
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5) !important;
    overflow: hidden !important; /* Prevents overlap */
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important; /* slate-400 */
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    line-height: 1.2 !important;
}

/* Headings */
h1 { font-weight: 800 !important; color: #f8fafc !important; letter-spacing: -0.03em; font-size: 2.25rem !important; }
h2 { font-weight: 700 !important; color: #f1f5f9 !important; letter-spacing: -0.02em; }
h3 { font-weight: 600 !important; color: #e2e8f0 !important; letter-spacing: -0.01em; }
h4, h5 { font-weight: 600 !important; color: #cbd5e1 !important; }

/* Dividers */
hr { border-color: #1e293b !important; margin: 2rem 0 !important; }

/* Captions */
[data-testid="stCaptionContainer"] p {
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
}

/* Alert / info / warning / success / error */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.9rem !important;
    padding: 1rem !important;
    border: 1px solid #1e293b !important;
    background-color: #0f172a !important;
    color: #e2e8f0 !important;
}

/* All buttons (primary and secondary/page links disguised as buttons) */
.stButton > button,
[data-testid="stBaseButton-secondary"] {
    background-color: #4f46e5 !important; /* indigo-600 */
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.01em;
    transition: all 0.2s ease !important;
    padding: 0.5rem 1rem !important;
    box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.4) !important;
}
.stButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover {
    background-color: #6366f1 !important; /* indigo-500 */
    box-shadow: 0 6px 8px -1px rgba(79, 70, 229, 0.5) !important;
    color: #ffffff !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    overflow: hidden;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5) !important;
}
div[data-testid="stDataFrame"] > div {
    background: #0f172a !important;
}

/* Progress bar */
[data-testid="stProgressBar"] > div { background-color: #6366f1 !important; border-radius: 4px !important; }
[data-testid="stProgressBar"] { background-color: #1e293b !important; border-radius: 4px !important; }

/* Container borders - Adjusted padding & background */
[data-testid="stVerticalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #1e293b !important;
    border-radius: 12px !important;
    background-color: #0f172a !important;
    padding: 1.25rem !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3) !important;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    background: #0f172a !important;
}

/* Tabs */
[data-testid="stTabs"] [role="tab"] {
    font-weight: 600 !important;
    color: #64748b !important;
    padding-bottom: 0.5rem !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #818cf8 !important;
    border-bottom-color: #818cf8 !important;
}

/* Selectbox */
[data-testid="stSelectbox"] label {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.stSelectbox > div > div {
    background: #0f172a !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
    color: #f8fafc !important;
}

/* Radio */
[data-testid="stRadio"] label {
    font-size: 0.9rem !important;
    color: #e2e8f0 !important;
    font-weight: 500 !important;
}

/* Text inputs */
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
}
[data-testid="stTextInput"] > div > div > input,
[data-testid="stTextArea"] > div > div > textarea {
    background-color: #0f172a !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #f8fafc !important;
}
[data-testid="stTextInput"] > div > div > input:focus,
[data-testid="stTextArea"] > div > div > textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 1px #6366f1 !important;
}

/* Plotly charts text color override inside dark mode */
.js-plotly-plot .xtitle, .js-plotly-plot .ytitle {
    fill: #94a3b8 !important;
}
.js-plotly-plot .g-gtitle {
    fill: #f8fafc !important;
}
</style>
"""

def inject_styles():
    st.markdown(SHARED_CSS, unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.caption("NAVIGATION")
        st.page_link("app.py",                           label="Home / Overview")
        st.page_link("pages/1_ai_audit.py",              label="AI Audit Results")
        st.page_link("pages/2_prompt_sensitivity.py",    label="Prompt Sensitivity")
        st.page_link("pages/3_political_sensitivity.py", label="Political Symmetry")
        st.page_link("pages/4_live_analyser.py",         label="Live Analyzer")
        st.markdown("---")
        st.caption("Ayushi Patel · MS CS · Spring 2026")

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter"),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)