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
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#6366f1'),
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    bold_body = ParagraphStyle(
        'DocBoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    elements = []

    # Header Banner
    elements.append(Paragraph("AI BUSINESS DECISION ENGINE", ParagraphStyle('Eyebrow', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#6366f1'), leading=11, spaceAfter=4)))
    elements.append(Paragraph("Executive Strategic Decision Report", title_style))
    elements.append(Paragraph(f"Query: <b>{safe_str(task)}</b>", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

    # Decision Recommendation Hero
    decision_text = safe_str(report_data.get("decision"), "Decision recommendation generated.")
    risk_level = safe_str(report_data.get("risk_level"), "Medium")

    risk_color = colors.HexColor('#f59e0b')
    if risk_level.lower() == "low":
        risk_color = colors.HexColor('#10b981')
    elif risk_level.lower() == "high":
        risk_color = colors.HexColor('#ef4444')

    rec_title = decision_text.split('\n')[0] if decision_text else "RECOMMENDATION GENERATED"
    if len(rec_title) > 120:
        rec_title = rec_title[:117] + "..."

    hero_table_data = [
        [
            Paragraph(f"<b>FINAL RECOMMENDATION:</b><br/>{rec_title}", ParagraphStyle('HeroText', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#0f172a'))),
            Paragraph(f"<b>MARKET RISK</b><br/><font color='{risk_color.hexval()}'><b>{risk_level.upper()} RISK</b></font>", ParagraphStyle('RiskText', fontName='Helvetica-Bold', fontSize=11, leading=15, alignment=1))
        ]
    ]

    hero_table = Table(hero_table_data, colWidths=[380, 150])
    hero_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(hero_table)
    elements.append(Spacer(1, 15))

    # Executive Summary Section
    elements.append(Paragraph("01. Executive Summary", h2_style))
    elements.append(Paragraph(decision_text.replace('\n', '<br/>'), body_style))
    elements.append(Spacer(1, 10))

    # Tool Analysis Section
    tool_analysis = report_data.get("tool_analysis")
    if isinstance(tool_analysis, dict):
        elements.append(Paragraph("02. Quantitative Tool Analysis", h2_style))
        tool_name = safe_str(tool_analysis.get("tool_name"), "Market Risk Tool")
        tool_risk = safe_str(tool_analysis.get("risk_level"), risk_level)
        tool_rec = safe_str(tool_analysis.get("recommendation"), "")

        elements.append(Paragraph(f"<b>Analysis Tool:</b> {tool_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Risk Rating:</b> {tool_risk}", bold_body))
        if tool_rec:
            elements.append(Paragraph(f"<b>Tool Recommendation:</b> {tool_rec}", body_style))

        obs_list = tool_analysis.get("observations")
        if isinstance(obs_list, list) and len(obs_list) > 0:
            elements.append(Paragraph("<b>Key Observations:</b>", bold_body))
            for obs in obs_list:
                elements.append(Paragraph(f"• {safe_str(obs)}", body_style))
        elements.append(Spacer(1, 10))

    # Research Summary
    research_summary = report_data.get("research_summary")
    if isinstance(research_summary, list) and len(research_summary) > 0:
        elements.append(Paragraph("03. Market Research Insights", h2_style))
        for idx, insight in enumerate(research_summary, 1):
            elements.append(Paragraph(f"<b>[{idx:02d}]</b> {safe_str(insight)}", body_style))
        elements.append(Spacer(1, 10))

    # Business Plan
    business_plan = report_data.get("business_plan")
    if isinstance(business_plan, list) and len(business_plan) > 0:
        elements.append(Paragraph("04. Strategic Execution Plan", h2_style))
        for idx, phase in enumerate(business_plan, 1):
            if isinstance(phase, dict):
                p_title = safe_str(phase.get("title"), f"Phase {idx}")
                p_desc = safe_str(phase.get("description"), "")
                elements.append(Paragraph(f"<b>Phase {idx}: {p_title}</b>", bold_body))
                if p_desc:
                    elements.append(Paragraph(p_desc, body_style))
        elements.append(Spacer(1, 10))

    # Conversation History
    if isinstance(conversation_history, list) and len(conversation_history) > 0:
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceBefore=15, spaceAfter=10))
        elements.append(Paragraph("Follow-up Q&A Discussion Thread", h2_style))
        for idx, turn in enumerate(conversation_history, 1):
            if isinstance(turn, dict):
                q = safe_str(turn.get("question"))
                a = safe_str(turn.get("answer"))
                if q:
                    elements.append(Paragraph(f"<b>User Question {idx}:</b> {q}", ParagraphStyle('QStyle', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#4f46e5'))))
                if a:
                    elements.append(Paragraph(f"<b>AI Decision Engine:</b><br/>{a.replace('\n', '<br/>')}", body_style))
                elements.append(Spacer(1, 6))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
