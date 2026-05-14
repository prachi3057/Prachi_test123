"""
export.py — MedVault PDF generator
Uses ReportLab Platypus (flow-based) layout so text NEVER overlaps.
"""

import os, time
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable

EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

# ── Colour palette ───────────────────────────────────────────
C_DARK    = colors.HexColor('#0d1219')
C_SURFACE = colors.HexColor('#141c27')
C_TEAL    = colors.HexColor('#00d4b4')
C_GOLD    = colors.HexColor('#f0b429')
C_TEXT    = colors.HexColor('#f0f4f8')
C_TEXT2   = colors.HexColor('#8fa3b8')
C_BORDER  = colors.HexColor('#1f2b3e')
C_WHITE   = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


# ── Style helpers ────────────────────────────────────────────
def _style(name, **kw):
    defaults = dict(
        fontName='Helvetica', fontSize=10,
        textColor=colors.HexColor('#1a1a2e'),
        leading=16, spaceAfter=0, spaceBefore=0,
    )
    defaults.update(kw)
    return ParagraphStyle(name=name, **defaults)


S_TITLE   = _style('title',  fontName='Helvetica-Bold', fontSize=26, textColor=C_DARK,  leading=32, spaceAfter=4)
S_SUB     = _style('sub',    fontName='Helvetica',       fontSize=10, textColor=C_TEXT2, leading=14, spaceAfter=2)
S_HEAD    = _style('head',   fontName='Helvetica-Bold', fontSize=11, textColor=C_TEAL,  leading=16, spaceBefore=6, spaceAfter=4)
S_BODY    = _style('body',   fontName='Helvetica',       fontSize=10, textColor=C_DARK,  leading=16, spaceAfter=3)
S_SMALL   = _style('small',  fontName='Helvetica',       fontSize=8,  textColor=C_TEXT2, leading=12)
S_TAG     = _style('tag',    fontName='Helvetica-Bold', fontSize=9,  textColor=C_TEAL,  leading=12)
S_LABEL   = _style('label',  fontName='Helvetica-Bold', fontSize=9,  textColor=C_TEXT2, leading=12)
S_VALUE   = _style('value',  fontName='Helvetica',       fontSize=10, textColor=C_DARK,  leading=14)
S_BULLET  = _style('bullet', fontName='Helvetica',       fontSize=10, textColor=C_DARK,  leading=16, leftIndent=12, spaceAfter=3)
S_EMPTY   = _style('empty',  fontName='Helvetica-Oblique', fontSize=9, textColor=C_TEXT2, leading=14)
S_FOOTER  = _style('footer', fontName='Helvetica',       fontSize=8,  textColor=C_TEXT2, leading=12, alignment=TA_CENTER)


def _divider(color=C_BORDER, thickness=0.8):
    return HRFlowable(width='100%', thickness=thickness, color=color,
                      spaceAfter=8, spaceBefore=6)


def _section_header(text):
    return KeepTogether([
        _divider(C_TEAL, 1.5),
        Paragraph(text, S_HEAD),
        Spacer(1, 4),
    ])


def _info_table(rows):
    """Two-column label/value table, self-wrapping."""
    col_w = [(PAGE_W - 2*MARGIN) * f for f in (0.32, 0.68)]
    data = [[Paragraph(k, S_LABEL), Paragraph(v or '—', S_VALUE)] for k, v in rows]
    t = Table(data, colWidths=col_w, repeatRows=0)
    t.setStyle(TableStyle([
        ('TOPPADDING',   (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',  (0,0),(-1,-1), 8),
        ('RIGHTPADDING', (0,0),(-1,-1), 8),
        ('ROWBACKGROUNDS',(0,0),(-1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ('GRID',         (0,0),(-1,-1), 0.3, colors.HexColor('#e0e0e0')),
    ]))
    return t


def _today():
    return date.today().strftime('%d %B %Y')


# ── Header block ─────────────────────────────────────────────
def _header_block(title_text, subtitle_text, story):
    """Draws the top branding block as flowables — no canvas overlap."""
    # Title row as a table so logo + text sit side by side
    logo_cell = Paragraph('<b>✚</b>', ParagraphStyle(
        'logo', fontName='Helvetica-Bold', fontSize=22,
        textColor=C_WHITE, alignment=TA_CENTER
    ))
    logo_bg_data = [[logo_cell]]
    logo_tbl = Table(logo_bg_data, colWidths=[1.1*cm], rowHeights=[1.1*cm])
    logo_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(0,0), C_TEAL),
        ('ROUNDEDCORNERS', [6]),
        ('VALIGN', (0,0),(0,0), 'MIDDLE'),
        ('TOPPADDING',   (0,0),(0,0), 2),
        ('BOTTOMPADDING',(0,0),(0,0), 2),
    ]))

    title_p = Paragraph(title_text, ParagraphStyle(
        'htitle', fontName='Helvetica-Bold', fontSize=22,
        textColor=C_DARK, leading=26
    ))
    sub_p = Paragraph(subtitle_text, ParagraphStyle(
        'hsub', fontName='Helvetica', fontSize=10,
        textColor=C_TEXT2, leading=14
    ))

    header_row = Table(
        [[logo_tbl, [title_p, sub_p]]],
        colWidths=[1.4*cm, PAGE_W - 2*MARGIN - 1.4*cm]
    )
    header_row.setStyle(TableStyle([
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (1,0),(1,0), 12),
        ('TOPPADDING',  (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
    ]))

    story.append(header_row)
    story.append(Spacer(1, 0.5*cm))

    # Teal/gold accent bar
    accent = Table([['', '']], colWidths=[
        (PAGE_W - 2*MARGIN) * 0.6,
        (PAGE_W - 2*MARGIN) * 0.4,
    ], rowHeights=[3])
    accent.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(0,0), C_TEAL),
        ('BACKGROUND', (1,0),(1,0), C_GOLD),
        ('TOPPADDING',   (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
    ]))
    story.append(accent)
    story.append(Spacer(1, 0.6*cm))


def _footer(story):
    story.append(Spacer(1, 0.5*cm))
    story.append(_divider())
    story.append(Paragraph(
        f'MedVault Health Record System &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; Generated: {_today()}',
        S_FOOTER
    ))


# ── EXPORT: single record ────────────────────────────────────
def export_record_pdf(record, patient):
    ts = int(time.time())
    path = os.path.join(EXPORT_DIR, f'record_{record["id"]}_{ts}.pdf')

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        topMargin=MARGIN, bottomMargin=MARGIN,
        leftMargin=MARGIN, rightMargin=MARGIN,
        title=f'Medical Record — {record["file_name"]}',
    )
    story = []

    _header_block('Medical Record', 'MedVault Health Record System', story)

    # ── Patient section ──
    if patient:
        story.append(_section_header('Patient Information'))
        story.append(_info_table([
            ('Full Name',         str(patient['name'] or '')),
            ('Age',               (str(patient['age']) + ' years') if patient['age'] else ''),
            ('Gender',            str(patient['gender'] or '')),
            ('Blood Group',       str(patient['blood_group'] or '')),
            ('Emergency Contact', str(patient['emergency_contact'] or '')),
        ]))
        story.append(Spacer(1, 0.3*cm))

    # ── Record section ──
    story.append(_section_header('Record Details'))
    story.append(_info_table([
        ('Record Name',  str(record['file_name'] or '')),
        ('Category',     str(record['cat_name'] or '')),
        ('File',         str(record['file_path'] or '')),
        ('File Type',    str(record['file_type'] or '')),
        ('Upload Date',  str(record['upload_date'])[:10] if record['upload_date'] else ''),
    ]))

    _footer(story)
    doc.build(story)
    return path


# ── EXPORT: full health summary ──────────────────────────────
def export_summary_pdf(patient, medicines, diseases, allergies, recent_records):
    ts = int(time.time())
    path = os.path.join(EXPORT_DIR, f'health_summary_{ts}.pdf')

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        topMargin=MARGIN, bottomMargin=MARGIN,
        leftMargin=MARGIN, rightMargin=MARGIN,
        title='Personal Health Summary',
    )
    story = []

    _header_block('Personal Health Summary', 'MedVault Health Record System', story)

    # ── Patient profile ──
    if patient:
        story.append(_section_header('Patient Profile'))
        story.append(_info_table([
            ('Full Name',         str(patient['name'] or '')),
            ('Age',               (str(patient['age']) + ' years') if patient['age'] else ''),
            ('Gender',            str(patient['gender'] or '')),
            ('Blood Group',       str(patient['blood_group'] or '')),
            ('Emergency Contact', str(patient['emergency_contact'] or '')),
        ]))
        story.append(Spacer(1, 0.3*cm))

    # ── Medicines ──
    story.append(_section_header('Current Medicines'))
    if medicines:
        for m in medicines:
            story.append(Paragraph(f'• {m["medicine_text"]}', S_BULLET))
    else:
        story.append(Paragraph('No medicines recorded.', S_EMPTY))
    story.append(Spacer(1, 0.2*cm))

    # ── Diseases ──
    story.append(_section_header('Past Diseases'))
    if diseases:
        for d in diseases:
            story.append(Paragraph(f'• {d["disease_name"]}', S_BULLET))
    else:
        story.append(Paragraph('No past diseases recorded.', S_EMPTY))
    story.append(Spacer(1, 0.2*cm))

    # ── Allergies ──
    story.append(_section_header('Allergies'))
    if allergies:
        for a in allergies:
            story.append(Paragraph(f'• {a["allergy_name"]}', S_BULLET))
    else:
        story.append(Paragraph('No allergies recorded.', S_EMPTY))
    story.append(Spacer(1, 0.3*cm))

    # ── Recent records table ──
    story.append(_section_header('Recently Uploaded Records'))
    if recent_records:
        usable_w = PAGE_W - 2*MARGIN
        col_widths = [usable_w*0.45, usable_w*0.28, usable_w*0.27]
        header = [
            Paragraph('<b>Record Name</b>', S_LABEL),
            Paragraph('<b>Category</b>',    S_LABEL),
            Paragraph('<b>Upload Date</b>', S_LABEL),
        ]
        rows = [header] + [
            [
                Paragraph(str(r['file_name']),  S_BODY),
                Paragraph(str(r['cat_name']),   S_BODY),
                Paragraph(str(r['upload_date'])[:10] if r['upload_date'] else '', S_BODY),
            ]
            for r in recent_records
        ]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            # Header
            ('BACKGROUND',   (0,0), (-1,0), C_TEAL),
            ('TEXTCOLOR',    (0,0), (-1,0), C_WHITE),
            ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',     (0,0), (-1,0), 9),
            # Body
            ('FONTNAME',     (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE',     (0,1), (-1,-1), 9),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
            # Padding
            ('TOPPADDING',   (0,0),(-1,-1), 6),
            ('BOTTOMPADDING',(0,0),(-1,-1), 6),
            ('LEFTPADDING',  (0,0),(-1,-1), 8),
            ('RIGHTPADDING', (0,0),(-1,-1), 8),
            # Grid
            ('GRID',         (0,0),(-1,-1), 0.3, colors.HexColor('#cccccc')),
            ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
            # Word wrap
            ('WORDWRAP',     (0,0),(-1,-1), True),
        ]))
        story.append(t)
    else:
        story.append(Paragraph('No records uploaded yet.', S_EMPTY))

    _footer(story)
    doc.build(story)
    return path
