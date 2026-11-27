"""Capture the default system-output monitor with FFmpeg."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ..config import RECORDINGS_DIR, VoxStudyError
from ..models import CaptureSession


CHUNK_SECONDS = 30


def run_command(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise VoxStudyError(f"No encuentro el programa requerido: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VoxStudyError(f"El comando tardó demasiado: {command[0]}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise VoxStudyError(detail or f"El comando terminó con código {result.returncode}: {command[0]}")
    return result


def find_default_monitor() -> str:
    sink = run_command(["pactl", "get-default-sink"]).stdout.strip()
    monitor = f"{sink}.monitor"
    sources = run_command(["pactl", "list", "short", "sources"]).stdout
    if not any(line.split() and line.split()[1] == monitor for line in sources.splitlines()):
        raise VoxStudyError(f"No encuentro el monitor de la salida predeterminada: {monitor}")
    return monitor


def start_capture(title: str) -> CaptureSession:
    monitor = find_default_monitor()
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audio_path = RECORDINGS_DIR / f"{session_id}.wav"
    log_path = RECORDINGS_DIR / f"{session_id}.log"
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning",
        "-f", "pulse", "-i", monitor,
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path),
    ]
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    time.sleep(0.5)
    if process.poll() is not None:
        detail = log_path.read_text(encoding="utf-8", errors="replace").strip()
        audio_path.unlink(missing_ok=True)
        log_path.unlink(missing_ok=True)
        raise VoxStudyError(f"FFmpeg no pudo iniciar la captura.\n{detail}")
    return CaptureSession(
        pid=process.pid,
        title=title,
        monitor=monitor,
        audio_path=audio_path,
        log_path=log_path,
        started_at=datetime.now(timezone.utc).isoformat(),
    )


def _process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            return proc_stat.read_text(encoding="utf-8").rsplit(") ", 1)[1][0] != "Z"
        except (IndexError, OSError):
            pass
    return True


def stop_capture(session: CaptureSession) -> None:
    if session.capture_finished:
        return
    if _process_is_running(session.pid):
        try:
            os.killpg(session.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 30
        while _process_is_running(session.pid) and time.monotonic() < deadline:
            time.sleep(0.25)
        if _process_is_running(session.pid):
            raise VoxStudyError("FFmpeg no se detuvo a tiempo; la grabación sigue pendiente.")
    if not session.audio_path.is_file() or session.audio_path.stat().st_size < 44:
        raise VoxStudyError("No se guardó audio. Revisa la salida y el registro de FFmpeg.")
    session.capture_finished = True


def split_audio(audio_path: Path, work_dir: Path) -> list[Path]:
    pattern = work_dir / "chunk-%05d.wav"
    run_command([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(audio_path), "-f", "segment", "-segment_time", str(CHUNK_SECONDS),
        "-reset_timestamps", "1", "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(pattern),
    ], timeout=300)
    chunks = sorted(work_dir.glob("chunk-*.wav"))
    if not chunks:
        raise VoxStudyError("FFmpeg no pudo dividir la grabación en bloques.")
    return chunks
