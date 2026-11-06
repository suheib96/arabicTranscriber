"""Thread-safe FIFO, selected transcripts and an isolated reusable model worker."""

import math
import multiprocessing as mp
import tempfile
import threading
import time
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from .media import download_audio, youtube_title, youtube_url
from .runlog import event
from .worker import Signal, serve, stop_process

TERMINAL = {"completed", "cancelled", "error"}


class Job:
    def __init__(
        self,
        recognizer=None,
        downloader=download_audio,
        segment_seconds=12,
        pause_retention_seconds=300,
        title_resolver=youtube_title,
    ):
        self._condition = threading.Condition(threading.RLock())
        self._context = mp.get_context("spawn")
        self._recognizer = recognizer
        self._downloader = downloader
        self._seconds = segment_seconds
        self._title_resolver = title_resolver
        self._items = []
        self._work = {}
        self._selected = None
        self._active = None
        self._options = {}
        self._closed = False
        self._process = None
        self._connection = None
        self._cancel = None
        self._cancel_at = None
        self._model_loaded = False
        self._blocked = None
        self._paused = False
        self._paused_since = None
        self._pause_ack = False
        self._pause = None
        self._retention = max(0, pause_retention_seconds)
        self._release_requested = False
        self._releasing = False
        self._worker_settings = None
        self._last_metrics = 0
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="transcription-supervisor"
        )
        self._thread.start()
        self._metadata_thread = threading.Thread(
            target=self._resolve_titles, daemon=True, name="youtube-titles"
        )
        self._metadata_thread.start()

    def _find(self, identifier):
        return next((item for item in self._items if item["id"] == identifier), None)

    def snapshot(self):
        with self._condition:
            selected = self._find(self._selected)
            now = time.monotonic()
            summaries = []
            for item in self._items:
                summary = {
                    k: v
                    for k, v in item.items()
                    if k
                    not in (
                        "segments",
                        "started",
                        "offset",
                        "finished",
                        "paused_at",
                        "resume_stage",
                    )
                }
                end = item.get("finished") or item.get("paused_at") or now
                summary["elapsed_seconds"] = int(end - item["started"]) if item["started"] else 0
                summaries.append(summary)
            return deepcopy(
                {
                    "items": summaries,
                    "selected_id": self._selected,
                    "active_id": self._active,
                    "model_loaded": self._model_loaded,
                    "worker_running": self._process is not None,
                    "queue_error": self._find(self._blocked)["error"]
                    if self._blocked and self._find(self._blocked)
                    else None,
                    "blocked": bool(self._blocked),
                    "paused": self._paused,
                    "pausing": bool(self._paused and self._active and not self._pause_ack),
                    "releasing_memory": self._releasing or self._release_requested,
                    "release_in_seconds": max(
                        0, math.ceil(self._retention - (now - self._paused_since))
                    )
                    if self._paused_since is not None and self._process
                    else None,
                    "status": selected["status"] if selected else "idle",
                    "stage": selected["stage"] if selected else "Bereit",
                    "progress": selected["progress"] if selected else None,
                    "segments": selected["segments"] if selected else [],
                    "error": selected["error"] if selected else None,
                    "elapsed_seconds": int(
                        (selected.get("finished") or selected.get("paused_at") or now)
                        - selected["started"]
                    )
                    if selected and selected["started"]
                    else 0,
                }
            )

    def start(self, source, value, options=None):
        value = value.strip()
        options = dict(options or {})
        if source not in ("file", "youtube"):
            return {"ok": False, "error": "Unbekannte Eingabequelle."}
        if source == "file" and not Path(value).is_file():
            return {"ok": False, "error": "Datei nicht gefunden. Bitte erneut auswählen."}
        if source == "youtube" and not youtube_url(value):
            return {"ok": False, "error": "Bitte einen gültigen HTTPS-YouTube-Videolink eingeben."}
        if options.get("device", "cpu") not in ("cpu", "cuda", "mps"):
            return {"ok": False, "error": "Ungültiges Ausführungsgerät."}
        with self._condition:
            if self._closed:
                return {"ok": False, "error": "Die App wird geschlossen."}
            pending = any(i["status"] not in TERMINAL for i in self._items)
            if not pending:
                self._options = options
            elif options.get("token"):
                self._options["token"] = options["token"]
            item = {
                "id": uuid4().hex,
                "source": source,
                "value": value,
                "title": Path(value).name if source == "file" else value,
                "metadata_status": "pending" if source == "youtube" else "ready",
                "status": "queued",
                "stage": "Wartet",
                "progress": None,
                "error": None,
                "segments": [],
                "started": None,
                "offset": 0,
            }
            self._items.append(item)
            if self._selected is None:
                self._selected = item["id"]
            self._condition.notify_all()
            return {"ok": True, "id": item["id"]}

    def select(self, identifier):
        with self._condition:
            if not self._find(identifier):
                return {"ok": False, "error": "Auftrag nicht gefunden."}
            self._selected = identifier
            return {"ok": True}

    def pause(self):
        with self._condition:
            if not self._paused:
                self._paused = True
                self._paused_since = time.monotonic()
                self._pause_ack = False
                if self._pause:
                    self._pause.set()
            self._condition.notify_all()
            return {"ok": True}

    def resume(self, options=None):
        with self._condition:
            if not self._paused:
                return {"ok": True}
            options = options or {}
            if options.get("device", self._options.get("device", "cpu")) not in (
                "cpu",
                "cuda",
                "mps",
            ):
                return {"ok": False, "error": "Ungültiges Ausführungsgerät."}
            if options:
                old_device = self._options.get("device", "cpu")
                old_offline = self._options.get("offline", False)
                self._options.update({k: v for k, v in options.items() if k != "token" or v})
                if (
                    self._options.get("device", "cpu") != old_device
                    or self._options.get("offline", False) != old_offline
                ):
                    self._release_requested = True
            if self._blocked:
                self._release_requested = True
                item = self._find(self._blocked)
                if item:
                    item.update(status="queued", error=None, stage="Wartet")
                self._blocked = None
            self._paused = False
            self._paused_since = None
            self._pause_ack = False
            if self._pause:
                self._pause.clear()
            for item in self._items:
                if item.get("paused_at"):
                    item["started"] += time.monotonic() - item.pop("paused_at")
                if item["id"] == self._active and item["status"] == "paused":
                    item.update(status="running", stage=item.pop("resume_stage", "Transkribieren"))
            self._condition.notify_all()
            return {"ok": True}

    def release_memory(self):
        with self._condition:
            if not self._paused:
                return {"ok": False, "error": "Bitte die Warteschlange zuerst pausieren."}
            self._release_requested = True
            self._condition.notify_all()
            return {"ok": True}

    def cancel(self, identifier=None):
        with self._condition:
            item = self._find(identifier or self._active)
            if item and item["status"] not in TERMINAL:
                if item["id"] == self._active:
                    item.update(status="cancelling", stage="Abbrechen")
                    self._cancel_at = time.monotonic()
                else:
                    item.update(
                        status="cancelled",
                        stage="Abgebrochen",
                        finished=item.pop("paused_at", None) or time.monotonic(),
                    )
                    work = self._work.pop(item["id"], None)
                    if work:
                        work["temporary"].cleanup()
                self._condition.notify_all()
            return {"ok": True}

    def remove(self, identifier):
        with self._condition:
            item = self._find(identifier)
            if not item or identifier == self._active:
                return {"ok": False, "error": "Laufenden Auftrag zuerst abbrechen."}
            self._items.remove(item)
            work = self._work.pop(identifier, None)
            if work:
                work["temporary"].cleanup()
            if self._blocked == identifier:
                self._blocked = None
            if identifier == self._selected:
                self._selected = self._items[0]["id"] if self._items else None
            self._condition.notify_all()
            return {"ok": True}

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        self._thread.join(3)

    def _resolve_titles(self):
        while True:
            with self._condition:
                if self._closed:
                    return
                item = next((i for i in self._items if i["metadata_status"] == "pending"), None)
                if not item:
                    self._condition.wait(0.2)
                    continue
                item["metadata_status"] = "loading"
                identifier, value = item["id"], item["value"]
            try:
                title = self._title_resolver(value)
            except Exception:
                title = None
            with self._condition:
                current = self._find(identifier)
                if current:
                    if title:
                        current["title"] = str(title)[:500]
                    current["metadata_status"] = "ready" if title else "unavailable"
                self._condition.notify_all()

    def _spawn(self):
        self._worker_settings = (
            self._options.get("device", "cpu"),
            self._options.get("offline", False),
        )
        self._cancel = Signal(self._context)
        self._pause = Signal(self._context)
        if self._paused:
            self._pause.set()
        parent, child = self._context.Pipe()
        self._connection = parent
        self._process = self._context.Process(
            target=serve,
            args=(
                child,
                self._cancel,
                self._pause,
                self._recognizer,
                self._downloader,
                self._seconds,
            ),
            daemon=True,
            name="transcription-worker",
        )
        self._process.start()
        child.close()

    def _release(self):
        if self._process is None:
            return
        with self._condition:
            self._releasing = True
        try:
            if not self._active:
                self._connection.send({"kind": "stop"})
                self._process.join(0.15)
        except (OSError, EOFError):
            pass
        stop_process(self._process)
        self._process.close()
        self._connection.close()
        self._process = self._connection = self._cancel = self._pause = None
        with self._condition:
            self._model_loaded = False
            self._releasing = False
            self._condition.notify_all()

    def _finish(self, item, status, error=None):
        item.update(
            status=status,
            stage={"completed": "Fertig", "cancelled": "Abgebrochen", "error": "Fehler"}[status],
            error=error,
            finished=item.pop("paused_at", None) or time.monotonic(),
        )
        if status == "completed":
            item["progress"] = 1
        self._active = None
        self._cancel_at = None
        work = None if self._blocked == item["id"] else self._work.pop(item["id"], None)
        if work:
            work["temporary"].cleanup()
        event("finished", status=status)

    def _message(self, message):
        with self._condition:
            item = self._find(message["id"])
            if not item or item["id"] != self._active:
                return
            kind = message["kind"]
            if kind == "model_loaded":
                self._model_loaded = True
                self._options.pop("token", None)
            elif kind == "downloaded":
                self._work[item["id"]]["download_path"] = message["path"]
            elif kind == "prepared":
                self._work[item["id"]]["decoded_ready"] = True
            elif (
                kind == "paused"
                and self._paused
                and not self._cancel_at
                and message["generation"] == self._pause.value.value
            ):
                if not self._pause_ack:
                    self._paused_since = time.monotonic()
                self._pause_ack = True
                item.update(
                    status="paused",
                    resume_stage=item["stage"],
                    stage="Pausiert",
                    paused_at=time.monotonic(),
                )
            elif kind == "stage" and not self._cancel_at:
                if item["stage"] != message["stage"]:
                    event(
                        "stage",
                        phase=message["stage"],
                        elapsed_s=round(time.monotonic() - item["started"], 2),
                    )
                item.update(stage=message["stage"], progress=message["progress"])
            elif kind == "checkpoint":
                if message["text"]:
                    item["segments"].append({key: message[key] for key in ("start", "end", "text")})
                item.update(offset=message["end"], progress=message["end"] / message["total"])
            elif kind in ("done", "cancelled", "error"):
                status = (
                    "cancelled"
                    if self._cancel_at or kind == "cancelled"
                    else ("completed" if kind == "done" else "error")
                )
                if message.get("blocked"):
                    self._blocked = item["id"]
                    self._paused = True
                    self._paused_since = time.monotonic()
                if kind == "error":
                    event(
                        "failed", phase=message.get("stage"), error_type=message.get("error_type")
                    )
                if status == "cancelled":
                    self._release_requested = True
                self._finish(item, status, message.get("error"))

    def _run(self):
        try:
            while True:
                with self._condition:
                    if self._closed:
                        break
                if self._connection and self._connection.poll(0.02):
                    try:
                        self._message(self._connection.recv())
                    except (EOFError, OSError):
                        if self._active:
                            with self._condition:
                                self._finish(
                                    self._find(self._active),
                                    "error",
                                    "Verarbeitung wurde unterbrochen. Bitte erneut versuchen.",
                                )
                        self._release()
                with self._condition:
                    cancelled = self._cancel_at is not None
                    expired = cancelled and time.monotonic() - self._cancel_at >= 0.5
                    active = self._active
                if cancelled and self._cancel:
                    self._cancel.set()
                if expired:
                    self._release()
                    with self._condition:
                        self._finish(self._find(active), "cancelled")
                with self._condition:
                    timed_out = (
                        self._paused_since is not None
                        and time.monotonic() - self._paused_since >= self._retention
                    )
                    release = (
                        self._release_requested
                        or (timed_out and self._process is not None)
                        or bool(self._blocked)
                    )
                    active = self._active
                if release:
                    self._release()
                    with self._condition:
                        item = self._find(active)
                        if item and item["status"] not in TERMINAL:
                            if self._cancel_at:
                                self._finish(item, "cancelled")
                            else:
                                item.update(
                                    status="paused",
                                    stage="Pausiert",
                                    paused_at=item.get("paused_at") or time.monotonic(),
                                )
                                self._active = None
                        self._pause_ack = True
                        self._release_requested = False
                with self._condition:
                    item = next(
                        (i for i in self._items if i["status"] in ("queued", "paused")), None
                    )
                    start = (
                        not self._active
                        and item
                        and item["metadata_status"] not in ("pending", "loading")
                        and not self._blocked
                        and not self._paused
                    )
                    idle = not self._active and (item is None or self._blocked)
                    if start:
                        # Reserve before spawning: removing a queued row can never race a hidden download.
                        if item.get("paused_at"):
                            item["started"] += time.monotonic() - item.pop("paused_at")
                        self._active = item["id"]
                        item.update(
                            status="running",
                            stage="Vorbereiten",
                            started=item["started"] or time.monotonic(),
                        )
                if start:
                    settings = (
                        self._options.get("device", "cpu"),
                        self._options.get("offline", False),
                    )
                    if self._process and self._worker_settings != settings:
                        self._release()
                    if not self._process:
                        self._spawn()
                    with self._condition:
                        if self._cancel_at:
                            self._cancel.set()
                        else:
                            self._cancel.clear()
                        item.pop("finished", None)
                        if item["id"] not in self._work:
                            self._work[item["id"]] = {
                                "temporary": tempfile.TemporaryDirectory(
                                    prefix="arabic-transcriber-"
                                ),
                                "decoded_ready": False,
                                "download_path": None,
                            }
                        work = self._work[item["id"]]
                        payload = {k: item[k] for k in ("id", "source", "value", "offset")}
                        payload.update(
                            directory=work["temporary"].name,
                            decoded_ready=work["decoded_ready"],
                            download_path=work["download_path"],
                        )
                        self._connection.send(
                            {"kind": "run", "item": payload, "options": dict(self._options)}
                        )
                        event("started", pid=self._process.pid)
                elif idle:
                    self._release()
                    if not self._blocked:
                        self._options.pop("token", None)
                if self._active and self._process and time.monotonic() - self._last_metrics > 5:
                    import psutil

                    try:
                        event(
                            "resources",
                            phase=self._find(self._active)["stage"],
                            rss_mb=round(
                                psutil.Process(self._process.pid).memory_info().rss / 2**20
                            ),
                            available_mb=round(psutil.virtual_memory().available / 2**20),
                        )
                    except (psutil.Error, OSError):
                        pass
                    self._last_metrics = time.monotonic()
                with self._condition:
                    self._condition.wait(0.02)
        finally:
            self._release()
            for work in self._work.values():
                work["temporary"].cleanup()
            self._work.clear()
            self._options.clear()
