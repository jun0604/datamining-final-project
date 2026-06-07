import re

from recommendation.csv_loader import load_csv, split_items, unique_list



# ============================================================
# 근거문장 출력 정제 유틸
# ============================================================
# symptom_nutrient.csv의 근거문장 컬럼에는 row 생성에 사용된 원문 chunk 전체가 들어갈 수 있다.
# 추천엔진 출력에서는 사용자 입력 증상, 추천영양소, 생활습관과 직접 관련된 문장만 선별해 사용한다.

NUTRIENT_EVIDENCE_KEYWORDS = {
    "수분": ["수분", "물", "음료", "마셔", "섭취", "탈수", "수액"],
    "식이섬유": ["식이섬유", "섬유소", "잡곡", "전곡", "채소", "과일", "해조류", "콩", "버섯"],
    "철분": ["철분", "철", "철분제", "철 결핍", "철결핍", "빈혈", "육류", "조개류"],
    "엽산": ["엽산", "신경관", "푸른 잎채소", "딸기", "참외", "해조류"],
    "비타민 C": ["비타민 C", "비타민C", "과일", "과일 주스", "철 흡수"],
    "비타민 B6": ["비타민 B6", "비타민B6", "B6"],
    "비타민 B12": ["비타민 B12", "비타민B12", "B12"],
    "단백질": ["단백질", "고기", "생선", "달걀", "콩", "유제품", "아미노산"],
    "탄수화물": ["탄수화물", "토스트", "크래커", "곡류", "포도당", "당"],
    "칼슘": ["칼슘", "우유", "치즈", "멸치", "뼈", "유제품"],
    "비타민 D": ["비타민 D", "비타민D", "유제품"],
    "오메가-3": ["오메가-3", "오메가3", "EPA", "DHA", "고등어", "멸치", "오징어", "꽁치"],
    "EPA": ["EPA", "오메가-3", "오메가3"],
    "DHA": ["DHA", "오메가-3", "오메가3"],
    "나트륨 제한": ["나트륨", "염분", "소금", "짠", "싱겁게", "젓갈", "가공식품", "국물"],
}

LIFESTYLE_EVIDENCE_KEYWORDS = {
    "수분 섭취가 부족함": ["수분", "물", "음료", "마셔", "섭취", "탈수"],
    "신체활동이 부족함": ["운동", "신체활동", "활동", "걷기", "규칙적으로 운동"],
    "한 번에 많은 양을 섭취함": ["소량", "조금씩", "자주", "4~6", "4-6", "나누어", "적게 자주"],
    "철분 섭취가 부족함": ["철분", "철", "철분제", "빈혈", "철 결핍", "철결핍", "육류", "조개류"],
    "식이섬유 섭취가 부족함": ["식이섬유", "섬유소", "잡곡", "전곡", "채소", "과일", "해조류", "콩", "버섯"],
    "자극적인 음식을 자주 섭취함": ["자극", "향신료", "카페인", "커피", "홍차", "녹차", "기름진", "기름기", "냄새", "피합니다", "피하고", "줄입니다"],
}

SYMPTOM_EVIDENCE_KEYWORDS = {
    "입덧": ["입덧", "메스꺼움", "구토", "구역"],
    "구토": ["구토", "구역", "메스꺼움", "입덧"],
    "변비": ["변비", "장운동", "대변", "치질"],
    "빈혈": ["빈혈", "철 결핍", "철결핍", "혈액 희석", "헤모글로빈"],
    "피로": ["피로", "잠이", "쉽게 피곤"],
    "소화불량": ["소화", "소화기능", "위 배출", "복부팽만", "속쓰림", "위식도역류", "가슴쓰림"],
    "부종": ["부종", "붓", "하지부종"],
    "임신고혈압": ["임신고혈압", "고혈압", "혈압", "자간전증", "임신중독증", "전자간증"],
    "임신당뇨": ["임신당뇨", "혈당", "당뇨", "거대아", "케톤"],
}


def _compact_for_evidence(text):
    return str(text or "").replace(" ", "").lower().strip()


def _split_evidence_sentences(text):
    """긴 원문 chunk를 UI 출력용 근거 문장 후보로 분리한다."""
    text = str(text or "").strip()
    if not text:
        return []

    # 번호형 목록 앞뒤에 공백을 넣어 분리 안정화
    text = re.sub(r"\s*([①②③④⑤⑥⑦⑧⑨⑩])\s*", r" \1 ", text)
    text = re.sub(r"\s*([0-9]+[).])\s*", r" \1 ", text)

    # 마침표/물음표/느낌표/번호형 목록 기준으로 분리
    parts = re.split(r"(?<=[.!?。])\s+|(?=\s*[①②③④⑤⑥⑦⑧⑨⑩]\s)|(?=\s*[0-9]+[).]\s)", text)
    sentences = []
    for part in parts:
        sent = " ".join(str(part or "").split()).strip()
        if len(sent) >= 8 and sent not in sentences:
            sentences.append(sent)
    return sentences


def _keyword_hit(sentence, keywords):
    sent_norm = _compact_for_evidence(sentence)
    return any(_compact_for_evidence(k) in sent_norm for k in keywords if k)


def extract_relevant_evidence(evidence_text, symptom="", nutrient="", lifestyle="", max_sentences=5):
    """
    원문 chunk 전체에서 사용자 입력 증상, 추천영양소, 생활습관과 직접 관련된 근거 문장만 선별한다.
    - 전처리 CSV의 긴 근거문장은 유지하되, 추천엔진 출력에는 짧은 관련 근거만 사용하기 위한 함수.
    - 관련 문장이 없으면 원문 앞부분 일부를 fallback으로 반환한다.
    """
    sentences = _split_evidence_sentences(evidence_text)
    if not sentences:
        return str(evidence_text or "")[:800]

    symptom_keywords = SYMPTOM_EVIDENCE_KEYWORDS.get(str(symptom or "").strip(), [symptom] if symptom else [])
    nutrient_keywords = NUTRIENT_EVIDENCE_KEYWORDS.get(str(nutrient or "").strip(), [nutrient] if nutrient else [])
    lifestyle_keywords = LIFESTYLE_EVIDENCE_KEYWORDS.get(str(lifestyle or "").strip(), [lifestyle] if lifestyle and lifestyle != "해당 없음" else [])

    scored = []
    for idx, sent in enumerate(sentences):
        score = 0
        labels = []
        if symptom_keywords and _keyword_hit(sent, symptom_keywords):
            score += 3
            labels.append("증상")
        if nutrient_keywords and _keyword_hit(sent, nutrient_keywords):
            score += 3
            labels.append("추천영양소")
        if lifestyle_keywords and _keyword_hit(sent, lifestyle_keywords):
            score += 2
            labels.append("생활습관")
        if score > 0:
            scored.append((idx, score, sent, labels))

    if not scored:
        return " ".join(sentences[:min(3, len(sentences))])[:1200]

    # 점수 높은 문장을 우선 고른 뒤, 최종 출력은 원문 순서를 유지한다.
    top = sorted(scored, key=lambda x: (-x[1], x[0]))[:max_sentences]
    top = sorted(top, key=lambda x: x[0])
    selected = []
    for _, _, sent, _ in top:
        if sent not in selected:
            selected.append(sent)

    return " ".join(selected).strip()



# ============================================================
# 주의사항 근거 추출 유틸
# ============================================================
# 주의사항 근거는 LLM이 생성한 주의사항 문장이 아니라,
# symptom_nutrient.csv의 근거문장 원문 chunk 안에서 사용자 입력의
# 증상/추천영양소/생활습관/주의조건과 직접 관련된 "주의·관리·회피" 원문 문장만 선별한다.

CAUTION_SIGNAL_KEYWORDS = [
    # 명시적 주의/제한/회피
    "주의", "주의해야", "피하", "피합니다", "피하고", "피해야", "제한", "줄", "적게",
    "삼가", "금", "상담", "위험", "방해", "과도", "반드시", "익혀", "말아",
    "않도록", "최대", "섭취하지", "보충할 필요", "권장하지",

    # 증상 악화/진료 필요
    "증상을 악화", "악화", "심하면", "지속", "탈수", "전해질", "수액", "입원", "의사", "약사",

    # 식이 주의
    "카페인", "커피", "홍차", "녹차", "콜라", "알코올", "술", "기름진", "기름기",
    "냄새", "향신료", "염분", "소금", "짠", "싱겁게", "젓갈", "가공식품", "인스턴트",
    "패스트푸드", "국물", "당류", "단맛", "혈당", "케톤",
]

# 생활습관/증상 관리 문장은 '주의'라는 단어가 없어도 주의사항 근거로 쓸 수 있다.
# 예: 입덧이 심하면 소량씩 자주 먹기, 변비 예방을 위해 물을 충분히 마시기
# 넓은 단어(예: "섭취", "도움")만으로는 일반 설명문까지 근거로 잡히므로
# 실제 주의/관리 행동을 나타내는 구체 표현 위주로 제한한다.
MANAGEMENT_SIGNAL_KEYWORDS = [
    "소량", "조금씩", "자주", "나누어", "적게 자주", "4~6", "4-6",
    "충분히 마", "물을 충분", "수분을 충분", "음료를 충분",
    "규칙적", "규칙적으로 운동", "신체활동", "걷기",
    "늘립니다", "줄입니다", "피합니다", "선택합니다", "유지합니다",
    "예방", "완화", "관리", "상담", "진료",
]

BAD_EVIDENCE_PATTERNS = [
    "도움 및 지지", "국가 기관", "공공기관", "정보를 제공합니다", "참고문헌",
    "자료실", "아카이브", "최신 영양", "식생활 정보", "질병관련 진단과 치료",
]

GENERIC_NUTRIENT_EXPLANATION_PATTERNS = [
    # 영양소 자체 설명이지만 사용자의 증상/생활습관 주의와 직접 연결되지 않는 경우 제외하기 위한 패턴
    "태아에게 가장 중요한 에너지원",
    "총 에너지 요구량",
    "하루 175 g의 탄수화물",
    "태아의 급속 성장",
    "필수 지방산은 태아의 뇌와 망막",
]


def _dedupe_sentences(sentences):
    """공백 정규화 기준으로 문장 중복을 제거하되 원문 순서를 유지한다."""
    out = []
    seen = set()
    for sent in sentences or []:
        sent = " ".join(str(sent or "").split()).strip()
        if not sent:
            continue
        key = _compact_for_evidence(sent)
        if key in seen:
            continue
        seen.add(key)
        out.append(sent)
    return out


def _collect_keywords(symptom="", nutrient="", lifestyle="", extra_keywords=None):
    keywords = []
    symptom = str(symptom or "").strip()
    nutrient = str(nutrient or "").strip()
    lifestyle = str(lifestyle or "").strip()

    if symptom:
        keywords.extend(SYMPTOM_EVIDENCE_KEYWORDS.get(symptom, [symptom]))
    if nutrient:
        keywords.extend(NUTRIENT_EVIDENCE_KEYWORDS.get(nutrient, [nutrient]))
    if lifestyle and lifestyle != "해당 없음":
        keywords.extend(LIFESTYLE_EVIDENCE_KEYWORDS.get(lifestyle, [lifestyle]))
    if extra_keywords:
        for item in extra_keywords:
            item = str(item or "").strip()
            if not item:
                continue
            keywords.append(item)
            keywords.extend(SYMPTOM_EVIDENCE_KEYWORDS.get(item, []))
            keywords.extend(LIFESTYLE_EVIDENCE_KEYWORDS.get(item, []))
            keywords.extend(NUTRIENT_EVIDENCE_KEYWORDS.get(item, []))
    return _dedupe_sentences(keywords)


def _has_bad_pattern(sentence):
    return any(p in sentence for p in BAD_EVIDENCE_PATTERNS)




def _is_caution_related_sentence(sentence):
    """주의사항 근거에 적합한 원문인지 판정한다.
    단순 영양소 효능/권장량 설명은 제외하고, 주의·제한·회피·상담·증상관리·생활습관관리 문장만 허용한다.
    """
    sent = str(sentence or "")
    if _keyword_hit(sent, CAUTION_SIGNAL_KEYWORDS):
        return True
    # 관리 문장은 구체 행동 표현이 있을 때만 허용한다.
    return _keyword_hit(sent, MANAGEMENT_SIGNAL_KEYWORDS)

def _is_generic_nutrient_only(sentence, symptom_hit, lifestyle_hit, caution_hit, management_hit):
    """증상/생활습관/주의와 연결되지 않는 단순 영양소 설명 문장 제외."""
    if symptom_hit or lifestyle_hit or caution_hit or management_hit:
        return False
    return any(p in sentence for p in GENERIC_NUTRIENT_EXPLANATION_PATTERNS)


def extract_caution_evidence_from_chunk(
    evidence_text,
    symptom="",
    nutrient="",
    lifestyle="",
    extra_keywords=None,
    max_sentences=4,
):
    """
    긴 근거문장 chunk에서 결과 페이지의 '주의사항 근거'에 표시할 원문 문장만 추출한다.

    핵심 기준:
    1) 반드시 symptom_nutrient.csv의 '근거문장' chunk 안에 실제 존재하는 문장만 사용한다.
    2) 사용자 입력의 증상/추천영양소/생활습관/주의조건과 관련된 문장만 사용한다.
    3) 그중에서도 주의·제한·회피·상담·증상관리·생활습관관리 성격이 있는 문장만 사용한다.
    4) 단순 영양소 설명 문장(예: 탄수화물 일반 설명)은 제외한다.
    5) 중복 문장은 제거한다.
    """
    sentences = _split_evidence_sentences(evidence_text)
    if not sentences:
        return "해당 없음"

    symptom = str(symptom or "").strip()
    nutrient = str(nutrient or "").strip()
    lifestyle = str(lifestyle or "").strip()

    symptom_keywords = SYMPTOM_EVIDENCE_KEYWORDS.get(symptom, [symptom] if symptom else [])
    nutrient_keywords = NUTRIENT_EVIDENCE_KEYWORDS.get(nutrient, [nutrient] if nutrient else [])
    lifestyle_keywords = LIFESTYLE_EVIDENCE_KEYWORDS.get(lifestyle, [lifestyle] if lifestyle and lifestyle != "해당 없음" else [])
    extra_context_keywords = _collect_keywords(extra_keywords=extra_keywords)

    scored = []
    for idx, sent in enumerate(sentences):
        if _has_bad_pattern(sent):
            continue

        symptom_hit = bool(symptom_keywords and _keyword_hit(sent, symptom_keywords))
        nutrient_hit = bool(nutrient_keywords and _keyword_hit(sent, nutrient_keywords))
        lifestyle_hit = bool(lifestyle_keywords and _keyword_hit(sent, lifestyle_keywords))
        extra_hit = bool(extra_context_keywords and _keyword_hit(sent, extra_context_keywords))
        caution_hit = _keyword_hit(sent, CAUTION_SIGNAL_KEYWORDS)
        management_hit = _keyword_hit(sent, MANAGEMENT_SIGNAL_KEYWORDS)

        context_hit = symptom_hit or nutrient_hit or lifestyle_hit or extra_hit
        caution_or_management_hit = _is_caution_related_sentence(sent)

        # 사용자 입력/추천과 관련 없는 일반 주의문은 제외한다.
        if not context_hit:
            continue

        # 관련은 있지만 단순 설명이면 제외한다. 주의/관리/생활습관 성격이 있어야 한다.
        if not caution_or_management_hit:
            continue

        if _is_generic_nutrient_only(sent, symptom_hit, lifestyle_hit, caution_hit, management_hit):
            continue

        score = 0
        if symptom_hit:
            score += 5
        if lifestyle_hit:
            score += 5
        if caution_hit:
            score += 4
        if management_hit:
            score += 3
        if nutrient_hit:
            score += 2
        if extra_hit:
            score += 2

        scored.append((idx, score, sent))

    if not scored:
        return "해당 없음"

    # 높은 점수 우선 선택 후 원문 순서로 출력한다.
    top = sorted(scored, key=lambda x: (-x[1], x[0]))[:max_sentences]
    top = sorted(top, key=lambda x: x[0])
    selected = _dedupe_sentences([sent for _, _, sent in top])
    return "\n".join(selected).strip() if selected else "해당 없음"


def extract_combined_caution_evidence(recommendations, user_context_items=None, max_sentences=6):
    """최종 추천 후보들의 raw_evidence에서 사용자 입력 기반 주의사항 근거를 통합 추출하고 중복 제거한다."""
    all_sentences = []
    user_context_items = user_context_items or []

    for rec in recommendations or []:
        nutrient = rec.get("nutrient", "")
        triggers = rec.get("triggers", []) or []
        lifestyles = rec.get("matched_health_status", []) or []
        raw_evidences = rec.get("raw_evidences", []) or []

        # trigger 문자열에 "입덧, 한 번에..."처럼 들어올 수 있으므로 분해한다.
        trigger_items = []
        for trig in triggers:
            for part in re.split(r"[,/|]", str(trig or "")):
                part = part.strip()
                if part:
                    trigger_items.append(part)

        # 추천 후보의 trigger와 사용자 입력을 모두 맥락으로 사용한다.
        context_items = _dedupe_sentences(trigger_items + lifestyles + user_context_items)
        symptoms = [t for t in context_items if t in SYMPTOM_EVIDENCE_KEYWORDS]
        if not symptoms:
            symptoms = [""]
        if not lifestyles:
            lifestyles = [""]

        for raw in raw_evidences:
            for symptom in symptoms:
                for lifestyle in lifestyles:
                    evidence = extract_caution_evidence_from_chunk(
                        raw,
                        symptom=symptom,
                        nutrient=nutrient,
                        lifestyle=lifestyle,
                        extra_keywords=context_items,
                        max_sentences=max_sentences,
                    )
                    if evidence and evidence != "해당 없음":
                        all_sentences.extend(_split_evidence_sentences(evidence))

    selected = _dedupe_sentences(all_sentences)[:max_sentences]
    return "\n".join(selected).strip() if selected else "해당 없음"

def _row_stage_match(row, stage_name):
    val = str(row.get("임신단계", "")).strip()
    return not val or val == stage_name


def get_symptom_rows(symptoms, trace=None):
    if not symptoms:
        if trace:
            trace.step("증상 원본 행 조회 생략", {"사유": "입력 증상 없음"})
        return []
    df = load_csv("symptom_nutrient")
    rows = df[df["증상"].isin(symptoms)] if "증상" in df.columns else df.iloc[0:0]
    out = [r.to_dict() for _, r in rows.iterrows()]
    if trace:
        trace.step("증상 원본 행 조회", {
            "입력증상": symptoms,
            "조회행수": len(out),
            "조회행": out,
        })
    return out


def get_symptom_recommendations(symptoms, lifestyles=None, stage_name=None, trace=None):
    symptoms = symptoms or []
    lifestyles = lifestyles or []
    df = load_csv("symptom_nutrient")
    results = []
    skipped_by_stage = 0
    scanned_rows = 0

    if trace:
        trace.step("symptom_nutrient.csv 검색 시작", {
            "입력증상": symptoms,
            "입력생활습관": lifestyles,
            "임신단계": stage_name,
            "전체행수": len(df),
            "컬럼": list(df.columns),
        })

    for row_index, row in df.iterrows():
        scanned_rows += 1
        symptom = row.get("증상", "")
        lifestyle = row.get("생활습관", "")
        if stage_name and not _row_stage_match(row, stage_name):
            skipped_by_stage += 1
            continue

        symptom_hit = symptom in symptoms
        lifestyle_hit = lifestyle in lifestyles and lifestyle != "해당 없음"
        if not symptom_hit and not lifestyle_hit:
            continue

        nutrients = split_items(row.get("추천영양소", ""))
        if not nutrients:
            if trace:
                trace.step("추천영양소 없음으로 행 제외", {
                    "행번호": int(row_index),
                    "증상": symptom,
                    "생활습관": lifestyle,
                })
            continue

        for nutrient in nutrients:
            triggers = []
            score = 0.0
            score_breakdown = []
            if symptom_hit:
                triggers.append(symptom)
                score += 1.0
                score_breakdown.append({"항목": "증상일치", "값": symptom, "가산점": 1.0})
            if lifestyle_hit:
                triggers.append(lifestyle)
                score += 0.7
                score_breakdown.append({"항목": "생활습관일치", "값": lifestyle, "가산점": 0.7})

            reason_parts = []
            if symptom_hit:
                desc = row.get("증상설명", "")
                reason_parts.append(f"{symptom} 증상과 관련된 추천 영양소입니다" + (f": {desc}" if desc else ""))
            if lifestyle_hit:
                l_reason = row.get("생활습관추천이유", "")
                reason_parts.append(f"선택한 생활습관({lifestyle})과 관련됩니다" + (f": {l_reason}" if l_reason else ""))

            raw_evidence = row.get("근거문장", "")
            filtered_evidence = extract_relevant_evidence(
                evidence_text=raw_evidence,
                symptom=symptom if symptom_hit else "",
                nutrient=nutrient,
                lifestyle=lifestyle if lifestyle_hit else "",
                max_sentences=5,
            )

            item = {
                "type": "symptom_lifestyle",
                "row_index": int(row_index),
                "trigger": ", ".join(unique_list(triggers)),
                "nutrient": nutrient,
                "reason": " / ".join(reason_parts),
                "source": "국가건강정보포털(질병관리청)_정상임신관리(임신의 진단과 관리) / 국가건강정보포털(질병관리청)_식이영양(임산부)",
                "score": score,
                "score_breakdown": score_breakdown,
                "nutrient_caution": row.get("주의사항", ""),
                "feature": row.get("증상설명", ""),
                "management": row.get("생활습관추천이유", ""),
                "evidence": filtered_evidence,
                "raw_evidence": raw_evidence,
                "lifestyle_evidence": row.get("생활습관근거", ""),
                "source_page": row.get("출처페이지", ""),
                "source_pdf": row.get("출처PDF", ""),
                "matched_health_status": [lifestyle] if lifestyle_hit else [],
            }
            results.append(item)
            if trace:
                trace.step("증상/생활습관 행 매칭", {
                    "행번호": int(row_index),
                    "증상일치": symptom_hit,
                    "생활습관일치": lifestyle_hit,
                    "추천영양소": nutrient,
                    "점수": score,
                    "점수근거": score_breakdown,
                    "추천이유원천": item["reason"],
                    "주의사항원천": item["nutrient_caution"],
                    "근거문장": item["evidence"],
                    "출처PDF": item["source_pdf"],
                    "출처페이지": item["source_page"],
                })

    if trace:
        trace.step("symptom_nutrient.csv 검색 완료", {
            "스캔행수": scanned_rows,
            "단계불일치제외행수": skipped_by_stage,
            "생성후보수": len(results),
            "생성후보영양소": [r.get("nutrient") for r in results],
        })
    return results
