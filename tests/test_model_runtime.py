"""Actual fixed model preprocessing, without gated weights or inference."""

import numpy as np
from transformers import CohereAsrFeatureExtractor


def test_official_cohere_preprocessor_accepts_bounded_arabic_audio_input():
    extractor = CohereAsrFeatureExtractor()
    audio = np.sin(np.arange(16000, dtype=np.float32) * 0.1) * 0.1
    inputs = extractor(audio, sampling_rate=16000, return_tensors="pt")
    assert inputs["input_features"].shape[0] == 1
    assert inputs["input_features"].shape[-1] == 128
    assert inputs["attention_mask"].sum() > 0


def test_model_memory_check_reserves_space_for_system_and_gpu():
    from arabic_transcriber.model import memory_budget

    # A 4.13 GB checkpoint expands to ~8.26 GB in Float32, before working memory.
    cpu = memory_budget("cpu", weight_bytes=4_130_000_000, available_bytes=3_000_000_000)
    assert not cpu["fits"]
    assert cpu["required_bytes"] > 8_260_000_000
    assert memory_budget("cpu", 4_130_000_000, 14_000_000_000)["fits"]
    # CUDA's half precision still needs extra working VRAM; 4 GB cannot hold it.
    assert not memory_budget("cuda", 4_130_000_000, 4_000_000_000)["fits"]
    assert memory_budget("cuda", 4_130_000_000, 8_000_000_000)["fits"]
