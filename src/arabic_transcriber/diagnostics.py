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
