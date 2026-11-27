"""Command-line entry point for VoxStudy."""

from __future__ import annotations

import argparse
import sys

from .adapters.deepseek import DEFAULT_MODEL
from .config import DEFAULT_GUIDE_FOLDER, DEFAULT_TRANSCRIPT_FOLDER, DEFAULT_VAULT, VoxStudyError
from .models import WorkflowProgress
from .workflow import create_guide, setup, start, status, stop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe system audio with Voxtype and create Obsidian notes.")
    commands = parser.add_subparsers(dest="command")

    setup_parser = commands.add_parser("setup", help="Configure the Obsidian vault.")
    setup_parser.add_argument("--vault", default=str(DEFAULT_VAULT), help="Path to the vault.")
    setup_parser.add_argument("--folder", default=DEFAULT_TRANSCRIPT_FOLDER, help="Transcript folder inside the vault.")
    setup_parser.add_argument("--guide-folder", default=DEFAULT_GUIDE_FOLDER, help="Study guide folder inside the vault.")

    start_parser = commands.add_parser("start", help="Start capturing system audio.")
    start_parser.add_argument("--title", default="Video sin título", help="Title for the Obsidian note.")
    commands.add_parser("stop", help="Stop capture, transcribe, and save a note.")
    commands.add_parser("status", help="Show capture or transcription status.")

    guide_parser = commands.add_parser("guide", help="Create a study guide with DeepSeek.")
    guide_parser.add_argument("transcript", nargs="?", help="Transcript note; defaults to the most recent one.")
    guide_parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Provider model (default: {DEFAULT_MODEL}).")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command is None:
            from .ui.app import VoxStudyApp

            VoxStudyApp().run()
        elif args.command == "setup":
            config = setup(args.vault, args.folder, args.guide_folder)
            print("Configuración guardada.")
            print(f"Transcripciones: {config.vault / config.transcript_folder}")
            print(f"Guías de estudio: {config.vault / config.guide_folder}")
        elif args.command == "start":
            session = start(args.title)
            print(f"Capturando solo el audio del sistema: {session.monitor}")
            print(f"Video: {session.title}")
            print("Al terminar, ejecuta: voxstudy stop")
        elif args.command == "stop":
            result = stop(_print_progress)
            print(f"Nota guardada en la bóveda:\n{result.note_path}")
            print("La captura excluyó el micrófono.")
        elif args.command == "status":
            _print_status()
        elif args.command == "guide":
            result = create_guide(args.transcript, args.model, _print_progress)
            print(f"Guía guardada en la bóveda:\n{result.note_path}")
            print(
                "Tokens según el proveedor: "
                f"entrada {int(result.usage.get('prompt_tokens', 0) or 0)}, "
                f"salida {int(result.usage.get('completion_tokens', 0) or 0)}."
            )
        return 0
    except (VoxStudyError, OSError, KeyError, ValueError, IndexError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _print_progress(progress: WorkflowProgress) -> None:
    if progress.stage == "transcription_started":
        print(f"Audio capturado. Transcribiendo {progress.total} bloques con Voxtype local…")
    elif progress.message:
        print(progress.message)


def _print_status() -> None:
    result = status()
    session = result.session
    if session is None:
        print("No hay una sesión de VoxStudy activa.")
        return
    if session.capture_finished:
        print(
            "Captura detenida; transcripción en curso "
            f"({result.completed_chunks}/{result.total_chunks} bloques)."
        )
    else:
        print(f"Capturando audio del sistema: {session.monitor}")
    print(f"Video: {session.title}")
    print(f"Inició: {session.started_at}")
