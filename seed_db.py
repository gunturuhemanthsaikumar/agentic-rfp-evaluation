from db import init_db, seed_criteria

init_db()
seed_criteria()
print("SQLite database initialized and evaluation criteria seeded.")
