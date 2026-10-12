"""PDF report generation from a stored triage record (ReportLab).

Font handling: a Unicode TrueType font is used when one is found. ReportLab does
NOT perform complex text shaping, so Devanagari (Hindi) may render with incorrect
conjuncts/vowel signs even when glyphs exist. Characters the font lacks are
replaced with '?' and the report says so. Hindi support is therefore LIMITED.
"""
from __future__ import annotations

import io
import os
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_CANDIDATES = [
    "C:/Windows/Fonts/Nirmala.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]
_URGENCY_COLORS = {"emergency": "#b00020", "urgent": "#c75000", "routine": "#2e7d32", "undetermined": "#555555"}


def _find_font(custom_path: Optional[str] = None) -> Tuple[str, Optional[Any]]:
    """Return (font_name, ttfont_or_None). Registers the font on first success."""
    for path in ([custom_path] if custom_path else []) + FONT_CANDIDATES:
        if path and os.path.isfile(path):
            name = "MedTriageUnicode"
            try:
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
                return name, pdfmetrics.getFont(name)
            except Exception:
                continue
    return "Helvetica", None


def _sanitize(text: str, font: Any) -> Tuple[str, bool]:
    """Replace characters the font cannot draw. Returns (text, replaced_any)."""
    replaced = False
    out = []
    covered = getattr(getattr(font, "face", None), "charToGlyph", None) if font else None
    for ch in text:
        if ch in "\n\t" or (covered is not None and ord(ch) in covered):
            out.append(ch)
        elif covered is None and ord(ch) < 256:  # Helvetica: Latin-1 only
            out.append(ch)
        else:
            out.append("?"); replaced = True
    return "".join(out), replaced


def generate_pdf(record: Dict[str, Any], font_path: Optional[str] = None) -> bytes:
    font_name, font = _find_font(font_path)
    any_replaced = False

    def clean(value: Any) -> str:
        nonlocal any_replaced
        text, rep = _sanitize(str(value), font)
        any_replaced = any_replaced or rep
        return escape(text)

    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["BodyText"], fontName=font_name, fontSize=10, leading=14)
    h1 = ParagraphStyle("h1", parent=base["Title"], fontName=font_name, fontSize=18, leading=22)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], fontName=font_name, fontSize=12, spaceBefore=10, spaceAfter=4)
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.HexColor("#444444"))

    def bullets(items: List[str]) -> List[Paragraph]:
        return [Paragraph("&bull; " + clean(i), body) for i in items] or [Paragraph("None recorded.", body)]

    urgency = str(record.get("urgency", "undetermined"))
    story: List[Any] = [
        Paragraph("MedTriage AI - Triage Support Report", h1),
        Paragraph(f"Report ID: {clean(record.get('request_id', ''))}<br/>Generated for request created: "
                  f"{clean(record.get('created_at', ''))}<br/>Input source: {clean(record.get('source', 'text'))}", body),
        Spacer(1, 6),
    ]
    badge = Table([[f"URGENCY (preliminary): {urgency.upper()}"]], colWidths=[170 * mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_URGENCY_COLORS.get(urgency, "#555555"))),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white), ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [badge]
    if record.get("emergency_advice"):
        story += [Spacer(1, 4), Paragraph("<b>" + clean(record["emergency_advice"]) + "</b>", body)]

    story += [Paragraph("Reported symptoms (rule-detected)", h2)] + bullets(record.get("reported_symptoms", []))
    if record.get("negated_symptoms"):
        story += [Paragraph("Reported as absent", h2)] + bullets(record["negated_symptoms"])
    src = "AI-assisted" if record.get("summary_source") == "ai" else "Rule-based (no AI)"
    story += [Paragraph(f"Summary - {src}", h2), Paragraph(clean(record.get("summary", "")), body)]
    story += [Paragraph("Urgency explanation", h2), Paragraph(clean(record.get("explanation", "")), body)]
    story += [Paragraph("Missing information and uncertainty", h2)] + bullets(record.get("uncertainties", []))
    if record.get("transcription"):
        t = record["transcription"]
        story += [Paragraph("Transcript", h2),
                  Paragraph(clean(f"Status: {t.get('status', 'unknown')}. Transcript is machine-generated and may contain errors."), small),
                  Paragraph(clean(record.get("input_text", "")), body)]
    story += [Paragraph("Processing mode", h2),
              Paragraph(clean(f"Mode: {record.get('mode')}; AI used: {record.get('ai_used')}; AI status: {record.get('ai_status')}"), body)]
    story += [Spacer(1, 10), Paragraph("<b>Disclaimer</b>", body),
              Paragraph(clean(record.get("disclaimer", "")) + " This report is NOT a diagnosis.", body)]
    if any_replaced or font is None:
        story += [Spacer(1, 6), Paragraph(
            "Note: some characters could not be rendered with the available font and were replaced with '?'. "
            "Hindi/Devanagari support in PDFs is limited.", small)]

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                      title="MedTriage AI Report", author="MedTriage AI (prototype)").build(story)
    return buf.getvalue()
