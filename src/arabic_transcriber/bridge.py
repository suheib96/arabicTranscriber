"""Small native desktop boundary; heavy work belongs to a background job."""

from pathlib import Path


class DesktopAPI:
    def __init__(self, job=None, clipboard=None):
        self.window = None
        self.job = job
        self.clipboard = clipboard

    def snapshot(self):
        if self.job is None:
            return {
                "status": "idle",
                "stage": "Bereit",
                "progress": None,
                "segments": [],
                "error": None,
                "revision": 0,
            }
        return self.job.snapshot()

    def choose_file(self):
        import webview

        result = self.window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=(
                "Audio und Video (*.wav;*.mp3;*.m4a;*.mp4;*.mkv;*.webm;*.ogg;*.flac)",
                "Alle Dateien (*.*)",
            ),
        )
        return result[0] if result else None

    def start(self, source, value, options=None):
        if source == "file" and not Path(value).is_file():
            return {"ok": False, "error": "Datei nicht gefunden. Bitte Audio oder Video auswählen."}
        if self.job is None:
            from .jobs import Job

            self.job = Job()
        return self.job.start(source, value, options or {})

    def cancel(self):
        if self.job:
            self.job.cancel()
        return {"ok": True}

    def close(self):
        if self.job:
            self.job.close()

    def platform_info(self):
        import sys

        return {"platform": sys.platform}

    def open_model_access(self):
        import webbrowser

        from .model import MODEL_ID

        webbrowser.open("https://huggingface.co/" + MODEL_ID)
        return {"ok": True}

    def copy_all(self, include_times=False):
        from .exports import render_text

        try:
            text = render_text(self.snapshot()["segments"], bool(include_times))
            if not text:
                return {"ok": False, "error": "Noch kein Transkript vorhanden."}
            if self.clipboard:
                self.clipboard(text)
            else:
                import pyperclip

                pyperclip.copy(text)
            return {"ok": True}
        except Exception:
            return {"ok": False, "error": "Kopieren fehlgeschlagen. Bitte als TXT exportieren."}

    def export(self, fmt, include_times=False):
        import webview

        from .exports import export_transcript

        if fmt not in ("txt", "docx", "pdf"):
            return {"error": "Unbekanntes Exportformat."}
        segments = self.snapshot()["segments"]
        if not segments:
            return {"error": "Noch kein Transkript vorhanden."}
        chosen = self.window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename="Transkript." + fmt,
            file_types=(f"{fmt.upper()} (*.{fmt})",),
        )
        if not chosen:
            return {"path": None}
        destination = chosen[0] if isinstance(chosen, (list, tuple)) else chosen
        try:
            return {"path": str(export_transcript(segments, destination, fmt, bool(include_times)))}
        except Exception:
            return {"error": "Export fehlgeschlagen. Schreibrechte und freien Speicher prüfen."}
