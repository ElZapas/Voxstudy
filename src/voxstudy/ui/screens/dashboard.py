"""Main VoxStudy terminal dashboard."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from ...application.dashboard import DashboardData, load_dashboard_data
from ...config import VoxStudyError
from ...models import CaptureSession, TranscriptionResult, WorkflowProgress
from ...workflow import start, stop
from ..messages import WorkflowFinishedMessage, WorkflowProgressMessage


class DashboardScreen(Screen[None]):
    """Show setup/capture status and the latest Obsidian notes."""

    BINDINGS = [
        Binding("l", "library", "Biblioteca", show=True),
        Binding("r", "refresh", "Actualizar", show=True),
        Binding("q", "quit", "Salir", show=True),
    ]

    CSS = """
    DashboardScreen {
        layout: vertical;
    }

    #dashboard-body {
        height: 1fr;
        padding: 1 2;
    }

    #status-row {
        height: auto;
        margin-bottom: 1;
    }

    .status-card {
        width: 1fr;
        height: auto;
        min-height: 5;
        padding: 1;
        margin-right: 1;
        border: round $accent;
    }

    #recent-title {
        height: 1;
        margin: 1 0;
        text-style: bold;
    }

    #recent-notes {
        height: 1fr;
    }

    #capture-controls {
        height: auto;
        margin-bottom: 1;
    }

    #capture-title {
        width: 100%;
        margin-bottom: 1;
    }

    #capture-buttons {
        height: auto;
    }

    #start-capture, #stop-capture {
        margin-right: 1;
    }

    #operation-status {
        height: auto;
        margin-bottom: 1;
        color: $text-muted;
    }

    #hint {
        height: auto;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="dashboard-body"):
            with Horizontal(id="status-row"):
                yield Static(id="vault-status", classes="status-card")
                yield Static(id="capture-status", classes="status-card")
            with Vertical(id="capture-controls"):
                yield Input(placeholder="Título del video", id="capture-title")
                with Horizontal(id="capture-buttons"):
                    yield Button("Iniciar captura", id="start-capture", variant="success")
                    yield Button("Detener y transcribir", id="stop-capture", variant="warning")
            yield Static("", id="operation-status")
            yield Static("Notas recientes", id="recent-title")
            yield DataTable(id="recent-notes", zebra_stripes=True)
            yield Static("l: biblioteca · r: actualizar · q: salir", id="hint")
        yield Footer()

    def on_mount(self) -> None:
        self._active_operation: str | None = None
        table = self.query_one("#recent-notes", DataTable)
        table.add_columns("Tipo", "Nota", "Modificada")
        self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-capture":
            title = self.query_one("#capture-title", Input).value.strip() or "Video sin título"
            self._begin_operation("capture-start", "Iniciando captura de audio del sistema…")
            self._start_capture_worker(title)
        elif event.button.id == "stop-capture":
            self._begin_operation("transcription", "Deteniendo captura y preparando la transcripción…")
            self._stop_capture_worker()

    def on_workflow_progress_message(self, event: WorkflowProgressMessage) -> None:
        if event.operation != self._active_operation:
            return
        self.query_one("#operation-status", Static).update(event.progress.message)

    def on_workflow_finished_message(self, event: WorkflowFinishedMessage) -> None:
        if event.operation != self._active_operation:
            return
        self._active_operation = None
        self._set_controls_enabled(True)
        status = self.query_one("#operation-status", Static)
        if event.error:
            status.update(f"[red]{event.error}[/red]")
            self.notify(event.error, severity="error", timeout=8)
            self.refresh_data()
            return
        if event.operation == "capture-start" and isinstance(event.result, CaptureSession):
            status.update(f"Capturando: {event.result.title}")
        elif event.operation == "transcription" and isinstance(event.result, TranscriptionResult):
            status.update(f"Transcripción guardada: {event.result.note_path.name}")
            self.notify("Transcripción completada", timeout=4)
        self.refresh_data()

    def action_refresh(self) -> None:
        self.refresh_data()
        self.notify("Panel actualizado", timeout=2)

    async def action_library(self) -> None:
        await self.app.push_screen("library")

    def action_quit(self) -> None:
        self.app.exit()

    def _begin_operation(self, operation: str, message: str) -> None:
        self._active_operation = operation
        self._set_controls_enabled(False)
        self.query_one("#operation-status", Static).update(message)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.query_one("#start-capture", Button).disabled = not enabled
        self.query_one("#stop-capture", Button).disabled = not enabled
        self.query_one("#capture-title", Input).disabled = not enabled

    @work(thread=True, group="voxstudy-workflow", exclusive=True, exit_on_error=False)
    def _start_capture_worker(self, title: str) -> None:
        try:
            result = start(title)
        except Exception as exc:
            self.post_message(WorkflowFinishedMessage("capture-start", error=str(exc)))
        else:
            self.post_message(WorkflowFinishedMessage("capture-start", result=result))

    @work(thread=True, group="voxstudy-workflow", exclusive=True, exit_on_error=False)
    def _stop_capture_worker(self) -> None:
        def report(progress: WorkflowProgress) -> None:
            self.post_message(WorkflowProgressMessage("transcription", progress))

        try:
            result = stop(report)
        except Exception as exc:
            self.post_message(WorkflowFinishedMessage("transcription", error=str(exc)))
        else:
            self.post_message(WorkflowFinishedMessage("transcription", result=result))

    def refresh_data(self) -> None:
        data = load_dashboard_data()
        self._render_status(data)
        self._render_recent_notes(data)

    def _render_status(self, data: DashboardData) -> None:
        vault_widget = self.query_one("#vault-status", Static)
        if data.config is None:
            vault_widget.update(
                "[b]Bóveda[/b]\n"
                f"[yellow]{data.configuration_error or 'Sin configurar'}[/yellow]"
            )
        else:
            vault_widget.update(
                "[b]Bóveda[/b]\n"
                f"{data.config.vault}\n"
                f"Transcripciones: {data.config.transcript_folder}\n"
                f"Guías: {data.config.guide_folder}"
            )

        capture_widget = self.query_one("#capture-status", Static)
        if data.capture_error:
            capture_widget.update(f"[b]Captura[/b]\n[red]{data.capture_error}[/red]")
        elif data.capture is None or data.capture.session is None:
            capture_widget.update("[b]Captura[/b]\nSin sesión activa")
        else:
            session = data.capture.session
            if session.capture_finished:
                description = (
                    f"Transcripción en curso: {data.capture.completed_chunks}/"
                    f"{data.capture.total_chunks} bloques"
                )
            else:
                description = f"Capturando audio del sistema ({session.monitor})"
            capture_widget.update(
                f"[b]Captura[/b]\n{description}\nVideo: {session.title}"
            )

        has_session = data.capture is not None and data.capture.session is not None
        busy = self._active_operation is not None
        self.query_one("#start-capture", Button).disabled = busy or has_session
        self.query_one("#stop-capture", Button).disabled = busy or not has_session
        self.query_one("#capture-title", Input).disabled = busy or has_session

    def _render_recent_notes(self, data: DashboardData) -> None:
        table = self.query_one("#recent-notes", DataTable)
        table.clear(columns=False)
        if not data.recent_notes:
            table.add_row("—", "Todavía no hay notas de VoxStudy", "—")
            return
        for note in data.recent_notes:
            note_type = "Transcripción" if note.note_type == "transcription" else "Guía"
            table.add_row(
                note_type,
                note.title,
                note.modified_at.strftime("%Y-%m-%d %H:%M"),
                key=str(note.path),
            )
