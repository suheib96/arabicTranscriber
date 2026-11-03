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
