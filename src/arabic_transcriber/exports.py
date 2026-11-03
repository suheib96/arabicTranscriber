"""One transcript representation for clipboard, UTF-8 and shaped RTL documents."""

import os
import tempfile
import uuid
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


def _docx(segments, path, include_times):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

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
    for s in segments:
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


def _pdf(segments, path, include_times):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_margins(22, 20, 22)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_font("NotoArabic", fname=str(FONT))
    pdf.add_font("NotoSans", fname=str(LATIN_FONT))
    pdf.set_fallback_fonts(["NotoSans"])
    pdf.add_page()
    for s in segments:
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
