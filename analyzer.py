import sqlite3
import ollama
from sentence_transformers import SentenceTransformer, util

# CONFIGURATION

DB_PATH    = "data/news_vault.db"
MODEL_8B   = "llama3"
MODEL_3B   = "llama3.2:3b"
SNIPPET_LEN = 800   # Characters sent to AI per article

print(" Loading embedding model...")
embed_model = SentenceTransformer('all-MiniLM-L6-v2')
print(" Embedding model loaded.")

# HELPER

def get_db_connection():
    return sqlite3.connect(DB_PATH)


def ask_model(model_name, system_prompt, user_content):
    """
    Send a prompt to an Ollama model and return the response text.
    Returns None if model call fails.
    """
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content}
            ]
        )
        return response["message"]["content"].strip()
    except Exception as e:
        print(f"   Model error ({model_name}): {e}")
        return None


def extract_label(text):
    """
    Extract BIASED or NEUTRAL from model response.
    Handles cases where model adds extra words.
    """
    if text is None:
        return "ERROR"
    text_upper = text.upper()
    if "BIASED" in text_upper:
        return "BIASED"
    elif "NEUTRAL" in text_upper:
        return "NEUTRAL"
    else:
        return "UNCLEAR"


# EXPERIMENT 1 + 2 — DUAL MODEL AUDIT

def run_dual_model_audit(limit=10):
    """
    EXPERIMENT 1 & 2:
    Send the same article to both Llama3 8B and Llama3.2 3B.
    Records both verdicts and reasoning.
    Research Question: Do larger and smaller models agree on bias detection?
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, outlet, lean, title, content 
        FROM articles 
        WHERE label_8b IS NULL 
        LIMIT ?
    """, (limit,))
    articles = cursor.fetchall()

    if not articles:
        print(" All articles already audited by dual model.")
        conn.close()
        return

    print(f"\n Running Dual-Model Audit on {len(articles)} articles...\n")

    # Using a strict system prompt to force the models into standard output format
    system_prompt = "You are a media bias analyst. Respond ONLY with: BIASED or NEUTRAL."

    for row_id, outlet, lean, title, content in articles:
        snippet = content[:SNIPPET_LEN]

        print(f"  Auditing: [{outlet}] {title[:50]}...")

        # Llama3 8B
        response_8b = ask_model(
            MODEL_8B,
            system_prompt,
            f"Analyze this news article for political bias:\n\n{snippet}"
        )
        label_8b = extract_label(response_8b)

        # Llama3.2 3B
        response_3b = ask_model(
            MODEL_3B,
            system_prompt,
            f"Analyze this news article for political bias:\n\n{snippet}"
        )
        label_3b = extract_label(response_3b)

        agreement = "AGREE" if label_8b == label_3b else "DISAGREE"
        print(f"    8B: {label_8b} | 3B: {label_3b} | {agreement}")

        cursor.execute("""
            UPDATE articles 
            SET label_8b = ?, label_3b = ?, reason_8b = ?, reason_3b = ?, processed = 1
            WHERE id = ?
        """, (label_8b, label_3b, response_8b, response_3b, row_id))
        conn.commit()

    conn.close()
    print("\n Dual-Model Audit complete.")


# EXPERIMENT 3 — PROMPT SENSITIVITY

PROMPT_A = "Is this article biased? Answer BIASED or NEUTRAL only."
PROMPT_B = "Does this article show political bias in its language or framing? Answer BIASED or NEUTRAL only."
PROMPT_C = "As a neutral fact-checker, evaluate if this text presents information fairly. Answer BIASED or NEUTRAL only."

def run_prompt_sensitivity(limit=5):
    """
    EXPERIMENT 3: PROMPT SENSITIVITY ANALYSIS
    Send the same article to the same model (8B) with 3 different prompts.
    Research Question: Does rephrasing the question change the AI's verdict?
    If yes — the AI is sensitive to prompt wording, showing unreliability.
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, outlet, lean, title, content 
        FROM articles 
        WHERE prompt_a_label IS NULL AND label_8b IS NOT NULL
        LIMIT ?
    """, (limit,))
    articles = cursor.fetchall()

    if not articles:
        print(" All articles already processed for prompt sensitivity.")
        conn.close()
        return

    print(f"\n Running Prompt Sensitivity on {len(articles)} articles...\n")

    for row_id, outlet, lean, title, content in articles:
        snippet = content[:SNIPPET_LEN]

        print(f"  Testing: [{outlet}] {title[:50]}...")

        label_a = extract_label(ask_model(MODEL_8B, PROMPT_A, snippet))
        label_b = extract_label(ask_model(MODEL_8B, PROMPT_B, snippet))
        label_c = extract_label(ask_model(MODEL_8B, PROMPT_C, snippet))

        # Count how many prompts gave different results
        labels = [label_a, label_b, label_c]
        unique = len(set(labels))
        stable = "STABLE" if unique == 1 else "UNSTABLE"

        print(f"    A: {label_a} | B: {label_b} | C: {label_c} → {stable}")

        cursor.execute("""
            UPDATE articles
            SET prompt_a_label = ?, prompt_b_label = ?, prompt_c_label = ?
            WHERE id = ?
        """, (label_a, label_b, label_c, row_id))
        conn.commit()

    conn.close()
    print("\n Prompt Sensitivity analysis complete.")


# EXPERIMENT 4 — POLITICAL SYMMETRY

def run_political_symmetry():
    # Comparing how the AI treats left-leaning vs right-leaning outlets
    # This directly tests if the AI itself has a political bias
    """
    EXPERIMENT 4: POLITICAL SYMMETRY TEST
    Research Question: Does the AI label Left-leaning and Right-leaning 
    articles as BIASED at the same rate?
    
    If AI labels more Right articles as BIASED → AI has Left lean
    If AI labels more Left articles as BIASED  → AI has Right lean
    If rates are similar                        → AI is politically symmetric
    
    This directly answers the professor's question about bias IN the AI.
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lean, label_8b, COUNT(*) as count
        FROM articles
        WHERE label_8b IS NOT NULL AND lean != 'Center'
        GROUP BY lean, label_8b
    """)
    rows = cursor.fetchall()
    conn.close()

    results = {"Left": {"BIASED": 0, "NEUTRAL": 0}, "Right": {"BIASED": 0, "NEUTRAL": 0}}

    for lean, label, count in rows:
        if lean in results and label in results[lean]:
            results[lean][label] = count

    return results


# CONVERGENCE SCORE

def calculate_convergence(outlet_a="CNN", outlet_b="Fox News"):
    """
    Calculate semantic similarity between two outlets on recent articles.
    Uses cosine similarity on sentence embeddings.
    Score near 1.0 = outlets using similar language (high convergence)
    Score near 0.0 = outlets telling very different stories (polarization)
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT content FROM articles 
        WHERE outlet = ? 
        ORDER BY id DESC LIMIT 3
    """, (outlet_a,))
    arts_a = cursor.fetchall()

    cursor.execute("""
        SELECT content FROM articles 
        WHERE outlet = ? 
        ORDER BY id DESC LIMIT 3
    """, (outlet_b,))
    arts_b = cursor.fetchall()

    conn.close()

    if not arts_a or not arts_b:
        return None

    text_a = " ".join([r[0] for r in arts_a])[:2000]
    text_b = " ".join([r[0] for r in arts_b])[:2000]

    emb_a = embed_model.encode(text_a, convert_to_tensor=True)
    emb_b = embed_model.encode(text_b, convert_to_tensor=True)

    score = float(util.cos_sim(emb_a, emb_b)[0][0])
    return round(score, 3)


# SUMMARY STATISTICS

def get_audit_summary():
    """Return summary statistics for dashboard display."""
    conn   = get_db_connection()
    cursor = conn.cursor()

    # Overall agreement rate
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN label_8b = label_3b THEN 1 ELSE 0 END) as agreed
        FROM articles
        WHERE label_8b IS NOT NULL AND label_3b IS NOT NULL
    """)
    row = cursor.fetchone()
    total, agreed = row if row else (0, 0)

    # Prompt stability rate
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN prompt_a_label = prompt_b_label 
                        AND prompt_b_label = prompt_c_label 
                        THEN 1 ELSE 0 END) as stable
        FROM articles
        WHERE prompt_a_label IS NOT NULL
    """)
    row2 = cursor.fetchone()
    p_total, p_stable = row2 if row2 else (0, 0)

    # Bias rate by outlet
    cursor.execute("""
        SELECT outlet, lean,
               COUNT(*) as total,
               SUM(CASE WHEN label_8b = 'BIASED' THEN 1 ELSE 0 END) as biased
        FROM articles
        WHERE label_8b IS NOT NULL
        GROUP BY outlet, lean
    """)
    outlet_stats = cursor.fetchall()

    conn.close()

    agreement_rate = (agreed / total * 100) if total > 0 else 0
    stability_rate = (p_stable / p_total * 100) if p_total > 0 else 0

    return {
        "total_audited":   total,
        "agreement_rate":  round(agreement_rate, 1),
        "stability_rate":  round(stability_rate, 1),
        "outlet_stats":    outlet_stats
    }


# MAIN — Run all experiments

if __name__ == "__main__":
    print("=" * 60)
    print("  MEDIA BIAS AI AUDITOR — Experiment Pipeline")
    print("=" * 60)

    print("\n[1/3] Running Dual-Model Audit...")
    run_dual_model_audit(limit=10)

    print("\n[2/3] Running Prompt Sensitivity Analysis...")
    run_prompt_sensitivity(limit=10)

    print("\n[3/3] Running Political Symmetry Check...")
    sym = run_political_symmetry()
    print(f"  Left  → BIASED: {sym['Left']['BIASED']}  NEUTRAL: {sym['Left']['NEUTRAL']}")
    print(f"  Right → BIASED: {sym['Right']['BIASED']}  NEUTRAL: {sym['Right']['NEUTRAL']}")

    print("\n Summary Statistics:")
    summary = get_audit_summary()
    print(f"  Total articles audited : {summary['total_audited']}")
    print(f"  Model agreement rate   : {summary['agreement_rate']}%")
    print(f"  Prompt stability rate  : {summary['stability_rate']}%")

    print("\n All experiments complete.")