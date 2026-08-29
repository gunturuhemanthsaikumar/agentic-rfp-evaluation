from services.database_service import get_active_criteria, validate_active_weights

class CriteriaTool:
    """Database-backed criteria tool. The orchestrator uses this instead of querying SQLite directly."""
    def load_active(self):
        criteria = get_active_criteria()
        validate_active_weights(criteria)
        return criteria
