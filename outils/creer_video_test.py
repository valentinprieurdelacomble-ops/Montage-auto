"""Fabrique une fausse vidéo brute pour tester le système (nécessite espeak-ng).

Voix de synthèse française dite mot par mot, avec des blancs et des « euh ».
Le mot prononcé est écrit en petit en haut à gauche de l'image : après montage,
on peut vérifier que les sous-titres tombent pile sur le bon mot.
Écrit aussi la transcription exacte (verite.json) pour tester sans Whisper."""
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 48000
TEXTE = [
    ("Tu", 0), ("veux", 0), ("parler", 0), ("avec", 0), ("charisme", 0), ("?", 1.4),
    ("Arrête", 0), ("de", 0), ("remplir", 0), ("tes", 0), ("silences.", 1.1),
    ("euh", 0.5), ("Le", 0), ("silence", 0), ("est", 0), ("ton", 0), ("meilleur", 0), ("allié.", 0.9),
    ("Voici", 0), ("trois", 0), ("règles", 0), ("simples.", 1.2),
    ("Un,", 0.3), ("ralentis", 0), ("ton", 0), ("débit.", 0.8),
    ("Deux,", 0.3), ("regarde", 0), ("ton", 0), ("public", 0), ("dans", 0), ("les", 0), ("yeux.", 1.5),
    ("euh", 0.6), ("Trois,", 0.3), ("fais", 0), ("une", 0), ("pause", 0), ("avant", 0), ("ta", 0),
    ("phrase", 0), ("importante.", 1.0),
    ("Quatre-vingts", 0), ("pour", 0), ("cent", 0), ("de", 0), ("ton", 0), ("impact", 0), ("vient", 0),
    ("de", 0), ("ta", 0), ("voix,", 0.3), ("pas", 0), ("de", 0), ("tes", 0), ("mots.", 1.3),
    ("Alors", 0), ("essaie", 0), ("dès", 0), ("aujourd'hui.", 0.8),
]


def dire(mot: str, dossier: Path) -> np.ndarray:
    f = dossier / "m.wav"
    subprocess.run(["espeak-ng", "-v", "fr", "-s", "165", "-p", "40", "-w", str(f), mot.strip("?,.")],
                   check=True)
    with wave.open(str(f)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    fort = np.where(np.abs(x) > 0.02)[0]
    return x[fort[0]:fort[-1] + 1] if len(fort) else x


def main(sortie: Path):
    sortie.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(1)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        morceaux, mots, t = [np.zeros(int(SR * 0.8))], [], 0.8
        for mot, pause in TEXTE:
            if mot == "?":
                mots[-1]["texte"] += " ?"
            else:
                x = dire(mot, tmp) * (0.25 if mot == "euh" else 0.5)
                mots.append({"texte": mot, "debut": round(t, 3), "fin": round(t + len(x) / SR, 3)})
                morceaux.append(x)
                t += len(x) / SR
                pause = pause or 0.07
            morceaux.append(np.zeros(int(SR * pause)))
            t += pause
        morceaux.append(np.zeros(int(SR * 1.0)))
        audio = np.concatenate(morceaux)
        audio += rng.standard_normal(len(audio)) * 0.0015  # léger bruit de pièce
        duree = len(audio) / SR
        wav = tmp / "voix.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())

        police = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "InterDisplay-ExtraBold.ttf"
        (tmp / "f.ttf").write_bytes(police.read_bytes())
        textes = [f"drawtext=fontfile=f.ttf:text='{m['texte'].replace(chr(39), '')}':x=40:y=60:fontsize=54:"
                  f"fontcolor=yellow:enable='between(t,{m['debut']},{m['fin']})'" for m in mots]
        filtre = ("[0:v]drawbox=x=340:y=420:w=400:h=520:color=0xC9A07A@1:t=fill,"
                  "drawbox=x=240:y=1000:w=600:h=920:color=0x2B3A55@1:t=fill,"
                  "drawtext=fontfile=f.ttf:text='SOURCE %{pts\\:hms}':x=40:y=1820:fontsize=40:fontcolor=white,"
                  + ",".join(textes) + "[v]")
        (tmp / "filtre.txt").write_text(filtre, encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"gradients=s=1080x1920:r=30:d={duree}:c0=0x30343c:c1=0x1a1c22:speed=0.01",
                        "-i", str(wav), "-filter_complex_script", "filtre.txt", "-map", "[v]", "-map", "1:a",
                        "-c:v", "libx265", "-preset", "fast", "-pix_fmt", "yuv420p", "-x265-params", "log-level=error", "-tag:v", "hvc1", "-c:a", "aac", "-ac", "2",
                        "-t", f"{duree:.3f}", str(sortie.resolve())], check=True, cwd=tmp)
    verite = sortie.with_name(sortie.stem + "_verite.json")
    verite.write_text(json.dumps({"mots": mots}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Vidéo de test : {sortie} ({duree:.1f} s) ; transcription exacte : {verite}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "a_monter/test_eloquence.mov"))
