"""
Shared worker state for pause/resume functionality
"""

from typing import TypedDict


class WorkerState(TypedDict):
    is_paused: bool
    pause_reason: str | None
    paused_at: str | None


# Global state for worker control
worker_state: WorkerState = {
    "is_paused": False,
    "pause_reason": None,
    "paused_at": None,
}
