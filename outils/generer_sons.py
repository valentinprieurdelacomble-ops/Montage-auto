"""Crée des bruitages de base (whoosh, pop) libres de droits, fabriqués par calcul.

Ils servent de point de départ : remplace-les par tes propres sons quand tu veux
(voir assets/sfx/LISEZMOI.md)."""
import wave
from pathlib import Path

import numpy as np

SR = 48000
DOSSIER = Path(__file__).resolve().parent.parent / "assets" / "sfx"
rng = np.random.default_rng(7)


def ecrire(chemin: Path, x: np.ndarray) -> None:
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def whoosh(duree=0.55, f0=300, f1=4500, pic=0.6):
    n = int(SR * duree)
    t = np.linspace(0, 1, n)
    bruit = rng.standard_normal(n)
    # filtre passe-bas dont la fréquence monte puis redescend (effet de souffle qui passe)
    fc = f0 + (f1 - f0) * np.sin(np.pi * np.clip(t / (2 * pic), 0, 1)) ** 2
    a = np.exp(-2 * np.pi * fc / SR)
    y, prec = np.zeros(n), 0.0
    for i in range(n):
        prec = (1 - a[i]) * bruit[i] + a[i] * prec
        y[i] = prec
    for _ in range(1):  # 2e passage : plus doux
        prec = 0.0
        for i in range(n):
            prec = (1 - a[i]) * y[i] + a[i] * prec
            y[i] = prec
    env = np.where(t < pic, (t / pic) ** 2, ((1 - t) / (1 - pic)) ** 1.5)
    return y * env


def pop(duree=0.09, f0=1400, f1=380):
    n = int(SR * duree)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 60)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t * 55) * np.minimum(1, t * SR / 40)


def click(duree=0.03):
    n = int(SR * duree)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2600 * t) + 0.4 * rng.standard_normal(n)) * np.exp(-t * 260)


if __name__ == "__main__":
    ecrire(DOSSIER / "whoosh" / "whoosh_base_1.wav", whoosh())
    ecrire(DOSSIER / "whoosh" / "whoosh_base_2.wav", whoosh(0.45, 400, 6000, 0.55))
    ecrire(DOSSIER / "pop" / "pop_base_1.wav", pop())
    ecrire(DOSSIER / "pop" / "click_base_1.wav", click())
    print("Sons créés dans", DOSSIER)
