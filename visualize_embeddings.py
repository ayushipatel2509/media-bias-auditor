import sqlite3
import pandas as pd
import plotly.express as px
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
import numpy as np

# --- CONFIGURATION ---
DB_PATH = "data/news_vault.db"
MODEL_NAME = 'all-MiniLM-L6-v2'  # The model you are already using
MAX_ARTICLES = 150              # Limit how many dots to plot for clarity

print("1. Connecting to Database...")
try:
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT outlet, lean, title, content 
        FROM articles 
        WHERE content IS NOT NULL AND lean != 'Unknown'
        ORDER BY id DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(MAX_ARTICLES,))
    conn.close()
    
    if df.empty:
        print("Error: No articles found in the database. Run the scraper and analyzer first.")
        exit()
    print(f"   Found {len(df)} articles.")
    
except Exception as e:
    print(f"Database Error: {e}")
    exit()

# --- 1. GENERATE EMBEDDINGS ---
print(f"2. Loading {MODEL_NAME} model and generating embeddings...")
# Newspaper text is often long, we limit characters sent to the model for speed
model = SentenceTransformer(MODEL_NAME)
texts = df['content'].str[:2000].tolist()  # Clean content, max 2000 chars
embeddings = model.encode(texts, convert_to_tensor=False, show_progress_bar=True)

# Convert list of arrays to a single 2D NumPy array (shape: articles x 384)
X = np.array(embeddings)
print(f"   Generated {X.shape[1]}-dimensional embeddings for {X.shape[0]} articles.")

# --- 2. DIMENSIONAL REDUCTION (PCA) ---
print("3. Running PCA to reduce 384 dimensions to 2D...")
# PCA is a linear algebraic method to find the directions (axes) of maximum variance.
pca = PCA(n_components=2)
# The output component_2d is an array with shape (articles x 2)
components_2d = pca.fit_transform(X)

# Explain how much information we kept (useful for Master's presentation!)
variance_ratio = pca.explained_variance_ratio_
print(f"   PCA Complete. x-axis represents {variance_ratio[0]:.1%} variance.")
print(f"   PCA Complete. y-axis represents {variance_ratio[1]:.1%} variance.")

# --- 3. CREATE PLOTLY VISUALIZATION ---
print("4. Creating Plotly Visualization...")
# Add the 2D PCA results back to our main DataFrame
df['PCA_x'] = components_2d[:, 0]
df['PCA_y'] = components_2d[:, 1]

# Define a clean color map for the political leans
# Use blue for Left, red for Right, and green for Center
color_map = {
    "Left": "#3b82f6",     # Blue
    "Lean Left": "#60a5fa",# Lighter Blue
    "Center": "#22c55e",   # Green
    "Lean Right": "#f87171",# Lighter Red
    "Right": "#ef4444"     # Red
}

# Create the scatter plot
fig = px.scatter(
    df, 
    x='PCA_x', 
    y='PCA_y', 
    color='lean',
    color_discrete_map=color_map,
    symbol='lean',  # Add symbols for accessibility and clarity
    hover_name='title',  # What to show when hovering over a dot
    hover_data=['outlet'], 
    title=f"Visualizing Media Bias Vector Space (PCA reduction of {MODEL_NAME})",
    labels={"PCA_x": "PCA Axis 1 (Semantic Variance)", "PCA_y": "PCA Axis 2 (Stylistic Variance)"},
    opacity=0.8,
    template="plotly_dark"  # Use dark mode to match your dashboard style
)

# Customize markers and layout for better visual impact
fig.update_traces(marker=dict(size=12, line=dict(width=1, color='white')))
fig.update_layout(
    font=dict(family="Inter", size=14),
    title_font_size=22,
    legend=dict(title=dict(text="Political Lean"), font=dict(size=14))
)

# Show the plot in your browser
print("5. Plot complete. Opening visualization in browser.")
fig.show()

# Optional: Save the plot as a static image (requires extra libraries)
# print("   Saving static image as embeddings_map.png")
# fig.write_image("embeddings_map.png", width=1200, height=800)