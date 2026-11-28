"""Shared VoxStudy masthead and page navigation."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static


class AppNavbar(Horizontal):
    """Brand, page navigation, refresh, and exit controls."""

    def __init__(self, active_page: str) -> None:
        super().__init__(id="app-navigation")
        self.active_page = active_page

    def compose(self) -> ComposeResult:
        yield Static(r"_/\/\_", id="brand-wave")
        yield Static("VOXSTUDY", id="brand-name")
        yield Button("⌂ Panel", id="nav-home", disabled=self.active_page == "dashboard")
        yield Static("│", classes="nav-separator")
        yield Button("▤ Notas", id="nav-library", disabled=self.active_page == "library")
        yield Static("│", classes="nav-separator")
        yield Button("✎ Prompt", id="nav-prompts", disabled=self.active_page == "prompts")
        yield Static("│", classes="nav-separator")
        yield Button("↻ Act.", id="nav-refresh")
        yield Static("│", classes="nav-separator")
        yield Button("× Salir", id="nav-quit")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "nav-home":
            await self.app.show_dashboard()
        elif event.button.id == "nav-library":
            await self.app.show_library()
        elif event.button.id == "nav-prompts":
            await self.app.show_prompt_settings()
        elif event.button.id == "nav-refresh":
            if self.app.refresh_current_screen():
                self.app.notify("Vista actualizada", timeout=2)
        elif event.button.id == "nav-quit":
            self.app.exit()
