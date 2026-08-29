from tools.validation_tool import validate_and_normalize
from tools.ranking_tool import benchmark_and_rank

CRITERIA=[
 {"criterion_id":1,"name":"A","description":"","weight":50,"max_score":10,"is_active":1},
 {"criterion_id":2,"name":"B","description":"","weight":50,"max_score":10,"is_active":1},
]

def test_validation_clips_and_fills():
    r=validate_and_normalize({"supplier_name":"S","criteria":[{"criterion_id":1,"score":15,"max_score":10,"justification":"","evidence":""}]},"S",CRITERIA)
    assert r["criteria"][0]["score"]==10
    assert r["criteria"][1]["score"]==0
    assert r["warnings"]

def test_ranking_is_deterministic():
    scored={
      "B":{"supplier_name":"B","submission_date":"2026-08-22","experience_rating":5,"absolute_score":50,"criteria":[{"criterion_id":1,"score":10,"weight":50},{"criterion_id":2,"score":8,"weight":50}]},
      "A":{"supplier_name":"A","submission_date":"2026-08-20","experience_rating":5,"absolute_score":50,"criteria":[{"criterion_id":1,"score":10,"weight":50},{"criterion_id":2,"score":8,"weight":50}]},
    }
    ranked=benchmark_and_rank(scored,CRITERIA)
    assert ranked[0]["supplier_name"]=="A"
    assert ranked[0]["final_rank"]==1
