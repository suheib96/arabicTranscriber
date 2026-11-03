from zipfile import ZipFile

from docx import Document
from pypdf import PdfReader

from arabic_transcriber.exports import export_transcript, render_text

SEGMENTS = [
    {"start": 0, "end": 24, "text": "مرحبًا بكم في Berlin 2026.\nهذا نص عربي للاختبار."},
    {"start": 3661, "end": 3680, "text": "نتحدث اليوم عن أهمية التعلم وتبادل المعرفة."},
]


def test_copy_and_real_exports_preserve_arabic_and_timestamp_choice(tmp_path):
    assert render_text(SEGMENTS, False) == (
        "مرحبًا بكم في Berlin 2026.\nهذا نص عربي للاختبار.\n\n"
        "نتحدث اليوم عن أهمية التعلم وتبادل المعرفة."
    )
    assert "[ca. 01:01:01 – 01:01:20]" in render_text(SEGMENTS, True)
    for times in (False, True):
        for fmt in ("txt", "docx", "pdf"):
            path = export_transcript(SEGMENTS, tmp_path / f"result-{times}.{fmt}", fmt, times)
            assert path.is_file()
            if fmt == "txt":
                assert path.read_text("utf-8") == render_text(SEGMENTS, times)
            if fmt == "docx":
                text = "\n".join(p.text for p in Document(path).paragraphs)
                assert "مرحبًا بكم في Berlin 2026." in text
                assert ("01:01:01" in text) is times
                with ZipFile(path) as zip:
                    assert b"w:bidi" in zip.read("word/document.xml")
            if fmt == "pdf":
                reader = PdfReader(path)
                assert len(reader.pages) == 1
                text = reader.pages[0].extract_text()
                assert "Berlin" in text
                assert ("01:01:01" in text) is times
