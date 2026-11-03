"""Fixed official Cohere ASR runtime. No alternative model or remote inference."""

import os

from .media import Cancelled, check_cancel

MODEL_ID = "CohereLabs/cohere-transcribe-arabic-07-2026"


class CohereRecognizer:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None

    def load(self, options, cancel, stage):
        check_cancel(cancel)
        device = options.get("device", "cpu")
        if self.model is not None and self.device == device:
            stage("Modell im Speicher bereit")
            return
        stage("Modellcache wird geprüft · erster Download ca. 4,13 GB")
        try:
            import torch
            from huggingface_hub import snapshot_download
            from transformers import AutoProcessor, CohereAsrForConditionalGeneration

            if device == "cuda" and not torch.cuda.is_available():
                raise ValueError("NVIDIA CUDA ist nicht verfügbar. Bitte CPU auswählen.")
            if device == "mps" and not torch.backends.mps.is_available():
                raise ValueError("Apple MPS ist nicht verfügbar. Bitte CPU auswählen.")
            self.model = None
            self.processor = None
            import gc

            gc.collect()
            token = options.get("token") or os.environ.get("HF_TOKEN") or None
            parameters = dict(
                repo_id=MODEL_ID,
                token=token,
                allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.jinja"],
            )
            try:
                local = snapshot_download(**parameters, local_files_only=True)
                # A snapshot may be partial. Loading below determines completeness.
                processor = AutoProcessor.from_pretrained(local, local_files_only=True)
                model = CohereAsrForConditionalGeneration.from_pretrained(
                    local, local_files_only=True, dtype=torch.float32
                )
            except (OSError, ValueError):
                if options.get("offline"):
                    raise ValueError(
                        "Modellcache fehlt oder ist unvollständig. Offline ausschalten "
                        "und mit freigeschaltetem Hugging-Face-Lesetoken einmal laden."
                    ) from None
                stage("Cohere-Modell wird geladen · Download / Laden ohne Prozentanzeige")
                check_cancel(cancel)
                local = snapshot_download(**parameters)
                check_cancel(cancel)
                processor = AutoProcessor.from_pretrained(local, local_files_only=True)
                model = CohereAsrForConditionalGeneration.from_pretrained(
                    local, local_files_only=True, dtype=torch.float32
                )
            check_cancel(cancel)
            # Float32 on CPU/MPS: conservative baseline. CUDA uses float16 after loading.
            dtype = torch.float16 if device == "cuda" else torch.float32
            self.model = model.to(device=device, dtype=dtype).eval()
            self.processor = processor
            self.device = device
            stage(f"Cohere bereit · {device.upper()} · Batch 1")
        except (Cancelled, ValueError):
            raise
        except Exception:
            self.model = None
            raise RuntimeError(
                "Cohere-Modell konnte nicht geladen werden. Modellbedingungen bei "
                "Hugging Face akzeptieren, Lesetoken prüfen und genügend RAM / "
                "Cache-Speicher bereitstellen. Offline nur mit vollständigem Cache."
            ) from None

    def transcribe(self, audio, cancel):
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList

        class StopOnCancel(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return cancel.is_set()

        check_cancel(cancel)
        try:
            inputs = self.processor(audio, sampling_rate=16000, return_tensors="pt", language="ar")
            chunk_index = inputs.get("audio_chunk_index")
            inputs = inputs.to(self.model.device, dtype=self.model.dtype)
            with torch.inference_mode():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=448,
                    stopping_criteria=StoppingCriteriaList([StopOnCancel()]),
                )
            check_cancel(cancel)
            text = self.processor.decode(
                output, skip_special_tokens=True, audio_chunk_index=chunk_index, language="ar"
            )
            return text if isinstance(text, str) else text[0]
        except Cancelled:
            raise
        except Exception:
            raise RuntimeError(
                "Cohere-Inferenz fehlgeschlagen. CPU versuchen, andere Programme "
                "schließen und freien Arbeitsspeicher prüfen. MPS ist experimentell."
            ) from None
