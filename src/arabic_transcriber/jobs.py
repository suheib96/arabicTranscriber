"""Desktop jobs supervise isolated workers; heavy calls cannot trap the UI process."""

import multiprocessing as mp
import tempfile
import threading
import time
from copy import deepcopy
from pathlib import Path

from .media import (
    Cancelled,
    audio_segments,
    check_cancel,
    decode,
    download_audio,
    is_silent,
    youtube_url,
)
from .runlog import event


def _pipeline(send, cancel, directory, source, value, options, recognizer, downloader, seconds):
    """Spawn entry point: all model/media libraries and their memory live here."""
    phase = "Vorbereiten"

    def report(stage, progress=None):
        nonlocal phase
        check_cancel(cancel)
        phase = stage
        send.send({"kind": "stage", "stage": stage, "progress": progress})

    try:
        directory = Path(directory)
        if source == "youtube":
            report("Audio laden")
            path = downloader(value, directory, cancel, report)
        else:
            path = Path(value)
        check_cancel(cancel)
        wav = decode(path, directory, cancel, report)
        loaded = False
        for start, end, total, audio in audio_segments(wav, seconds):
            check_cancel(cancel)
            if not is_silent(audio):
                if recognizer is None:
                    from .model import CohereRecognizer

                    recognizer = CohereRecognizer()
                if not loaded:
                    recognizer.load(options, cancel, report)
                    options.pop("token", None)
                    loaded = True
                check_cancel(cancel)
                report("Transkribieren", start / total)
                text = recognizer.transcribe(audio, cancel).strip()
                check_cancel(cancel)
                if text:
                    send.send(
                        {"kind": "segment", "segment": {"start": start, "end": end, "text": text}}
                    )
            report("Transkribieren", end / total)
        check_cancel(cancel)
        send.send({"kind": "done"})
    except Cancelled:
        send.send({"kind": "cancelled"})
    except Exception as error:
        message = (
            str(error)
            if isinstance(error, (ValueError, RuntimeError))
            else ("Verarbeitung fehlgeschlagen. Bitte erneut versuchen.")
        )
        send.send(
            {"kind": "error", "error": message, "error_type": type(error).__name__, "stage": phase}
        )
    finally:
        options.clear()
        send.close()


def _stop(process):
    """Stop only this job and its FFmpeg/Node descendants, including blocked calls."""
    if process.pid is None:
        return
    import psutil

    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except (psutil.Error, OSError):
        descendants = []
    for child in descendants:
        try:
            child.terminate()
        except (psutil.Error, OSError):
            pass
    if process.is_alive():
        process.terminate()
        process.join(0.4)
    if process.is_alive():
        process.kill()
        process.join(0.4)
    for child in descendants:
        try:
            if child.is_running():
                child.kill()
        except (psutil.Error, OSError):
            pass


class Job:
    def __init__(self, recognizer=None, downloader=download_audio, segment_seconds=12):
        self._lock = threading.RLock()
        self._context = mp.get_context("spawn")
        self._cancel = None
        self._cancel_started = None
        self._started = None
        self._thread = None
        self._recognizer = recognizer
        self._downloader = downloader
        self._seconds = segment_seconds
        self._state = {
            "status": "idle",
            "stage": "Bereit",
            "progress": None,
            "segments": [],
            "error": None,
            "revision": 0,
        }

    def snapshot(self):
        with self._lock:
            state = deepcopy(self._state)
            state["elapsed_seconds"] = int(time.monotonic() - self._started) if self._started else 0
            return state

    def _update(self, **fields):
        with self._lock:
            self._state.update(fields)
            self._state["revision"] += 1

    def start(self, source, value, options):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"ok": False, "error": "Ein Auftrag läuft bereits."}
            if source not in ("file", "youtube"):
                return {"ok": False, "error": "Unbekannte Eingabequelle."}
            if source == "file" and not Path(value).is_file():
                return {"ok": False, "error": "Datei nicht gefunden. Bitte erneut auswählen."}
            if source == "youtube" and not youtube_url(value):
                return {
                    "ok": False,
                    "error": "Bitte einen gültigen HTTPS-YouTube-Videolink eingeben.",
                }
            if options.get("device", "cpu") not in ("cpu", "cuda", "mps"):
                return {"ok": False, "error": "Ungültiges Ausführungsgerät."}
            self._cancel = self._context.Event()
            self._cancel_started = None
            self._started = time.monotonic()
            self._update(
                status="running", stage="Vorbereiten", progress=None, segments=[], error=None
            )
            self._thread = threading.Thread(
                target=self._run,
                args=(source, value, dict(options)),
                daemon=True,
                name="transcription-supervisor",
            )
            self._thread.start()
            return {"ok": True}

    def cancel(self):
        with self._lock:
            if self._state["status"] == "running":
                self._cancel_started = time.monotonic()
                self._cancel.set()
                self._update(status="cancelling", stage="Abbrechen", progress=None)

    def close(self):
        self.cancel()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(2)

    def _run(self, source, value, options):
        receive, send = self._context.Pipe(duplex=False)
        process = None
        outcome = "error"
        message = "Verarbeitung wurde unterbrochen. Bitte erneut versuchen."
        last_metrics = 0
        try:
            with tempfile.TemporaryDirectory(prefix="arabic-transcriber-") as directory:
                process = self._context.Process(
                    target=_pipeline,
                    args=(
                        send,
                        self._cancel,
                        directory,
                        source,
                        value,
                        options,
                        self._recognizer,
                        self._downloader,
                        self._seconds,
                    ),
                    name="transcription-worker",
                    daemon=True,
                )
                process.start()
                send.close()
                options.clear()
                event("started", pid=process.pid)
                while True:
                    if self._cancel.is_set() and time.monotonic() - self._cancel_started >= 0.5:
                        outcome = "cancelled"
                        break
                    if receive.poll(0.05):
                        try:
                            update = receive.recv()
                        except EOFError:
                            break
                        kind = update["kind"]
                        if kind == "stage" and not self._cancel.is_set():
                            if update["stage"] != self._state["stage"]:
                                event(
                                    "stage",
                                    phase=update["stage"],
                                    elapsed_s=round(time.monotonic() - self._started, 2),
                                )
                            self._update(stage=update["stage"], progress=update["progress"])
                        elif kind == "segment" and not self._cancel.is_set():
                            self._update(segments=[*self._state["segments"], update["segment"]])
                        elif kind in ("done", "cancelled", "error"):
                            outcome = {
                                "done": "completed",
                                "cancelled": "cancelled",
                                "error": "error",
                            }[kind]
                            message = update.get("error", message)
                            if kind == "error":
                                event(
                                    "failed",
                                    phase=update.get("stage"),
                                    error_type=update.get("error_type"),
                                )
                            break
                    elif not process.is_alive():
                        break
                    if time.monotonic() - last_metrics > 5:
                        import psutil

                        try:
                            event(
                                "resources",
                                phase=self._state["stage"],
                                rss_mb=round(psutil.Process(process.pid).memory_info().rss / 2**20),
                                available_mb=round(psutil.virtual_memory().available / 2**20),
                                elapsed_s=round(time.monotonic() - self._started, 2),
                            )
                        except (psutil.Error, OSError):
                            pass
                        last_metrics = time.monotonic()
                if self._cancel.is_set():
                    outcome = "cancelled"
                # Worker exit releases model memory even on success; do not retain 8+ GB while idle.
                process.join(0.2)
                _stop(process)
                event(
                    "finished", status=outcome, elapsed_s=round(time.monotonic() - self._started, 2)
                )
        except Exception as error:
            event("failed", error_type=type(error).__name__)
            outcome = "cancelled" if self._cancel.is_set() else "error"
        finally:
            if process:
                _stop(process)
                process.close()
            send.close()
            receive.close()
            options.clear()
        self._update(
            status=outcome,
            stage={"completed": "Fertig", "cancelled": "Abgebrochen", "error": "Unterbrochen"}[
                outcome
            ],
            progress=1 if outcome == "completed" else None,
            error=message if outcome == "error" else None,
        )
