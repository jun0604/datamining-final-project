from pathlib import Path
from datetime import datetime

from recommendation.utils import get_fixed_public_sources

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


BASE_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = BASE_DIR / "exports"
PDF_DIR.mkdir(exist_ok=True)


def _register_korean_font():
    font_path = Path("C:/Windows/Fonts/malgun.ttf")

    if font_path.exists():
        pdfmetrics.registerFont(TTFont("Malgun", str(font_path)))
        return "Malgun"

    return "Helvetica"


def export_recommendation_pdf(result):
    font_name = _register_korean_font()

    filename = f"pregnancy_recommendation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = PDF_DIR / filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "KoreanTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=24,
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "KoreanHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        leading=20,
        spaceBefore=14,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "KoreanBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10,
        leading=16,
    )

    story = []

    stage = result.get("stage", {})
    user_input = result.get("input", {})
    recommendations = result.get("recommendations", [])
    cautions = result.get("cautions", [])
    llm_cautions = result.get("llm_cautions", [])
    llm_summary = result.get("llm_summary", "")

    story.append(Paragraph("임산부 맞춤 영양 추천 결과", title_style))

    story.append(Paragraph("입력 정보", heading_style))
    story.append(Paragraph(f"임신 주차: {user_input.get('week')}주", body_style))
    story.append(Paragraph(f"임신 단계: {stage.get('stage_name', '단계 정보 없음')}", body_style))
    story.append(Paragraph(f"증상: {', '.join(user_input.get('symptoms', [])) or '없음'}", body_style))
    story.append(Paragraph(f"식습관: {', '.join(user_input.get('diets', [])) or '없음'}", body_style))
    story.append(Paragraph(f"복용 정보: {user_input.get('intake_text') or '없음'}", body_style))

    story.append(Spacer(1, 12))

    story.append(Paragraph("추천 영양 성분 TOP 3", heading_style))

    for idx, rec in enumerate(recommendations, start=1):
        nutrient = rec.get("nutrient", "")
        reasons = " / ".join(rec.get("reasons", []))
        triggers = ", ".join(rec.get("triggers", []))

        story.append(Paragraph(f"{idx}. {nutrient}", body_style))
        story.append(Paragraph(f"추천 근거: {reasons}", body_style))
        story.append(Paragraph(f"관련 입력: {triggers}", body_style))
        story.append(Spacer(1, 8))

    story.append(Paragraph("추천 이유", heading_style))
    story.append(Paragraph(llm_summary or "추천 이유가 생성되지 않았습니다.", body_style))

    story.append(Paragraph("주의사항", heading_style))

    if llm_cautions:
        for caution in llm_cautions:
            story.append(Paragraph(f"- {caution}", body_style))
    else:
        story.append(Paragraph("조회된 추가 주의사항은 없습니다. 영양제나 의약품 복용은 전문가와 상담하세요.", body_style))

    story.append(Paragraph("주의사항 근거", heading_style))
    evidence_lines = []
    for caution in cautions:
        ev = caution.get("evidence", "")
        if ev and ev != "해당 없음":
            for line in str(ev).splitlines():
                line = line.strip()
                if line and line not in evidence_lines:
                    evidence_lines.append(line)
    if evidence_lines:
        for line in evidence_lines[:8]:
            story.append(Paragraph(f"- {line}", body_style))
    else:
        story.append(Paragraph("표시할 원문 근거가 없습니다.", body_style))

    story.append(Paragraph("참고 자료", heading_style))
    for source in get_fixed_public_sources():
        story.append(Paragraph(f"- {source}", body_style))

    doc.build(story)

    return str(pdf_path)