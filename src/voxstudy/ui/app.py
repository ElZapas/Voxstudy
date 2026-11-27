"""Textual application shell and screen routing."""

from textual.app import App

from .screens.dashboard import DashboardScreen
from .screens.library import LibraryScreen


class VoxStudyApp(App[None]):
    """Interactive terminal entry point for VoxStudy."""

    TITLE = "VoxStudy"
    AUTO_FOCUS = None
    DEFAULT_MODE = "main"
    MODES = {"main": "dashboard"}
    SCREENS = {"dashboard": DashboardScreen, "library": LibraryScreen}
