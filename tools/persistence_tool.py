from services.database_service import create_run, complete_run, fail_run, persist_supplier_results

class PersistenceTool:
    """Persistence tool isolated from orchestration and UI."""
    def create(self, run_id, criteria):
        create_run(run_id, criteria)
    def complete(self, run_id, warnings, results):
        persist_supplier_results(run_id, results)
        complete_run(run_id, warnings)
    def fail(self, run_id, warnings):
        fail_run(run_id, warnings)
