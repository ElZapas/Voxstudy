"""Detail view for a transcription note."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Markdown, Static

from ...application.library import load_note_detail, open_library_note
from ...config import VoxStudyError
from ...models import GuideResult, WorkflowProgress
from ...workflow import create_guide
from ..messages import WorkflowFinishedMessage, WorkflowProgressMessage
from ..widgets.navbar import AppNavbar


class NoteDetailScreen(Screen[None]):
    """Shared note preview and Obsidian opening action."""

    BINDINGS = [
        Binding("o", "open_in_obsidian", "Abrir en Obsidian", show=True),
        Binding("escape", "back", "Volver", show=True),
    ]
    NOTE_KIND = "Nota"

    CSS = """
    NoteDetailScreen {
        layout: vertical;
    }

    #detail-body {
        height: 1fr;
        padding: 1 2;
    }

    #detail-title {
        height: auto;
        text-style: bold;
    }

    #detail-meta {
        height: auto;
        color: $foreground-muted;
        margin-bottom: 1;
    }

    #operation-status {
        height: auto;
        margin-bottom: 1;
        color: $foreground-muted;
    }

    #note-scroll {
        height: 1fr;
        border: round $accent;
        padding: 1;
    }
    """

    def __init__(self, note_path: str | Path) -> None:
        super().__init__()
        self.note_path = Path(note_path)
        self._guide_running = False

    def compose(self) -> ComposeResult:
        yield AppNavbar(active_page="library")
        with Vertical(id="detail-body"):
            yield Static(self.NOTE_KIND, id="detail-title")
            yield Static(id="detail-meta")
            if self.NOTE_KIND == "Transcripción":
                yield Button("Generar guía de estudio", id="generate-guide", variant="primary")
            yield Static("", id="operation-status")
            with VerticalScroll(id="note-scroll"):
                yield Markdown(id="note-content")
        yield Footer()

    async def on_mount(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        try:
            detail = load_note_detail(self.note_path)
        except (VoxStudyError, OSError) as exc:
            self.notify(str(exc), severity="error", timeout=6)
            return
        self.query_one("#detail-title", Static).update(detail.note.title)
        self.query_one("#detail-meta", Static).update(
            f"{self.NOTE_KIND} · Modificada {detail.note.modified_at:%Y-%m-%d %H:%M} · {detail.note.path}"
        )
        self.query_one("#note-content", Markdown).update(detail.content)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate-guide":
            self.action_generate_guide()

    def on_workflow_progress_message(self, event: WorkflowProgressMessage) -> None:
        if event.operation == "guide":
            self.query_one("#operation-status", Static).update(event.progress.message)

    def on_workflow_finished_message(self, event: WorkflowFinishedMessage) -> None:
        if event.operation != "guide":
            return
        self._guide_running = False
        self.query_one("#generate-guide", Button).disabled = False
        status = self.query_one("#operation-status", Static)
        if event.error:
            status.update(f"[red]{event.error}[/red]")
            self.notify(event.error, severity="error", timeout=8)
            return
        if isinstance(event.result, GuideResult):
            usage = event.result.usage
            prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage.get("completion_tokens", 0) or 0)
            status.update(
                f"Guía guardada: {event.result.note_path.name} · "
                f"tokens: {prompt_tokens} entrada, {completion_tokens} salida"
            )
            self.notify("Guía de estudio creada", timeout=4)

    def action_generate_guide(self) -> None:
        if self.NOTE_KIND != "Transcripción" or self._guide_running:
            return
        self._guide_running = True
        self.query_one("#generate-guide", Button).disabled = True
        self.query_one("#operation-status", Static).update("Preparando la guía de estudio…")
        self._generate_guide_worker()

    def action_open_in_obsidian(self) -> None:
        try:
            open_library_note(self.note_path)
        except (VoxStudyError, OSError) as exc:
            self.notify(str(exc), severity="error", timeout=6)
            return
        self.notify("Abriendo nota en Obsidian…", timeout=3)

    async def action_back(self) -> None:
        await self.app.pop_screen()

    @work(thread=True, group="voxstudy-guide", exclusive=True, exit_on_error=False)
    def _generate_guide_worker(self) -> None:
        def report(progress: WorkflowProgress) -> None:
            self.post_message(WorkflowProgressMessage("guide", progress))

        try:
            result = create_guide(str(self.note_path), on_progress=report)
        except Exception as exc:
            self.post_message(WorkflowFinishedMessage("guide", error=str(exc)))
        else:
            self.post_message(WorkflowFinishedMessage("guide", result=result))


class TranscriptDetailScreen(NoteDetailScreen):
    NOTE_KIND = "Transcripción"
    BINDINGS = [
        *NoteDetailScreen.BINDINGS,
        Binding("g", "generate_guide", "Generar guía", show=True),
    ]
