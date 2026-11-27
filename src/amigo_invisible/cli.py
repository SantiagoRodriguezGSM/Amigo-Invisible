"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
import random
import re
import shutil
import smtplib
import sys
import tempfile
import time
import unicodedata
from collections.abc import Callable, Sequence
from pathlib import Path

from . import __version__
from .config import DEFAULT_ENV_FILE, Settings, load_settings
from .draw import draw_assignments
from .errors import AmigoInvisibleError
from .mailer import Mailer
from .participants import Participant, load_participants
from .pdf import create_assignment_pdf

DEFAULT_PARTICIPANTS = "participants.json"
DEFAULT_OUTPUT_DIR = "pdfs"


def _slug(text: str) -> str:
    """Nombre seguro para un archivo: sin tildes, espacios ni símbolos."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower() or "participante"


def send_all(
    participants: list[Participant],
    settings: Settings,
    *,
    dry_run: bool = False,
    keep_pdfs: bool = False,
    output_dir: Path = Path(DEFAULT_OUTPUT_DIR),
    delay: float = 3.0,
    rng: random.Random | None = None,
    log: Callable[[str], None] = print,
) -> int:
    """Hace el sorteo, genera los PDF y los envía. Devuelve el nº de envíos fallidos.

    Los PDF se crean en una carpeta temporal que se borra al terminar, para que ni
    siquiera el organizador pueda ver quién le toca a quién. Se conservan en
    ``output_dir`` solo con ``keep_pdfs``/``dry_run`` y, en un envío real, los de
    quienes no hayan recibido su correo.
    """
    if not dry_run:
        settings.require_smtp()

    assignments = draw_assignments(participants, rng=rng)
    failures: list[tuple[Participant, Path]] = []

    with tempfile.TemporaryDirectory(prefix="amigo-invisible-") as tmp:
        pdfs: list[Path] = []
        for i, (giver, receiver) in enumerate(assignments, start=1):
            pdf = create_assignment_pdf(
                giver.name, receiver.name, Path(tmp) / f"{i:02d}_{_slug(giver.name)}.pdf", settings
            )
            pdfs.append(pdf)

        if dry_run or keep_pdfs:
            output_dir.mkdir(parents=True, exist_ok=True)
            for pdf in pdfs:
                shutil.copy2(pdf, output_dir / pdf.name)
            log(f"PDF guardados en {output_dir}/ (¡revelan el sorteo, no los compartas!).")

        if dry_run:
            log("Modo de prueba: no se ha enviado ningún correo.")
            return 0

        with Mailer(settings) as mailer:
            for n, ((giver, _), pdf) in enumerate(zip(assignments, pdfs, strict=True)):
                try:
                    mailer.send(giver.name, giver.email, pdf)
                except (smtplib.SMTPException, OSError) as exc:
                    log(f"[ERROR] {giver.email}: {exc}")
                    failures.append((giver, pdf))
                else:
                    log(f"[OK]    Enviado a {giver.email}")
                if n < len(assignments) - 1:
                    time.sleep(delay)

        if failures:
            output_dir.mkdir(parents=True, exist_ok=True)
            log(f"\nNo se pudo enviar a {len(failures)} persona(s). Sus PDF se guardan en {output_dir}/:")
            for giver, pdf in failures:
                shutil.copy2(pdf, output_dir / pdf.name)
                log(f"  - {giver.name} <{giver.email}> -> {output_dir / pdf.name}")

    return len(failures)


def _confirm(question: str) -> bool:
    try:
        return input(f"{question} [s/N] ").strip().lower() in {"s", "si", "sí", "y", "yes"}
    except EOFError:
        return False


def _cmd_send(args: argparse.Namespace) -> int:
    settings = load_settings(args.env_file)
    participants = load_participants(args.participants)

    if not args.dry_run:
        settings.require_smtp()
        if not args.yes and not _confirm(
            f"Se enviarán {len(participants)} correos desde {settings.smtp_user}. ¿Continuar?"
        ):
            print("Cancelado.")
            return 1

    print(f"\n=== Amigo Invisible: {len(participants)} participantes ===\n")
    failed = send_all(
        participants,
        settings,
        dry_run=args.dry_run,
        keep_pdfs=args.keep_pdfs,
        output_dir=Path(args.output_dir),
        delay=args.delay,
    )
    if failed:
        return 1
    if not args.dry_run:
        print("\nListo: todos los correos se han enviado.")
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    settings = load_settings(args.env_file)
    out = create_assignment_pdf("Lucía Muñoz", "Íñigo Peña", Path(args.output), settings)
    print(f"Vista previa creada en {out} (con nombres ficticios).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amigo-invisible",
        description="Sortea el Amigo Invisible y envía a cada persona su asignación en PDF.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send", help="hace el sorteo y envía los correos")
    send.add_argument(
        "-p",
        "--participants",
        default=DEFAULT_PARTICIPANTS,
        help="JSON con los participantes (por defecto: %(default)s)",
    )
    send.add_argument(
        "--env-file",
        default=DEFAULT_ENV_FILE,
        help="archivo con la configuración y credenciales (por defecto: %(default)s)",
    )
    send.add_argument("--dry-run", action="store_true", help="hace el sorteo y genera los PDF sin enviar nada")
    send.add_argument("--keep-pdfs", action="store_true", help="conserva los PDF en --output-dir tras el envío")
    send.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="carpeta para los PDF conservados (por defecto: %(default)s)",
    )
    send.add_argument("--delay", type=float, default=3.0, help="segundos entre correos (por defecto: %(default)s)")
    send.add_argument("-y", "--yes", action="store_true", help="no pedir confirmación antes de enviar")
    send.set_defaults(func=_cmd_send)

    preview = sub.add_parser("preview", help="genera un PDF de ejemplo con nombres ficticios")
    preview.add_argument("-o", "--output", default="preview.pdf", help="archivo de salida (por defecto: %(default)s)")
    preview.add_argument(
        "--env-file", default=DEFAULT_ENV_FILE, help="archivo con la configuración (por defecto: %(default)s)"
    )
    preview.set_defaults(func=_cmd_preview)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except AmigoInvisibleError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrumpido.", file=sys.stderr)
        return 130
    except smtplib.SMTPAuthenticationError:
        print(
            "Error: el servidor rechazó el usuario o la contraseña. Con Gmail necesitas una "
            "«contraseña de aplicación» (consulta el README).",
            file=sys.stderr,
        )
        return 2
    except (smtplib.SMTPException, OSError) as exc:
        print(f"Error de conexión con el servidor de correo: {exc}", file=sys.stderr)
        return 2
