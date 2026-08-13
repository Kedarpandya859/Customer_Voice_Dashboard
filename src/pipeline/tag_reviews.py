"""
Tags un-tagged reviews with sentiment + complaint category using an LLM.
Runs on Gemini's free tier by default (see LLM_PROVIDER in .env).

Run directly:
    python -m src.pipeline.tag_reviews
"""
import json
import time

from src.config import TARGET_COMPANY_NAME, COMPLAINT_TAXONOMY
from src.db import get_connection, get_company_id, get_untagged_reviews, update_review_tags
from src.llm_client import call_llm

BATCH_SIZE = 15
SLEEP_BETWEEN_BATCHES = 4  # keeps well within free-tier requests-per-minute limits


def build_prompt(batch):
    numbered = "\n".join(f"{i + 1}. (id={r[0]}, rating={r[2]}) {r[1][:500]}" for i, r in enumerate(batch))
    categories = ", ".join(COMPLAINT_TAXONOMY)
    return f"""You are tagging app store reviews for sentiment and complaint category.

Categories: {categories}

For each review below, return its sentiment (positive, negative, or neutral) and the
single best-fitting complaint category. If a review isn't a complaint, still pick the
closest category, or "other" if nothing fits.

Reviews:
{numbered}

Respond ONLY with a JSON array, no other text, in this exact format:
[{{"id": <review id>, "sentiment": "...", "complaint_category": "..."}}, ...]
"""


def tag_batch(batch):
    prompt = build_prompt(batch)
    text = call_llm(prompt, tier="fast", max_tokens=2000).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
        text = text.replace("json", "", 1).strip()
    return json.loads(text)


def run():
    conn = get_connection()
    try:
        company_id = get_company_id(conn, TARGET_COMPANY_NAME)
        if company_id is None:
            print(f"No company found named {TARGET_COMPANY_NAME}. Run the scraper first.")
            return

        total_tagged = 0
        while True:
            batch = get_untagged_reviews(conn, company_id, limit=BATCH_SIZE)
            if not batch:
                break
            try:
                tagged = tag_batch(batch)
                update_review_tags(conn, tagged)
                total_tagged += len(tagged)
                print(f"Tagged {len(tagged)} reviews (running total: {total_tagged})")
            except Exception as e:
                print(f"Stopping: batch failed to tag ({e}). Re-run to retry remaining reviews.")
                break
            time.sleep(SLEEP_BETWEEN_BATCHES)

        print(f"Done. Tagged {total_tagged} reviews total.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
