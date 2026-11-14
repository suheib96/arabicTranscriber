"""Actual ZIP/export artifacts through the public exporter and desktop dialog."""

import zipfile

from arabic_transcriber.exports import export_collection


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
        assert len(names) == len(set(names)) == 2
        assert all("/" not in name and "\\" not in name and name.endswith(".txt") for name in names)
        assert archive.read(names[0]).decode("utf-8") == "[ca. 00:00 – 00:12]\nمرحبا Berlin 2026"
        assert archive.read(names[1]).decode("utf-8") == "[ca. 00:12 – 00:24]\nنص ثان"


def test_collection_preserves_existing_word_and_pdf_exporters(tmp_path):
    import io

    from docx import Document
    from pypdf import PdfReader

    entry = {
        "title": "مقابلة",
        "status": "completed",
        "segments": [{"start": 0, "end": 12, "text": "مرحبا Berlin 2026"}],
    }
    for fmt in ("docx", "pdf"):
        path = export_collection([entry], tmp_path / ("all-" + fmt + ".zip"), fmt)
        with zipfile.ZipFile(path) as archive:
            name = archive.namelist()[0]
            assert name.endswith("." + fmt)
            content = io.BytesIO(archive.read(name))
            if fmt == "docx":
                assert Document(content).paragraphs[0].text == "مرحبا Berlin 2026"
            else:
                assert len(PdfReader(content).pages) == 1
