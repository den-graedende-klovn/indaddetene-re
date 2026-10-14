"""Lydhjælpere: stilhed, trimning, afkodning og MP3 via ffmpeg."""

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 24000


def stilhed(sekunder):
    return np.zeros(int(SR * max(0.0, sekunder)), dtype=np.float32)


def trim(x, taerskel_db=-42.0, polstring=0.03):
    """Fjerner stilhed i start og slut, relativt til lydens højeste niveau."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if x.size == 0:
        return x
    top = float(np.max(np.abs(x)))
    if top <= 0:
        return x[:0]
    graense = top * (10 ** (taerskel_db / 20))
    vindue = max(1, int(SR * 0.01))
    n = x.size // vindue
    if n == 0:
        return x
    rms = np.sqrt(np.mean(x[: n * vindue].reshape(n, vindue) ** 2, axis=1))
    hoej = np.where(rms > graense)[0]
    if hoej.size == 0:
        return x[:0]
    pad = int(SR * polstring)
    start = max(0, hoej[0] * vindue - pad)
    slut = min(x.size, (hoej[-1] + 1) * vindue + pad)
    return x[start:slut]


def afkod(sti):
    """Afkoder en vilkårlig lydfil til mono float32 ved SR."""
    res = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(sti), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True,
    )
    return np.frombuffer(res.stdout, dtype=np.float32).copy()


def gem_wav(x, sti):
    x = np.clip(np.asarray(x, dtype=np.float32), -1.0, 1.0)
    with wave.open(str(sti), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def gem_mp3(x, sti, titel, album):
    """Gemmer som MP3 med podcast-lydstyrke (-16 LUFS)."""
    sti = Path(sti)
    sti.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "afsnit.wav"
        gem_wav(x, wav)
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y", "-i", str(wav),
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar", "44100", "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "64k",
                "-metadata", f"title={titel}", "-metadata", f"album={album}",
                "-metadata", f"artist={album}", "-id3v2_version", "3",
                str(sti),
            ],
            check=True,
        )
    return sti.stat().st_size
