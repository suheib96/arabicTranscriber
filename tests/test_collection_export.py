"""Actual ZIP/export artifacts through the public exporter and desktop dialog."""

import zipfile
from datetime import date

from arabic_transcriber.exports import collection_title, export_collection


def test_collection_name_uses_only_a_common_playlist_and_actual_results():
    entries = [
        {
            "playlist_url": "https://www.youtube.com/playlist?list=PLone",
            "playlist_title": "دروس: Berlin",
            "segments": [{"text": "نص"}],
        },
        {
            "playlist_url": "https://www.youtube.com/playlist?list=PLone",
            "playlist_title": "دروس: Berlin",
            "segments": [{"text": "نص"}],
        },
        {"title": "Failed video", "segments": []},
    ]
    assert (
        collection_title(entries, date(2026, 11, 14)) == "دروس_ Berlin - 2 Transkripte - 2026-11-14"
    )
    entries[1]["playlist_url"] = "https://www.youtube.com/playlist?list=PLtwo"
    assert collection_title(entries, date(2026, 11, 14)) == "2 Transkripte - 2026-11-14"
    entries[1].pop("playlist_url")
    assert collection_title(entries, date(2026, 11, 14)) == "2 Transkripte - 2026-11-14"
    assert (
        collection_title(entries[:1], date(2026, 11, 14))
        == "دروس_ Berlin - 1 Transkript - 2026-11-14"
    )


def test_collection_contains_unique_safe_named_unicode_transcripts(tmp_path):
    entries = [
        {
            "title": "../../مقابلة: Berlin",
            "status": "completed",
            "segments": [{"start": 0, "end": 12, "text": "مرحبا Berlin 2026"}],
        },
        {
            "title": "../../مقابلة: Berlin",
            "status": "completed",
            "segments": [{"start": 12, "end": 24, "text": "نص ثان"}],
        },
    ]
    result = export_collection(entries, tmp_path / "transcripts.zip", "txt", True)
    with zipfile.ZipFile(result) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) == 3
        assert all("/" not in name and "\\" not in name and name.endswith(".txt") for name in names)
        assert archive.read(names[0]).decode("utf-8") == "[ca. 00:00 – 00:12]\nمرحبا Berlin 2026"
        assert archive.read(names[1]).decode("utf-8") == "[ca. 00:12 – 00:24]\nنص ثان"
        assert names[2] == f"Alle - 2 Transkripte - {date.today().isoformat()}.txt"
        combined = archive.read(names[2]).decode("utf-8")
        assert combined == (
            f"2 Transkripte - {date.today().isoformat()}\n\n"
            "1. ../../مقابلة: Berlin\n\n[ca. 00:00 – 00:12]\nمرحبا Berlin 2026\n\n"
            "2. ../../مقابلة: Berlin\n\n[ca. 00:12 – 00:24]\nنص ثان"
        )


def test_collection_preserves_existing_word_and_pdf_exporters(tmp_path):
    import io

    from docx import Document
    from pypdf import PdfReader

    entry = {
        "title": "Interview Berlin 2026",
        "status": "completed",
        "segments": [{"start": 0, "end": 12, "text": "مرحبا Berlin 2026"}],
    }
    for fmt in ("docx", "pdf"):
        second = {
            "title": "Second video",
            "status": "cancelled",
            "segments": [{"start": 0, "end": 3, "text": "نص ثان"}],
        }
        path = export_collection([entry, second], tmp_path / ("all-" + fmt + ".zip"), fmt)
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            assert len(names) == 3
            assert "Teiltranskript" in names[1]
            name = names[0]
            assert name.endswith("." + fmt)
            content = io.BytesIO(archive.read(name))
            if fmt == "docx":
                assert Document(content).paragraphs[0].text == "مرحبا Berlin 2026"
            else:
                assert len(PdfReader(content).pages) == 1
            combined = io.BytesIO(archive.read(names[-1]))
            if fmt == "docx":
                doc = Document(combined)
                assert [p.text for p in doc.paragraphs] == [
                    f"2 Transkripte - {date.today().isoformat()}",
                    "1. Interview Berlin 2026",
                    "مرحبا Berlin 2026",
                    "2. Second video - Teiltranskript",
                    "نص ثان",
                ]
                assert doc.paragraphs[3].paragraph_format.page_break_before
                assert doc.paragraphs[0].style.name == "Title"
            else:
                pdf = PdfReader(combined)
                assert len(pdf.pages) == 2
                assert "Interview Berlin 2026" in pdf.pages[0].extract_text()
                assert "Second video - Teiltranskript" in pdf.pages[1].extract_text()


def test_large_collection_keeps_individual_titles_order_and_combined_file(tmp_path):
    entries = [
        {
            "title": f"فيديو {n}: " + "العربية " * 60,
            "status": "completed",
            "segments": [{"start": 0, "end": 12, "text": f"نص {n}"}],
        }
        for n in range(1, 81)
    ]
    path = export_collection(entries, tmp_path / "eighty.zip", "txt")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == 81
        assert names[0].startswith("001 - فيديو 1_")
        assert names[79].startswith("080 - فيديو 80_")
        assert names[80] == f"Alle - 80 Transkripte - {date.today().isoformat()}.txt"
        assert archive.read(names[79]).decode("utf-8") == "نص 80"
        combined = archive.read(names[80]).decode("utf-8")
        assert combined.index("1. فيديو 1:") < combined.index("80. فيديو 80:")
        assert combined.endswith("نص 80")


def test_failed_combined_archive_write_preserves_existing_export(tmp_path, monkeypatch):
    import pytest

    destination = tmp_path / "existing.zip"
    destination.write_bytes(b"previous export")
    write = zipfile.ZipFile.write

    def storage_failure(archive, filename, arcname=None, **kwargs):
        if arcname.startswith("Alle - "):
            raise OSError("storage unavailable")
        return write(archive, filename, arcname, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "write", storage_failure)
    with pytest.raises(OSError):
        export_collection(
            [
                {
                    "title": "Video",
                    "status": "completed",
                    "segments": [{"start": 0, "end": 1, "text": "مرحبا"}],
                }
            ],
            destination,
            "txt",
        )
    assert destination.read_bytes() == b"previous export"
    assert list(tmp_path.iterdir()) == [destination]


def test_txt_archive_has_the_same_utf8_line_endings_on_windows(tmp_path, monkeypatch):
    from pathlib import Path

    original_open = Path.open

    def windows_text_open(path, mode="r", *args, **kwargs):
        if mode == "w" and kwargs.get("newline") is None:
            kwargs["newline"] = "\r\n"
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", windows_text_open)
    path = export_collection(
        [
            {
                "title": "Video",
                "status": "completed",
                "segments": [{"start": 0, "end": 1, "text": "مرحبا\nBerlin"}],
            }
        ],
        tmp_path / "windows.zip",
        "txt",
        True,
    )
    with zipfile.ZipFile(path) as archive:
        assert len(archive.namelist()) == 2
        assert all(b"\r" not in archive.read(name) for name in archive.namelist())
