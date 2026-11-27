"""Small data structures shared by the workflow and its adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    vault: Path
    transcript_folder: Path
    guide_folder: Path


@dataclass
class TranscriptSegment:
    start: int
    duration: int
    text: str

    @classmethod
    def from_dict(cls, value: dict) -> "TranscriptSegment":
        return cls(
            start=int(value["start"]),
            duration=int(value["duration"]),
            text=str(value.get("text", "")),
        )


@dataclass
class CaptureSession:
    pid: int
    title: str
    monitor: str
    audio_path: Path
    log_path: Path
    started_at: str
    capture_finished: bool = False
    segments: list[TranscriptSegment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict) -> "CaptureSession":
        return cls(
            pid=int(value["pid"]),
            title=str(value["title"]),
            monitor=str(value["monitor"]),
            audio_path=Path(value["audio_path"]),
            log_path=Path(value["log_path"]),
            started_at=str(value["started_at"]),
            capture_finished=bool(value.get("capture_finished", False)),
            segments=[TranscriptSegment.from_dict(item) for item in value.get("segments", [])],
        )

    def to_dict(self) -> dict:
        value = asdict(self)
        value["audio_path"] = str(self.audio_path)
        value["log_path"] = str(self.log_path)
        return value


@dataclass(frozen=True)
class WorkflowProgress:
    """Progress emitted by a long-running application workflow."""

    stage: str
    current: int = 0
    total: int = 0
    message: str = ""


@dataclass(frozen=True)
class CaptureStatus:
    """Current capture/transcription state, or an empty state when idle."""

    session: CaptureSession | None
    completed_chunks: int = 0
    total_chunks: int = 0


@dataclass(frozen=True)
class TranscriptionResult:
    note_path: Path
    completed_chunks: int
    monitor: str


@dataclass(frozen=True)
class GuideResult:
    note_path: Path
    model: str
    usage: dict[str, Any]
    transcript_characters: int
