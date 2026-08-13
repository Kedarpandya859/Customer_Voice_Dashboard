"""
Full review opportunity dashboard - overview, complaint breakdown,
opportunity shortlist, and raw review drill-down.

Run locally:
    streamlit run dashboard/app.py
"""
import os
import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

st.set_page_config(page_title="Review Opportunity Dashboard", layout="wide")


@st.cache_data(ttl=600)
def load_companies():
    conn = psycopg2.connect(DATABASE_URL)
    df = pd.read_sql("SELECT id, name FROM companies ORDER BY name", conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def load_reviews(company_id):
    conn = psycopg2.connect(DATABASE_URL)
    df = pd.read_sql(
        """
        SELECT platform, rating, review_text, review_date, sentiment, complaint_category
        FROM reviews
        WHERE company_id = %(company_id)s
        ORDER BY review_date DESC
        """,
        conn,
        params={"company_id": company_id},
    )
    conn.close()
    return df


@st.cache_data(ttl=600)
def load_opportunities(company_id):
    conn = psycopg2.connect(DATABASE_URL)
    df = pd.read_sql(
        """
        SELECT complaint_category, review_count, avg_rating, score, title, rationale, generated_at
        FROM opportunities
        WHERE company_id = %(company_id)s
        ORDER BY score DESC
        """,
        conn,
        params={"company_id": company_id},
    )
    conn.close()
    return df


st.title("Review Opportunity Dashboard")

companies = load_companies()
if companies.empty:
    st.warning("No companies in the database yet. Run the scraper first: `python -m src.scrapers.play_store`")
    st.stop()

company_name = st.sidebar.selectbox("Company", companies["name"])
company_id = int(companies[companies["name"] == company_name]["id"].iloc[0])

reviews_df = load_reviews(company_id)
opportunities_df = load_opportunities(company_id)

tab_overview, tab_complaints, tab_opportunities, tab_raw = st.tabs(
    ["Overview", "Complaint Breakdown", "Opportunities", "Raw Reviews"]
)

with tab_overview:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total reviews", len(reviews_df))
    col2.metric("Avg rating", f"{reviews_df['rating'].mean():.2f}" if len(reviews_df) else "\u2014")
    tagged = int(reviews_df["sentiment"].notna().sum())
    col3.metric("Tagged", f"{tagged}/{len(reviews_df)}")

    if len(reviews_df):
        reviews_df["review_date"] = pd.to_datetime(reviews_df["review_date"])
        daily = reviews_df.set_index("review_date").resample("W")["rating"].mean()
        st.subheader("Average rating over time")
        st.line_chart(daily)

        if reviews_df["sentiment"].notna().any():
            st.subheader("Sentiment split")
            st.bar_chart(reviews_df["sentiment"].value_counts())
    else:
        st.info("No reviews yet.")

with tab_complaints:
    if reviews_df["complaint_category"].notna().any():
        counts = reviews_df["complaint_category"].value_counts()
        st.bar_chart(counts)
        counts_table = counts.reset_index()
        counts_table.columns = ["category", "count"]
        st.dataframe(counts_table, use_container_width=True
        )
    
    else:
        st.info("No reviews tagged yet. Run `python -m src.pipeline.tag_reviews`.")

with tab_opportunities:
    if opportunities_df.empty:
        st.info("No opportunities generated yet. Run `python -m src.pipeline.generate_opportunities`.")
    else:
        for _, opp in opportunities_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### {opp['title']}")
                st.caption(
                    f"{opp['complaint_category'].replace('_', ' ').title()} \u00b7 "
                    f"{opp['review_count']} reviews \u00b7 {opp['avg_rating']:.1f}\u2605 avg \u00b7 "
                    f"score {opp['score']:.0f}/100"
                )
                st.write(opp["rationale"])

with tab_raw:
    st.dataframe(reviews_df, use_container_width=True)
