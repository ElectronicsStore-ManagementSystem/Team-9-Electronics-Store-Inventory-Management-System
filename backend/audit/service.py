from datetime import datetime, timezone
def audit_delete(user_id, component_id):
    return {"action": "DELETE_COMPONENT", "user_id": user_id,
            "component_id": component_id,
            "timestamp": datetime.now(timezone.utc).isoformat()}
