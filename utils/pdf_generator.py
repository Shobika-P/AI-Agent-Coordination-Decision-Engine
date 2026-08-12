import os
import io
import json
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Registered font names
FONT_NORMAL = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

def _init_pdf_fonts():
    global FONT_NORMAL, FONT_BOLD
    font_candidates = [
        (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf', 'EnterpriseArial'),
        (r'C:\Windows\Fonts\segoeui.ttf', r'C:\Windows\Fonts\segoeuib.ttf', 'EnterpriseSegoe'),
        (r'C:\Windows\Fonts\calibri.ttf', r'C:\Windows\Fonts\calibrib.ttf', 'EnterpriseCalibri'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'EnterpriseDejaVu'),
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 'EnterpriseLiberation'),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf', 'EnterpriseMacArial'),
    ]

    for reg_path, bold_path, family_name in font_candidates:
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont(family_name, reg_path))
                FONT_NORMAL = family_name
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(family_name + "-Bold", bold_path))
                    FONT_BOLD = family_name + "-Bold"
                else:
                    FONT_BOLD = family_name
                print(f"[PDF Generator] Registered Unicode TTF font: {family_name}")
                return
            except Exception as e:
                print(f"[PDF Generator] Warning registering font {family_name}: {e}")

_init_pdf_fonts()


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

    eyebrow_style = ParagraphStyle(
        'DocEyebrow',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=2
    )

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0b0f19'),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName=FONT_NORMAL,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#475569'),
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName=FONT_BOLD,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontName=FONT_NORMAL,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceAfter=5
    )

    bold_body = ParagraphStyle(
        'DocBoldBody',
        parent=body_style,
        fontName=FONT_BOLD
    )

    elements = []

    # Document Header Banner
    elements.append(Paragraph("ENTERPRISE AI BUSINESS DECISION SUPPORT ENGINE", eyebrow_style))
    elements.append(Paragraph("EXECUTIVE STRATEGIC ASSESSMENT REPORT", title_style))
    elements.append(Paragraph(f"<b>Business Question:</b> {safe_str(task)}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=10))

    # Executive Intelligence Scores
    decision_text = safe_str(report_data.get("decision"), "Decision recommendation generated.")
    risk_level = safe_str(report_data.get("risk_level"), "Medium")
    viability_score = report_data.get("viability_score", 78)
    confidence = report_data.get("confidence", 82)

    risk_color = colors.HexColor('#d97706')
    if risk_level.lower() == "low":
        risk_color = colors.HexColor('#059669')
    elif risk_level.lower() == "high":
        risk_color = colors.HexColor('#dc2626')

    score_card_data = [
        [
            Paragraph(f"<b>BUSINESS VIABILITY</b><br/><font size='15' color='#2563eb'><b>{viability_score} / 100</b></font>", ParagraphStyle('S1', fontName=FONT_NORMAL, fontSize=8, leading=11, alignment=1)),
            Paragraph(f"<b>AI CONFIDENCE</b><br/><font size='15' color='#059669'><b>{confidence}%</b></font>", ParagraphStyle('S2', fontName=FONT_NORMAL, fontSize=8, leading=11, alignment=1)),
            Paragraph(f"<b>MARKET RISK</b><br/><font size='13' color='{risk_color.hexval()}'><b>{risk_level.upper()}</b></font>", ParagraphStyle('S3', fontName=FONT_NORMAL, fontSize=8, leading=11, alignment=1))
        ]
    ]

    score_table = Table(score_card_data, colWidths=[175, 175, 180])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 8))

    # 01. Executive Summary
    elements.append(Paragraph("01. Executive Summary", h2_style))
    elements.append(Paragraph(decision_text.replace('\n', '<br/>'), body_style))
    elements.append(Spacer(1, 4))

    # 02. Strategic Drivers (Why This Decision?)
    why_list = report_data.get("why_this_decision")
    if isinstance(why_list, list) and len(why_list) > 0:
        elements.append(Paragraph("02. Strategic Drivers (Why This Decision?)", h2_style))
        for item in why_list:
            elements.append(Paragraph(f"• {safe_str(item)}", body_style))
        elements.append(Spacer(1, 4))

    # 03 & 04. Key Risk Factors & Strategic Opportunities Grid
    risks_list = report_data.get("key_risks")
    opps_list = report_data.get("key_opportunities")

    if (isinstance(risks_list, list) and risks_list) or (isinstance(opps_list, list) and opps_list):
        risk_text_cell = "<b>03. Key Risk Factors</b><br/>" + "<br/>".join([f"• {safe_str(r)}" for r in (risks_list or [])])
        opp_text_cell = "<b>04. Strategic Opportunities</b><br/>" + "<br/>".join([f"• {safe_str(o)}" for o in (opps_list or [])])

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
        elements.append(Spacer(1, 8))

    # 05. Recommended Decision
    rec_decision = safe_str(report_data.get("recommended_decision") or report_data.get("recommendation_title"))
    if rec_decision:
        elements.append(Paragraph("05. Recommended Decision", h2_style))
        rec_table = Table([[Paragraph(f"<b>RECOMMENDATION:</b> {rec_decision}", ParagraphStyle('RecText', fontName=FONT_BOLD, fontSize=9.5, leading=14, textColor=colors.HexColor('#1e3a8a')))]], colWidths=[530])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#93c5fd')),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        elements.append(rec_table)
        elements.append(Spacer(1, 6))

    # 06. Implementation Roadmap
    roadmap = report_data.get("implementation_roadmap")
    if isinstance(roadmap, list) and len(roadmap) > 0:
        elements.append(Paragraph("06. Implementation Roadmap", h2_style))
        roadmap_rows = []
        for phase_item in roadmap:
            if isinstance(phase_item, dict):
                p_name = safe_str(phase_item.get("phase") or phase_item.get("title"), "Phase")
                steps = phase_item.get("steps") or []
                steps_str = "<br/>".join([f"• {safe_str(s)}" for s in steps]) if isinstance(steps, list) else safe_str(steps)
                roadmap_rows.append([
                    Paragraph(f"<b>{p_name}</b>", ParagraphStyle('PLabel', fontName=FONT_BOLD, fontSize=9, textColor=colors.HexColor('#1d4ed8'))),
                    Paragraph(steps_str, body_style)
                ])
        if roadmap_rows:
            rmap_table = Table(roadmap_rows, colWidths=[140, 390])
            rmap_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))
            elements.append(rmap_table)
            elements.append(Spacer(1, 6))

    # 07. Success Metrics
    metrics = report_data.get("success_metrics")
    if isinstance(metrics, list) and len(metrics) > 0:
        elements.append(Paragraph("07. Success Metrics", h2_style))
        metric_items = []
        for m in metrics:
            metric_items.append(Paragraph(f"🎯 &nbsp;{safe_str(m)}", body_style))
        
        # 2-column table layout for metrics
        half = (len(metric_items) + 1) // 2
        col1 = metric_items[:half]
        col2 = metric_items[half:]
        
        c1_str = "<br/>".join([m.text for m in col1])
        c2_str = "<br/>".join([m.text for m in col2]) if col2 else ""
        
        metrics_table = Table([[Paragraph(c1_str, body_style), Paragraph(c2_str, body_style)]], colWidths=[260, 270])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecfdf5')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#a7f3d0')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 6))

    # 08. Conditions & Assumptions
    conditions = report_data.get("conditions_and_assumptions")
    if isinstance(conditions, list) and len(conditions) > 0:
        elements.append(Paragraph("08. Conditions & Assumptions", h2_style))
        for cond in conditions:
            elements.append(Paragraph(f"📌 {safe_str(cond)}", body_style))
        elements.append(Spacer(1, 4))

    # 09. Conclusion
    conclusion = safe_str(report_data.get("conclusion"))
    if conclusion:
        elements.append(Paragraph("09. Conclusion", h2_style))
        elements.append(Paragraph(conclusion.replace('\n', '<br/>'), body_style))
        elements.append(Spacer(1, 6))

    # Quantitative Tool Analysis (If present)
    tool_analysis = report_data.get("tool_analysis")
    if isinstance(tool_analysis, dict):
        elements.append(Paragraph("Quantitative Business Tool Analysis", h2_style))
        tool_name = safe_str(tool_analysis.get("tool_name") or tool_analysis.get("tool"), "Market Risk Tool")
        tool_risk = safe_str(tool_analysis.get("risk_level"), risk_level)
        tool_rec = safe_str(tool_analysis.get("recommendation"), "")

        elements.append(Paragraph(f"<b>Analysis Tool:</b> {tool_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Risk Rating:</b> {tool_risk}", bold_body))
        if tool_rec:
            elements.append(Paragraph(f"<b>Tool Recommendation:</b> {tool_rec}", body_style))

        obs_list = tool_analysis.get("observations")
        if isinstance(obs_list, list) and len(obs_list) > 0:
            for obs in obs_list:
                elements.append(Paragraph(f"• {safe_str(obs)}", body_style))
        elements.append(Spacer(1, 6))

    # 10. Follow-up Conversation Thread
    if isinstance(conversation_history, list) and len(conversation_history) > 0:
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=8, spaceAfter=8))
        elements.append(Paragraph("10. Follow-up Conversation", h2_style))
        for idx, turn in enumerate(conversation_history, 1):
            if isinstance(turn, dict):
                q = safe_str(turn.get("question"))
                a = safe_str(turn.get("answer"))
                if q:
                    elements.append(Paragraph(f"<b>Q{idx}:</b> {q}", ParagraphStyle('QStyle', parent=body_style, fontName=FONT_BOLD, textColor=colors.HexColor('#1d4ed8'))))
                if a:
                    elements.append(Paragraph(f"<b>AI Decision Engine:</b> {a.replace('\n', '<br/>')}", body_style))
                elements.append(Spacer(1, 4))

    # Page Footer Canvas Callback
    gen_time = datetime.datetime.now().strftime('%d %b %Y, %H:%M')
    def draw_footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont(FONT_NORMAL, 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(40, 20, f"Enterprise AI Strategic Assessment Report  |  Generated: {gen_time}")
        canvas.drawRightString(572, 20, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
