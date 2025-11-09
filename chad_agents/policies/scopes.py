"""Actor scope definitions and matching logic.

Deliverable #1: Actor scopes ✅
"""

ACTOR_SCOPES = {
    "admin": ["*"],
    "n8n_workflow_*": ["notion.*", "google.*", "github.read", "local.*"],
    "user_*": ["local.summarize", "github.read"],
}


def scope_matches(required: str, granted: str) -> bool:
    """
    Check if a granted scope matches a required scope.

    Supports:
    - Exact match: "runs:read" == "runs:read"
    - Wildcard: "runs:*" matches "runs:read"
    - Admin: "*" matches everything
    - Hierarchy: "runs:write" includes "runs:read" (write implies read)

    Args:
        required: Required scope pattern
        granted: Granted scope from token

    Returns:
        bool: True if granted scope satisfies required scope

    Example:
        scope_matches("runs:read", "runs:*")  # True
        scope_matches("runs:read", "*")  # True
        scope_matches("runs:write", "runs:read")  # False
    """
    # Admin wildcard grants everything
    if granted == "*":
        return True

    # Exact match
    if required == granted:
        return True

    # Wildcard matching: "notion.*" matches "notion.read"
    if granted.endswith(".*"):
        prefix = granted[:-2]  # Remove ".*"
        if required.startswith(prefix + ".") or required.startswith(prefix + ":"):
            return True

    if granted.endswith(":*"):
        prefix = granted[:-2]  # Remove ":*"
        if required.startswith(prefix + ".") or required.startswith(prefix + ":"):
            return True

    # Hierarchy: "runs:write" includes "runs:read"
    if ":" in required and ":" in granted:
        req_resource, req_action = required.rsplit(":", 1)
        grant_resource, grant_action = granted.rsplit(":", 1)

        if req_resource == grant_resource:
            # Write includes read
            if grant_action == "write" and req_action == "read":
                return True

    return False


def check_scopes(required_scopes: list[str], user_scopes: list[str]) -> bool:
    """
    Check if user has all required scopes.

    Args:
        required_scopes: List of required scopes
        user_scopes: List of scopes granted to user

    Returns:
        bool: True if all required scopes are satisfied

    Example:
        if not check_scopes(["notion.write"], user.scopes):
            raise HTTPException(403, "Insufficient permissions")
    """
    for required in required_scopes:
        # Check if any granted scope matches the required scope
        if not any(scope_matches(required, granted) for granted in user_scopes):
            return False

    return True
