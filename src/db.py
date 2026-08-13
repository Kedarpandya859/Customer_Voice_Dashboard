import psycopg2
from src.config import DATABASE_URL


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db(conn):
    """Create tables if they don't exist yet. Safe to run every time."""
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    play_store_app_id TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER REFERENCES companies(id),
                    platform TEXT NOT NULL,
                    external_review_id TEXT NOT NULL,
                    author TEXT,
                    rating INTEGER,
                    review_text TEXT,
                    review_date TIMESTAMP,
                    sentiment TEXT,
                    complaint_category TEXT,
                    scraped_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(platform, external_review_id)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER REFERENCES companies(id),
                    complaint_category TEXT,
                    review_count INTEGER,
                    avg_rating NUMERIC,
                    score NUMERIC,
                    title TEXT,
                    rationale TEXT,
                    generated_at TIMESTAMP DEFAULT NOW()
                );
            """)


def get_or_create_company(conn, name, play_store_app_id=None):
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM companies WHERE name = %s", (name,))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO companies (name, play_store_app_id) VALUES (%s, %s) RETURNING id",
                (name, play_store_app_id),
            )
            return cur.fetchone()[0]


def get_company_id(conn, name):
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM companies WHERE name = %s", (name,))
            row = cur.fetchone()
            return row[0] if row else None


def upsert_reviews(conn, company_id, platform, reviews_list):
    """Insert reviews, skipping ones already stored (same platform + review id)."""
    inserted = 0
    with conn:
        with conn.cursor() as cur:
            for r in reviews_list:
                cur.execute(
                    """
                    INSERT INTO reviews
                        (company_id, platform, external_review_id, author, rating, review_text, review_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (platform, external_review_id) DO NOTHING
                    """,
                    (
                        company_id,
                        platform,
                        r["external_review_id"],
                        r["author"],
                        r["rating"],
                        r["review_text"],
                        r["review_date"],
                    ),
                )
                inserted += cur.rowcount
    return inserted


def get_untagged_reviews(conn, company_id, limit=50):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, review_text, rating FROM reviews
                WHERE company_id = %s AND sentiment IS NULL
                  AND review_text IS NOT NULL AND review_text != ''
                LIMIT %s
                """,
                (company_id, limit),
            )
            return cur.fetchall()


def update_review_tags(conn, tagged):
    """tagged: list of dicts with id, sentiment, complaint_category"""
    with conn:
        with conn.cursor() as cur:
            for t in tagged:
                cur.execute(
                    "UPDATE reviews SET sentiment = %s, complaint_category = %s WHERE id = %s",
                    (t["sentiment"], t["complaint_category"], t["id"]),
                )


def get_category_stats(conn, company_id):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT complaint_category, COUNT(*) AS review_count, AVG(rating) AS avg_rating
                FROM reviews
                WHERE company_id = %s AND complaint_category IS NOT NULL
                GROUP BY complaint_category
                ORDER BY review_count DESC
                """,
                (company_id,),
            )
            cols = ["complaint_category", "review_count", "avg_rating"]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_sample_reviews_for_category(conn, company_id, category, limit=8):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_text FROM reviews
                WHERE company_id = %s AND complaint_category = %s
                ORDER BY RANDOM()
                LIMIT %s
                """,
                (company_id, category, limit),
            )
            return [row[0] for row in cur.fetchall()]


def insert_opportunity(conn, company_id, category, review_count, avg_rating, score, title, rationale):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO opportunities
                    (company_id, complaint_category, review_count, avg_rating, score, title, rationale)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (company_id, category, review_count, avg_rating, score, title, rationale),
            )


def get_latest_opportunities(conn, company_id, limit=8):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT complaint_category, review_count, avg_rating, score, title, rationale, generated_at
                FROM opportunities
                WHERE company_id = %s
                ORDER BY generated_at DESC, score DESC
                LIMIT %s
                """,
                (company_id, limit),
            )
            cols = ["complaint_category", "review_count", "avg_rating", "score", "title", "rationale", "generated_at"]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
