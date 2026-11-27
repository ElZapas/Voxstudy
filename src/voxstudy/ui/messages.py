"""Thread-safe events carrying workflow updates into the Textual UI."""

from __future__ import annotations

from textual.message import Message

from ..models import WorkflowProgress


class WorkflowProgressMessage(Message):
    def __init__(self, operation: str, progress: WorkflowProgress) -> None:
        super().__init__()
        self.operation = operation
        self.progress = progress


class WorkflowFinishedMessage(Message):
    def __init__(self, operation: str, result: object | None = None, error: str | None = None) -> None:
        super().__init__()
        self.operation = operation
        self.result = result
        self.error = error
