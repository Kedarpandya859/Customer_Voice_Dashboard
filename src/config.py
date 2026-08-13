import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TARGET_APP_ID = os.getenv("TARGET_APP_ID", "com.meesho.supply")
TARGET_COMPANY_NAME = os.getenv("TARGET_COMPANY_NAME", "Meesho")

if not DATABASE_URL:
    raise EnvironmentError(
        "DATABASE_URL not set. Copy .env.example to .env and fill it in "
        "(or set it as a GitHub Actions / Streamlit secret)."
    )

# Which LLM powers the tagging + opportunity steps.
# "gemini" = free (Google AI Studio, no card needed). "anthropic" = paid, needs credits.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")  # used for both bulk tagging and opportunity reasoning

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_FAST_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_STRONG_MODEL = "claude-sonnet-5"

# Default complaint taxonomy - tuned for e-commerce/marketplace apps.
# Edit this list if you point the pipeline at a different kind of product.
COMPLAINT_TAXONOMY = [
    "delivery_delay",
    "product_quality",
    "refund_issues",
    "seller_fraud",
    "app_bugs_ux",
    "customer_support",
    "pricing",
    "other",
]
