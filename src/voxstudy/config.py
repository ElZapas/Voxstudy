"""User configuration and resumable session state."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AppConfig, CaptureSession


APP_NAME = "voxstudy"
CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME / "config.json"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / APP_NAME
STATE_PATH = STATE_DIR / "session.json"
RECORDINGS_DIR = STATE_DIR / "recordings"
DEFAULT_VAULT = Path("/home/greep/Documents/Obsidian/MDY")
DEFAULT_TRANSCRIPT_FOLDER = "Transcripciones"
DEFAULT_GUIDE_FOLDER = "Guías de estudio"


class VoxStudyError(Exception):
    """An expected error that can be shown directly in the CLI."""


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_config() -> AppConfig:
    try:
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VoxStudyError("Falta la configuración. Ejecuta: voxstudy setup") from exc
    except json.JSONDecodeError as exc:
        raise VoxStudyError(f"La configuración no contiene JSON válido: {CONFIG_PATH}") from exc

    vault = Path(value.get("vault", "")).expanduser()
    transcript_folder = Path(value.get("folder", DEFAULT_TRANSCRIPT_FOLDER))
    guide_folder = Path(value.get("guide_folder", DEFAULT_GUIDE_FOLDER))
    folders = (transcript_folder, guide_folder)
    if not vault.is_dir():
        raise VoxStudyError(f"La bóveda configurada no existe o no es una carpeta: {vault}")
    if any(folder.is_absolute() or ".." in folder.parts for folder in folders):
        raise VoxStudyError("Las carpetas de notas deben ser rutas relativas dentro de la bóveda.")
    return AppConfig(vault, transcript_folder, guide_folder)


def setup_config(vault_value: str, transcript_folder_value: str, guide_folder_value: str) -> AppConfig:
    vault = Path(vault_value).expanduser().resolve()
    transcript_folder = Path(transcript_folder_value)
    guide_folder = Path(guide_folder_value)
    if not vault.is_dir():
        raise VoxStudyError(f"No existe la bóveda: {vault}")
    if any(folder.is_absolute() or ".." in folder.parts for folder in (transcript_folder, guide_folder)):
        raise VoxStudyError("Las carpetas deben ser rutas relativas dentro de la bóveda.")
    _write_json(CONFIG_PATH, {
        "vault": str(vault),
        "folder": transcript_folder.as_posix(),
        "guide_folder": guide_folder.as_posix(),
    })
    return AppConfig(vault, transcript_folder, guide_folder)


def load_session() -> CaptureSession | None:
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise VoxStudyError(f"El estado de sesión está dañado: {STATE_PATH}") from exc
    return CaptureSession.from_dict(value)


def save_session(session: CaptureSession) -> None:
    _write_json(STATE_PATH, session.to_dict())


def clear_session() -> None:
    STATE_PATH.unlink(missing_ok=True)
