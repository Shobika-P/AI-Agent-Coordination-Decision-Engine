import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def safe_str(val, fallback=""):
    if val is None:
        return fallback
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float, bool)):
        return str(val)
    if isinstance(val, (list, dict)):
        try:
            return json.dumps(val, indent=2)
        except:
            return fallback
    return fallback


def generate_decision_pdf(report_data: dict, task: str, conversation_history: list = None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0b0f19'),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=12
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    bold_body = ParagraphStyle(
        'DocBoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    elements = []

    # Header Banner
    elements.append(Paragraph("ENTERPRISE AI BUSINESS DECISION SUPPORT ENGINE", ParagraphStyle('Eyebrow', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#2563eb'), leading=10, spaceAfter=2)))
    elements.append(Paragraph("Executive Strategic Assessment Report", title_style))
    elements.append(Paragraph(f"Query: <b>{safe_str(task)}</b>", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=12))

    # Decision Recommendation Hero & Intelligence Scores
    decision_text = safe_str(report_data.get("decision"), "Decision recommendation generated.")
    risk_level = safe_str(report_data.get("risk_level"), "Medium")
    viability_score = report_data.get("viability_score", 78)
    confidence = report_data.get("confidence", 82)

    risk_color = colors.HexColor('#d97706')
    if risk_level.lower() == "low":
        risk_color = colors.HexColor('#059669')
    elif risk_level.lower() == "high":
        risk_color = colors.HexColor('#dc2626')

    hero_table_data = [
        [
            Paragraph(f"<b>BUSINESS VIABILITY</b><br/><font size='16' color='#2563eb'><b>{viability_score} / 100</b></font>", ParagraphStyle('Score1', fontName='Helvetica', fontSize=8, leading=12, alignment=1)),
            Paragraph(f"<b>AI CONFIDENCE</b><br/><font size='16' color='#059669'><b>{confidence}%</b></font>", ParagraphStyle('Score2', fontName='Helvetica', fontSize=8, leading=12, alignment=1)),
            Paragraph(f"<b>MARKET RISK</b><br/><font size='14' color='{risk_color.hexval()}'><b>{risk_level.upper()}</b></font>", ParagraphStyle('Score3', fontName='Helvetica', fontSize=8, leading=12, alignment=1))
        ]
    ]

    hero_table = Table(hero_table_data, colWidths=[175, 175, 180])
    hero_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(hero_table)
    elements.append(Spacer(1, 10))

    # Executive Summary Section
    elements.append(Paragraph("01. Executive Summary", h2_style))
    elements.append(Paragraph(decision_text.replace('\n', '<br/>'), body_style))
    elements.append(Spacer(1, 8))

    # Why This Decision Drivers
    why_list = report_data.get("why_this_decision")
    if isinstance(why_list, list) and len(why_list) > 0:
        elements.append(Paragraph("<b>Strategic Drivers (Why This Decision?):</b>", bold_body))
        for item in why_list:
            elements.append(Paragraph(f"• {safe_str(item)}", body_style))
        elements.append(Spacer(1, 6))

    # Key Risks & Key Opportunities Grid
    risks_list = report_data.get("key_risks")
    opps_list = report_data.get("key_opportunities")

    if (isinstance(risks_list, list) and risks_list) or (isinstance(opps_list, list) and opps_list):
        risk_text_cell = "<b>Key Risk Factors</b><br/>" + "<br/>".join([f"⚠️ {safe_str(r)}" for r in (risks_list or [])])
        opp_text_cell = "<b>Strategic Opportunities</b><br/>" + "<br/>".join([f"✦ {safe_str(o)}" for o in (opps_list or [])])

        grid_table = Table([[
            Paragraph(risk_text_cell, body_style),
            Paragraph(opp_text_cell, body_style)
        ]], colWidths=[260, 270])

        grid_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#fef2f2')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f0fdf4')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        elements.append(grid_table)
        elements.append(Spacer(1, 10))

    # Tool Analysis Section
    tool_analysis = report_data.get("tool_analysis")
    if isinstance(tool_analysis, dict):
        elements.append(Paragraph("02. Quantitative Business Tool Analysis", h2_style))
        tool_name = safe_str(tool_analysis.get("tool_name"), "Market Risk Tool")
        tool_risk = safe_str(tool_analysis.get("risk_level"), risk_level)
        tool_rec = safe_str(tool_analysis.get("recommendation"), "")

        elements.append(Paragraph(f"<b>Analysis Tool:</b> {tool_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Risk Rating:</b> {tool_risk}", bold_body))
        if tool_rec:
            elements.append(Paragraph(f"<b>Tool Recommendation:</b> {tool_rec}", body_style))

        obs_list = tool_analysis.get("observations")
        if isinstance(obs_list, list) and len(obs_list) > 0:
            for obs in obs_list:
                elements.append(Paragraph(f"• {safe_str(obs)}", body_style))
        elements.append(Spacer(1, 8))

    # Conversation History Thread
    if isinstance(conversation_history, list) and len(conversation_history) > 0:
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=10, spaceAfter=8))
        elements.append(Paragraph("Follow-up Conversation Thread", h2_style))
        for idx, turn in enumerate(conversation_history, 1):
            if isinstance(turn, dict):
                q = safe_str(turn.get("question"))
                a = safe_str(turn.get("answer"))
                if q:
                    elements.append(Paragraph(f"<b>User Question {idx}:</b> {q}", ParagraphStyle('QStyle', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#1d4ed8'))))
                if a:
                    elements.append(Paragraph(f"<b>AI Decision Engine:</b> {a.replace('\n', '<br/>')}", body_style))
                elements.append(Spacer(1, 4))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

