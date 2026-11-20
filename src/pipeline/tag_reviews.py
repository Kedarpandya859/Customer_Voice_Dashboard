"""
Tags un-tagged reviews with sentiment + complaint category using an LLM.
Runs on Gemini's free tier by default (see LLM_PROVIDER in .env).

Run directly:
    python -m src.pipeline.tag_reviews
"""
import json
import time

from src.config import TARGETS, taxonomy_for
from src.db import get_connection, get_company_id, get_untagged_reviews, update_review_tags
from src.llm_client import call_llm

BATCH_SIZE = 15
SLEEP_BETWEEN_BATCHES = 4  # keeps well within free-tier requests-per-minute limits


def build_prompt(batch, taxonomy):
    numbered = "\n".join(f"{i + 1}. (id={r[0]}, rating={r[2]}) {r[1][:500]}" for i, r in enumerate(batch))
    categories = ", ".join(taxonomy)
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


def _clean_tags(tags, batch, taxonomy):
    """Keep only well-formed tags for ids in this batch. Reviews the LLM
    skipped get tagged neutral/"other" so the loop can't spin on them forever."""
    by_id = {r[0] for r in batch}
    good = {}
    for t in tags if isinstance(tags, list) else []:
        try:
            rid = int(t["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if rid not in by_id:
            continue
        cat = t.get("complaint_category")
        sentiment = t.get("sentiment")
        good[rid] = {
            "id": rid,
            "sentiment": sentiment if sentiment in ("positive", "negative", "neutral") else "neutral",
            "complaint_category": cat if cat in taxonomy else "other",
        }
    for rid in by_id:
        good.setdefault(rid, {"id": rid, "sentiment": "neutral", "complaint_category": "other"})
    return list(good.values())


def tag_batch(batch, taxonomy):
    prompt = build_prompt(batch, taxonomy)
    text = call_llm(prompt, tier="fast", max_tokens=2000).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
        text = text.replace("json", "", 1).strip()
    return _clean_tags(json.loads(text), batch, taxonomy)


def run_for(conn, target):
    company_id = get_company_id(conn, target["name"])
    if company_id is None:
        print(f"No company found named {target['name']}. Run the scraper first.")
        return

    taxonomy = taxonomy_for(target)
    total_tagged = 0
    while True:
        batch = get_untagged_reviews(conn, company_id, limit=BATCH_SIZE)
        if not batch:
            break
        try:
            tagged = tag_batch(batch, taxonomy)
            update_review_tags(conn, tagged)
            total_tagged += len(tagged)
            print(f"[{target['name']}] Tagged {len(tagged)} reviews (running total: {total_tagged})")
        except Exception as e:
            print(f"[{target['name']}] Stopping: batch failed to tag ({e}). Re-run to retry remaining reviews.")
            break
        time.sleep(SLEEP_BETWEEN_BATCHES)

    print(f"[{target['name']}] Done. Tagged {total_tagged} reviews total.")


def run():
    conn = get_connection()
    try:
        for target in TARGETS:
            run_for(conn, target)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
