import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ranking import rank_suppliers
from validation import validate_and_normalize

CRITERIA = [
    {"criterion_id": 1, "name": "Technical Capability", "weight": 30, "max_score": 10},
    {"criterion_id": 2, "name": "Implementation Plan", "weight": 20, "max_score": 10},
    {"criterion_id": 3, "name": "Commercial Value", "weight": 20, "max_score": 10},
    {"criterion_id": 4, "name": "Security & Compliance", "weight": 20, "max_score": 10},
    {"criterion_id": 5, "name": "Support & Experience", "weight": 10, "max_score": 10},
]

def supplier(name, dt, exp, scores):
    items = [{"criterion_id": i+1, "score": s, "max_score": 10, "evidence": "[Page 1] evidence", "justification": "evidence"} for i, s in enumerate(scores)]
    return {"supplier_name": name, "submission_date": dt, "experience_rating": exp, "criterion_results": items, "criterion_results_by_id": {x["criterion_id"]: x for x in items}}

def test_validation_handles_missing_and_out_of_range():
    normalized, warnings = validate_and_normalize({"supplier_name": "X", "criteria": [{"criterion_id": 1, "score": 99}]}, CRITERIA)
    assert normalized["criteria"][0]["score"] == 10
    assert len(normalized["criteria"]) == 5
    assert any("outside" in w for w in warnings)
    assert any("Missing criterion" in w for w in warnings)

def test_tie_break_order():
    ranked = rank_suppliers(CRITERIA, [supplier("Zulu", "2026-08-02", 9, [8]*5), supplier("Alpha", "2026-08-01", 5, [8]*5), supplier("Beta", "2026-08-01", 9, [8]*5)])
    assert [r["supplier_name"] for r in ranked] == ["Beta", "Alpha", "Zulu"]
    assert [r["final_rank"] for r in ranked] == [1, 2, 3]

def test_benchmark_leader_ppi_is_100():
    ranked = rank_suppliers(CRITERIA, [supplier("A", "2026-08-01", 5, [9]*5), supplier("B", "2026-08-02", 5, [8]*5)])
    assert ranked[0]["ppi"] == 100.0
