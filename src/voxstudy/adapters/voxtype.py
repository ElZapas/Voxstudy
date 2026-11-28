"""Local Voxtype configuration checks and file transcription."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ..config import VoxStudyError
from .audio_capture import run_command


_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_PLAIN_STYLE_MARKER = re.compile(r"\[(?:\d{1,3})(?:;\d{1,3})*m")
_TIMESTAMPED_LOG = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\S+\s+(?:TRACE|DEBUG|INFO|WARN|ERROR)\b"
)
_TRANSCRIBED_LINE = re.compile(r"\bTranscribed:\s*(.+)$", re.IGNORECASE)
_DIAGNOSTIC_PATTERNS = (
    r"^Loading audio file:",
    r"^Audio format:",
    r"^Processing \d+ samples",
    r"^Transcribing .* of audio",
    r"^Transcription completed in ",
    r"^Using local .* transcription mode",
    r"^Loading .* model from ",
    r"^Model loaded in ",
    r"^Language detection:",
    r"^whisper_(?:model|init|full|sampling|print|state)",
)


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

    for raw_output in (result.stdout, result.stderr):
        if raw_output.strip():
            transcript = clean_transcription_text(raw_output)
            if transcript:
                return transcript
    return ""


def clean_transcription_text(raw: str) -> str:
    """Keep recognized text and timestamps while removing Voxtype diagnostics."""
    cleaned_lines: list[str] = []
    for line in _strip_terminal_styles(raw).splitlines():
        match = _TRANSCRIBED_LINE.search(line)
        if match is not None:
            cleaned_lines.append(_decode_voxtype_string(match.group(1)))
            continue
        if _TIMESTAMPED_LOG.search(line):
            continue
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in _DIAGNOSTIC_PATTERNS):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _decode_voxtype_string(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            slash = chr(92)
            decoded = value[1:-1].replace(slash + '"', '"').replace(slash + slash, slash)
        if isinstance(decoded, str):
            value = decoded
    return value.strip()


def _strip_terminal_styles(value: str) -> str:
    """Remove ANSI colors, including style markers left after terminal rendering."""
    return _PLAIN_STYLE_MARKER.sub("", _ANSI_ESCAPE.sub("", value))
