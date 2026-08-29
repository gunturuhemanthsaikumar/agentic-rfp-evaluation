import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from tools.criteria_tool import CriteriaTool
from tools.document_tool import extract_pdf_document
from tools.validation_tool import validate_and_normalize
from tools.scoring_tool import calculate_absolute_score
from tools.ranking_tool import benchmark_and_rank
from tools.persistence_tool import PersistenceTool
from .evaluation_agent import EvaluationAgent

class RFPState(TypedDict, total=False):
    rfp_run_id: str
    pdf_files: dict
    supplier_metadata: dict
    criteria: list
    documents: dict
    llm_results: dict
    validated_results: dict
    scored_results: dict
    final_results: list
    warnings: list
    api_key: str
    model_name: str

class RFPOrchestrator:
    """Agentic orchestrator: coordinates agents/tools; never performs business-rule arithmetic itself."""
    def __init__(self, api_key, model_name):
        self.evaluation_agent = EvaluationAgent(api_key, model_name)
        self.criteria_tool = CriteriaTool()
        self.persistence = PersistenceTool()
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(RFPState)
        g.add_node("load_criteria", self.load_criteria)
        g.add_node("extract_documents", self.extract_documents)
        g.add_node("evaluate_suppliers", self.evaluate_suppliers)
        g.add_node("validate_outputs", self.validate_outputs)
        g.add_node("calculate_scores", self.calculate_scores)
        g.add_node("benchmark_and_rank", self.benchmark_and_rank)
        g.add_node("persist_results", self.persist_results)
        g.add_edge(START, "load_criteria")
        g.add_edge("load_criteria", "extract_documents")
        g.add_edge("extract_documents", "evaluate_suppliers")
        g.add_edge("evaluate_suppliers", "validate_outputs")
        g.add_edge("validate_outputs", "calculate_scores")
        g.add_edge("calculate_scores", "benchmark_and_rank")
        g.add_edge("benchmark_and_rank", "persist_results")
        g.add_edge("persist_results", END)
        return g.compile()

    def load_criteria(self, state):
        criteria = self.criteria_tool.load_active()
        return {"criteria": criteria}

    def extract_documents(self, state):
        return {"documents": {name: extract_pdf_document(path) for name, path in state["pdf_files"].items()}}

    def evaluate_suppliers(self, state):
        results = {}
        for file_name, document in state["documents"].items():
            meta = state["supplier_metadata"][file_name]
            supplier = meta["supplier_name"]
            results[supplier] = self.evaluation_agent.evaluate(supplier, document["text"], state["criteria"])
        return {"llm_results": results}

    def validate_outputs(self, state):
        validated, warnings = {}, list(state.get("warnings", []))
        for supplier, raw in state["llm_results"].items():
            item = validate_and_normalize(raw, supplier, state["criteria"])
            validated[supplier] = item
            warnings.extend(f"{supplier}: {w}" for w in item["warnings"])
        return {"validated_results": validated, "warnings": warnings}

    def calculate_scores(self, state):
        scored = {}
        for supplier, result in state["validated_results"].items():
            absolute, rows = calculate_absolute_score(result, state["criteria"])
            meta = state["supplier_metadata"][next(k for k,v in state["supplier_metadata"].items() if v["supplier_name"] == supplier)]
            scored[supplier] = {"supplier_name": supplier, "submission_date": meta["submission_date"],
                                "experience_rating": float(meta["experience_rating"]), "absolute_score": absolute,
                                "criteria": rows, "risks": result["risks"], "overall_summary": result["overall_summary"],
                                "warnings": result["warnings"]}
        return {"scored_results": scored}

    def benchmark_and_rank(self, state):
        return {"final_results": benchmark_and_rank(state["scored_results"], state["criteria"])}

    def persist_results(self, state):
        self.persistence.create(state["rfp_run_id"], state["criteria"])
        self.persistence.complete(state["rfp_run_id"], state.get("warnings", []), state["final_results"])
        return {}

    def run(self, pdf_files, supplier_metadata):
        run_id = "RFP_RUN_" + uuid.uuid4().hex[:10].upper()
        initial = {"rfp_run_id": run_id, "pdf_files": pdf_files, "supplier_metadata": supplier_metadata, "warnings": []}
        return self.graph.invoke(initial)
