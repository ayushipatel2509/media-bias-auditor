import feedparser
import sqlite3
import datetime
from newspaper import Article, Config

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'

config = Config()
config.browser_user_agent = USER_AGENT
config.request_timeout = 15

RSS_FEEDS = {
    "CNN":       {"url": "http://rss.cnn.com/rss/cnn_allpolitics.rss",        "lean": "Left"},
    "MSNBC":     {"url": "https://feeds.nbcnews.com/nbcnews/public/news",      "lean": "Left"},
    "HuffPost":  {"url": "https://www.huffpost.com/section/politics/feed",     "lean": "Left"},
    "Fox News":  {"url": "http://feeds.foxnews.com/foxnews/politics",          "lean": "Right"},
    "Breitbart": {"url": "http://feeds.feedburner.com/breitbart",              "lean": "Right"},
    "NY Post":   {"url": "https://nypost.com/feed/",                           "lean": "Right"},
    "Reuters":   {"url": "https://feeds.reuters.com/reuters/politicsNews",     "lean": "Center"},
    "NPR":       {"url": "https://feeds.npr.org/1014/rss.xml",                 "lean": "Center"},
}

DB_PATH = "data/news_vault.db"
ARTICLES_PER_OUTLET = 10

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            url             TEXT UNIQUE,
            outlet          TEXT,
            lean            TEXT,
            title           TEXT,
            content         TEXT,
            date            TEXT,
            label_8b        TEXT,
            label_3b        TEXT,
            reason_8b       TEXT,
            reason_3b       TEXT,
            prompt_a_label  TEXT,
            prompt_b_label  TEXT,
            prompt_c_label  TEXT,
            processed       INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print(" Database initialized successfully.")

def scrape_latest(articles_per_outlet=ARTICLES_PER_OUTLET):
    init_db()
    print(f"\n Starting news scrape ({articles_per_outlet} articles per outlet)...\n")
    total_saved = 0

    # Pulling directly from RSS feeds instead of scraping front pages
    # This is much faster and less likely to get blocked by bot protection
    for outlet, info in RSS_FEEDS.items():
        rss_url = info["url"]
        lean    = info["lean"]
        print(f" Scanning {outlet} ({lean})...")

        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                print(f"    No entries found for {outlet}")
                continue
        except Exception as e:
            print(f"   RSS error for {outlet}: {e}")
            continue

        saved_count = 0
        for entry in feed.entries:
            if saved_count >= articles_per_outlet:
                break
            try:
                # Using newspaper3k for actual article text extraction
                article = Article(entry.link, config=config)
                article.download()
                article.parse()
                
                # Skip video-only pages or stubs
                if not article.text or len(article.text) < 150:
                    continue
                conn   = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    INSERT OR IGNORE INTO articles
                        (url, outlet, lean, title, content, date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (entry.link, outlet, lean, article.title, article.text[:3000], now))
                if cursor.rowcount > 0:
                    saved_count += 1
                    total_saved += 1
                    print(f"   Saved: {article.title[:65]}...")
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"    Skipped: {e}")
                continue

        print(f"  → {saved_count} new articles saved from {outlet}\n")

    print(f" Scrape complete. Total new articles saved: {total_saved}")
    return total_saved

def get_article_count():
    try:
        conn  = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def get_article_counts_by_outlet():
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT outlet, lean, COUNT(*) as count
            FROM articles
            GROUP BY outlet, lean
            ORDER BY lean, outlet
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        return []

if __name__ == "__main__":
    scrape_latest()
    print("\n Current article counts by outlet:")
    for outlet, lean, count in get_article_counts_by_outlet():
        print(f"  {outlet:12} ({lean:6}) → {count} articles")