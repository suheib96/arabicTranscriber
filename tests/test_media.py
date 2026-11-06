"""Real video decode; inference/network are intentionally outside this boundary."""

import subprocess
import threading

from arabic_transcriber.media import audio_segments, decode, tool


def test_two_minute_video_has_bounded_audio_and_preserves_full_timeline(tmp_path):
    video = tmp_path / "two-minutes.mp4"
    subprocess.run(
        [
            tool("ffmpeg"),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x90:r=5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "120",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-threads",
            "1",
            "-c:a",
            "aac",
            str(video),
        ],
        check=True,
    )
    wav = decode(video, tmp_path, threading.Event(), lambda *args: None)
    windows = [
        (start, end, total, len(samples))
        for start, end, total, samples in audio_segments(wav, seconds=12)
    ]
    assert windows[0][0] == 0
    assert abs(windows[-1][1] - 120) < 0.1  # AAC may add a partial terminal frame.
    assert max(w[3] for w in windows) <= 192_000
    assert all(first[1] == second[0] for first, second in zip(windows, windows[1:]))


def test_youtube_title_uses_small_verified_metadata_request(monkeypatch):
    import io
    import json
    import ssl
    from urllib.parse import parse_qs, urlparse

    from arabic_transcriber import media

    def fetch(request, **options):
        assert request.full_url.startswith("https://www.youtube.com/oembed?")
        assert parse_qs(urlparse(request.full_url).query)["url"] == ["https://youtu.be/example"]
        assert options["timeout"] == 8
        assert isinstance(options["context"], ssl.SSLContext)
        return io.BytesIO(json.dumps({"title": "مقابلة Berlin"}).encode())

    monkeypatch.setattr(media, "urlopen", fetch)
    assert media.youtube_title("https://youtu.be/example") == "مقابلة Berlin"
