
from typing import List
from pydantic import BaseModel, Field, ValidationError

class CriterionResult(BaseModel):
    criterion_id: int
    score: float
    max_score: float
    justification: str = ""
    evidence: str = ""

class EvaluationOutput(BaseModel):
    supplier_name: str
    criteria: List[CriterionResult] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    overall_summary: str = ""

def validate_and_normalize(raw, criteria):
    warnings = []
    expected = {int(c["criterion_id"]): c for c in criteria}

    if not isinstance(raw, dict):
        warnings.append("LLM output was not a JSON object; all criteria defaulted to 0.")
        raw = {}

    supplier_name = str(raw.get("supplier_name") or "Unknown Supplier").strip()
    raw_items = raw.get("criteria", [])
    if not isinstance(raw_items, list):
        warnings.append("criteria was not a list; all criteria defaulted to 0.")
        raw_items = []

    by_id = {}
    for item in raw_items:
        if not isinstance(item, dict):
            warnings.append("Ignored malformed criterion item.")
            continue
        try:
            cid = int(item.get("criterion_id"))
        except (TypeError, ValueError):
            warnings.append("Ignored criterion with invalid criterion_id.")
            continue
        if cid in by_id:
            warnings.append(f"Duplicate criterion_id {cid}; first valid occurrence retained.")
            continue
        by_id[cid] = item

    normalized = []
    for cid, c in expected.items():
        item = by_id.get(cid)
        if item is None:
            warnings.append(f"Missing criterion {cid} ({c['name']}); score set to 0.")
            normalized.append({
                "criterion_id": cid, "score": 0.0,
                "max_score": float(c["max_score"]),
                "justification": "No valid LLM result was returned.",
                "evidence": ""
            })
            continue

        try:
            score = float(item.get("score", 0))
        except (TypeError, ValueError):
            warnings.append(f"Criterion {cid} had a malformed score; set to 0.")
            score = 0.0

        max_score = float(c["max_score"])
        if score < 0 or score > max_score:
            warnings.append(
                f"Criterion {cid} score {score} was outside 0..{max_score}; clipped."
            )
            score = max(0.0, min(score, max_score))

        normalized.append({
            "criterion_id": cid,
            "score": score,
            "max_score": max_score,
            "justification": str(item.get("justification") or ""),
            "evidence": str(item.get("evidence") or ""),
        })

    unknown = sorted(set(by_id) - set(expected))
    if unknown:
        warnings.append(f"Ignored unknown criterion IDs: {unknown}.")

    risks = raw.get("risks", [])
    if not isinstance(risks, list):
        warnings.append("risks was not a list; replaced with empty list.")
        risks = []

    return {
        "supplier_name": supplier_name,
        "criteria": normalized,
        "risks": [str(x) for x in risks],
        "overall_summary": str(raw.get("overall_summary") or ""),
    }, warnings
