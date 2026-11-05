"""Fixed official Cohere ASR with bounded CPU use and a memory preflight."""

import os
from pathlib import Path

from .media import Cancelled, check_cancel

MODEL_ID = "CohereLabs/cohere-transcribe-arabic-07-2026"
PATTERNS = ["*.json", "*.safetensors", "*.model", "*.txt", "*.jinja"]


def memory_budget(device, weight_bytes, available_bytes):
    """Conservative estimate, not a hardware or inference-speed guarantee."""
    parameter_bytes = weight_bytes if device == "cuda" else weight_bytes * 2
    required = parameter_bytes + int(1.5 * 2**30)
    return {
        "fits": available_bytes >= required,
        "required_bytes": required,
        "available_bytes": available_bytes,
    }


def configure_cpu(torch):
    threads = min(4, max(1, (os.cpu_count() or 2) // 2))
    torch.set_num_threads(threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass  # A caller may have initialized the inter-op pool already.
    return threads


class CohereRecognizer:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None

    def load(self, options, cancel, stage):
        check_cancel(cancel)
        device = options.get("device", "cpu")
        if self.model is not None and self.device == device:
            return
        stage("Modell laden")
        try:
            import psutil
            import torch
            from huggingface_hub import snapshot_download
            from transformers import AutoProcessor, CohereAsrForConditionalGeneration

            configure_cpu(torch)
            if device == "cuda" and not torch.cuda.is_available():
                raise ValueError("NVIDIA-GPU nicht verfügbar. Bitte CPU auswählen.")
            if device == "mps" and not torch.backends.mps.is_available():
                raise ValueError("Apple-GPU nicht verfügbar. Bitte CPU auswählen.")
            self.model = None
            self.processor = None
            token = options.get("token") or os.environ.get("HF_TOKEN") or None
            parameters = {"repo_id": MODEL_ID, "token": token, "allow_patterns": PATTERNS}
            try:
                local = snapshot_download(**parameters, local_files_only=True)
            except OSError:
                if options.get("offline"):
                    raise ValueError(
                        "Modell fehlt. Bitte Offline ausschalten und den Modellzugang einrichten."
                    ) from None
                stage("Modell herunterladen")
                local = snapshot_download(**parameters)
            check_cancel(cancel)
            stage("Modell laden")
            weights = sum(p.stat().st_size for p in Path(local).glob("*.safetensors"))
            if not weights:
                raise ValueError("Modelldownload unvollständig. Bitte erneut laden.")
            available = (
                torch.cuda.mem_get_info()[0]
                if device == "cuda"
                else psutil.virtual_memory().available
            )
            budget = memory_budget(device, weights, available)
            if not budget["fits"]:
                label = "Grafikspeicher" if device == "cuda" else "Arbeitsspeicher"
                raise ValueError(
                    f"Zu wenig freier {label}: ca. {budget['required_bytes'] / 1e9:.1f} GB benötigt, "
                    f"{available / 1e9:.1f} GB verfügbar. Bitte andere Programme schließen"
                    + (" oder CPU auswählen." if device == "cuda" else " und erneut versuchen.")
                )
            processor = AutoProcessor.from_pretrained(local, local_files_only=True)
            dtype = torch.float16 if device == "cuda" else torch.float32
            # Load directly at the target precision/device instead of first materializing
            # an 8 GB CPU copy and then allocating another GPU copy.
            model = CohereAsrForConditionalGeneration.from_pretrained(
                local, local_files_only=True, dtype=dtype, device_map={"": device}
            )
            check_cancel(cancel)
            self.model = model.eval()
            self.processor = processor
            self.device = device
        except (Cancelled, ValueError):
            raise
        except Exception:
            self.model = None
            raise RuntimeError(
                "Modell konnte nicht geladen werden. Bitte Modellzugang und freien Speicher prüfen."
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
                "Transkription fehlgeschlagen. Bitte freien Speicher prüfen oder CPU versuchen."
            ) from None
