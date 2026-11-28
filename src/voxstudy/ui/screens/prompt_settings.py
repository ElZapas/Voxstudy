"""Editor for the per-user study-guide system prompt."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Static, TextArea

from ...config import VoxStudyError
from ...prompts import (
    DEFAULT_GUIDE_SYSTEM_PROMPT,
    load_guide_system_prompt,
    reset_guide_system_prompt,
    save_guide_system_prompt,
)
from ..widgets.navbar import AppNavbar


class PromptSettingsScreen(Screen[None]):
    """Edit the system prompt used to generate study guides."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Guardar prompt", show=True),
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    CSS = """
    PromptSettingsScreen { layout: vertical; }

    #prompt-settings-body {
        height: 1fr;
        padding: 1 2;
    }

    #prompt-settings-panel {
        height: 1fr;
        min-height: 8;
        padding: 1;
        border: heavy $muted;
        background: $surface;
    }

    #prompt-settings-title {
        height: 1;
        color: $accent;
        text-style: bold;
    }

    #prompt-settings-help, #prompt-settings-status {
        height: auto;
        color: $muted;
        margin-bottom: 1;
    }

    #guide-prompt-editor {
        height: 1fr;
        min-height: 4;
        border: heavy $muted;
        background: $background;
    }

    #prompt-settings-buttons { height: 3; margin-top: 1; }
    #save-prompt { margin-right: 1; }
    #reset-prompt { margin-right: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._load_error: str | None = None
        try:
            self._prompt = load_guide_system_prompt()
        except VoxStudyError as exc:
            self._prompt = DEFAULT_GUIDE_SYSTEM_PROMPT
            self._load_error = str(exc)

    def compose(self) -> ComposeResult:
        yield AppNavbar(active_page="prompts")
        with Vertical(id="prompt-settings-body"):
            with Vertical(id="prompt-settings-panel"):
                yield Static("PROMPT DE SISTEMA · GUÍAS DE ESTUDIO", id="prompt-settings-title")
                yield Static(
                    "Edita las instrucciones que DeepSeek recibe antes de la transcripción. "
                    "Se guardan solo en la configuración local de VoxStudy.",
                    id="prompt-settings-help",
                )
                yield TextArea(self._prompt, id="guide-prompt-editor", soft_wrap=True)
                yield Static(self._load_error or "", id="prompt-settings-status")
                with Horizontal(id="prompt-settings-buttons"):
                    yield Button("Guardar prompt", id="save-prompt", variant="primary")
                    yield Button("Restaurar predeterminado", id="reset-prompt")
                    yield Button("Cancelar", id="cancel-prompt")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#guide-prompt-editor", TextArea).focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-prompt":
            self.action_save()
        elif event.button.id == "reset-prompt":
            self.action_reset()
        elif event.button.id == "cancel-prompt":
            self.action_cancel()

    def action_save(self) -> None:
        prompt = self.query_one("#guide-prompt-editor", TextArea).text
        try:
            path = save_guide_system_prompt(prompt)
        except VoxStudyError as exc:
            self.query_one("#prompt-settings-status", Static).update(f"[red]{exc}[/red]")
            return
        self._load_error = None
        self.query_one("#prompt-settings-status", Static).update(f"Prompt guardado en {path}")
        self.notify("Prompt personalizado guardado", timeout=3)

    def action_reset(self) -> None:
        try:
            reset_guide_system_prompt()
        except VoxStudyError as exc:
            self.query_one("#prompt-settings-status", Static).update(f"[red]{exc}[/red]")
            return
        self.query_one("#guide-prompt-editor", TextArea).text = DEFAULT_GUIDE_SYSTEM_PROMPT
        self.query_one("#prompt-settings-status", Static).update("Usando el prompt predeterminado.")
        self.notify("Prompt predeterminado restaurado", timeout=3)

    def action_cancel(self) -> None:
        self.app.return_from_prompt_settings()
