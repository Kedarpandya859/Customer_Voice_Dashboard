"""
Scores tagged complaint categories and generates product-opportunity hypotheses.
Runs on Gemini's free tier by default (see LLM_PROVIDER in .env).

Run directly:
    python -m src.pipeline.generate_opportunities
"""
import time

from src.config import TARGETS
from src.db import (
    get_connection,
    get_company_id,
    get_category_stats,
    get_sample_reviews_for_category,
    insert_opportunity,
)
from src.llm_client import call_llm

TOP_N_CATEGORIES = 5
SLEEP_BETWEEN_CALLS = 4  # keeps well within free-tier requests-per-minute limits


def score_category(stat, max_count):
    """Simple frequency x severity score, 0-100."""
    frequency_score = (stat["review_count"] / max_count) * 100 if max_count else 0
    avg_rating = float(stat["avg_rating"] or 3)  # ratings run 1-5; lower = more severe
    severity_score = (5 - avg_rating) / 4 * 100
    return round(0.5 * frequency_score + 0.5 * severity_score, 1)


def generate_hypothesis(company_name, category, samples):
    joined_samples = "\n".join(f"- {s[:300]}" for s in samples)
    prompt = f"""You're a product strategist. Below are real user complaints about \
"{category}" for {company_name}, pulled from public app reviews.

Complaints:
{joined_samples}

Write a short product opportunity brief in this exact format, nothing else:
TITLE: <one line, a specific product/feature idea that addresses this gap>
RATIONALE: <2-3 sentences: what's the underlying pain point, and why is this a \
standalone-solvable opportunity rather than something only {company_name} itself could fix>
"""
    text = call_llm(prompt, tier="strong", max_tokens=400).strip()

    title, rationale = "", ""
    for line in text.splitlines():
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("RATIONALE:"):
            rationale = line.replace("RATIONALE:", "").strip()
    return title or text[:80], rationale or text


def run_for(conn, company_name):
    company_id = get_company_id(conn, company_name)
    if company_id is None:
        print(f"No company found named {company_name}. Run the scraper and tagger first.")
        return

    stats = get_category_stats(conn, company_id)
    stats = [s for s in stats if s["complaint_category"] not in (None, "other")]
    if not stats:
        print(f"[{company_name}] No tagged reviews yet. Run `python -m src.pipeline.tag_reviews` first.")
        return

    max_count = max(s["review_count"] for s in stats)
    for s in stats:
        s["score"] = score_category(s, max_count)
    stats.sort(key=lambda s: s["score"], reverse=True)

    for stat in stats[:TOP_N_CATEGORIES]:
        samples = get_sample_reviews_for_category(conn, company_id, stat["complaint_category"])
        if not samples:
            continue
        title, rationale = generate_hypothesis(company_name, stat["complaint_category"], samples)
        insert_opportunity(
            conn,
            company_id,
            stat["complaint_category"],
            stat["review_count"],
            float(stat["avg_rating"] or 0),
            stat["score"],
            title,
            rationale,
        )
        print(f"[{company_name}] [{stat['score']}] {stat['complaint_category']} -> {title}")
        time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"[{company_name}] Done generating opportunities.")


def run():
    conn = get_connection()
    try:
        for target in TARGETS:
            run_for(conn, target["name"])
    finally:
        conn.close()


if __name__ == "__main__":
    run()
