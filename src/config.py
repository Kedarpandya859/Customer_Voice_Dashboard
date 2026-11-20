import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# Legacy single-app settings. Still honoured if TARGET_APPS isn't set.
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

# Complaint taxonomies per product domain. Each target app picks one.
# Add a new domain here if you point the pipeline at a different kind of product.
TAXONOMIES = {
    # e-commerce / marketplace apps (Meesho, Flipkart, ...)
    "ecommerce": [
        "delivery_delay",
        "product_quality",
        "refund_issues",
        "seller_fraud",
        "app_bugs_ux",
        "customer_support",
        "pricing",
        "other",
    ],
    # payments / fintech apps (Paytm, PhonePe, ...)
    "fintech": [
        "payment_failures",
        "refund_issues",
        "kyc_account_blocks",
        "fraud_security",
        "app_bugs_ux",
        "customer_support",
        "fees_charges",
        "other",
    ],
}

# Backwards-compatible alias: the e-commerce taxonomy.
COMPLAINT_TAXONOMY = TAXONOMIES["ecommerce"]

DEFAULT_TARGET_APPS = "Meesho|com.meesho.supply|ecommerce;Paytm|net.one97.paytm|fintech"


def _parse_targets(spec):
    """TARGET_APPS format: "Name|play.store.id|domain;Name2|id2|domain2".
    domain must be a key of TAXONOMIES (defaults to ecommerce)."""
    targets = []
    for chunk in spec.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in chunk.split("|")]
        name = parts[0]
        app_id = parts[1] if len(parts) > 1 and parts[1] else None
        domain = parts[2] if len(parts) > 2 and parts[2] else "ecommerce"
        if domain not in TAXONOMIES:
            raise ValueError(f"Unknown domain {domain!r} for {name} in TARGET_APPS. Use one of {list(TAXONOMIES)}.")
        targets.append({"name": name, "app_id": app_id, "domain": domain})
    return targets


_target_apps_env = os.getenv("TARGET_APPS")
if _target_apps_env:
    TARGETS = _parse_targets(_target_apps_env)
elif os.getenv("TARGET_APP_ID") or os.getenv("TARGET_COMPANY_NAME"):
    # Old single-app setup
    TARGETS = [{"name": TARGET_COMPANY_NAME, "app_id": TARGET_APP_ID, "domain": "ecommerce"}]
else:
    TARGETS = _parse_targets(DEFAULT_TARGET_APPS)


def taxonomy_for(target):
    return TAXONOMIES[target["domain"]]
