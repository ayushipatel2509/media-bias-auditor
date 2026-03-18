# Media Bias AI Auditor

This project investigates whether Large Language Models (LLMs) exhibit political bias when tasked with detecting bias in news articles. By scraping real-time articles from politically diverse news outlets and running controlled experiments, this application evaluates the objectivity, consistency, and resilience of AI models (specifically Llama3 8B and Llama3.2 3B).

## Features & Methodology

The application employs a multi-tiered approach built around 4 core experiments:

1. **Model Audit (Experiments 1 & 2)**: Compares the bias verdicts of different models (Llama3 8B vs. Llama3.2 3B) on identical articles to see if bias detection is subjective and model-dependent.
2. **Prompt Sensitivity (Experiment 3)**: Tests each article with differently worded prompts to determine if the AI's verdict changes based on the framing of the question.
3. **Political Symmetry (Experiment 4)**: Compares AI bias detection rates across left-leaning and right-leaning outlets to reveal any inherent political bias in the model itself.
4. **Live Article Analyzer**: Allows you to paste any news article or URL and receive an instant bias analysis, reasoning, and database comparison in real-time.

## Technology Stack

- **Frontend**: [Streamlit](https://streamlit.io/) for the interactive dashboard and data visualization.
- **Backend & Data**: Python, SQLite (`data/news_vault.db`), Pandas.
- **Scraping**: `feedparser`, `newspaper3k`, `lxml-html-clean`.
- **AI/ML**: `ollama`, `sentence-transformers` for running local models and calculating semantic similarities.
- **Charts**: `plotly` for interactive graphs and gauges.

## Installation & Setup

### Prerequisites
1. **Python 3.8+**
2. **Ollama**: Ensure you have [Ollama](https://ollama.com/) installed and running on your system, and have pulled the necessary Llama models (`llama3` or models corresponding to 8B/3B parameters).

### Quickstart

1. Clone or download this repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```

## Usage

Once the application is running in your browser:

1. **Step 1 — Scrape Latest News**: Navigate to the main dashboard and run the scraper. This fetches the latest news articles from various RSS feeds and stores them in the local SQLite database.
2. **Step 2 — Run AI Experiments**: Trigger the AI analyzer to evaluate the scraped articles using local LLMs.
3. **Explore Results**: Use the sidebar to navigate through the detailed analysis pages (AI Audit, Prompt Sensitivity, Political Symmetry, and the Live Analyzer).

## Author
Ayushi Patel  
MS Computer Science · Montclair State University · Spring 2026
