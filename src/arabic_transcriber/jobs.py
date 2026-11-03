"""One background transcription job with immutable, revisioned desktop snapshots."""

import tempfile
import threading
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


class Job:
    def __init__(self, recognizer=None, downloader=download_audio, segment_seconds=24):
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._thread = None
        self._recognizer = recognizer
        self._downloader = downloader
        self._seconds = segment_seconds
        self._state = {
            "status": "idle",
            "stage": "Bereit für deine Aufnahme",
            "progress": None,
            "segments": [],
            "error": None,
            "revision": 0,
        }

    def snapshot(self):
        with self._lock:
            return deepcopy(self._state)

    def _update(self, **fields):
        with self._lock:
            self._state.update(fields)
            self._state["revision"] += 1

    def _report(self, stage, progress=None):
        check_cancel(self._cancel)
        self._update(stage=stage, progress=progress)

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
            self._cancel.clear()
            self._update(
                status="running",
                stage="Auftrag wird vorbereitet",
                progress=None,
                segments=[],
                error=None,
            )
            self._thread = threading.Thread(
                target=self._run,
                args=(source, value, dict(options)),
                daemon=True,
                name="transcription",
            )
            self._thread.start()
            return {"ok": True}

    def cancel(self):
        with self._lock:
            if self._state["status"] == "running":
                self._cancel.set()
                self._update(status="cancelling", stage="Wird abgebrochen …", progress=None)

    def _run(self, source, value, options):
        try:
            with tempfile.TemporaryDirectory(prefix="arabic-transcriber-") as temp:
                directory = Path(temp)
                if source == "youtube":
                    self._report("YouTube wird geöffnet")
                    path = self._downloader(value, directory, self._cancel, self._report)
                else:
                    path = Path(value)
                check_cancel(self._cancel)
                wav = decode(path, directory, self._cancel, self._report)
                loaded = False
                for start, end, total, audio in audio_segments(wav, self._seconds):
                    check_cancel(self._cancel)
                    if not is_silent(audio):
                        if self._recognizer is None:
                            from .model import CohereRecognizer

                            self._recognizer = CohereRecognizer()
                        if not loaded:
                            self._recognizer.load(options, self._cancel, self._report)
                            options.pop("token", None)
                            loaded = True
                        check_cancel(self._cancel)
                        self._report("Arabisch wird transkribiert", start / total)
                        text = self._recognizer.transcribe(audio, self._cancel).strip()
                        check_cancel(self._cancel)
                        if text:
                            with self._lock:
                                segments = [
                                    *self._state["segments"],
                                    {"start": start, "end": end, "text": text},
                                ]
                                self._update(segments=segments)
                    self._report("Arabisch wird transkribiert", end / total)
                check_cancel(self._cancel)
                self._update(status="completed", stage="Transkription abgeschlossen", progress=1)
        except Cancelled:
            self._update(
                status="cancelled",
                stage="Abgebrochen · erkannte Abschnitte bleiben erhalten",
                progress=None,
            )
        except Exception as error:
            # Only our user-facing errors cross the bridge; model/network exceptions can contain tokens.
            message = (
                str(error)
                if isinstance(error, (ValueError, RuntimeError))
                else (
                    "Verarbeitung fehlgeschlagen. Datei, Modellzugang und freien Speicher prüfen."
                )
            )
            self._update(status="error", stage="Auftrag unterbrochen", error=message, progress=None)
        finally:
            options.clear()
