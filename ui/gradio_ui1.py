# ui/gradio_ui1.py

import gradio as gr
from recommendation.recommendation_engine import run_recommendation
from recommendation.pdf_exporter import export_recommendation_pdf

CSS = """
:root {
    --primary: #6C4EEA;
    --primary-2: #8A63FF;
    --primary-light: #F1ECFF;
    --label-bg: #E9DFFF;
    --label-text: #351A92;
    --bg: #FFFFFF;
    --card: #FFFFFF;
    --sub-card: #FAFAFF;
    --text: #1F1F1F;
    --muted: #666666;
    --border: #E5DAFF;
    --border-soft: #EFE9FF;
    --success: #59B36B;
    --info: #4A90E2;
    --warning: #FF9F2E;
}

html,
body,
main,
.contain,
.gradio-container,
.dark,
.dark body,
.dark main,
.dark .contain,
.dark .gradio-container {
    background: #FFFFFF !important;
    color: var(--text) !important;
    font-family: "Pretendard", "Noto Sans KR", Arial, sans-serif !important;
}

.gradio-container {
    max-width: 1440px !important;
    width: 96% !important;
    margin: auto !important;
    padding: 20px 24px 28px 24px !important;
}

h1, h2, h3, h4, h5, h6,
p, span, label, li, div {
    color: var(--text) !important;
    letter-spacing: -0.02em;
}

p, li, label, span {
    font-size: 14px !important;
    line-height: 1.55 !important;
}

.gradio-container .block,
.gradio-container .form,
.gradio-container .panel,
.gradio-container .wrap,
.gradio-container .gap,
.gradio-container .compact,
.gradio-container .prose,
.gradio-container .gr-box,
.gradio-container .block.padded,
.gradio-container .input-container,
.gradio-container .row,
.gradio-container .column,
.gradio-container .tabs,
.gradio-container .tabitem,
.gradio-container .button-row {
    background: #FFFFFF !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

.clean-page,
.clean-row,
.clean-column,
.clean-group,
.clean-page *,
.clean-row *,
.clean-column *,
.clean-group * {
    background-color: transparent !important;
    outline: none !important;
}

hr,
footer,
.footer,
.api-docs,
.built-with,
.settings {
    display: none !important;
}

.header {
    display: flex;
    justify-content: center !important;
    align-items: center;
    background: #FFFFFF !important;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 24px 28px;
    margin: 0 0 24px 0;
    box-shadow: 0 4px 14px rgba(108, 78, 234, 0.045);
}

.logo-wrap {
    display: flex;
    align-items: center;
    gap: 14px;
}

.logo-icon {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--primary), var(--primary-2)) !important;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF !important;
    font-size: 23px;
    font-weight: 900;
}

.logo-title {
    font-size: 25px !important;
    font-weight: 850;
    color: var(--primary) !important;
    line-height: 1.15 !important;
}

.sub-title {
    margin-top: 4px;
    font-size: 13px !important;
    color: var(--muted) !important;
}

.nav {
    display: none !important;
}

.page-card,
.side-card,
.form-panel {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 24px !important;
    box-shadow: 0 5px 16px rgba(108, 78, 234, 0.05) !important;
    overflow: visible !important;
}

.page-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.side-card {
    padding: 36px 28px 28px 28px;
    min-height: 540px;
}

.form-panel {
    padding: 36px 30px 30px 30px !important;
}

.side-card,
.side-card * {
    overflow: visible !important;
}

.side-title {
    font-size: 25px !important;
    font-weight: 850;
    line-height: 1.35 !important;
    margin: 0 0 14px 0 !important;
    padding-top: 2px !important;
}

.side-desc {
    font-size: 14px !important;
    color: var(--muted) !important;
    line-height: 1.65 !important;
}
`
.main-card {
    max-width: 900px !important;
    width: 100% !important;
    margin: 0 auto;
    text-align: center !important;
}

.hero-title {
    font-size: 31px !important;
    font-weight: 900;
    color: var(--primary) !important;
    line-height: 1.25 !important;
    margin-bottom: 8px;
}

.hero-sub {
    font-size: 16px !important;
    font-weight: 850;
    margin-bottom: 26px;
}

.hero-icon {
    font-size: 82px;
    margin: 8px 0 8px 0 !important;
}

.info-list,
.input-guide,
.source-box {
    background: var(--sub-card) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 18px !important;
}

.info-list {
    width: 95% !important;
    max-width: 980px !important;
    padding: 32px 40px !important;
    margin-top: 30px !important;
    margin-bottom: 80px !important;
}

.input-guide {
    margin-top: 28px;
    padding: 22px;
}

.source-box {
    padding: 18px 20px;
    margin-top: 16px;
}

.info-row {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin: 16px 0;

    font-size: 24px !important;
    line-height: 1.8 !important;
    font-weight: 600 !important;
}

.info-row span:not(.icon) {
    font-size: 24px !important;
}

.info-row .icon {
    color: var(--success) !important;
    font-weight: 900;
    min-width: 32px;

    font-size: 22px !important;
}

/* 직접 작성한 카테고리 라벨 */
.form-label {
    display: inline-block !important;
    width: fit-content !important;
    background: var(--label-bg) !important;
    color: var(--label-text) !important;
    padding: 8px 14px !important;
    margin: 0 0 10px 0 !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    font-weight: 900 !important;
    line-height: 1.4 !important;
}

/* Gradio 기본 label 숨김/초기화 */
.form-panel label,
.form-panel legend,
.form-panel .label-wrap {
    background: transparent !important;
    color: var(--text) !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
}

/* 입력 컴포넌트 간격 */
.form-item {
    margin-bottom: 18px !important;
}

.form-item .block,
.form-item .form,
.form-item .wrap,
.form-item .input-container {
    background: #FFFFFF !important;
    overflow: visible !important;
}

input,
textarea,
select {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border: 1.5px solid #DCD3F6 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    font-size: 14px !important;
}

input::placeholder,
textarea::placeholder {
    color: #888888 !important;
}

input:focus,
textarea:focus,
select:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(108, 78, 234, 0.12) !important;
}

/* CheckboxGroup */
.form-panel fieldset {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
    display: block !important;
}

.form-panel fieldset > div {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 10px !important;
    margin-top: 0 !important;
    padding-left: 0 !important;
    overflow: visible !important;
}

.form-panel fieldset label {
    display: inline-flex !important;
    align-items: center !important;
    min-height: 42px !important;
    padding: 8px 14px !important;

    background: transparent !important;
    border: none !important;
    box-shadow: none !important;

    font-size: 15px !important;
    font-weight: 700 !important;
}

.form-panel fieldset label span {
    background: transparent !important;
    color: var(--text) !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 0 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: 1.4 !important;
    white-space: nowrap !important;
}

input[type="checkbox"] {
    appearance: none !important;
    -webkit-appearance: none !important;
    width: 17px !important;
    height: 17px !important;
    min-width: 17px !important;
    min-height: 17px !important;
    border: 1.8px solid #BDB7DB !important;
    border-radius: 5px !important;
    background: #FFFFFF !important;
    display: inline-grid !important;
    place-content: center !important;
    margin: 0 8px 0 0 !important;
    padding: 0 !important;
    vertical-align: middle !important;
    box-sizing: border-box !important;
}

input[type="checkbox"]::before {
    content: "✓";
    font-size: 13px;
    font-weight: 900;
    line-height: 1;
    color: #FFFFFF !important;
    transform: scale(0);
}

input[type="checkbox"]:checked {
    background: var(--primary) !important;
    border-color: var(--primary) !important;
}

input[type="checkbox"]:checked::before {
    transform: scale(1);
}

.form-panel fieldset label:has(input[type="checkbox"]:checked) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-weight: 800 !important;
}

.clean-row {
    border-top: none !important;
    box-shadow: none !important;
}

.clean-row > .button-row,
.clean-row > .button-row * {
    border-top: none !important;
    box-shadow: none !important;
}

.result-card {
    position: relative;
    display: flex;
    gap: 16px;
    align-items: center;
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 4px 14px rgba(108, 78, 234, 0.05) !important;
}

.result-icon {
    width: 42px;
    height: 42px;
    min-width: 42px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF !important;
    font-size: 20px;
    font-weight: 900;
}

.icon-green { background: var(--success) !important; }
.icon-blue { background: var(--info) !important; }
.icon-orange { background: var(--warning) !important; }

.result-body h3 {
    font-size: 17px !important;
    font-weight: 850;
    margin: 0 0 5px 0;
}

.result-body p,
.result-body li {
    font-size: 13px !important;
    line-height: 1.55 !important;
    margin: 3px 0;
}

.rank {
    position: absolute;
    top: 18px;
    right: 18px;
    padding: 5px 11px;
    border-radius: 9px;
    font-size: 12px !important;
    font-weight: 800;
}

.rank1 {
    background: #E7F8E8 !important;
    color: #2F8F3A !important;
}

.rank2 {
    background: #EAF3FF !important;
    color: #2674C8 !important;
}

.rank3 {
    background: #FFF1DF !important;
    color: #E27913 !important;
}

.green-box {
    background: #F3FFF5 !important;
    border: 1px solid #BDE5C5 !important;
    border-radius: 16px;
    padding: 18px 20px;
    margin-top: 16px;
}

.red-box {
    background: #FFF4F4 !important;
    border: 1px solid #FFC5C5 !important;
    border-radius: 16px;
    padding: 18px 20px;
    margin-top: 16px;
}

.section-title {
    font-size: 18px !important;
    font-weight: 850;
    margin-bottom: 10px;
}

button {
    border-radius: 14px !important;
    box-shadow: none !important;
    font-size: 14px !important;
}

.primary-btn button,
.primary-btn {
    background: linear-gradient(90deg, var(--primary), var(--primary-2)) !important;
    color: #FFFFFF !important;
    border: none !important;
    height: 50px !important;
    font-weight: 850 !important;
}

.primary-btn button *,
.primary-btn * {
    color: #FFFFFF !important;
}

.secondary-btn button,
.secondary-btn {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border: 1px solid #DED7EA !important;
    height: 48px !important;
    font-weight: 750 !important;
}

.footer-custom {
    margin-top: 26px;
    background: #FFFFFF !important;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px;
    text-align: center;
    font-size: 12px !important;
    color: var(--muted) !important;
    box-shadow: 0 4px 14px rgba(108, 78, 234, 0.04);
}

.progress-text,
.generating {
    display: none !important;
}


.result-wide-page,
.evidence-wide-page {
    width: 100% !important;
    max-width: 1040px !important;
    margin: 0 auto !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 24px !important;
    padding: 30px !important;
    box-sizing: border-box !important;
    box-shadow: 0 5px 16px rgba(108, 78, 234, 0.05) !important;
}

.result-wide-page *,
.evidence-wide-page * {
    color: var(--text) !important;
}

.result-wide-page .muted-text,
.evidence-wide-page .muted-text {
    color: #555555 !important;
    font-weight: 700 !important;
}

.result-wide-page .sub-label,
.evidence-wide-page .sub-label {
    color: #666666 !important;
    font-weight: 850 !important;
    margin: 8px 0 4px 0 !important;
}

.result-wide-page ul,
.evidence-wide-page ul {
    padding-left: 20px !important;
}

.result-wide-page li,
.evidence-wide-page li {
    color: #1F1F1F !important;
}

.result-wide-page .result-card,
.evidence-wide-page .result-card {
    width: 100% !important;
    box-sizing: border-box !important;
}

.evidence-wide-page .result-body,
.result-wide-page .result-body {
    padding-right: 88px !important;
}


.loading-page-card {
    width: 100% !important;
    max-width: 1280px !important;
    min-height: 560px !important;
    margin: 0 auto !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 24px !important;
    padding: 30px !important;
    box-sizing: border-box !important;
    box-shadow: 0 5px 16px rgba(108, 78, 234, 0.05) !important;

    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    text-align: center !important;
}

.loading-spinner {
    width: 68px !important;
    height: 68px !important;
    border: 7px solid #E5DAFF !important;
    border-top: 7px solid var(--primary) !important;
    border-radius: 50% !important;
    animation: loadingSpin 1s linear infinite !important;
    margin-bottom: 24px !important;
}

@keyframes loadingSpin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.loading-title {
    font-size: 24px !important;
    font-weight: 900 !important;
    color: var(--primary) !important;
    margin-bottom: 10px !important;
}

.loading-desc {
    font-size: 15px !important;
    color: var(--muted) !important;
    line-height: 1.7 !important;
    margin-bottom: 22px !important;
}

.loading-step-box {
    width: 100% !important;
    max-width: 520px !important;
    background: var(--sub-card) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 18px !important;
    padding: 18px 22px !important;
    text-align: left !important;
}

.loading-step {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    font-size: 14px !important;
    line-height: 1.7 !important;
    color: var(--text) !important;
}

.loading-step span:first-child {
    color: var(--primary) !important;
    font-weight: 900 !important;
}

@media (max-width: 768px) {
    .gradio-container {
        padding: 14px !important;
    }

    .header {
        padding: 20px;
    }

    .logo-title {
        font-size: 21px !important;
    }

    .page-card,
    .side-card,
    .form-panel {
        padding: 22px;
        min-height: auto;
    }

    .hero-title {
        font-size: 42px !important;
    }
}
"""

LAST_RESULT = {}


def show_input():
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def show_start():
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def show_result_page():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
    )


def show_evidence():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
    )


def show_loading():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(value=None, visible=False),
    )


def build_result_html(result):
    stage = result["stage"]
    recommendations = result["recommendations"]
    caution_evidences = result.get("cautions", [])
    llm_cautions = result.get("llm_cautions", [])
    user_input = result["input"]
    llm_summary = result.get("llm_summary", "")

    icon_classes = ["icon-green", "icon-blue", "icon-orange"]
    icons = ["🌿", "💧", "🟠"]
    rank_classes = ["rank1", "rank2", "rank3"]

    cards = ""

    for idx, rec in enumerate(recommendations, start=1):
        trigger = ", ".join(rec.get("triggers", []))
        status = rec.get("filter_status", "추천가능")
        products = rec.get("supplements", []) or []

        if products:
            product_items = "".join([
                f"<li>{p.get('product_name', '')} / {p.get('manufacturer', '')} / {p.get('registration_date', '')}</li>"
                for p in products
            ])
            product_html = f"<p class='muted-text'><b>영양제 후보</b></p><ul>{product_items}</ul>"
        else:
            product_html = "<p class='muted-text'>영양제 후보: 현재 CSV에서 매칭된 제품 없음 또는 복용 중 제품과 중복 제거됨</p>"

        cards += f"""
        <div class="result-card">
            <div class="result-icon {icon_classes[idx - 1]}">
                {icons[idx - 1]}
            </div>

            <div class="result-body">
                <h3>{rec.get("nutrient")}</h3>
                <p class="muted-text">관련 입력: {trigger}</p>
                <p class="muted-text">필터링 결과: {status}</p>
                {product_html}
            </div>

            <span class="rank {rank_classes[idx - 1]}">우선순위 {idx}</span>
        </div>
        """

    symptom_text = ", ".join(user_input["symptoms"]) if user_input["symptoms"] else "없음"
    diet_text = ", ".join(user_input["diets"]) if user_input["diets"] else "없음"
    intake_text = user_input["intake_text"] if user_input["intake_text"] else "없음"

    if llm_cautions:
        caution_html = "".join([
            f"<li>{c}</li>"
            for c in llm_cautions
        ])
    else:
        caution_html = """
        <li>권장 섭취량을 초과하지 않도록 주의하세요.</li>
        <li>영양제나 의약품 복용은 전문가와 상담하세요.</li>
        """

    source_set = []

    for rec in recommendations:
        source_set.extend(rec.get("sources", []))

    for caution in caution_evidences:
        if caution.get("source"):
            source_set.append(caution.get("source"))

    source_set = list(dict.fromkeys([x for x in source_set if x]))

    if not source_set:
        source_set = [
            "공공데이터포털(MFDS)_의약품개요정보(e약은요)",
            "공공데이터포털(MFDS)_의약품 제품 허가정보",
            "공공데이터포털(MFDS)_건강기능식품 품목분류정보",
            "국가건강정보포털(질병관리청)_정상임신관리(임신의 진단과 관리)",
            "국가건강정보포털(질병관리청)_식이영양(임산부)"
        ]

    source_html = "".join([f"<li>{src}</li>" for src in source_set])

    if llm_summary:
        summary_text = llm_summary
    else:
        summary_text = (
            "입력하신 증상과 생활습관을 바탕으로 부족할 가능성이 높은 "
            "영양소를 우선순위로 추천했습니다."
        )

    html = f"""
    <div class="result-wide-page">
        <div style="text-align:center; margin-bottom:22px;">
            <div style="
                font-size:21px;
                font-weight:900;
                color:#111 !important;
                margin-bottom:8px;
            ">
                맞춤 영양 추천 결과
            </div>

            <div style="font-size:14px; color:#555 !important;">
                임신 {user_input["week"]}주 · {stage.get("stage_name", "단계 정보 없음")}
            </div>

            <div style="font-size:13px; color:#555 !important; margin-top:8px;">
                <b>증상:</b> {symptom_text} ·
                <b>생활습관:</b> {diet_text} ·
                <b>복용 정보:</b> {intake_text}
            </div>
        </div>

        <div style="
            font-size:15px;
            font-weight:850;
            color:#6C4EEA !important;
            margin-bottom:12px;
        ">
            추천 영양 성분 TOP 3
        </div>

        {cards}

        <div class="green-box">
            <div class="section-title">추천 이유</div>
            <p>{summary_text}</p>
        </div>

        <div class="red-box">
            <div class="section-title">주의사항</div>
            <ul>{caution_html}</ul>
        </div>

        <div class="source-box">
            <div class="section-title">참고 자료</div>
            <ul>{source_html}</ul>
        </div>
    </div>
    """

    return html

def build_evidence_html(result):
    recommendations = result["recommendations"]
    cautions = result.get("cautions", [])
    user_input = result["input"]

    rec_html = ""

    icon_classes = ["icon-green", "icon-blue", "icon-orange"]
    rank_classes = ["rank1", "rank2", "rank3"]

    for idx, rec in enumerate(recommendations, start=1):
        reasons = "".join([
            f"<li>{reason}</li>"
            for reason in rec.get("reasons", [])
        ])

        sources = "".join([
            f"<li>{source}</li>"
            for source in rec.get("sources", [])
        ])

        rec_html += f"""
        <div class="result-card">
            <div class="result-icon {icon_classes[idx - 1]}">{idx}</div>

            <div class="result-body">
                <h3>{rec.get("nutrient")}</h3>

                <p class="sub-label">추천 근거</p>
                <ul>{reasons}</ul>

                <p class="sub-label">출처</p>
                <ul>{sources}</ul>

                <p class="sub-label">영양제 후보</p>
                <ul>{''.join([f"<li>{p.get('product_name', '')} / {p.get('manufacturer', '')} / {p.get('registration_date', '')}</li>" for p in rec.get('supplements', [])]) or '<li>매칭된 제품 없음</li>'}</ul>
            </div>

            <span class="rank {rank_classes[idx - 1]}">근거</span>
        </div>
        """

    if cautions:
        caution_html = "".join([
            f"<li>{c.get('evidence') or c.get('warning', '')}</li>"
            for c in cautions
        ])
    else:
        caution_html = "<li>DB에서 조회된 추가 주의사항은 없습니다.</li>"

    supplements_text = ", ".join(user_input.get("supplements", [])) or "없음"
    medicines_text = ", ".join(user_input.get("medicines", [])) or "없음"
    caution_items_text = ", ".join(user_input.get("caution_items", [])) or "없음"

    parsed_html = f"""
    <ul>
        <li><b>LLM 분석 supplements:</b> <span>{supplements_text}</span></li>
        <li><b>LLM 분석 medicines:</b> <span>{medicines_text}</span></li>
        <li><b>LLM 분석 caution_items:</b> <span>{caution_items_text}</span></li>
    </ul>
    """

    html = f"""
    <div class="evidence-wide-page">
        <div style="margin-bottom:22px;">
            <div style="
                font-size:21px;
                font-weight:900;
                color:#111 !important;
                margin-bottom:8px;
            ">
                추천 근거 및 출처
            </div>

            <p class="muted-text">추천된 영양 성분별 DB 조회 근거입니다.</p>
        </div>

        {rec_html}

        <div class="green-box">
            <div class="section-title">복용 정보 LLM 분석 결과</div>
            {parsed_html}
        </div>

        <div class="red-box">
            <div class="section-title">주의사항 근거</div>
            <ul>{caution_html}</ul>
        </div>
    </div>
    """

    return html

def recommend_from_engine(
    week,
    symptoms,
    diets,
    intake_text
):
    global LAST_RESULT

    if week is None:
        raise gr.Error("임신 주차를 입력하세요.")

    result = run_recommendation(
        week=int(week),
        symptoms=symptoms or [],
        diets=diets or [],
        intake_text=intake_text or "",
        use_llm_intake=True,
        use_llm_summary=True,
        use_llm_caution=True
    )

    LAST_RESULT = result

    result_html = build_result_html(result)
    evidence_html = build_evidence_html(result)

    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        result_html,
        evidence_html
    )


def save_pdf(progress=gr.Progress()):
    global LAST_RESULT

    if not LAST_RESULT:
        raise gr.Error("먼저 추천 결과를 생성하세요.")

    progress(0.3, desc="PDF 저장을 준비하고 있습니다.")
    pdf_path = export_recommendation_pdf(LAST_RESULT)
    progress(1.0, desc="PDF 저장이 완료되었습니다.")

    return gr.update(value=pdf_path, visible=True)

def build_app():
    theme = gr.themes.Soft(
        primary_hue="violet",
        neutral_hue="gray"
    )

    with gr.Blocks(
        css=CSS,
        title="Mom's Nutrition Guide",
        theme=theme
    ) as demo:

        gr.HTML("""
        <div class="header">
            <div class="logo-wrap">
                <div class="logo-icon">♡</div>
                <div>
                    <div class="logo-title">Mom's Nutrition Guide</div>
                    <div class="sub-title">임산부 맞춤 영양 추천 서비스</div>
                </div>
            </div>
        </div>
        """)

        with gr.Group(visible=True, elem_classes=["clean-page"]) as start_page:
            gr.HTML("""
            <div class="page-card main-card">
                <div class="hero-title"><br>Mom's Nutrition Guide<br></div>
                <div class="hero-sub">임산부 맞춤 영양 추천 서비스</div>

                <div class="hero-icon">🤰</div>

                <div class="info-list">
                    <div class="info-row">
                        <span class="icon">✓</span>
                        <span>임신 주차, 증상, 건강상태를 입력하면 필요한 영양소를 추천합니다.</span>
                    </div>
                    <div class="info-row">
                        <span class="icon">✓</span>
                        <span>공공기관 데이터를 기반으로 근거 있는 정보를 제공합니다.</span>
                    </div>
                    <div class="info-row">
                        <span class="icon">✓</span>
                        <span>주의사항과 근거 출처까지 함께 확인할 수 있습니다.</span>
                    </div>
                </div>
            </div>
            """)

            start_btn = gr.Button("시작하기  →", elem_classes=["primary-btn"])

        with gr.Group(visible=False, elem_classes=["clean-page"]) as input_page:
            with gr.Row(elem_classes=["clean-row"]):
                with gr.Column(scale=4, elem_classes=["clean-column"]):
                    gr.HTML("""
                    <div class="side-card">
                        <div class="side-title">입력 폼 화면</div>
                        <div class="side-desc">
                            임신 주차, 현재 증상, 건강상태, 복용 정보를 입력하세요.
                        </div>

                        <div class="input-guide">
                            <h3>입력 항목</h3>
                            <ul>
                                <li>임신 주차</li>
                                <li>현재 증상</li>
                                <li>생활습관 체크</li>
                                <li>복용 중 영양제/의약품</li>
                            </ul>
                        </div>

                        <div class="info-list">
                            <div class="info-row">
                                <span class="icon">📝</span>
                                <span>체크박스를 선택하면 추천 결과에 바로 반영됩니다.</span>
                            </div>
                            <div class="info-row">
                                <span class="icon">🔎</span>
                                <span>복용 정보는 AI가 영양제/의약품명으로 정리합니다.</span>
                            </div>
                        </div>
                    </div>
                    """)

                with gr.Column(scale=6, elem_classes=["form-panel"]):

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">임신 주차</div>')
                        week = gr.Number(
                            label=None,
                            show_label=False,
                            value=None,
                            minimum=1,
                            maximum=42
                        )

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">주요 증상</div>')
                        symptoms = gr.CheckboxGroup(
                            choices=["입덧", "구토", "변비", "빈혈", "피로", "소화불량", "부종", "임신고혈압", "임신당뇨"],
                            label=None,
                            show_label=False,
                            value=None
                        )

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">생활습관 체크</div>')
                        diets = gr.CheckboxGroup(
                            choices=[
                                "수분 섭취가 부족함",
                                "신체활동이 부족함",
                                "한 번에 많은 양을 섭취함",
                                "철분 섭취가 부족함",
                                "식이섬유 섭취가 부족함",
                                "자극적인 음식을 자주 섭취함"
                            ],
                            label=None,
                            show_label=False,
                            value=None
                        )

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">현재 복용 중인 영양제/의약품</div>')
                        intake_text = gr.Textbox(
                            label=None,
                            show_label=False,
                            placeholder="예: 철분제, 유산균, 비타민D",
                            lines=2
                        )

                    with gr.Row(elem_classes=["clean-row"]):
                        back_btn = gr.Button("처음으로", elem_classes=["secondary-btn"])
                        recommend_btn = gr.Button("다음  →", elem_classes=["primary-btn"])

        with gr.Group(visible=False, elem_classes=["clean-page"]) as loading_page:
            gr.HTML("""
            <div class="loading-page-card">
                <div class="loading-spinner"></div>

                <div class="loading-title">
                    맞춤 영양 추천 생성 중
                </div>

                <div class="loading-desc">
                    입력하신 임신 주차, 증상, 건강상태, 복용 정보를 분석하고 있습니다.<br>
                    LLM 기반 복용 정보 분석과 추천 이유 생성을 진행 중입니다.
                </div>

                <div class="loading-step-box">
                    <div class="loading-step">
                        <span>1</span>
                        <span>입력 정보 확인</span>
                    </div>
                    <div class="loading-step">
                        <span>2</span>
                        <span>복용 정보 LLM 분석</span>
                    </div>
                    <div class="loading-step">
                        <span>3</span>
                        <span>CSV 기반 영양 성분 추천</span>
                    </div>
                    <div class="loading-step">
                        <span>4</span>
                        <span>추천 이유 및 주의사항 정리</span>
                    </div>
                </div>
            </div>
            """)

        with gr.Group(visible=False, elem_classes=["clean-page"]) as result_page:
            result_html = gr.HTML()

            with gr.Row(elem_classes=["clean-row"]):
                evidence_btn = gr.Button("근거 보기", elem_classes=["secondary-btn"])
                retry_btn = gr.Button("다시 입력하기", elem_classes=["secondary-btn"])
                pdf_btn = gr.Button("PDF로 저장", elem_classes=["primary-btn"])

            pdf_file = gr.File(
                label="PDF 다운로드",
                visible=False
            )

        with gr.Group(visible=False, elem_classes=["clean-page"]) as evidence_page:
            evidence_html = gr.HTML()
            evidence_back_btn = gr.Button("결과로 돌아가기", elem_classes=["primary-btn"])

        gr.HTML("""
        <div class="footer-custom">
            API를 통해 사용 🚀 · Gradio로 제작됨 📦 · 설정 ⚙️
        </div>
        """)

        start_btn.click(
            fn=show_input,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        back_btn.click(
            fn=show_start,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        recommend_btn.click(
            fn=show_loading,
            inputs=[],
            outputs=[
                start_page,
                input_page,
                loading_page,
                result_page,
                evidence_page,
                pdf_file
            ],
            show_progress="hidden"
        ).then(
            fn=recommend_from_engine,
            inputs=[week, symptoms, diets, intake_text],
            outputs=[
                input_page,
                evidence_page,
                loading_page,
                result_page,
                result_html,
                evidence_html
            ],
            show_progress="hidden"
        )

        retry_btn.click(
            fn=show_input,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        evidence_btn.click(
            fn=show_evidence,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        evidence_back_btn.click(
            fn=show_result_page,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        pdf_btn.click(
            fn=save_pdf,
            inputs=[],
            outputs=[pdf_file],
            show_progress="full"
        )

    return demo