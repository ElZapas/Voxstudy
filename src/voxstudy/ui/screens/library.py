"""Searchable library of VoxStudy notes."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input, Static

from ...application.library import list_library_notes
from ...config import VoxStudyError
from ...models import VaultNote
from .study_guide import StudyGuideDetailScreen
from .transcript import TranscriptDetailScreen
from ..widgets.navbar import AppNavbar


class LibraryScreen(Screen[None]):
    """Show and filter all VoxStudy notes in the configured vault."""

    BINDINGS = [Binding("escape", "back", "Volver", show=True)]

    CSS = """
    LibraryScreen {
        layout: vertical;
    }

    #library-body {
        height: 1fr;
        padding: 1 2 0 2;
        overflow-y: auto;
    }

    #library-panel {
        height: 1fr;
        min-height: 8;
        padding: 1;
        border: heavy $muted;
        background: $surface;
    }

    #library-title {
        height: 1;
        color: $accent;
        text-style: bold;
        margin-bottom: 0;
    }

    #note-search {
        margin-bottom: 1;
        background: $panel;
        border: round $muted;
    }

    #library-notes {
        height: 1fr;
        border: heavy $muted;
        background: $background;
    }

    #library-hint {
        height: auto;
        margin-top: 1;
        color: $muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._notes_by_path: dict[str, VaultNote] = {}

    def compose(self) -> ComposeResult:
        yield AppNavbar(active_page="library")
        with Vertical(id="library-body"):
            with Vertical(id="library-panel"):
                yield Static("BIBLIOTECA DE ESTUDIO", id="library-title")
                yield Input(placeholder="Buscar por título…", id="note-search")
                yield DataTable(id="library-notes", cursor_type="row", zebra_stripes=True)
                yield Static("↑/↓: seleccionar · Enter: ver nota · Esc: volver", id="library-hint")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#library-notes", DataTable)
        table.add_columns("Tipo", "Nota", "Modificada")
        self.refresh_notes()
        self.query_one("#note-search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "note-search":
            self.refresh_notes(event.value)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        note = self._notes_by_path.get(event.row_key.value)
        if note is None:
            return
        screen_type = (
            TranscriptDetailScreen if note.note_type == "transcription"
            else StudyGuideDetailScreen
        )
        await self.app.push_screen(screen_type(note.path))

    async def action_back(self) -> None:
        self.app.show_dashboard()

    def refresh_notes(self, query: str = "") -> None:
        table = self.query_one("#library-notes", DataTable)
        table.clear(columns=False)
        self._notes_by_path.clear()
        try:
            notes = list_library_notes(query)
        except (VoxStudyError, OSError) as exc:
            self.notify(str(exc), severity="error", timeout=6)
            table.add_row("Error", "No se pudo cargar la biblioteca", "")
            return

        if not notes:
            empty_message = "No hay notas de VoxStudy" if not query.strip() else "Sin resultados"
            table.add_row("—", empty_message, "—")
            return
        for note in notes:
            self._notes_by_path[str(note.path)] = note
            note_type = "Transcripción" if note.note_type == "transcription" else "Guía"
            table.add_row(
                note_type,
                note.title,
                note.modified_at.strftime("%Y-%m-%d %H:%M"),
                key=str(note.path),
            )

    def refresh_view(self) -> None:
        self.refresh_notes(self.query_one("#note-search", Input).value)
