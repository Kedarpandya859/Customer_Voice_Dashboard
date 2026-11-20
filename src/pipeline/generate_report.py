"""
Turns the latest opportunities into a shareable one-pager + a short
email-ready snippet - the artifact you'd attach to or quote in a cold email.

Run directly:
    python -m src.pipeline.generate_report
"""
import os
from datetime import datetime

from src.config import TARGETS
from src.db import get_connection, get_company_id, get_latest_opportunities

OUTPUT_DIR = "data/reports"


def build_markdown_report(company_name, opportunities):
    lines = [
        f"# Product Opportunities in {company_name} — User Feedback Analysis",
        "",
        f"_Generated {datetime.now().strftime('%d %b %Y')} from public app store review data._",
        "",
    ]
    for i, opp in enumerate(opportunities, start=1):
        lines += [
            f"## {i}. {opp['title']}",
            f"**Pattern:** {opp['complaint_category'].replace('_', ' ').title()} "
            f"({opp['review_count']} reviews, {opp['avg_rating']:.1f}\u2605 avg)",
            "",
            opp["rationale"],
            "",
        ]
    lines += [
        "---",
        "_Built with a scraper + LLM pipeline that mines public reviews for recurring "
        "complaint patterns and scores them by frequency and severity._",
    ]
    return "\n".join(lines)


def build_email_snippet(company_name, opportunities):
    if not opportunities:
        return ""
    top = opportunities[0]
    others = ", ".join(o["complaint_category"].replace("_", " ") for o in opportunities[1:3])
    snippet = (
        f"I built a small tool that mines {company_name}'s public app reviews for recurring "
        f"complaint patterns. The sharpest one: {top['title']} \u2014 {top['review_count']} reviews "
        f"cluster around {top['complaint_category'].replace('_', ' ')} "
        f"(avg {top['avg_rating']:.1f}\u2605)."
    )
    if others:
        snippet += f" A couple more patterns showed up around {others} too."
    return snippet


def run_for(conn, company_name):
    company_id = get_company_id(conn, company_name)
    if company_id is None:
        print(f"No company found named {company_name}.")
        return

    opportunities = get_latest_opportunities(conn, company_id, limit=5)
    if not opportunities:
        print(f"[{company_name}] No opportunities generated yet. Run `python -m src.pipeline.generate_opportunities` first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    slug = company_name.lower().replace(" ", "_")

    report_path = f"{OUTPUT_DIR}/{slug}_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(build_markdown_report(company_name, opportunities))

    snippet_path = f"{OUTPUT_DIR}/{slug}_email_snippet.txt"
    with open(snippet_path, "w", encoding="utf-8") as f:
        f.write(build_email_snippet(company_name, opportunities))

    print(f"Wrote {report_path}")
    print(f"Wrote {snippet_path}")


def run():
    conn = get_connection()
    try:
        for target in TARGETS:
            run_for(conn, target["name"])
    finally:
        conn.close()


if __name__ == "__main__":
    run()
