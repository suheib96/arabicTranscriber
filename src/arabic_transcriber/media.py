"""Media I/O. Decode to temporary PCM on disk; never load a whole movie into RAM."""

import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np


class Cancelled(Exception):
    pass


def check_cancel(cancel):
    if cancel.is_set():
        raise Cancelled()


def tool(name):
    suffix = ".exe" if os.name == "nt" else ""
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "tools" / (name + suffix)
    if bundled.is_file():
        return str(bundled)
    if not getattr(sys, "frozen", False):
        prepared = Path(__file__).resolve().parents[2] / "build" / "tools" / (name + suffix)
        if prepared.is_file():
            return str(prepared)
    if name == "ffmpeg":
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} fehlt. Bitte vollständiges App-Paket installieren.")
    return found


def youtube_url(value):
    try:
        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
            return False
        parts = parsed.path.strip("/").split("/")
        if parsed.hostname == "youtu.be":
            return len(parts) == 1 and bool(parts[0])
        if parsed.hostname not in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
        }:
            return False
        if parsed.path == "/watch":
            return bool(parse_qs(parsed.query).get("v", [""])[0])
        return len(parts) == 2 and parts[0] in ("shorts", "embed") and bool(parts[1])
    except (ValueError, AttributeError):
        return False


def download_audio(url, directory, cancel, report):
    if not youtube_url(url):
        raise ValueError("Bitte einen gültigen HTTPS-YouTube-Videolink eingeben.")
    import yt_dlp

    class QuietLogger:
        def debug(self, msg):
            pass

        def warning(self, msg):
            pass

        def error(self, msg):
            pass

    def hook(event):
        check_cancel(cancel)
        total = event.get("total_bytes") or event.get("total_bytes_estimate")
        fraction = min(event.get("downloaded_bytes", 0) / total, 1) if total else None
        report("Audio laden", fraction)

    options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "outtmpl": str(directory / "youtube.%(ext)s"),
        "progress_hooks": [hook],
        "logger": QuietLogger(),
        "socket_timeout": 15,
        "retries": 2,
        "ffmpeg_location": tool("ffmpeg"),
        "js_runtimes": {"node": {"path": tool("node")}},
        "remote_components": [],
        "cachedir": False,
        "match_filter": lambda info, **kw: (
            "Livestreams werden nicht unterstützt." if info.get("is_live") else None
        ),
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            check_cancel(cancel)
            info = downloader.extract_info(url, download=True)
            check_cancel(cancel)
            if not info or info.get("_type") == "playlist":
                raise ValueError("Bitte einen einzelnen verfügbaren Videolink verwenden.")
            return Path(downloader.prepare_filename(info))
    except Exception:
        check_cancel(cancel)
        raise RuntimeError(
            "YouTube-Audio nicht verfügbar. Verbindung, Videofreigabe und aktuelle "
            "App-Version prüfen. Private, geschützte oder gesperrte Videos können scheitern."
        ) from None


def decode(source, directory, cancel, report):
    target = directory / "decoded.wav"
    report("Audio vorbereiten", None)
    # Redirect both streams to disk: no unconsumed pipe can deadlock long inputs.
    with (directory / "decode.log").open("w+b") as log:
        process = subprocess.Popen(
            [
                tool("ffmpeg"),
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-threads",
                "1",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-rf64",
                "never",
                str(target),
            ],
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            while process.poll() is None:
                check_cancel(cancel)
                time.sleep(0.05)
            check_cancel(cancel)
            if process.returncode:
                raise ValueError(
                    "Audio kann nicht gelesen werden. Eine abspielbare Audio- oder "
                    "Videodatei ohne Kopierschutz auswählen."
                )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return target


def audio_segments(path, seconds=24):
    """Contiguous windows with a nearby quiet cut. No overlap or timeline compression."""
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        frames = wav.getnframes()
        if not frames:
            raise ValueError("Die Datei enthält kein Audio.")
        position = 0
        while position < frames:
            wav.setpos(position)
            samples = np.frombuffer(wav.readframes(int(seconds * rate)), dtype="<i2")
            count = len(samples)
            if position + count < frames and count > rate * 3:
                # Prefer the quietest 100 ms in the last two seconds of the window.
                blocks = samples[-2 * rate :].astype(np.float32).reshape(-1, rate // 10)
                energy = np.mean(blocks**2, axis=1)
                quiet = int(np.argmin(energy))
                if energy[quiet] < 120**2:
                    count = count - 2 * rate + (quiet + 1) * (rate // 10)
                    samples = samples[:count]
            audio = samples.astype(np.float32) / 32768
            start, end = position / rate, (position + count) / rate
            position += count
            yield start, end, frames / rate, audio


def is_silent(audio):
    # Conservative all-window threshold. No second speech model; quiet speech may remain.
    return not len(audio) or float(np.max(np.abs(audio))) < 0.003
