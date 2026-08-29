TIE_BREAK_RULE = "Higher PPI -> earlier submission date -> higher historical experience rating -> supplier name ascending"

def benchmark_and_rank(scored_results, criteria):
    """Deterministic ranking tool. No LLM calls occur in this module."""
    benchmark_by_id = {}
    for c in criteria:
        cid = int(c["criterion_id"])
        scores = [float(i["score"]) for r in scored_results.values() for i in r["criteria"] if int(i["criterion_id"]) == cid]
        benchmark_by_id[cid] = max(scores) if scores else 0.0
    for result in scored_results.values():
        numerator = denominator = 0.0
        for item in result["criteria"]:
            benchmark = float(benchmark_by_id[int(item["criterion_id"])])
            score, weight = float(item["score"]), float(item["weight"])
            relative = 100.0 if benchmark == 0 and score == 0 else (0.0 if benchmark == 0 else (score / benchmark) * 100.0)
            item["benchmark"] = benchmark
            item["gap"] = score - benchmark
            item["relative_performance_pct"] = relative
            numerator += relative * weight
            denominator += weight
        result["ppi"] = numerator / denominator if denominator else 0.0
    ordered = sorted(scored_results.values(), key=lambda x: (-float(x["ppi"]), x["submission_date"], -float(x["experience_rating"]), x["supplier_name"].lower()))
    for rank, result in enumerate(ordered, start=1):
        result["final_rank"] = rank
        result["tie_break_rule"] = TIE_BREAK_RULE
    return ordered
