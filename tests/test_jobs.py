import threading
import time
import wave

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


def test_cancel_retains_completed_segments_and_new_job_can_start(tmp_path):
    entered_second = threading.Event()
    release = threading.Event()

    class SlowRecognizer(Recognizer):
        calls = 0

        def transcribe(self, audio, cancel):
            self.calls += 1
            if self.calls == 2:
                entered_second.set()
                release.wait(5)
            return "نص محفوظ"

    job = Job(recognizer=SlowRecognizer(), segment_seconds=1)
    path = str(audio_file(tmp_path))
    assert job.start("file", path, {})["ok"]
    assert entered_second.wait(5)
    growing = job.snapshot()
    assert len(growing["segments"]) == 1
    assert 0 < growing["progress"] < 1
    assert not job.start("file", path, {})["ok"]
    job.cancel()
    release.set()
    state = wait_for(job, lambda s: s["status"] == "cancelled")
    assert [s["text"] for s in state["segments"]] == ["نص محفوظ"]
    assert job.start("file", path, {})["ok"]
    assert wait_for(job, lambda s: s["status"] == "completed")["progress"] == 1


def test_youtube_adapter_uses_same_job_path_and_surfaces_failure(tmp_path):
    path = audio_file(tmp_path)

    def downloaded(url, directory, cancel, report):
        report("Audio wird heruntergeladen", 0.5)
        return path

    job = Job(recognizer=Recognizer(), downloader=downloaded)
    assert not job.start("youtube", "https://example.com/watch?v=x", {})["ok"]
    assert job.start("youtube", "https://youtu.be/example", {})["ok"]
    assert wait_for(job, lambda s: s["status"] == "completed")["segments"]

    def unavailable(*args):
        raise RuntimeError("YouTube-Audio nicht verfügbar.")

    job = Job(recognizer=Recognizer(), downloader=unavailable)
    job.start("youtube", "https://youtu.be/example", {})
    assert (
        wait_for(job, lambda s: s["status"] == "error")["error"] == "YouTube-Audio nicht verfügbar."
    )


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

    class MissingModel(Recognizer):
        def load(self, options, cancel, stage):
            raise RuntimeError("Modellzugang bei Hugging Face freischalten.")

    job = Job(recognizer=MissingModel())
    job.start("file", str(path), {})
    assert "Hugging Face" in wait_for(job, lambda s: s["status"] == "error")["error"]


def test_playlist_and_channel_urls_are_rejected_before_download():
    job = Job(recognizer=Recognizer())
    for url in (
        "https://www.youtube.com/playlist?list=123",
        "https://www.youtube.com/@channel",
        "https://www.youtube.com/watch?list=123",
    ):
        assert not job.start("youtube", url, {})["ok"]
