"""Dashboard query combining app configuration, capture state, and recent notes."""

from __future__ import annotations

from dataclasses import dataclass

from ..adapters.obsidian import list_vault_notes
from ..config import VoxStudyError, load_config
from ..models import AppConfig, CaptureStatus, VaultNote
from ..workflow import status


@dataclass(frozen=True)
class DashboardData:
    config: AppConfig | None
    configuration_error: str | None
    capture: CaptureStatus | None
    capture_error: str | None
    recent_notes: list[VaultNote]


def load_dashboard_data(note_limit: int = 5) -> DashboardData:
    """Load a snapshot for the dashboard without coupling it to Textual."""
    try:
        config = load_config()
        configuration_error = None
    except (VoxStudyError, OSError) as exc:
        config = None
        configuration_error = str(exc)

    try:
        capture = status()
        capture_error = None
    except (VoxStudyError, OSError, ValueError, KeyError) as exc:
        capture = None
        capture_error = str(exc)

    recent_notes = list_vault_notes(config, note_limit) if config is not None else []
    return DashboardData(
        config=config,
        configuration_error=configuration_error,
        capture=capture,
        capture_error=capture_error,
        recent_notes=recent_notes,
    )
