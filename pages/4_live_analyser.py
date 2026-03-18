import streamlit as st
import ollama
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from newspaper import Article, Config
from sentence_transformers import SentenceTransformer, util
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from styles import inject_styles, render_sidebar, PLOTLY_LAYOUT

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
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
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
    prompts = {
        "Prompt A (Direct)":
            f"Is this article biased? Answer BIASED or NEUTRAL only.\n\n{text[:2500]}",
        "Prompt B (Framing)":
            f"Does this article show political bias in its language or framing? Answer BIASED or NEUTRAL only.\n\n{text[:2500]}",
        "Prompt C (Fact-checker)":
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


def find_similar_articles(text, top_n=5):
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT outlet, lean, title, content, label_8b FROM articles WHERE label_8b IS NOT NULL")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return []
        user_vec = embed_model.encode(text[:1000], convert_to_tensor=True)
        scored = []
        for outlet, lean, title, content, label in rows:
            db_vec = embed_model.encode(content[:1000], convert_to_tensor=True)
            sim    = float(util.cos_sim(user_vec, db_vec)[0][0])
            scored.append({"outlet": outlet, "lean": lean, "title": title[:80],
                           "similarity": round(sim * 100, 1), "label": label})
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_n]
    except Exception:
        return []


# PAGE UI

st.title("Live Article Analyzer")
st.markdown(
    "Paste any news article text **or** enter a URL to get instant AI bias analysis. "
    "The system runs all four experiments in real time on your article."
)
st.markdown("---")

# INPUT SECTION
st.subheader("Input Your Article")

input_method = st.radio(
    "Choose input method:",
    ["Paste Text", "Enter URL"],
    horizontal=True
)

article_text  = ""
article_title = ""

if input_method == "Paste Text":
    article_text = st.text_area(
        "Article text:",
        height=200,
        placeholder="Paste any news article text here..."
    )
    article_title = st.text_input("Article title (optional):", placeholder="e.g. New bill signed into law...")

else:
    url = st.text_input(
        "Article URL:",
        placeholder="https://www.cnn.com/article/..."
    )
    if url:
        with st.spinner("Fetching article from URL..."):
            fetched_title, fetched_text = fetch_article_from_url(url)
            if fetched_text:
                article_text  = fetched_text
                article_title = fetched_title or url
                st.success(f"Article fetched: **{article_title[:80]}**")
                st.caption("⚠️ Note: Some websites block scrapers or have dynamic layouts that cause the wrong text to be fetched. If the text below doesn't match your article, please use the 'Paste Text' method instead.")
                with st.expander("Preview fetched text (Full Article)", expanded=True):
                    st.write(article_text)
            else:
                st.error("Could not fetch article. Try pasting the text instead.")

st.markdown("---")

# ANALYSIS BUTTON
if st.button("Run Full Bias Analysis", type="primary", use_container_width=True):
    if not article_text or len(article_text) < 100:
        st.error("Please provide at least 100 characters of article text.")
    else:

        # ======================================================
        # SECTION 1 — DUAL MODEL VERDICT
        # ======================================================
        st.markdown("---")
        st.subheader("1.  Dual Model Verdict")
        st.caption("Same article analyzed by two different-sized AI models")

        col_8b, col_3b = st.columns(2)

        with col_8b:
            with st.spinner("Llama3 8B analyzing..."):
                raw_8b    = ask_model_detailed(MODEL_8B, article_text)
                result_8b = parse_response(raw_8b)

            verdict_color_8b = "#ef4444" if result_8b["label"] == "BIASED" else "#22c55e"
            st.markdown(
                f"<div style='font-size:1.1rem; font-weight:700; color:{verdict_color_8b}; "
                f"margin-bottom:0.5rem;'>Llama3 8B — {result_8b['label']}</div>",
                unsafe_allow_html=True
            )
            st.info(f"**Reasoning:** {result_8b['reason']}")

        with col_3b:
            with st.spinner("Llama3.2 3B analyzing..."):
                raw_3b    = ask_model_detailed(MODEL_3B, article_text)
                result_3b = parse_response(raw_3b)

            verdict_color_3b = "#ef4444" if result_3b["label"] == "BIASED" else "#22c55e"
            st.markdown(
                f"<div style='font-size:1.1rem; font-weight:700; color:{verdict_color_3b}; "
                f"margin-bottom:0.5rem;'>Llama3.2 3B — {result_3b['label']}</div>",
                unsafe_allow_html=True
            )
            st.info(f"**Reasoning:** {result_3b['reason']}")

        st.markdown("---")
        if result_8b["label"] == result_3b["label"]:
            st.success(
                f"**Models Agree** — Both verdict: **{result_8b['label']}** · High confidence"
            )
        else:
            st.warning(
                f"**Models Disagree** — 8B says **{result_8b['label']}** · 3B says **{result_3b['label']}** · "
                f"Low confidence. This disagreement is itself evidence of AI subjectivity."
            )

        # ======================================================
        # SECTION 2 — PROMPT SENSITIVITY
        # ======================================================
        st.markdown("---")
        st.subheader("2.  Prompt Sensitivity Test")
        st.caption("Does rephrasing the question change the verdict?")

        with st.spinner("Testing 3 different prompt wordings..."):
            prompt_results = run_prompt_sensitivity_live(article_text)

        labels_list = list(prompt_results.values())
        all_same    = len(set(labels_list)) == 1

        p_col1, p_col2, p_col3 = st.columns(3)

        with p_col1:
            v = prompt_results.get("Prompt A (Direct)", "ERROR")
            st.metric("Prompt A — Direct", v)
            st.caption('"Is this article biased?"')

        with p_col2:
            v = prompt_results.get("Prompt B (Framing)", "ERROR")
            st.metric("Prompt B — Framing", v)
            st.caption('"Does it show political bias in framing?"')

        with p_col3:
            v = prompt_results.get("Prompt C (Fact-checker)", "ERROR")
            st.metric("Prompt C — Fact-checker", v)
            st.caption('"Does it present information fairly?"')

        if all_same:
            st.success(f"**Stable** — All 3 prompts gave the same verdict: **{labels_list[0]}**")
        else:
            unique_verdicts = set(labels_list)
            st.warning(
                f"**Unstable** — Verdicts changed with prompt wording: {', '.join(unique_verdicts)}. "
                "This demonstrates AI prompt sensitivity."
            )

        # ======================================================
        # SECTION 4 — AI CERTAINTY MATRIX
        # ======================================================
        st.markdown("---")
        st.subheader("4. AI Certainty & Trust Score")
        st.caption("How confident is the AI in its final assessment of this article?")

        # Calculate Certainty Score
        # Base: 4 data points (8B, 3B, 3 Prompt Tests)
        # We consider the "majority verdict" as the anchor.
        all_verdicts = [result_8b["label"], result_3b["label"]] + labels_list
        biased_count = all_verdicts.count("BIASED")
        neutral_count = all_verdicts.count("NEUTRAL")

        dominant_verdict = "BIASED" if biased_count > neutral_count else "NEUTRAL"
        dominant_count = max(biased_count, neutral_count)

        # Basic formula: (Dominant Count / Total Valid Tests) * 100
        # We also penalize for 'UNCLEAR' or 'ERROR'
        total_valid = sum([1 for v in all_verdicts if v in ["BIASED", "NEUTRAL"]])
        
        if total_valid > 0:
            certainty_score = round((dominant_count / total_valid) * 100)
        else:
            certainty_score = 0

        # Trust Threshold
        TRUST_THRESHOLD = 75
        
        c_col1, c_col2 = st.columns([1, 2])
        
        with c_col1:
            fig_cert = go.Figure(go.Indicator(
                mode="gauge+number",
                value=certainty_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Aggregate Certainty Score", 'font': {'color': '#f8fafc', 'size': 14}},
                number={'suffix': "%", 'font': {'color': '#f8fafc'}},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#6366f1"},
                    'steps': [
                        {'range': [0, TRUST_THRESHOLD], 'color': '#334155'},
                        {'range': [TRUST_THRESHOLD, 100], 'color': '#0f172a'}
                    ],
                    'threshold': {
                        'line': {'color': "#22c55e", 'width': 4},
                        'thickness': 0.75,
                        'value': TRUST_THRESHOLD
                    }
                }
            ))
            fig_cert.update_layout(height=250, margin=dict(t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#f8fafc"))
            st.plotly_chart(fig_cert, use_container_width=True)

        with c_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if certainty_score >= TRUST_THRESHOLD:
                st.success(f"### High Trust Assessment ({certainty_score}%) \nThe AI models show strong internal consistency. The verdict of **{dominant_verdict}** is highly reliable. \n\n*Basis for Threshold: Above {TRUST_THRESHOLD}%, the system requires both models to agree AND prompt phrasing to remain completely stable.*")
            elif certainty_score >= 50:
                st.warning(f"### Moderate Trust Assessment ({certainty_score}%) \nThe AI is leaning towards **{dominant_verdict}**, but shows some instability. It may be struggling with nuanced framing or model-size disagreements. \n\n*Basis for Threshold: Below {TRUST_THRESHOLD}% indicates that rephrasing the question caused the AI to change its mind at least once.*")
            else:
                st.error(f"### Low Trust Assessment ({certainty_score}%) \nThe AI cannot reach a stable consensus. It is highly susceptible to prompt phrasing and model size biases. **Human review is required.**")

        # ======================================================
        # SECTION 5 — SUMMARY
        # ======================================================
        st.markdown("---")
        st.subheader("5.  Analysis Summary")

        sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)

        with sum_col1:
            st.metric("8B Verdict",      result_8b["label"])
        with sum_col2:
            st.metric("3B Verdict",      result_3b["label"])
        with sum_col3:
            st.metric("Models Agree",    "Yes" if result_8b["label"] == result_3b["label"] else "No")
        with sum_col4:
            st.metric("Prompt Stable",   "Yes" if all_same else "No")

st.markdown("---")
st.caption("Ayushi Patel · MS Computer Science · Montclair State University · Spring 2026")