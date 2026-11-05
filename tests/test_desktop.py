from arabic_transcriber.bridge import DesktopAPI


def test_desktop_starts_empty_and_cancelled_file_dialog_keeps_input():
    api = DesktopAPI()
    assert api.snapshot()["status"] == "idle"
    assert api.snapshot()["segments"] == []

    class Window:
        def create_file_dialog(self, *args, **kwargs):
            return None

    api.window = Window()
    assert api.choose_file() is None
    result = api.start("file", "/no/such/media.wav", {})
    assert not result["ok"]
    assert "Datei" in result["error"]


def test_desktop_copy_and_save_dialog_use_same_timestamp_choice(tmp_path):
    copied = []

    class Job:
        def snapshot(self):
            return {"segments": [{"start": 0, "end": 24, "text": "مرحبا Berlin 2026"}]}

    api = DesktopAPI(job=Job(), clipboard=copied.append)
    assert api.copy_all(True)["ok"]
    assert copied == ["[ca. 00:00 – 00:24]\nمرحبا Berlin 2026"]

    class Window:
        def create_file_dialog(self, *args, **kwargs):
            return str(tmp_path / "arabic")

    api.window = Window()
    result = api.export("txt", False)
    assert result["path"].endswith(".txt")
    assert (tmp_path / "arabic.txt").read_text("utf-8") == "مرحبا Berlin 2026"

    class CancelledWindow:
        def create_file_dialog(self, *args, **kwargs):
            return None

    api.window = CancelledWindow()
    assert api.export("docx", True) == {"path": None}


def test_desktop_document_contains_local_assets_without_loopback_dependency():
    from arabic_transcriber.app import ui_document

    html = ui_document()
    assert "<script src=" not in html
    assert 'href="style.css"' not in html
    assert "data:font/ttf;base64," in html
    assert "window.desktopSmoke" in html


def test_file_picker_uses_valid_native_filters_and_returns_selected_unicode_path(tmp_path):
    from webview.util import parse_file_type

    selected = str(tmp_path / "مقابلة Berlin.mp4")

    class NativeDialog:
        def create_file_dialog(self, dialog_type, **options):
            # Exercise the real validation performed by pywebview before any OS dialog opens.
            for file_type in options["file_types"]:
                parse_file_type(file_type)
            assert options["allow_multiple"] is False
            return (selected,)

    api = DesktopAPI()
    api.window = NativeDialog()
    assert api.choose_file() == selected
