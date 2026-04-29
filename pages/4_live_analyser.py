import streamlit as st
import ollama
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from newspaper import Article, Config
from sentence_transformers import SentenceTransformer, util
import sys, os

# Custom Imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from styles import inject_styles, render_sidebar, PLOTLY_LAYOUT
except ImportError:
    def inject_styles(): pass
    def render_sidebar(): st.sidebar.title("Navigation")
    PLOTLY_LAYOUT = {}

st.set_page_config(page_title="Live Article Analyzer", layout="wide")
inject_styles()
render_sidebar()

DB_PATH  = "data/news_vault.db"
MODEL_8B = "llama3"
MODEL_3B = "llama3.2:3b"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# MODELS
@st.cache_resource
def load_embed_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

embed_model = load_embed_model()

# HELPERS
def fetch_article_from_url(url):
    try:
        config = Config()
        config.browser_user_agent = USER_AGENT
        config.request_timeout = 15
        article = Article(url, config=config)
        article.download()
        article.parse()
        if article.text and len(article.text) > 100:
            return article.title, article.text
        return None, None
    except Exception:
        return None, None

def ask_model_detailed(model_name, text):
    prompt = f"""Analyze this news article for political bias.
Article:
{text[:4000]}
Respond in EXACTLY this format:
LABEL: [BIASED or NEUTRAL]
REASON: [2-3 sentence explanation of why]"""
    try:
        response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {e}"

def parse_response(text):
    result = {"label": "UNCLEAR", "reason": "Could not parse response"}
    if not text or text.startswith("ERROR"):
        return result
    text_upper = text.upper()
    if   "LABEL: BIASED"  in text_upper: result["label"] = "BIASED"
    elif "LABEL: NEUTRAL" in text_upper: result["label"] = "NEUTRAL"
    if "REASON:" in text:
        part = text.split("REASON:")[-1].strip()
        result["reason"] = part[:600]
    return result

def run_prompt_sensitivity_live(text):
    # REMOVED PROMPT A (DIRECT)
    prompts = {
        "Prompt 1: Framing":
            f"Does this article show political bias in its language or framing? Answer BIASED or NEUTRAL only.\n\n{text[:2500]}",
        "Prompt 2: Fact-checker":
            f"As a neutral fact-checker, evaluate if this text presents information fairly. Answer BIASED or NEUTRAL only.\n\n{text[:2500]}"
    }
    results = {}
    for name, prompt in prompts.items():
        try:
            res = ollama.chat(model=MODEL_8B, messages=[{"role": "user", "content": prompt}])
            raw = res["message"]["content"].strip().upper()
            results[name] = "BIASED" if "BIASED" in raw else "NEUTRAL" if "NEUTRAL" in raw else "UNCLEAR"
        except Exception:
            results[name] = "ERROR"
    return results

# PAGE UI
st.title("Live Article Analyzer")
st.markdown("Instantly audit any article using the Dual-Model and Multi-Lens experimental framework.")

# INPUT SECTION
st.subheader("Input Your Article")
input_method = st.radio("Choose input method:", ["Paste Text", "Enter URL"], horizontal=True)

article_text, article_title = "", ""

if input_method == "Paste Text":
    article_text = st.text_area("Article text:", height=200, placeholder="Paste article content here...")
    article_title = st.text_input("Article title (optional)")
else:
    url = st.text_input("Article URL:")
    if url:
        with st.spinner("Fetching..."):
            fetched_title, fetched_text = fetch_article_from_url(url)
            if fetched_text:
                article_text, article_title = fetched_text, fetched_title or url
                st.success(f"Fetched: {article_title[:80]}")
                with st.expander("Preview text"): st.write(article_text)

st.markdown("---")

# ANALYSIS BUTTON
if st.button("Run Full Bias Audit", type="primary", use_container_width=True):
    if len(article_text) < 100:
        st.error("Text too short for analysis.")
    else:
        # SECTION 1 — DUAL MODEL VERDICT
        st.subheader("1. Dual Model Verdict (Scale vs. Objectivity)")
        c1, c2 = st.columns(2)
        with c1:
            raw_8b = ask_model_detailed(MODEL_8B, article_text)
            res_8b = parse_response(raw_8b)
            st.markdown(f"**Llama3 8B:** {res_8b['label']}")
            st.info(res_8b['reason'])
        with c2:
            raw_3b = ask_model_detailed(MODEL_3B, article_text)
            res_3b = parse_response(raw_3b)
            st.markdown(f"**Llama3.2 3B:** {res_3b['label']}")
            st.info(res_3b['reason'])

        # SECTION 2 — PROMPT SENSITIVITY
        st.subheader("2. Prompt Sensitivity Test ")
        with st.spinner("Testing Framing vs. Fact-Checking"):
            prompt_results = run_prompt_sensitivity_live(article_text)

        ps1, ps2 = st.columns(2)
        with ps1:
            v_frame = prompt_results.get("Prompt 1: Framing", "ERROR")
            st.metric("Framing Prompt", v_frame)
        with ps2:
            v_fact = prompt_results.get("Prompt 2: Fact-checker", "ERROR")
            st.metric("Fact-Checker Prompt", v_fact)

        # SECTION 3 — CERTAINTY MATRIX
        st.subheader("3. AI Certainty & Trust Score")
        # Total data points: 8B verdict, 3B verdict, Framing Result, Fact-check Result (Total: 4)
        all_verdicts = [res_8b["label"], res_3b["label"], v_frame, v_fact]
        biased_count = all_verdicts.count("BIASED")
        neutral_count = all_verdicts.count("NEUTRAL")
        dominant_verdict = "BIASED" if biased_count > neutral_count else "NEUTRAL"
        
        # Calculate score (out of 4 possible points)
        certainty_score = int((max(biased_count, neutral_count) / 4) * 100)

        gauge_col, text_col = st.columns([1, 2])
        with gauge_col:
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=certainty_score,
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#6366f1"}, 'threshold': {'line': {'color': "white", 'width': 4}, 'value': 75}}
            ))
            fig.update_layout(height=200, margin=dict(t=30, b=0), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#f8fafc"})
            st.plotly_chart(fig, use_container_width=True)
        
        with text_col:
            if certainty_score == 100:
                st.success(f"**Absolute Consensus:** Both models and both lenses agree on **{dominant_verdict}**.")
            elif certainty_score >= 75:
                st.info(f"**High Certainty:** Minority disagreement detected, but consensus remains **{dominant_verdict}**.")
            else:
                st.warning(f"**Low Certainty ({certainty_score}%):** Significant disagreement between models or lenses. AI results are unstable.")

        st.markdown("---")
        st.caption("Ayushi Patel · MS Computer Science · Montclair State University")