"""One transcript representation for clipboard, UTF-8 and shaped RTL documents."""

import os
import re
import tempfile
import unicodedata
import uuid
import zipfile
from datetime import date
from pathlib import Path

FONT = Path(__file__).parent / "fonts" / "NotoSansArabic.ttf"
LATIN_FONT = FONT.with_name("NotoSans.ttf")


def timestamp(seconds):
    value = max(0, int(seconds))
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"


def time_range(segment):
    return f"[ca. {timestamp(segment['start'])} – {timestamp(segment['end'])}]"


def render_text(segments, include_times=False):
    return "\n\n".join(
        (time_range(s) + "\n" if include_times else "") + s["text"] for s in segments
    )


def _embed_docx_font(document, font_path, family):
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.opc.packuri import PackURI
    from docx.opc.part import Part
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    font_table = next(
        part for part in document.part.package.parts if str(part.partname) == "/word/fontTable.xml"
    )
    from lxml import etree

    root = etree.fromstring(font_table.blob)
    font = OxmlElement("w:font")
    font.set(qn("w:name"), family)
    key = uuid.uuid4()
    data = bytearray(font_path.read_bytes())
    xor = key.bytes[::-1]
    for i in range(32):
        data[i] ^= xor[i % 16]
    part = Part(
        PackURI("/word/fonts/" + font_path.stem + ".odttf"),
        "application/vnd.openxmlformats-officedocument.obfuscatedFont",
        bytes(data),
        document.part.package,
    )
    relation = font_table.relate_to(part, RT.FONT)
    embed = OxmlElement("w:embedRegular")
    embed.set(qn("r:id"), relation)
    embed.set(qn("w:fontKey"), "{" + str(key).upper() + "}")
    embed.set(qn("w:subsetted"), "false")
    font.append(embed)
    root.append(font)
    font_table._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _is_rtl(text):
    for char in text:
        direction = unicodedata.bidirectional(char)
        if direction in ("R", "AL", "L"):
            return direction != "L"
    return False


def _title_parts(title):
    parts = title.rsplit(" - ", 2)
    return [parts[0], " - ".join(parts[1:])] if len(parts) == 3 else [title]


def _docx(segments, path, include_times, entries=None, title=None):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2.2)
    normal = doc.styles["Normal"]
    normal.font.name = "Noto Sans"
    normal.font.size = Pt(13)
    normal.paragraph_format.line_spacing = Pt(25)
    normal.paragraph_format.space_after = Pt(10)
    fonts = normal.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        fonts.set(qn("w:" + attr), "Noto Sans Arabic" if attr == "cs" else "Noto Sans")
    for name, size in (("Title", 20), ("Subtitle", 11), ("Heading 1", 16)):
        style = doc.styles[name]
        style.font.name, style.font.size = "Noto Sans", Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.underline = False
        style.font.italic = False
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(8 if name == "Title" else 12)
        style.paragraph_format.line_spacing = Pt(size + 10)
        ppr = style.element.get_or_add_pPr()
        for border in ppr.findall(qn("w:pBdr")):
            ppr.remove(border)
        heading_fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
        heading_fonts.attrib.clear()
        for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
            heading_fonts.set(qn("w:" + attr), "Noto Sans Arabic" if attr == "cs" else "Noto Sans")
        cs_size = OxmlElement("w:szCs")
        cs_size.set(qn("w:val"), str(size * 2))
        for previous in style.element.rPr.findall(qn("w:szCs")):
            style.element.rPr.remove(previous)
        style.element.rPr.append(cs_size)

    def heading(text, style, new_page=False, align_rtl=None):
        p = doc.add_paragraph(text, style)
        p.paragraph_format.page_break_before = new_page
        p.paragraph_format.keep_with_next = True
        text_rtl = _is_rtl(text)
        rtl = text_rtl if align_rtl is None else align_rtl
        # Word reverses logical paragraph alignment when bidi is enabled.
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl != text_rtl else WD_ALIGN_PARAGRAPH.LEFT
        if text_rtl:
            bidi = OxmlElement("w:bidi")
            p._p.get_or_add_pPr().append(bidi)

    if title:
        doc.core_properties.title = title
        parts = _title_parts(title)
        for index, part in enumerate(parts):
            heading(part, "Title" if index == 0 else "Subtitle", align_rtl=_is_rtl(parts[0]))
    for number, entry in enumerate(entries or [{"segments": segments}], 1):
        if entries is not None:
            heading(_entry_heading(entry, number), "Heading 1", number > 1)
        for s in entry["segments"]:
            if include_times:
                p = doc.add_paragraph(time_range(s))
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.keep_with_next = True
                for run in p.runs:
                    run.font.size = Pt(9)
            for line in s["text"].split("\n"):
                p = doc.add_paragraph(line)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                bidi = OxmlElement("w:bidi")
                p._p.get_or_add_pPr().append(bidi)
                # Paragraph bidi handles mixed Latin runs; forcing rtl on all runs reverses Latin.
                for run in p.runs:
                    size = OxmlElement("w:szCs")
                    size.set(qn("w:val"), "26")
                    run._r.get_or_add_rPr().append(size)
    _embed_docx_font(doc, FONT, "Noto Sans Arabic")
    _embed_docx_font(doc, LATIN_FONT, "Noto Sans")
    doc.save(path)


def _pdf(segments, path, include_times, entries=None, title=None):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_margins(22, 20, 22)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_font("NotoArabic", fname=str(FONT))
    pdf.add_font("NotoSans", fname=str(LATIN_FONT))
    pdf.set_fallback_fonts(["NotoSans"])
    pdf.add_page()

    def heading(text, size, align_rtl=None):
        pdf.set_text_color(30, 45, 38)
        pdf.set_font("NotoArabic", size=size)
        rtl = _is_rtl(text)
        pdf.set_text_shaping(True, direction="rtl" if rtl else "ltr")
        alignment = rtl if align_rtl is None else align_rtl
        pdf.multi_cell(0, 10, text, align="R" if alignment else "L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    if title:
        pdf.set_title(title)
        parts = _title_parts(title)
        for index, part in enumerate(parts):
            heading(part, 20 if index == 0 else 11, align_rtl=_is_rtl(parts[0]))
    for number, entry in enumerate(entries or [{"segments": segments}], 1):
        if entries is not None:
            if number > 1 or pdf.will_page_break(40):
                pdf.add_page()
            heading(_entry_heading(entry, number), 16)
        for s in entry["segments"]:
            if pdf.will_page_break(26):
                pdf.add_page()
            if include_times:
                pdf.set_font("NotoSans", size=9)
                pdf.set_text_color(100, 115, 105)
                pdf.set_text_shaping(True, direction="ltr")
                pdf.multi_cell(0, 6, time_range(s), align="R", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(30, 45, 38)
            pdf.set_font("NotoArabic", size=13)
            # HarfBuzz shaping plus Unicode bidi retain joined Arabic and Latin/numeric runs.
            pdf.set_text_shaping(True, direction="rtl")
            pdf.multi_cell(0, 10, s["text"], align="R", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
    pdf.output(path)


def export_transcript(segments, destination, fmt, include_times=False):
    if fmt not in ("txt", "docx", "pdf"):
        raise ValueError("Exportformat nicht unterstützt.")
    if not segments:
        raise ValueError("Noch kein Transkript vorhanden.")
    destination = Path(destination).with_suffix("." + fmt)
    # Atomic replace protects an existing export if generation fails.
    fd, temporary = tempfile.mkstemp(suffix="." + fmt, dir=destination.parent)
    os.close(fd)
    try:
        if fmt == "txt":
            Path(temporary).write_text(render_text(segments, include_times), encoding="utf-8")
        elif fmt == "docx":
            _docx(segments, temporary, include_times)
        else:
            _pdf(segments, temporary, include_times)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination


def _safe_name(title, limit=160):
    title = re.sub(r'[\\/\x00-\x1f<>:"|?*\u202a-\u202e\u2066-\u2069]', "_", str(title))
    # Bound UTF-8 bytes too: long Arabic/emoji titles otherwise exceed filesystem limits.
    return (
        title.encode("utf-8")[:limit].decode("utf-8", errors="ignore").strip(" .") or "Transkript"
    )


def collection_title(entries, export_date=None):
    entries = [entry for entry in entries if entry.get("segments")]
    count = len(entries)
    label = f"{count} {'Transkript' if count == 1 else 'Transkripte'}"
    playlist = entries[0].get("playlist_url") if entries else None
    playlist_title = entries[0].get("playlist_title") if entries else None
    prefix = (
        _safe_name(playlist_title, 120) + " - "
        if playlist
        and playlist_title
        and all(entry.get("playlist_url") == playlist for entry in entries)
        else ""
    )
    return f"{prefix}{label} - {(export_date or date.today()).isoformat()}"


def _entry_heading(entry, number):
    partial = " - Teiltranskript" if entry.get("status") != "completed" else ""
    return f"{number}. {entry.get('title') or 'Transkript'}{partial}"


def export_collection(entries, destination, fmt, include_times=False, *, title=None):
    """One atomic ZIP with separate transcripts and one combined document."""
    if fmt not in ("txt", "docx", "pdf"):
        raise ValueError("Exportformat nicht unterstützt.")
    entries = [entry for entry in entries if entry.get("segments")]
    if not entries:
        raise ValueError("Noch kein Transkript vorhanden.")
    title = title or collection_title(entries)
    destination = Path(destination).with_suffix(".zip")
    fd, temporary = tempfile.mkstemp(suffix=".zip", dir=destination.parent)
    os.close(fd)
    try:
        with (
            tempfile.TemporaryDirectory(prefix="arabic-export-") as directory,
            zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive,
        ):
            width = max(3, len(str(len(entries))))
            for number, entry in enumerate(entries, 1):
                video_title = _safe_name(entry.get("title") or "Transkript")
                partial = " - Teiltranskript" if entry.get("status") != "completed" else ""
                name = f"{number:0{width}d} - {video_title}{partial}.{fmt}"
                path = export_transcript(
                    entry["segments"], Path(directory) / name, fmt, include_times
                )
                archive.write(path, arcname=name)
            name = f"Alle - {_safe_name(title, 200)}.{fmt}"
            path = Path(directory) / name
            if fmt == "txt":
                content = [title]
                for number, entry in enumerate(entries, 1):
                    content.extend(
                        [
                            _entry_heading(entry, number),
                            render_text(entry["segments"], include_times),
                        ]
                    )
                path.write_text("\n\n".join(content), encoding="utf-8")
            elif fmt == "docx":
                _docx([], path, include_times, entries=entries, title=title)
            else:
                _pdf([], path, include_times, entries=entries, title=title)
            archive.write(path, arcname=name)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination
