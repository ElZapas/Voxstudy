"""Main VoxStudy terminal dashboard."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Static

from ...application.dashboard import DashboardData, load_dashboard_data
from ...config import VoxStudyError
from ...models import CaptureSession, TranscriptionResult, WorkflowProgress
from ...workflow import start, stop
from ..messages import WorkflowFinishedMessage, WorkflowProgressMessage
from ..widgets.navbar import AppNavbar


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
        padding: 0 2;
        overflow-y: auto;
    }

    #status-row {
        height: auto;
        margin: 0 0 1 0;
    }

    .status-card {
        width: 1fr;
        height: auto;
        min-height: 5;
        padding: 0 1;
        margin-right: 1;
        border: heavy $muted;
        background: $surface;
    }

    .status-wide {
        width: 2fr;
    }

    .section-title {
        height: 1;
        margin-bottom: 0;
        color: $accent;
        text-style: bold;
    }

    #capture-controls {
        height: auto;
        padding: 0 1;
        border: double $accent;
        background: $surface;
    }

    #capture-title {
        width: 100%;
        margin-bottom: 0;
        background: $panel;
        border: round $muted;
    }

    #capture-buttons {
        height: 1;
    }

    #start-capture, #stop-capture {
        height: 1;
        min-height: 1;
        margin: 0 1 0 0;
        padding: 0 1;
        border: none;
    }

    #operation-status {
        display: none;
        height: auto;
        color: $foreground-muted;
    }

    #recent-panel {
        height: 1fr;
        min-height: 5;
        margin-top: 1;
        padding: 0 1;
        border: heavy $muted;
        background: $surface;
    }

    #recent-notes {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppNavbar(active_page="dashboard")
        with Vertical(id="dashboard-body"):
            with Horizontal(id="status-row"):
                yield Static(id="vault-status", classes="status-card status-wide")
                yield Static(id="capture-status", classes="status-card")
            with Vertical(id="capture-controls"):
                yield Static("CAPTURA DE AUDIO", classes="section-title")
                yield Input(placeholder="Título del video", id="capture-title")
                with Horizontal(id="capture-buttons"):
                    yield Button("Iniciar captura", id="start-capture", variant="success")
                    yield Button("Detener y transcribir", id="stop-capture", variant="warning")
                yield Static("", id="operation-status")
            with Vertical(id="recent-panel"):
                yield Static("NOTAS RECIENTES", classes="section-title")
                yield DataTable(id="recent-notes", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self._active_operation: str | None = None
        table = self.query_one("#recent-notes", DataTable)
        table.add_columns("Tipo", "Nota", "Modificada")
        self.refresh_data()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
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
        status = self.query_one("#operation-status", Static)
        status.display = True
        status.update(event.progress.message)

    def on_workflow_finished_message(self, event: WorkflowFinishedMessage) -> None:
        if event.operation != self._active_operation:
            return
        self._active_operation = None
        self._set_controls_enabled(True)
        status = self.query_one("#operation-status", Static)
        status.display = True
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
        self.refresh_view()
        self.notify("Panel actualizado", timeout=2)

    def refresh_view(self) -> None:
        self.refresh_data()

    async def action_library(self) -> None:
        await self.app.show_library()

    def action_quit(self) -> None:
        self.app.exit()

    def _begin_operation(self, operation: str, message: str) -> None:
        self._active_operation = operation
        self._set_controls_enabled(False)
        status = self.query_one("#operation-status", Static)
        status.display = True
        status.update(message)

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
                f"{data.config.transcript_folder} · {data.config.guide_folder}"
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
                description = "Capturando audio del sistema"
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
