import uuid
from typing import TypedDict, Callable, Optional

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


class RFPOrchestrator:
    """LangGraph controller. LLM reasoning and deterministic tools remain separated."""

    def __init__(self, api_key: str, model_name: str, progress_callback: Optional[Callable] = None):
        self.evaluation_agent = EvaluationAgent(api_key, model_name)
        self.criteria_tool = CriteriaTool()
        self.persistence = PersistenceTool()
        self.progress_callback = progress_callback or (lambda event: None)
        self.graph = self._build_graph()

    def _progress(self, phase, message, current=None, total=None, supplier=None):
        self.progress_callback({
            "phase": phase,
            "message": message,
            "current": current,
            "total": total,
            "supplier": supplier,
        })

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
        self._progress("criteria", "Loading active evaluation criteria from SQLite…")
        criteria = self.criteria_tool.load_active()
        self._progress("criteria", f"Loaded {len(criteria)} active criteria (weights = 100%).")
        return {"criteria": criteria}

    def extract_documents(self, state):
        total = len(state["pdf_files"])
        docs = {}
        for i, (name, path) in enumerate(state["pdf_files"].items(), 1):
            self._progress("documents", f"Extracting {name} ({i}/{total})…", i, total)
            docs[name] = extract_pdf_document(path)
        self._progress("documents", f"Extracted {total} supplier PDF(s).", total, total)
        return {"documents": docs}

    def evaluate_suppliers(self, state):
        results = {}
        total = len(state["documents"])
        for i, (file_name, document) in enumerate(state["documents"].items(), 1):
            meta = state["supplier_metadata"][file_name]
            supplier = meta["supplier_name"]
            self._progress("llm", f"Calling real Cohere Evaluation Agent for {supplier} ({i}/{total})…", i - 1, total, supplier)
            results[supplier] = self.evaluation_agent.evaluate(
                supplier, document["text"], state["criteria"]
            )
            self._progress("llm", f"Cohere evaluation completed for {supplier}.", i, total, supplier)
        return {"llm_results": results}

    def validate_outputs(self, state):
        validated, warnings = {}, list(state.get("warnings", []))
        self._progress("validation", "Validating and normalizing structured LLM outputs…")
        for supplier, raw in state["llm_results"].items():
            item = validate_and_normalize(raw, supplier, state["criteria"])
            validated[supplier] = item
            warnings.extend(f"{supplier}: {w}" for w in item["warnings"])
        self._progress("validation", f"Validation completed; {len(warnings)} warning(s) recorded.")
        return {"validated_results": validated, "warnings": warnings}

    def calculate_scores(self, state):
        scored = {}
        self._progress("scoring", "Calculating deterministic weighted scores…")
        for supplier, result in state["validated_results"].items():
            absolute, rows = calculate_absolute_score(result, state["criteria"])
            meta = next(v for v in state["supplier_metadata"].values() if v["supplier_name"] == supplier)
            scored[supplier] = {
                "supplier_name": supplier,
                "submission_date": meta["submission_date"],
                "experience_rating": float(meta["experience_rating"]),
                "absolute_score": absolute,
                "criteria": rows,
                "risks": result["risks"],
                "overall_summary": result["overall_summary"],
                "warnings": result["warnings"],
            }
        self._progress("scoring", "Weighted scores calculated by deterministic Python — not the LLM.")
        return {"scored_results": scored}

    def benchmark_and_rank(self, state):
        self._progress("ranking", "Calculating benchmarks, gaps, relative performance and PPI…")
        results = benchmark_and_rank(state["scored_results"], state["criteria"])
        self._progress("ranking", "Applying deterministic tie-break order and assigning final ranks…")
        return {"final_results": results}

    def persist_results(self, state):
        self._progress("persistence", "Persisting complete run and supplier results to SQLite…")
        run_id = state["rfp_run_id"]
        self.persistence.create(run_id, state["criteria"])
        self.persistence.complete(run_id, state.get("warnings", []), state["final_results"])
        self._progress("complete", f"Run {run_id} persisted successfully.")
        return {}

    def run(self, pdf_files, supplier_metadata):
        run_id = "RFP_RUN_" + uuid.uuid4().hex[:10].upper()
        self._progress("start", f"Starting agentic evaluation run {run_id}…")
        initial = {
            "rfp_run_id": run_id,
            "pdf_files": pdf_files,
            "supplier_metadata": supplier_metadata,
            "warnings": [],
        }
        try:
            return self.graph.invoke(initial)
        except Exception as exc:
            self._progress("error", f"Evaluation failed: {exc}")
            raise
