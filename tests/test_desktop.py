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


def test_desktop_exposes_queue_selection_pause_and_memory_controls(tmp_path):
    from arabic_transcriber.jobs import Job

    api = DesktopAPI(job=Job())
    try:
        assert api.pause()["ok"]
        first_path, second_path = tmp_path / "first.wav", tmp_path / "second.wav"
        first_path.write_bytes(b"fixture-not-decoded-while-paused")
        second_path.write_bytes(b"fixture-not-decoded-while-paused")
        first = api.start("file", str(first_path), {})
        second = api.start("file", str(second_path), {})
        assert api.select(second["id"])["ok"]
        assert api.snapshot()["selected_id"] == second["id"]
        assert api.release_memory()["ok"]
        assert api.remove(first["id"])["ok"]
        assert len(api.snapshot()["items"]) == 1
        assert api.cancel(second["id"])["ok"]
        assert api.resume()["ok"]
    finally:
        api.close()


def test_desktop_playlist_link_is_imported_into_paused_queue():
    import time

    from arabic_transcriber.jobs import Job

    def read(url, cancel, report):
        return {"title": "قائمة", "entries": [{"url": "https://youtu.be/one", "title": "الدرس"}]}

    api = DesktopAPI(job=Job(playlist_reader=read))
    try:
        api.pause()
        result = api.start("youtube", "https://www.youtube.com/playlist?list=PL_example", {})
        assert result["ok"] and result["importing"]
        deadline = time.monotonic() + 2
        while (
            time.monotonic() < deadline
            and api.snapshot()["playlist_import"]["status"] != "completed"
        ):
            time.sleep(0.01)
        assert api.snapshot()["items"][0]["title"] == "الدرس"
    finally:
        api.close()


def test_desktop_collection_export_uses_native_save_and_all_results(tmp_path):
    import zipfile
    from datetime import date

    class Results:
        def export_entries(self):
            return [
                {
                    "title": "واحد",
                    "playlist_title": "دروس",
                    "playlist_url": "https://www.youtube.com/playlist?list=PLone",
                    "status": "completed",
                    "segments": [{"start": 0, "end": 12, "text": "نص أول"}],
                },
                {
                    "title": "اثنان",
                    "playlist_title": "دروس",
                    "playlist_url": "https://www.youtube.com/playlist?list=PLone",
                    "status": "completed",
                    "segments": [{"start": 12, "end": 24, "text": "نص ثان"}],
                },
            ]

    class Window:
        def create_file_dialog(self, *args, **kwargs):
            assert (
                kwargs["save_filename"] == f"دروس - 2 Transkripte - {date.today().isoformat()}.zip"
            )
            return str(tmp_path / "all.zip")

    api = DesktopAPI(job=Results())
    api.window = Window()
    result = api.export_all("txt", False)
    assert result["count"] == 2
    with zipfile.ZipFile(result["path"]) as archive:
        assert [archive.read(name).decode("utf-8") for name in archive.namelist()] == [
            "نص أول",
            "نص ثان",
            f"دروس - 2 Transkripte - {date.today().isoformat()}\n\n1. واحد\n\nنص أول\n\n2. اثنان\n\nنص ثان",
        ]
    api.window.create_file_dialog = lambda *args, **kwargs: None
    assert api.export_all("pdf") == {"path": None}
