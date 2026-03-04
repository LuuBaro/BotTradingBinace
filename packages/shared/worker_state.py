"""
Shared worker state for pause/resume functionality
"""

# Global state for worker control
worker_state = {
    "is_paused": False,
    "pause_reason": None,
    "paused_at": None,
}
