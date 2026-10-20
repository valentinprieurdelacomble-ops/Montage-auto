"""Petits outils communs : config, appels FFmpeg, messages."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent


class ErreurMontage(Exception):
    """Erreur expliquée simplement à l'utilisateur."""


def info(msg: str) -> None:
    print(f"  • {msg}", flush=True)


def etape(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def attention(msg: str) -> None:
    print(f"  ⚠ {msg}", flush=True)


def charger_reglages(chemin: Path | None = None) -> dict:
    chemin = chemin or RACINE / "reglages.yaml"
    with open(chemin, encoding="utf-8") as f:
        return yaml.safe_load(f)


def verifier_ffmpeg() -> None:
    for prog in ("ffmpeg", "ffprobe"):
        if shutil.which(prog) is None:
            raise ErreurMontage(
                f"{prog} est introuvable. Lance l'installateur (installer_windows.bat "
                "ou installer_mac.command) puis ferme et rouvre ton terminal."
            )


def lancer(cmd: list[str], cwd: Path | None = None, capture: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=capture,
        text=True, encoding="utf-8", errors="replace",
    )
    if res.returncode != 0:
        fin = (res.stderr or "")[-3000:]
        raise ErreurMontage(f"La commande {Path(str(cmd[0])).name} a échoué :\n{fin}")
    return res


def sonder(video: Path) -> dict:
    res = lancer(["ffprobe", "-v", "error", "-print_format", "json",
                  "-show_format", "-show_streams", video])
    return json.loads(res.stdout)


def version_ffmpeg() -> int:
    """Numéro de version majeur (les versions 'git' récentes renvoient 99)."""
    res = lancer(["ffmpeg", "-version"])
    m = re.match(r"ffmpeg version n?(\d+)", res.stdout)
    return int(m.group(1)) if m else 99


def option_script_filtre() -> str:
    # FFmpeg 7+ : "-/filter_complex fichier" ; avant : "-filter_complex_script"
    return "-/filter_complex" if version_ffmpeg() >= 7 else "-filter_complex_script"


def filtre_disponible(nom: str) -> bool:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    return re.search(rf"^\s*\S+\s+{re.escape(nom)}\s", res.stdout, re.M) is not None


def couleur_ass(hexa: str, alpha: int = 0) -> str:
    """'#246BFD' -> '&H00FD6B24' (format ASS : alpha, bleu, vert, rouge)."""
    h = hexa.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()
