"""
Scrapes Play Store reviews for every configured app (TARGET_APPS) and stores them.

Run directly:
    python -m src.scrapers.play_store
"""

from google_play_scraper import reviews, Sort

from src.config import TARGETS
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


def run_for(conn, target):
    if not target["app_id"]:
        print(f"Skipping {target['name']}: no Play Store app id configured.")
        return
    company_id = get_or_create_company(conn, target["name"], target["app_id"])

    raw_reviews = fetch_reviews(target["app_id"])
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
        f"Fetched {len(formatted)} reviews for {target['name']}, "
        f"{inserted} were new and got inserted."
    )


def run():
    conn = get_connection()
    try:
        init_db(conn)
        for target in TARGETS:
            run_for(conn, target)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
