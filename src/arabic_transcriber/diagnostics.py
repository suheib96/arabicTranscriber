"""Package integrity check. Never downloads or claims real model inference."""

import json
import subprocess
import tempfile
import threading
import wave
from pathlib import Path


def self_check(destination):
    report = {"ok": False, "real_model_inference": False}
    try:
        import numpy as np
        import torch
        import yt_dlp
        import yt_dlp_ejs
        from transformers import (
            CohereAsrFeatureExtractor,
            CohereAsrForConditionalGeneration,
            CohereAsrProcessor,
        )

        from .exports import export_transcript
        from .media import audio_segments, decode, tool

        report.update(
            torch=torch.__version__,
            cohere_class=CohereAsrForConditionalGeneration.__name__,
            processor=CohereAsrProcessor.__name__,
            mps_available=torch.backends.mps.is_available(),
            downloader=yt_dlp.version.__version__,
            ejs=bool(yt_dlp_ejs),
        )
        features = CohereAsrFeatureExtractor()(
            np.zeros(16000, dtype=np.float32), sampling_rate=16000, return_tensors="pt"
        )
        assert features["input_features"].shape[-1] == 128
        report["real_cohere_preprocessing"] = True
        report["node"] = subprocess.check_output([tool("node"), "--version"], text=True).strip()
        report["ffmpeg"] = subprocess.check_output(
            [tool("ffmpeg"), "-version"], text=True
        ).splitlines()[0]
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source.wav"
            with wave.open(str(source), "wb") as wav:
                wav.setparams((1, 2, 16000, 0, "NONE", ""))
                wav.writeframes((np.sin(np.arange(16000) * 0.1) * 1000).astype("<i2").tobytes())
            decoded = decode(source, directory, threading.Event(), lambda *a: None)
            assert len(list(audio_segments(decoded))) == 1
            for fmt in ("txt", "docx", "pdf"):
                exported = export_transcript(
                    [{"start": 0, "end": 1, "text": "مرحبا Berlin 2026"}],
                    directory / ("test." + fmt),
                    fmt,
                    True,
                )
                assert exported.stat().st_size > 20
        report["ok"] = True
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report["ok"]


class _WorkerProbe:
    """Only used by the explicit package check; never a transcription fallback."""

    def __init__(self, blocked=False, slow=False):
        self.blocked = blocked
        self.slow = slow

    def load(self, options, cancel, stage):
        if self.blocked:
            stage("Worker-Prüfung")
            import ctypes
            import sys

            # PyDLL deliberately holds this worker's GIL, like an uncooperative native call.
            if sys.platform == "win32":
                ctypes.PyDLL("kernel32").Sleep(30_000)
            else:
                ctypes.PyDLL(None).sleep(30)

    def transcribe(self, audio, cancel):
        if self.slow:
            import time

            time.sleep(0.08)
        return "اختبار"


def worker_check(destination):
    """Exercise frozen spawn/IPC/cancel/restart without model access or weights."""
    import time

    from .jobs import Job

    report = {"ok": False, "real_model_inference": False}

    def wait(job, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = job.snapshot()
            if predicate(state):
                return state
            if state["status"] == "error":
                raise RuntimeError(state["error"])
            time.sleep(0.02)
        raise RuntimeError("Worker check timed out")

    job = None
    try:
        with tempfile.TemporaryDirectory(prefix="arabic-worker-check-") as temporary:
            path = Path(temporary) / "fixture.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setparams((1, 2, 16000, 0, "NONE", ""))
                wav.writeframes(b"\x00\x10" * 32000)
            job = Job(recognizer=_WorkerProbe(), segment_seconds=1)
            assert job.start("file", str(path), {})["ok"]
            state = wait(job, lambda s: s["status"] == "completed")
            assert len(state["segments"]) == 2
            report["spawn_and_segments"] = True
            job.close()
            job = Job(recognizer=_WorkerProbe(slow=True), segment_seconds=0.25)
            first = job.start("file", str(path), {})
            second = job.start("file", str(path), {})
            assert first["ok"] and second["ok"]
            wait(job, lambda s: len(s["segments"]) >= 1)
            job.pause()
            wait(job, lambda s: s["paused"] and not s["pausing"])
            assert job.snapshot()["model_loaded"]
            job.release_memory()
            wait(job, lambda s: not s["worker_running"] and not s["releasing_memory"])
            job.resume()
            state = wait(job, lambda s: all(i["status"] == "completed" for i in s["items"]))
            assert [segment["start"] for segment in state["segments"]] == [n / 4 for n in range(8)]
            assert state["selected_id"] == first["id"]
            job.select(second["id"])
            assert len(job.snapshot()["segments"]) == 8
            wait(job, lambda s: not s["worker_running"])
            report["queue_pause_release_resume"] = True
            job.close()
            job = Job(recognizer=_WorkerProbe(blocked=True))
            assert job.start("file", str(path), {})["ok"]
            wait(job, lambda s: s["stage"] == "Worker-Prüfung")
            started = time.monotonic()
            job.cancel()
            wait(job, lambda s: s["status"] == "cancelled", timeout=2)
            report["cancel_seconds"] = round(time.monotonic() - started, 2)
            restarted = job.start("file", str(path), {})
            assert restarted["ok"]
            job.select(restarted["id"])
            job.cancel(restarted["id"])
            wait(job, lambda s: s["status"] == "cancelled", timeout=2)
            report["restart"] = True
            report["ok"] = True
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if job:
            job.close()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report["ok"]
