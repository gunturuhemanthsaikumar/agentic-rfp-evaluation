import json
import cohere
from config import LLM_SEED, LLM_TEMPERATURE, LLM_TIMEOUT_SECONDS


def build_evaluation_prompt(supplier_name, proposal_text, criteria):
    criterion_block = "\n".join(
        f"- ID {c['criterion_id']}: {c['name']} | Weight {c['weight']}% | Inspect: {c['description']} | Max score {c['max_score']}"
        for c in criteria
    )
    return f"""You are a strict procurement proposal evaluator. Evaluate ONE supplier using ONLY the supplied proposal.

SUPPLIER: {supplier_name}

ACTIVE EVALUATION CRITERIA:
{criterion_block}

SUPPLIER PROPOSAL:
--- BEGIN PROPOSAL ---
{proposal_text}
--- END PROPOSAL ---

Return exactly one result for every active criterion. Score each criterion from 0 to its configured maximum.
Use only evidence present in the proposal. Do not infer missing certifications, capabilities, references, pricing,
timelines, integrations, SLAs, or experience. Missing/vague information should reduce the relevant score.
Evidence must be a short verbatim or highly faithful excerpt and include the proposal page number.
If evidence is absent, use 'No explicit evidence provided' and evidence_page=0.
Do NOT calculate weighted scores, benchmarks, PPI, tie-breaks or ranks. Return JSON only."""

EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "supplier_name": {"type": "string"},
        "criteria": {"type": "array", "items": {"type": "object", "properties": {
            "criterion_id": {"type": "integer"}, "score": {"type": "number"}, "max_score": {"type": "number"},
            "justification": {"type": "string"}, "evidence": {"type": "string"}, "evidence_page": {"type": "integer"}
        }, "required": ["criterion_id", "score", "max_score", "justification", "evidence", "evidence_page"]}},
        "risks": {"type": "array", "items": {"type": "string"}}, "overall_summary": {"type": "string"}
    }, "required": ["supplier_name", "criteria", "risks", "overall_summary"]
}

class EvaluationAgent:
    """LLM-only responsibility: judge proposal content and return structured evidence."""
    def __init__(self, api_key: str, model_name: str):
        self.client = cohere.ClientV2(api_key=api_key, timeout=LLM_TIMEOUT_SECONDS)
        self.model_name = model_name

    def evaluate(self, supplier_name, proposal_text, criteria):
        response = self.client.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "Return only the requested JSON object."},
                {"role": "user", "content": build_evaluation_prompt(supplier_name, proposal_text, criteria)},
            ],
            response_format={"type": "json_object", "schema": EVALUATION_SCHEMA},
            temperature=LLM_TEMPERATURE,
            seed=LLM_SEED,
        )
        content = getattr(response.message, "content", None) or []

        text_parts = []

        for item in content:
            text = getattr(item, "text", None)

            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

        if not text_parts:
            item_types = [type(item).__name__ for item in content]

            raise ValueError(
                "Cohere returned no text content. "
                f"Content item types: {item_types}"
            )

        raw_text = "\n".join(text_parts)

        try:
            return json.loads(raw_text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Cohere returned text, but it was not valid JSON. "
                f"Response preview: {raw_text[:1000]}"
            ) from exc
