def calculate_absolute_score(validated_result, criteria):
    criterion_map = {int(c["criterion_id"]): c for c in criteria}
    rows, absolute_score = [], 0.0
    for item in validated_result["criteria"]:
        c = criterion_map[int(item["criterion_id"])]
        contribution = (float(item["score"]) / float(c["max_score"])) * float(c["weight"])
        absolute_score += contribution
        rows.append({**item, "criterion_name": c["name"], "weight": float(c["weight"]),
                     "weighted_contribution": contribution})
    return absolute_score, rows
