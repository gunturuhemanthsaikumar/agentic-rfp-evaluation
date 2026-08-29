import json
import os

import cohere
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def get_config(name, default=""):
    """
    Read configuration from Streamlit Secrets first.
    Fall back to environment variables for local development.
    """

    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass

    return os.getenv(name, default)


def build_prompt(criteria, supplier_name, document_text):
    """
    Build the evaluation prompt dynamically from the active criteria.
    """

    criteria_block = "\n".join(
        f'- ID {c["criterion_id"]}: {c["name"]} | '
        f'weight={c["weight"]}% | '
        f'max_score={c["max_score"]} | '
        f'inspect: {c["description"]}'
        for c in criteria
    )

    return f"""
You are the Evaluation Agent in an Agentic RFP Evaluation system.

Supplier: {supplier_name}

ACTIVE EVALUATION CRITERIA:
{criteria_block}

STRICT RULES:

1. Use ONLY evidence present in the supplier proposal below.

2. Return exactly ONE result for EVERY active criterion.

3. Score each criterion from 0 through its stated max_score.

4. Never invent facts, certifications, prices, timelines,
   customers, references, or capabilities.

5. If evidence is missing, score conservatively and explicitly
   state that the evidence is missing.

6. The evidence field must identify supporting proposal text
   and include the page marker when possible, such as [Page 2].

7. The justification must explain why the evidence supports
   the assigned score.

8. Do NOT calculate:
   - weighted scores
   - benchmarks
   - criterion gaps
   - relative percentages
   - PPI
   - tie-breaks
   - final rank

9. Python will perform all arithmetic and ranking after
   your response is validated.

10. Return JSON ONLY.
    Do not return Markdown.
    Do not use ```json fences.
    Do not add commentary outside the JSON.

REQUIRED JSON SHAPE:

{{
  "supplier_name": "{supplier_name}",
  "criteria": [
    {{
      "criterion_id": 1,
      "score": 8,
      "max_score": 10,
      "justification": "Evidence-grounded reason for the score.",
      "evidence": "[Page 2] Supporting proposal evidence."
    }}
  ],
  "risks": [
    "Evidence-grounded risk"
  ],
  "overall_summary": "Evidence-grounded overall summary."
}}

SUPPLIER PROPOSAL:

--- BEGIN DOCUMENT ---

{document_text}

--- END DOCUMENT ---
""".strip()


def _extract_text_from_response(response):
    """
    Extract the actual text/JSON response from Cohere.

    Cohere may return multiple content blocks, for example:
        thinking
        text

    We specifically select the text block.
    """

    try:
        content_blocks = response.message.content
    except AttributeError as exc:
        raise RuntimeError(
            f"Unexpected Cohere response format: {response}"
        ) from exc

    if not content_blocks:
        raise RuntimeError("Cohere returned an empty response.")

    # Prefer the explicit text content block.
    for block in content_blocks:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)

            if text:
                return text

    # Defensive fallback for SDK responses where type may
    # not be populated.
    for block in content_blocks:
        text = getattr(block, "text", None)

        if text:
            return text

    raise RuntimeError(
        f"Cohere response did not contain a text block: {response}"
    )


def _parse_json(content):
    """
    Convert the Cohere response into a Python dictionary.
    """

    if not content:
        raise RuntimeError("Cohere returned an empty response.")

    content = content.strip()

    # Defensive removal of accidental Markdown fences.
    if content.startswith("```"):
        content = content.removeprefix("```json")
        content = content.removeprefix("```")
        content = content.removesuffix("```")
        content = content.strip()

    try:
        result = json.loads(content)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Cohere returned invalid JSON.\n\n"
            f"Response:\n{content}"
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "Cohere response must be a JSON object."
        )

    return result


def evaluate_supplier(criteria, supplier_name, document_text):
    """
    Evaluate one supplier proposal using Cohere.

    The LLM evaluates proposal content only.

    Deterministic Python modules handle:
        - validation
        - weighted scoring
        - benchmarks
        - gaps
        - relative performance
        - PPI
        - tie-breaks
        - final ranking
    """

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    api_key = get_config("COHERE_API_KEY").strip()

    model = get_config(
        "COHERE_MODEL",
        "command-a-plus-05-2026",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "COHERE_API_KEY is not configured.\n\n"
            "For local development, add it to .env.\n"
            "For Streamlit Cloud, add it under App Settings → Secrets."
        )

    if not model:
        raise RuntimeError(
            "COHERE_MODEL is not configured."
        )

    if not document_text or not document_text.strip():
        raise RuntimeError(
            f"No proposal text was extracted for supplier "
            f"'{supplier_name}'."
        )

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_prompt(
        criteria=criteria,
        supplier_name=supplier_name,
        document_text=document_text,
    )

    # --------------------------------------------------------
    # JSON Schema
    # --------------------------------------------------------

    criterion_schema = {
        "type": "object",
        "properties": {
            "criterion_id": {
                "type": "integer"
            },
            "score": {
                "type": "number"
            },
            "max_score": {
                "type": "number"
            },
            "justification": {
                "type": "string"
            },
            "evidence": {
                "type": "string"
            },
        },
        "required": [
            "criterion_id",
            "score",
            "max_score",
            "justification",
            "evidence",
        ],
    }

    response_schema = {
        "type": "object",
        "properties": {
            "supplier_name": {
                "type": "string"
            },
            "criteria": {
                "type": "array",
                "items": criterion_schema,
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "string"
                },
            },
            "overall_summary": {
                "type": "string"
            },
        },
        "required": [
            "supplier_name",
            "criteria",
            "risks",
            "overall_summary",
        ],
    }

    # --------------------------------------------------------
    # Cohere client
    # --------------------------------------------------------

    try:
        client = cohere.ClientV2(
            api_key=api_key
        )

    except Exception as exc:
        raise RuntimeError(
            f"Failed to initialize Cohere client: {exc}"
        ) from exc

    # --------------------------------------------------------
    # Call Cohere
    # --------------------------------------------------------

    try:
        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an evidence-grounded procurement "
                        "evaluation agent. "
                        "Return only the JSON object requested by "
                        "the user."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format={
                "type": "json_object",
                "schema": response_schema,
            },
        )

    except Exception as exc:
        raise RuntimeError(
            f"Cohere API request failed: {exc}"
        ) from exc

    # --------------------------------------------------------
    # Extract response text
    # --------------------------------------------------------

    content = _extract_text_from_response(response)

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    return _parse_json(content)