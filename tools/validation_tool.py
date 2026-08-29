def validate_and_normalize(llm_result, supplier_name, criteria):
    """Validation tool: repairs structure only; never invents substantive evidence or scores."""
    warnings = []
    criterion_by_id = {int(c["criterion_id"]): c for c in criteria}
    if llm_result.get("supplier_name") != supplier_name:
        warnings.append(f"Supplier name mismatch: expected '{supplier_name}', received '{llm_result.get('supplier_name')}'.")
    raw_items = llm_result.get("criteria", [])
    normalized = {}
    if not isinstance(raw_items, list):
        warnings.append("criteria was not an array; all active criteria normalized to zero.")
        raw_items = []
    for item in raw_items:
        try:
            cid = int(item.get("criterion_id"))
        except Exception:
            warnings.append("Ignored criterion with invalid criterion_id.")
            continue
        if cid not in criterion_by_id:
            warnings.append(f"Ignored unknown criterion_id={cid}.")
            continue
        if cid in normalized:
            warnings.append(f"Duplicate criterion_id={cid}; first valid result retained.")
            continue
        c = criterion_by_id[cid]
        max_score = float(c["max_score"])
        try:
            score = float(item.get("score"))
        except Exception:
            score = 0.0
            warnings.append(f"Criterion {cid}: malformed score normalized to 0.")
        if score < 0 or score > max_score:
            warnings.append(f"Criterion {cid}: score {score} outside [0, {max_score}], clipped.")
            score = max(0.0, min(score, max_score))
        justification = str(item.get("justification") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        if not justification:
            warnings.append(f"Criterion {cid}: missing justification.")
            justification = "No justification returned by the model."
        if not evidence:
            warnings.append(f"Criterion {cid}: missing evidence.")
            evidence = "No explicit evidence provided."
        try:
            evidence_page = int(item.get("evidence_page", 0))
        except Exception:
            evidence_page = 0
            warnings.append(f"Criterion {cid}: invalid evidence_page normalized to 0.")
        normalized[cid] = {"criterion_id": cid, "score": score, "max_score": max_score,
                           "justification": justification, "evidence": evidence, "evidence_page": evidence_page}
    for cid, c in criterion_by_id.items():
        if cid not in normalized:
            warnings.append(f"Missing criterion_id={cid} ({c['name']}); normalized to score 0.")
            normalized[cid] = {"criterion_id": cid, "score": 0.0, "max_score": float(c["max_score"]),
                               "justification": "No criterion result was returned by the model.",
                               "evidence": "No explicit evidence provided.", "evidence_page": 0}
    return {"supplier_name": supplier_name, "criteria": [normalized[cid] for cid in sorted(normalized)],
            "risks": [str(x) for x in llm_result.get("risks", [])],
            "overall_summary": str(llm_result.get("overall_summary", "")).strip(), "warnings": warnings}
