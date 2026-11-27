"""Local Voxtype configuration checks and file transcription."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..config import VoxStudyError
from .audio_capture import run_command


def require_local_whisper() -> None:
    engine = run_command(["voxtype", "config", "get", "engine"]).stdout.strip()
    mode = run_command(["voxtype", "config", "get", "whisper.mode"]).stdout.strip()
    if engine != "whisper" or mode != "local":
        raise VoxStudyError(
            "Para evitar enviar audio a un servicio externo, VoxStudy requiere "
            "engine=whisper y whisper.mode=local en Voxtype."
        )


def transcribe_chunk(path: Path) -> str:
    try:
        result = subprocess.run(
            ["voxtype", "transcribe", str(path)],
            capture_output=True,
            text=True,
            timeout=20 * 60,
            check=False,
        )
    except FileNotFoundError as exc:
        raise VoxStudyError("No encuentro el comando 'voxtype'.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VoxStudyError(f"Voxtype tardó demasiado en transcribir {path.name}.") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise VoxStudyError(detail or f"Voxtype no pudo transcribir {path.name}.")

    raw = result.stdout or result.stderr
    diagnostic_patterns = (
        r"^Loading audio file:",
        r"^Audio format:",
        r"^Processing \d+ samples",
        r"^\d{4}-\d{2}-\d{2}T\S+\s+(?:INFO|WARN|ERROR|DEBUG)\s+",
    )
    lines = [
        line for line in raw.splitlines()
        if not any(re.search(pattern, line) for pattern in diagnostic_patterns)
    ]
    text = "\n".join(lines).strip()
    text = re.sub(r"^Transcribed:\s*", "", text, flags=re.IGNORECASE)
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text.strip()
