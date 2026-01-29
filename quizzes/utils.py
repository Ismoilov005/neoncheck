from io import BytesIO
from datetime import datetime


def generate_certificate(user, test, percentage, certificate_id):
    """
    Generate a PDF certificate for user achievement.
    Design: Classic, minimalist — oltin/ko'k border va matn.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise ImportError("reportlab is required. Install it with: pip install reportlab")
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    styles = getSampleStyleSheet()
    gold = colors.HexColor('#c9a227')
    blue = colors.HexColor('#2c5282')
    dark = colors.HexColor('#1a202c')
    gray = colors.HexColor('#4a5568')
    
    title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=blue,
        spaceAfter=24,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        letterSpacing=2
    )
    subtitle_style = ParagraphStyle(
        'CertSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=gray,
        spaceAfter=16,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    name_style = ParagraphStyle(
        'CertName',
        parent=styles['Heading2'],
        fontSize=24,
        textColor=dark,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    content_style = ParagraphStyle(
        'CertContent',
        parent=styles['Normal'],
        fontSize=12,
        textColor=dark,
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    score_style = ParagraphStyle(
        'CertScore',
        parent=content_style,
        fontSize=16,
        textColor=blue,
        fontName='Helvetica-Bold'
    )
    date_style = ParagraphStyle(
        'CertDate',
        parent=styles['Normal'],
        fontSize=11,
        textColor=gray,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    id_style = ParagraphStyle(
        'CertID',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#a0aec0'),
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    story = []
    story.append(Paragraph("CERTIFICATE", title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("This is to certify that", subtitle_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(f"<b>{user.get_full_name() or user.username}</b>", name_style))
    story.append(Paragraph("has successfully completed the test", content_style))
    story.append(Paragraph(f"<b>{test.title}</b>", content_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"Score: <b>{percentage:.1f}%</b>", score_style))
    story.append(Spacer(1, 0.3*inch))
    current_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Date: {current_date}", date_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(f"Certificate ID: {str(certificate_id)[:8]}", id_style))
    
    def on_first_page(canvas_obj, doc):
        """Classic border: oltin tashqi, ichki ko'k chiziq"""
        w, h = letter[0], letter[1]
        margin = 0.5*inch
        canvas_obj.setStrokeColor(gold)
        canvas_obj.setLineWidth(3)
        canvas_obj.rect(margin, margin, w - 2*margin, h - 2*margin, fill=0, stroke=1)
        canvas_obj.setStrokeColor(blue)
        canvas_obj.setLineWidth(1)
        canvas_obj.rect(margin + 12, margin + 12, w - 2*margin - 24, h - 2*margin - 24, fill=0, stroke=1)
    
    doc.build(story, onFirstPage=on_first_page)
    buffer.seek(0)
    return buffer
