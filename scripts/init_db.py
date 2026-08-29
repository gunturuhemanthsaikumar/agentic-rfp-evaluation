import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.database_service import init_db, get_active_criteria

init_db(reset=False)
print("SQLite initialized.")
for c in get_active_criteria():
    print(f"{c['criterion_id']}: {c['name']} ({c['weight']}%)")
