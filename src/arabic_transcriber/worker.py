"""One isolated, reusable model process. Never starts a second media pipeline."""

import time
from pathlib import Path

from .media import Cancelled, audio_segments, check_cancel, decode, is_silent


class Signal:
    """Versioned shared signal; termination cannot poison an Event's lock."""

    def __init__(self, context):
        self.value = context.RawValue("q", 0)
        self._generation = 0

    def is_set(self):
        return bool(self.value.value)

    def set(self):
        self._generation += 1
        self.value.value = self._generation

    def clear(self):
        self.value.value = 0


def stop_process(process):
    """Bounded shutdown, including this worker's FFmpeg/Node descendants."""
    if process is None or process.pid is None:
        return
    import psutil

    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except (psutil.Error, OSError):
        children = []
    for child in children:
        try:
            child.terminate()
        except psutil.Error:
            pass
    if process.is_alive():
        process.terminate()
        process.join(0.3)
    if process.is_alive():
        process.kill()
        process.join(0.3)
    _, alive = psutil.wait_procs(children, timeout=0.2)
    for child in alive:
        try:
            child.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(alive, timeout=0.2)


def serve(connection, cancel, pause, recognizer, downloader, seconds):
    """Keep exactly one recognizer alive across successive run commands."""
    loaded = False
    while True:
        command = connection.recv()
        if command["kind"] == "stop":
            return
        item = command["item"]
        phase = "Vorbereiten"
        loading = False

        def send(kind, **fields):
            connection.send({"kind": kind, "id": item["id"], **fields})

        def checkpoint():
            check_cancel(cancel)
            acknowledged = None
            while pause.is_set():
                check_cancel(cancel)
                generation = pause.value.value
                if generation != acknowledged:
                    send("paused", generation=generation)
                    acknowledged = generation
                time.sleep(0.03)

        def report(stage, progress=None):
            nonlocal phase
            checkpoint()
            phase = stage
            send("stage", stage=stage, progress=progress)

        try:
            checkpoint()
            directory = Path(item["directory"])
            wav = directory / "decoded.wav"
            if not item.get("decoded_ready"):
                path = Path(item.get("download_path") or item["value"])
                if item["source"] == "youtube" and not item.get("download_path"):
                    path = downloader(item["value"], directory, cancel, report)
                    send("downloaded", path=str(path))
                wav = decode(path, directory, cancel, report)
                send("prepared")
            for start, end, total, audio in audio_segments(wav, seconds, item.get("offset", 0)):
                checkpoint()
                text = ""
                if not is_silent(audio):
                    if recognizer is None:
                        from .model import CohereRecognizer

                        recognizer = CohereRecognizer()
                    if not loaded:
                        loading = True
                        recognizer.load(command["options"], cancel, report)
                        command["options"].pop("token", None)
                        loading = False
                        loaded = True
                        send("model_loaded")
                    report("Transkribieren", start / total)
                    text = recognizer.transcribe(audio, cancel).strip()
                    check_cancel(cancel)
                # Text and resume offset are committed in a single IPC message.
                send("checkpoint", start=start, end=end, total=total, text=text)
                if end < total:
                    checkpoint()
            check_cancel(cancel)
            send("done")
        except Cancelled:
            send("cancelled")
        except Exception as error:
            message = (
                str(error)
                if isinstance(error, (ValueError, RuntimeError))
                else "Verarbeitung fehlgeschlagen. Bitte erneut versuchen."
            )
            send(
                "error",
                error=message,
                blocked=loading,
                error_type=type(error).__name__,
                stage=phase,
            )
        finally:
            command.get("options", {}).clear()
