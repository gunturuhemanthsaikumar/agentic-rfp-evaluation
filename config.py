import os
from pathlib import Path

APP_TITLE = "RFP Command Center"
DB_PATH = Path(os.getenv("RFP_DB_PATH", "data/rfp_evaluation.db"))
MODEL_NAME = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")
