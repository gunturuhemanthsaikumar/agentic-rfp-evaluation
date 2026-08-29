from datetime import datetime
import uuid

from db import create_run, get_active_criteria, save_results, save_failed_run
from document_tool import extract_pdf_text
from evaluator import evaluate_supplier
from ranking import rank_suppliers
from validation import validate_and_normalize


def create_run_id():
    return "RFP-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()


def evaluate_batch(suppliers):
    criteria = get_active_criteria()
    if not criteria:
        raise ValueError("No active evaluation criteria found.")
    total_weight = round(sum(float(c["weight"]) for c in criteria), 6)
    if total_weight != 100.0:
        raise ValueError(f"Active criterion weights must total 100%; current total is {total_weight}%.")

    run_id = create_run_id()
    create_run(run_id)
    prepared = []
    warnings = []
    try:
        for supplier in suppliers:
            text = extract_pdf_text(supplier["pdf_bytes"])
            if not text:
                raise ValueError(f'No extractable text found in {supplier["file_name"]}.')
            raw = evaluate_supplier(criteria, supplier["supplier_name"], text)
            normalized, item_warnings = validate_and_normalize(raw, criteria)
            warnings.extend(f'{supplier["supplier_name"]}: {w}' for w in item_warnings)
            prepared.append({
                "supplier_name": supplier["supplier_name"],
                "submission_date": supplier["submission_date"],
                "experience_rating": float(supplier["experience_rating"]),
                "criterion_results": normalized["criteria"],
                "criterion_results_by_id": {int(x["criterion_id"]): x for x in normalized["criteria"]},
                "risks": normalized["risks"],
                "overall_summary": normalized["overall_summary"],
                "warnings": item_warnings,
                "source_file": supplier["file_name"],
            })
        ranked = rank_suppliers(criteria, prepared)
        for row in ranked:
            row["rfp_run_id"] = run_id
            row["batch_warnings"] = warnings
        save_results(run_id, ranked, "COMPLETED")
        return run_id, criteria, ranked, warnings
    except Exception:
        save_failed_run(run_id)
        raise
