"""
Scrapes Play Store reviews for the configured app and stores them in Postgres.

Run directly:
    python -m src.scrapers.play_store
"""

from google_play_scraper import reviews, Sort

from src.config import TARGET_APP_ID, TARGET_COMPANY_NAME
from src.db import get_connection, init_db, get_or_create_company, upsert_reviews


def fetch_reviews(app_id, count=200, lang="en", country="in"):
    result, _ = reviews(
        app_id,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
        count=count,
    )
    return result


def run():
    conn = get_connection()
    try:
        init_db(conn)
        company_id = get_or_create_company(conn, TARGET_COMPANY_NAME, TARGET_APP_ID)

        raw_reviews = fetch_reviews(TARGET_APP_ID)
        formatted = [
            {
                "external_review_id": r["reviewId"],
                "author": r["userName"],
                "rating": r["score"],
                "review_text": r["content"],
                "review_date": r["at"],
            }
            for r in raw_reviews
        ]

        inserted = upsert_reviews(conn, company_id, "play_store", formatted)
        print(
            f"Fetched {len(formatted)} reviews for {TARGET_COMPANY_NAME}, "
            f"{inserted} were new and got inserted."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
