"""Explicit optional real-model check. Requires gated access and several GB free."""

import argparse
import tempfile
import threading
from pathlib import Path

from arabic_transcriber.media import audio_segments, decode
from arabic_transcriber.model import CohereRecognizer

parser = argparse.ArgumentParser()
parser.add_argument("audio", type=Path)
parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
parser.add_argument("--offline", action="store_true")
args = parser.parse_args()
cancel = threading.Event()
model = CohereRecognizer()
with tempfile.TemporaryDirectory() as temporary:
    wav = decode(args.audio, Path(temporary), cancel, lambda stage, p: print(stage))
    model.load(
        {"device": args.device, "offline": args.offline}, cancel, lambda text, *a: print(text)
    )
    for start, end, total, samples in audio_segments(wav):
        print(f"{start:.1f}-{end:.1f}: {model.transcribe(samples, cancel)}")
