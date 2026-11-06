"""Public queue lifecycle; real spawned processes and FFmpeg, external ASR fake."""

import time
import wave
from multiprocessing import get_context
from pathlib import Path

from arabic_transcriber.jobs import Job


def audio_file(tmp_path, seconds=1):
    path = tmp_path / "speech.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", ""))
        wav.writeframes(b"\x00\x10" * (16000 * seconds))
    return str(path)


def wait_for(job, predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = job.snapshot()
        if predicate(state):
            return state
        time.sleep(0.01)
    raise AssertionError(job.snapshot())


class TextRecognizer:
    def load(self, options, cancel, stage):
        pass

    def transcribe(self, audio, cancel):
        return "نص"


class AuditDownload:
    def __init__(self, audio, title_ready, audit):
        self.audio, self.title_ready, self.audit = audio, title_ready, audit

    def __call__(self, url, directory, cancel, report):
        assert self.title_ready.exists(), "download ran before metadata resolved"
        self.audit.write_text(url)
        return Path(self.audio)


class HeldRecognizer:
    def __init__(self, entered, release):
        self.entered = entered
        self.release = release
        self.loads = 0
        self.calls = 0

    def load(self, options, cancel, stage):
        self.loads += 1

    def transcribe(self, audio, cancel):
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            self.release.wait(8)
        return f"نص {self.loads}:{self.calls}"


def test_fifo_keeps_one_warm_model_and_separate_selected_transcripts(tmp_path):
    context = get_context("spawn")
    entered, release = context.Event(), context.Event()
    queue = Job(recognizer=HeldRecognizer(entered, release), segment_seconds=1)
    try:
        path = audio_file(tmp_path)
        first = queue.start("file", path, {})
        assert entered.wait(5)
        second = queue.start("file", path, {})
        assert second["ok"], second
        state = queue.snapshot()
        assert [item["status"] for item in state["items"]] == ["running", "queued"]
        assert state["selected_id"] == first["id"]
        release.set()
        state = wait_for(
            queue,
            lambda s: all(i["status"] == "completed" for i in s["items"]) and not s["model_loaded"],
        )
        assert state["segments"][0]["text"] == "نص 1:1"
        assert state["selected_id"] == first["id"]
        assert queue.select(second["id"])["ok"]
        assert queue.snapshot()["segments"][0]["text"] == "نص 1:2"
    finally:
        release.set()
        queue.close()


def test_pause_release_and_resume_keeps_complete_audio_checkpoints(tmp_path):
    context = get_context("spawn")
    entered, release = context.Event(), context.Event()
    queue = Job(recognizer=HeldRecognizer(entered, release), segment_seconds=1)
    try:
        queue.start("file", audio_file(tmp_path, 3), {})
        assert entered.wait(5)
        assert queue.pause()["ok"]
        release.set()
        state = wait_for(queue, lambda s: s["paused"] and not s["pausing"])
        assert len(state["segments"]) == 1
        assert state["model_loaded"]
        assert 290 <= state["release_in_seconds"] <= 300
        assert queue.release_memory()["ok"]
        wait_for(queue, lambda s: not s["model_loaded"] and not s["releasing_memory"])
        assert queue.resume()["ok"]
        state = wait_for(queue, lambda s: s["status"] == "completed" and not s["model_loaded"])
        assert [(s["start"], s["end"]) for s in state["segments"]] == [(0, 1), (1, 2), (2, 3)]
    finally:
        release.set()
        queue.close()


def test_pause_timeout_releases_without_frontend_polling(tmp_path):
    context = get_context("spawn")
    entered, release = context.Event(), context.Event()
    queue = Job(
        recognizer=HeldRecognizer(entered, release), segment_seconds=1, pause_retention_seconds=0.2
    )
    try:
        queue.start("file", audio_file(tmp_path, 2), {})
        assert entered.wait(5)
        queue.pause()
        release.set()
        wait_for(queue, lambda s: s["paused"] and not s["pausing"] and s["model_loaded"])
        time.sleep(0.6)  # No snapshot/UI poll drives the timeout.
        state = queue.snapshot()
        assert state["paused"] and not state["model_loaded"]
        assert queue.resume()["ok"]
        state = wait_for(queue, lambda s: s["status"] == "completed")
        assert [s["start"] for s in state["segments"]] == [0, 1]
    finally:
        release.set()
        queue.close()


def test_resume_before_deadline_reuses_loaded_recognizer(tmp_path):
    context = get_context("spawn")
    entered, release = context.Event(), context.Event()
    queue = Job(recognizer=HeldRecognizer(entered, release), segment_seconds=1)
    try:
        queue.start("file", audio_file(tmp_path, 2), {})
        assert entered.wait(5)
        queue.pause()
        release.set()
        wait_for(queue, lambda s: s["paused"] and not s["pausing"])
        queue.resume()
        state = wait_for(queue, lambda s: s["status"] == "completed")
        assert [s["text"] for s in state["segments"]] == ["نص 1:1", "نص 1:2"]
    finally:
        release.set()
        queue.close()


def test_youtube_title_precedes_download_and_removed_lookup_cannot_reappear(tmp_path):
    import threading

    entered, release = threading.Event(), threading.Event()
    downloads = tmp_path / "downloads.txt"
    ready = tmp_path / "title-ready"

    def title(url):
        entered.set()
        release.wait(5)
        ready.write_text("ready")
        return "عنوان الفيديو <b>Berlin</b>"

    queue = Job(
        recognizer=TextRecognizer(),
        downloader=AuditDownload(audio_file(tmp_path), ready, downloads),
        title_resolver=title,
    )
    try:
        first = queue.start("youtube", "https://youtu.be/first", {})
        assert entered.wait(2)
        assert queue.snapshot()["items"][0]["metadata_status"] == "loading"
        assert not downloads.exists()
        queue.remove(first["id"])
        second = queue.start("youtube", "https://youtu.be/second", {})
        release.set()
        state = wait_for(
            queue, lambda s: len(s["items"]) == 1 and s["items"][0]["metadata_status"] == "ready"
        )
        assert state["items"][0]["id"] == second["id"]
        assert state["items"][0]["title"] == "عنوان الفيديو <b>Berlin</b>"
        wait_for(queue, lambda s: s["status"] == "completed")
        assert downloads.read_text() == "https://youtu.be/second"
    finally:
        release.set()
        queue.close()


class FirstLoadBlocks(TextRecognizer):
    def __init__(self, entered, marker):
        self.entered, self.marker = entered, marker

    def load(self, options, cancel, stage):
        import ctypes
        import os
        import sys

        import psutil

        if self.marker.exists():
            assert not psutil.pid_exists(int(self.marker.read_text())), (
                "old model worker still alive"
            )
            return
        self.marker.write_text(str(os.getpid()))
        self.entered.set()
        if sys.platform == "win32":
            ctypes.PyDLL("kernel32").Sleep(30_000)
        else:
            ctypes.PyDLL(None).sleep(30)


def test_forced_cancel_stops_old_worker_before_next_queued_job(tmp_path):
    entered = get_context("spawn").Event()
    queue = Job(recognizer=FirstLoadBlocks(entered, tmp_path / "pid"))
    try:
        path = audio_file(tmp_path)
        first = queue.start("file", path, {})
        assert entered.wait(5)
        second = queue.start("file", path, {})
        queue.select(second["id"])
        started = time.monotonic()
        queue.cancel(first["id"])
        state = wait_for(queue, lambda s: s["status"] == "completed", timeout=3)
        assert time.monotonic() - started < 3
        assert state["items"][0]["status"] == "cancelled"
        assert not state["blocked"]
    finally:
        queue.close()


class RequiresAccess(TextRecognizer):
    def load(self, options, cancel, stage):
        if options.get("token") != "test-fixture-access":
            raise RuntimeError("Modellzugang einrichten.")


def test_shared_model_error_pauses_queue_and_resume_retries_with_new_access(tmp_path):
    queue = Job(recognizer=RequiresAccess())
    try:
        path = audio_file(tmp_path)
        queue.start("file", path, {})
        queue.start("file", path, {})
        state = wait_for(queue, lambda s: s["blocked"] and not s["model_loaded"])
        assert state["paused"]
        assert [i["status"] for i in state["items"]] == ["error", "queued"]
        queue.resume({"token": "test-fixture-access"})
        state = wait_for(queue, lambda s: all(i["status"] == "completed" for i in s["items"]))
        assert "test-fixture-access" not in str(state)
    finally:
        queue.close()


def test_immediate_release_interrupts_uncooperative_load_and_can_resume(tmp_path):
    entered = get_context("spawn").Event()
    queue = Job(recognizer=FirstLoadBlocks(entered, tmp_path / "pid"))
    try:
        queue.start("file", audio_file(tmp_path), {})
        assert entered.wait(5)
        queue.pause()
        started = time.monotonic()
        queue.release_memory()
        wait_for(
            queue,
            lambda s: s["paused"] and s["active_id"] is None and not s["worker_running"],
            timeout=2,
        )
        assert time.monotonic() - started < 2
        queue.resume()
        assert wait_for(queue, lambda s: s["status"] == "completed")["segments"]
    finally:
        queue.close()


class SelectiveDownload:
    def __init__(self, audio):
        self.audio = audio

    def __call__(self, url, directory, cancel, report):
        if url.endswith("unavailable"):
            raise RuntimeError("Video nicht verfügbar.")
        return Path(self.audio)


def missing_title(url):
    raise TimeoutError("external metadata fixture")


def test_metadata_failure_keeps_url_and_media_failure_continues_next_item(tmp_path):
    queue = Job(
        recognizer=TextRecognizer(),
        downloader=SelectiveDownload(audio_file(tmp_path)),
        title_resolver=missing_title,
    )
    try:
        first = queue.start("youtube", "https://youtu.be/unavailable", {})
        second = queue.start("youtube", "https://youtu.be/available", {})
        state = wait_for(queue, lambda s: s["items"][1]["status"] == "completed")
        assert state["items"][0]["status"] == "error"
        assert state["items"][0]["title"] == "https://youtu.be/unavailable"
        assert state["items"][0]["metadata_status"] == "unavailable"
        assert state["selected_id"] == first["id"]
        queue.select(second["id"])
        assert queue.snapshot()["segments"][0]["text"] == "نص"
    finally:
        queue.close()


def test_pause_on_final_chunk_still_finishes_and_releases_empty_queue(tmp_path):
    context = get_context("spawn")
    entered, release = context.Event(), context.Event()
    queue = Job(recognizer=HeldRecognizer(entered, release), segment_seconds=1)
    try:
        queue.start("file", audio_file(tmp_path), {})
        assert entered.wait(5)
        queue.pause()
        release.set()
        state = wait_for(
            queue, lambda s: s["status"] == "completed" and not s["worker_running"], timeout=2
        )
        assert len(state["segments"]) == 1
    finally:
        release.set()
        queue.close()


class PacedRecognizer(HeldRecognizer):
    def transcribe(self, audio, cancel):
        text = super().transcribe(audio, cancel)
        time.sleep(0.03)
        return text


def test_rapid_resume_then_pause_is_acknowledged_without_releasing_model(tmp_path):
    context = get_context("spawn")
    entered, release = context.Event(), context.Event()
    queue = Job(recognizer=PacedRecognizer(entered, release), segment_seconds=1)
    try:
        queue.start("file", audio_file(tmp_path, 20), {})
        assert entered.wait(5)
        queue.pause()
        release.set()
        wait_for(queue, lambda s: s["paused"] and not s["pausing"])
        for _ in range(3):
            queue.resume()
            queue.pause()
            state = wait_for(queue, lambda s: s["paused"] and not s["pausing"], timeout=1)
            assert state["model_loaded"]
    finally:
        release.set()
        queue.close()


class SlowPacedRecognizer(HeldRecognizer):
    def transcribe(self, audio, cancel):
        text = super().transcribe(audio, cancel)
        time.sleep(0.2)
        return text


def test_resume_with_changed_runtime_counts_processing_time_after_reload(tmp_path):
    context = get_context("spawn")
    entered, release = context.Event(), context.Event()
    queue = Job(recognizer=SlowPacedRecognizer(entered, release), segment_seconds=1)
    try:
        queue.start("file", audio_file(tmp_path, 8), {})
        assert entered.wait(5)
        queue.pause()
        release.set()
        wait_for(queue, lambda s: s["paused"] and not s["pausing"])
        queue.resume({"offline": True})
        state = wait_for(queue, lambda s: s["status"] == "completed")
        assert state["items"][0]["elapsed_seconds"] >= 1
    finally:
        release.set()
        queue.close()
