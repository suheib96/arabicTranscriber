import time
import wave
from multiprocessing import get_context

import numpy as np

from arabic_transcriber.jobs import Job


def audio_file(tmp_path, seconds=3):
    path = tmp_path / "speech.wav"
    samples = (np.sin(np.arange(16000 * seconds) * 0.1) * 8000).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(samples.tobytes())
    return path


def wait_for(job, predicate):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = job.snapshot()
        if predicate(state):
            return state
        time.sleep(0.01)
    raise AssertionError(job.snapshot())


class Recognizer:
    def load(self, options, cancel, stage):
        stage("Modell bereit")

    def transcribe(self, audio, cancel):
        return "مرحبًا بكم في Berlin 2026."


def test_local_media_grows_in_order_with_real_decode_and_finishes(tmp_path):
    job = Job(recognizer=Recognizer(), segment_seconds=1)
    assert job.start("file", str(audio_file(tmp_path)), {})["ok"]
    state = wait_for(job, lambda s: s["status"] in ("completed", "error"))
    assert state["status"] == "completed", state
    assert state["progress"] == 1
    assert [(s["start"], s["end"]) for s in state["segments"]] == [(0, 1), (1, 2), (2, 3)]
    assert state["segments"][1]["text"] == "مرحبًا بكم في Berlin 2026."
    job.close()


class SlowRecognizer(Recognizer):
    def __init__(self, entered_second, release):
        self.calls = 0
        self.entered_second = entered_second
        self.release = release

    def transcribe(self, audio, cancel):
        self.calls += 1
        if self.calls == 2:
            self.entered_second.set()
            self.release.wait(5)
        return "نص محفوظ"


def test_cancel_retains_completed_segments_and_new_job_can_start(tmp_path):
    entered_second = get_context("spawn").Event()
    release = get_context("spawn").Event()
    job = Job(recognizer=SlowRecognizer(entered_second, release), segment_seconds=1)
    path = str(audio_file(tmp_path))
    assert job.start("file", path, {})["ok"]
    assert entered_second.wait(5)
    growing = wait_for(job, lambda s: len(s["segments"]) == 1)
    assert len(growing["segments"]) == 1
    assert 0 < growing["progress"] < 1
    job.cancel()
    release.set()
    state = wait_for(job, lambda s: s["status"] == "cancelled")
    assert [s["text"] for s in state["segments"]] == ["نص محفوظ"]
    restarted = job.start("file", path, {})
    assert restarted["ok"]
    job.select(restarted["id"])
    assert wait_for(job, lambda s: s["status"] == "completed")["progress"] == 1
    job.close()


class DownloadedAudio:
    def __init__(self, path):
        self.path = path

    def __call__(self, url, directory, cancel, report):
        report("Audio wird heruntergeladen", 0.5)
        return self.path


def unavailable_download(*args):
    raise RuntimeError("YouTube-Audio nicht verfügbar.")


class MissingModel(Recognizer):
    def load(self, options, cancel, stage):
        raise RuntimeError("Modellzugang bei Hugging Face freischalten.")


def test_youtube_adapter_uses_same_job_path_and_surfaces_failure(tmp_path):
    path = audio_file(tmp_path)

    job = Job(
        recognizer=Recognizer(), downloader=DownloadedAudio(path), title_resolver=lambda _: "Video"
    )
    assert not job.start("youtube", "https://example.com/watch?v=x", {})["ok"]
    assert job.start("youtube", "https://youtu.be/example", {})["ok"]
    assert wait_for(job, lambda s: s["status"] == "completed")["segments"]
    job.close()

    job = Job(
        recognizer=Recognizer(), downloader=unavailable_download, title_resolver=lambda _: "Video"
    )
    job.start("youtube", "https://youtu.be/example", {})
    assert (
        wait_for(job, lambda s: s["status"] == "error")["error"] == "YouTube-Audio nicht verfügbar."
    )
    job.close()


def test_silence_skipping_keeps_original_offsets_and_missing_model_is_actionable(tmp_path):
    path = audio_file(tmp_path)
    with wave.open(str(path), "rb") as wav:
        content = wav.readframes(wav.getnframes())
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", ""))
        wav.writeframes(b"\0" * 32000 + content[32000:])
    job = Job(recognizer=Recognizer(), segment_seconds=1)
    job.start("file", str(path), {})
    state = wait_for(job, lambda s: s["status"] == "completed")
    assert state["segments"][0]["start"] == 1
    job.close()

    job = Job(recognizer=MissingModel())
    job.start("file", str(path), {})
    assert "Hugging Face" in wait_for(job, lambda s: s["status"] == "error")["error"]
    job.close()


def test_playlist_and_channel_urls_are_rejected_before_download():
    job = Job(recognizer=Recognizer())
    for url in (
        "https://www.youtube.com/playlist?list=123",
        "https://www.youtube.com/@channel",
        "https://www.youtube.com/watch?list=123",
    ):
        assert not job.start("youtube", url, {})["ok"]
    job.close()


class BlockedRecognizer(Recognizer):
    def __init__(self, entered):
        self.entered = entered

    def load(self, options, cancel, stage):
        stage("Modell wird geladen")
        self.entered.set()
        import ctypes
        import sys

        # Simulate a native extension that holds the GIL as well as ignoring cancel.
        if sys.platform == "win32":
            ctypes.PyDLL("kernel32").Sleep(30_000)
        else:
            ctypes.PyDLL(None).sleep(30)


def test_cancel_interrupts_stuck_model_and_allows_restart(tmp_path):
    from multiprocessing import get_context

    entered = get_context("spawn").Event()
    job = Job(recognizer=BlockedRecognizer(entered))
    path = str(audio_file(tmp_path, 1))
    assert job.start("file", path, {})["ok"]
    assert entered.wait(5)
    started = time.monotonic()
    job.cancel()
    while time.monotonic() - started < 2:
        if job.snapshot()["status"] == "cancelled":
            break
        time.sleep(0.01)
    assert job.snapshot()["status"] == "cancelled"
    assert time.monotonic() - started < 2
    restarted = job.start("file", path, {})
    assert restarted["ok"]
    job.select(restarted["id"])
    job.cancel(restarted["id"])
    wait_for(job, lambda s: s["status"] == "cancelled")
    job.close()
