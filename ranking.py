
from copy import deepcopy

def calculate_absolute_score(criteria, criterion_results):
    by_id = {int(x["criterion_id"]): x for x in criterion_results}
    total = 0.0
    for c in criteria:
        r = by_id[int(c["criterion_id"])]
        total += (float(r["score"]) / float(c["max_score"])) * float(c["weight"])
    return round(total, 4)

def add_peer_metrics(criteria, supplier_rows):
    # Benchmark is highest valid raw score observed for each criterion.
    benchmarks = {}
    for c in criteria:
        cid = int(c["criterion_id"])
        scores = [
            float(s["criterion_results_by_id"][cid]["score"])
            for s in supplier_rows
        ]
        benchmarks[cid] = max(scores) if scores else 0.0

    for s in supplier_rows:
        details = []
        weighted_relative = 0.0
        for c in criteria:
            cid = int(c["criterion_id"])
            score = float(s["criterion_results_by_id"][cid]["score"])
            max_score = float(c["max_score"])
            benchmark = benchmarks[cid]
            gap = round(score - benchmark, 4)
            relative = 100.0 if benchmark == 0 and score == 0 else (
                0.0 if benchmark == 0 else (score / benchmark) * 100.0
            )
            weighted_relative += (float(c["weight"]) / 100.0) * relative
            details.append({
                "criterion_id": cid,
                "criterion_name": c["name"],
                "score": score,
                "max_score": max_score,
                "benchmark": round(benchmark, 4),
                "gap": gap,
                "relative_performance_pct": round(relative, 4),
                "weight": float(c["weight"]),
                "evidence": s["criterion_results_by_id"][cid]["evidence"],
                "justification": s["criterion_results_by_id"][cid]["justification"],
            })
        s["criterion_details"] = details
        s["ppi"] = round(weighted_relative, 4)
        s["absolute_score"] = calculate_absolute_score(
            criteria, s["criterion_results"]
        )
    return supplier_rows

def rank_suppliers(criteria, supplier_rows):
    rows = add_peer_metrics(criteria, deepcopy(supplier_rows))
    # Mandatory deterministic order:
    # higher PPI -> earlier submission date -> higher experience -> supplier name ASC.
    rows.sort(key=lambda x: (
        -float(x["ppi"]),
        x["submission_date"],
        -float(x["experience_rating"]),
        x["supplier_name"].casefold(),
    ))
    for idx, row in enumerate(rows, start=1):
        row["final_rank"] = idx
        row["tie_break_explanation"] = (
            "Sorted by higher PPI, then earlier submission date, "
            "then higher historical experience rating, then supplier name ascending."
        )
    return rows
