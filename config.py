import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "RFP Command Center"


def _secret(name: str, default=None):
    """Read Streamlit Cloud secrets first, then environment/.env."""
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value not in (None, ""):
            return value
    except Exception:
        pass
    return os.getenv(name, default)


COHERE_API_KEY = _secret("COHERE_API_KEY")
COHERE_MODEL = _secret("COHERE_MODEL", "command-a-plus-05-2026")
RFP_DB_PATH = Path(_secret("RFP_DB_PATH", "data/rfp_evaluation.db"))
LLM_TEMPERATURE = float(_secret("LLM_TEMPERATURE", "0"))
LLM_SEED = int(_secret("LLM_SEED", "42"))
LLM_TIMEOUT_SECONDS = int(_secret("LLM_TIMEOUT_SECONDS", "180"))


def validate_llm_config():
    if not COHERE_API_KEY:
        raise ValueError(
            "COHERE_API_KEY is not configured. Add it to .env locally "
            "or Streamlit Cloud → Settings → Secrets."
        )

# Backward-compatible aliases for modules that use the original notebook naming.
DB_PATH = RFP_DB_PATH
MODEL_NAME = COHERE_MODEL
