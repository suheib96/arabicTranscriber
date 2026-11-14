"""Playlist metadata to the public FIFO; no speech model or media download."""

import threading
import time

from arabic_transcriber.jobs import Job


def wait_for(queue, predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = queue.snapshot()
        if predicate(state):
            return state
        time.sleep(0.01)
    raise AssertionError(queue.snapshot())


def test_playlist_import_is_async_preserves_order_titles_and_skips_duplicates():
    entered, release = threading.Event(), threading.Event()

    def read(url, cancel, report):
        assert url == "https://www.youtube.com/playlist?list=PL_example"
        entered.set()
        release.wait(3)
        return {
            "title": "دروس",
            "skipped": 1,
            "entries": [
                {"url": "https://www.youtube.com/watch?v=first", "title": "الدرس الأول"},
                {"url": "https://www.youtube.com/watch?v=second", "title": "الدرس الثاني"},
                {"url": "https://www.youtube.com/watch?v=first", "title": "مكرر"},
            ],
        }

    queue = Job(playlist_reader=read)
    try:
        queue.pause()
        result = queue.import_playlist("https://www.youtube.com/playlist?list=PL_example")
        assert result["ok"]
        assert entered.wait(1)
        assert queue.snapshot()["playlist_import"]["status"] == "loading"
        assert not queue.snapshot()["worker_running"]
        release.set()
        state = wait_for(queue, lambda s: s["playlist_import"]["status"] == "completed")
        assert [i["title"] for i in state["items"]] == ["الدرس الأول", "الدرس الثاني"]
        assert all(
            i["metadata_status"] == "ready" and i["status"] == "queued" for i in state["items"]
        )
        assert state["playlist_import"]["added"] == 2
        assert state["playlist_import"]["duplicates"] == 1
        assert state["playlist_import"]["skipped"] == 1
        assert queue.import_playlist("https://www.youtube.com/playlist?list=PL_example")["ok"]
        state = wait_for(queue, lambda s: s["playlist_import"]["status"] == "completed")
        assert state["playlist_import"]["added"] == 0
        assert len(state["items"]) == 2
    finally:
        release.set()
        queue.close()


def test_cancelled_playlist_does_not_add_late_results():
    entered, release = threading.Event(), threading.Event()

    def read(url, cancel, report):
        entered.set()
        release.wait(3)
        return {"title": "Playlist", "entries": [{"url": "https://youtu.be/first", "title": "One"}]}

    queue = Job(playlist_reader=read)
    try:
        queue.import_playlist("https://www.youtube.com/playlist?list=PL_example")
        assert entered.wait(1)
        queue.cancel_playlist_import()
        release.set()
        state = wait_for(queue, lambda s: s["playlist_import"]["status"] == "cancelled")
        assert state["items"] == []
        assert not state["worker_running"]
    finally:
        release.set()
        queue.close()


def test_playlist_adapter_never_downloads_streams_and_skips_unavailable_entries(monkeypatch):
    import yt_dlp

    from arabic_transcriber.playlists import read_playlist

    class Metadata:
        def __init__(self, options):
            assert options["skip_download"] is True
            assert options["extract_flat"] == "in_playlist"
            assert options["js_runtimes"] == {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download):
            assert download is False
            return {
                "_type": "playlist",
                "title": "دروس",
                "entries": [
                    {"id": "one", "title": "الأول"},
                    {"id": "private", "title": "[Private video]"},
                    None,
                    {"id": "two", "title": "الثاني"},
                ],
            }

    monkeypatch.setattr(yt_dlp, "YoutubeDL", Metadata)
    result = read_playlist(
        "https://www.youtube.com/playlist?list=PL_example", threading.Event(), lambda count: None
    )
    assert [e["title"] for e in result["entries"]] == ["الأول", "الثاني"]
    assert result["skipped"] == 2


def test_closing_during_playlist_lookup_discards_late_results():
    entered, release = threading.Event(), threading.Event()

    def read(url, cancel, report):
        entered.set()
        release.wait(3)
        return {"title": "Late", "entries": [{"url": "https://youtu.be/late", "title": "Late"}]}

    queue = Job(playlist_reader=read)
    try:
        assert not queue.import_playlist("https://example.com/playlist?list=PL_bad")["ok"]
        assert queue.import_playlist(
            "https://www.youtube.com/playlist?list=PL_ok", {"token": "fixture-secret"}
        )["ok"]
        assert entered.wait(1)
        queue.close()
        release.set()
        state = wait_for(queue, lambda s: s["playlist_import"]["status"] == "cancelled")
        assert state["items"] == []
        assert "fixture-secret" not in str(state)
    finally:
        release.set()
        queue.close()
