"""YouTube playlist metadata only; playback media always use the serial worker."""

import re
from urllib.parse import parse_qs, urlencode, urlparse

from .media import check_cancel, youtube_url


def playlist_url(value):
    try:
        parsed = urlparse(value.strip())
        identifier = parse_qs(parsed.query).get("list", [""])[0]
        if (
            parsed.scheme != "https"
            or parsed.hostname
            not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
            or parsed.username
            or parsed.password
            or parsed.port
            or parsed.path != "/playlist"
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", identifier)
        ):
            return None
        return "https://www.youtube.com/playlist?" + urlencode({"list": identifier})
    except (ValueError, AttributeError):
        return None


def video_key(value):
    if not youtube_url(value):
        return None
    parsed = urlparse(value)
    if parsed.hostname == "youtu.be":
        return parsed.path.strip("/")
    if parsed.path == "/watch":
        return parse_qs(parsed.query)["v"][0]
    return parsed.path.strip("/").split("/")[-1]


def read_playlist(value, cancel, report):
    """Enumerate titles/IDs without resolving streams or downloading any media."""
    url = playlist_url(value)
    if not url:
        raise ValueError("Bitte einen gültigen YouTube-Playlist-Link eingeben.")
    import yt_dlp

    class Quiet:
        def debug(self, message):
            pass

        warning = error = debug

    options = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "lazy_playlist": True,
        "quiet": True,
        "no_warnings": True,
        "logger": Quiet(),
        "ignoreerrors": True,
        "socket_timeout": 10,
        "retries": 1,
        "extractor_retries": 1,
        "js_runtimes": {},
        "remote_components": [],
        "cachedir": False,
    }
    entries, skipped = [], 0
    try:
        check_cancel(cancel)
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)
            if not info or info.get("_type") != "playlist":
                raise ValueError("Playlist ist nicht verfügbar oder nicht öffentlich.")
            for entry in info.get("entries") or []:
                check_cancel(cancel)
                title = entry.get("title") if entry else None
                identifier = entry.get("id") if entry else None
                if (
                    not entry
                    or not identifier
                    or not re.fullmatch(r"[A-Za-z0-9_-]+", identifier)
                    or title in ("[Private video]", "[Deleted video]")
                    or entry.get("availability")
                    in ("private", "premium_only", "subscriber_only", "needs_auth")
                    or entry.get("is_live")
                    or entry.get("live_status") in ("is_live", "is_upcoming")
                ):
                    skipped += 1
                    continue
                entries.append(
                    {
                        "url": "https://www.youtube.com/watch?" + urlencode({"v": identifier}),
                        "title": str(title or "")[:500],
                    }
                )
                report(len(entries))
            check_cancel(cancel)
            return {
                "title": str(info.get("title") or "YouTube-Playlist")[:500],
                "entries": entries,
                "skipped": skipped,
            }
    except Exception:
        check_cancel(cancel)
        raise RuntimeError(
            "Playlist konnte nicht eingelesen werden. Verbindung und öffentliche Freigabe prüfen."
        ) from None
