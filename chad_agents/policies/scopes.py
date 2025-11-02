"""Actor scope definitions.

Deliverable #1: Actor scopes ✅
"""

ACTOR_SCOPES = {
    "admin": ["*"],
    "n8n_workflow_*": ["notion.*", "google.*", "github.read", "local.*"],
    "user_*": ["local.summarize", "github.read"],
}
