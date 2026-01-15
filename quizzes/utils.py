from io import BytesIO
from datetime import datetime


def generate_certificate(user, test, percentage, certificate_id):
    """
    Generate a PDF certificate for user achievement
    Design: Dark background, neon green border, futuristic style
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
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    # Title style - Futuristic, bold
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=colors.HexColor('#10b981'),  # Neon green
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        letterSpacing=3
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=18,
        textColor=colors.HexColor('#e5e5e5'),  # Light gray
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Name style - Large, prominent
    name_style = ParagraphStyle(
        'CustomName',
        parent=styles['Heading2'],
        fontSize=28,
        textColor=colors.HexColor('#10b981'),  # Neon green
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Content style
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#a0a0a0'),  # Secondary text
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Date style
    date_style = ParagraphStyle(
        'CustomDate',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#10b981'),
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    # Build PDF content
    story = []
    
    # Add title
    story.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Add subtitle
    story.append(Paragraph("This is to certify that", subtitle_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Add user name
    story.append(Paragraph(f"<b>{user.username.upper()}</b>", name_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Add achievement text
    story.append(Paragraph(
        f"has successfully completed the test", 
        content_style
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        f"<b>'{test.title}'</b>", 
        ParagraphStyle(
            'TestTitle',
            parent=content_style,
            fontSize=16,
            textColor=colors.HexColor('#e5e5e5'),
            fontName='Helvetica-Bold'
        )
    ))
    story.append(Spacer(1, 0.2*inch))
    
    # Add score
    story.append(Paragraph(
        f"with a score of <b>{percentage:.1f}%</b>", 
        ParagraphStyle(
            'Score',
            parent=content_style,
            fontSize=16,
            textColor=colors.HexColor('#10b981'),
            fontName='Helvetica-Bold'
        )
    ))
    story.append(Spacer(1, 0.4*inch))
    
    # Add date
    current_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Date: {current_date}", date_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Add certificate ID (small, bottom)
    story.append(Paragraph(
        f"Certificate ID: {str(certificate_id)[:8]}", 
        ParagraphStyle(
            'CertID',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
    ))
    
    # Build PDF with custom background
    def on_first_page(canvas_obj, doc):
        """Draw dark background and neon border"""
        # Draw dark background
        canvas_obj.setFillColor(colors.HexColor('#1a1a1a'))
        canvas_obj.rect(0, 0, letter[0], letter[1], fill=1)
        
        # Draw neon green border
        canvas_obj.setStrokeColor(colors.HexColor('#10b981'))
        canvas_obj.setLineWidth(4)
        canvas_obj.setDash([10, 5], 0)  # Dashed line for futuristic look
        canvas_obj.rect(0.5*inch, 0.5*inch, letter[0]-inch, letter[1]-inch, fill=0, stroke=1)
        
        # Draw corner decorations
        corner_size = 0.3*inch
        canvas_obj.setLineWidth(2)
        canvas_obj.setDash([5, 3], 0)
        
        # Top-left corner
        canvas_obj.line(0.5*inch, letter[1]-0.5*inch, 0.5*inch, letter[1]-0.5*inch-corner_size)
        canvas_obj.line(0.5*inch, letter[1]-0.5*inch, 0.5*inch+corner_size, letter[1]-0.5*inch)
        
        # Top-right corner
        canvas_obj.line(letter[0]-0.5*inch, letter[1]-0.5*inch, letter[0]-0.5*inch, letter[1]-0.5*inch-corner_size)
        canvas_obj.line(letter[0]-0.5*inch, letter[1]-0.5*inch, letter[0]-0.5*inch-corner_size, letter[1]-0.5*inch)
        
        # Bottom-left corner
        canvas_obj.line(0.5*inch, 0.5*inch, 0.5*inch, 0.5*inch+corner_size)
        canvas_obj.line(0.5*inch, 0.5*inch, 0.5*inch+corner_size, 0.5*inch)
        
        # Bottom-right corner
        canvas_obj.line(letter[0]-0.5*inch, 0.5*inch, letter[0]-0.5*inch, 0.5*inch+corner_size)
        canvas_obj.line(letter[0]-0.5*inch, 0.5*inch, letter[0]-0.5*inch-corner_size, 0.5*inch)
    
    doc.build(story, onFirstPage=on_first_page)
    
    buffer.seek(0)
    return buffer
