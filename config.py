import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "RFP Command Center"


def _secret(name: str, default=None):
    """
    Read configuration in this order:

    1. Streamlit Community Cloud Secrets
    2. Environment variables / local .env
    3. Default value
    """

    try:
        import streamlit as st

        if name in st.secrets:
            value = st.secrets[name]

            if value not in (None, ""):
                return value

    except Exception:
        pass

    return os.getenv(name, default)


# ============================================================
# COHERE / LLM CONFIGURATION
# ============================================================

COHERE_API_KEY = _secret("COHERE_API_KEY")

COHERE_MODEL = _secret(
    "COHERE_MODEL",
    "command-a-plus-05-2026"
)

LLM_TEMPERATURE = float(
    _secret("LLM_TEMPERATURE", "0")
)

LLM_SEED = int(
    _secret("LLM_SEED", "42")
)

LLM_TIMEOUT_SECONDS = int(
    _secret("LLM_TIMEOUT_SECONDS", "180")
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

RFP_DB_PATH = Path(
    _secret(
        "RFP_DB_PATH",
        "data/rfp_evaluation.db"
    )
)


# ============================================================
# VALIDATION
# ============================================================

def validate_llm_config():

    if not COHERE_API_KEY:
        raise ValueError(
            "COHERE_API_KEY is not configured. "
            "For local execution add it to .env. "
            "For Streamlit Cloud add it under "
            "Settings → Secrets."
        )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

DB_PATH = RFP_DB_PATH

MODEL_NAME = COHERE_MODEL