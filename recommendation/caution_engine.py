from difflib import SequenceMatcher
from recommendation.csv_loader import load_csv, contains_match
from recommendation.symptom_engine import extract_combined_caution_evidence


def _dedupe_evidence_lines(text):
    lines = []
    seen = set()
    for line in str(text or "").splitlines():
        line = " ".join(line.split()).strip()
        if not line or line == "해당 없음":
            continue
        key = line.replace(" ", "").lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines) if lines else "해당 없음"


def _similarity(a, b):
    a, b = str(a or ""), str(b or "")
    if not a or not b:
        return 0
    if contains_match(a, b):
        return 100
    return int(SequenceMatcher(None, a, b).ratio() * 100)


def find_supplements_for_nutrients(nutrients, eaten_supplements=None, limit_per_nutrient=3, trace=None):
    eaten_supplements = eaten_supplements or []
    df = load_csv("supplement_info")
    results = {}
    if trace:
        trace.step("영양제 제품 후보 검색 시작", {
            "추천영양소": nutrients or [],
            "현재복용영양제": eaten_supplements,
            "검색행수": len(df),
            "영양소당_최대제품수": limit_per_nutrient,
        })

    for nutrient in nutrients or []:
        candidates = []
        skipped_duplicate = []
        matched_count = 0
        for row_index, row in df.iterrows():
            product = row.get("제품명", "")
            ingredients = row.get("성분", "")
            if not contains_match(nutrient, ingredients) and not contains_match(nutrient, product):
                continue
            matched_count += 1
            duplicate = any(contains_match(eaten, product) or contains_match(eaten, ingredients) for eaten in eaten_supplements)
            if duplicate:
                skipped_duplicate.append({"행번호": int(row_index), "제품명": product, "성분": ingredients, "제외이유": "현재 복용 영양제와 중복 가능"})
                continue
            candidates.append({
                "nutrient": nutrient,
                "row_index": int(row_index),
                "product_name": product,
                "manufacturer": row.get("제조사", ""),
                "registration_date": "",
                "ingredients": ingredients,
                "source": "공공데이터포털(MFDS)_건강기능식품 품목제조 신고사항 현황",
            })
            if len(candidates) >= limit_per_nutrient:
                break
        results[nutrient] = candidates
        if trace:
            trace.step("영양소별 제품 후보 검색 결과", {
                "영양소": nutrient,
                "DB매칭수_상한도달전기준": matched_count,
                "선택제품수": len(candidates),
                "선택제품": candidates,
                "중복제외제품": skipped_duplicate[:10],
            })
    return results


def get_medicine_warnings(medicines, threshold=65, trace=None):
    if not medicines:
        if trace:
            trace.step("의약품 주의사항 검색 생략", {"사유": "입력 의약품 없음"})
        return []
    df = load_csv("medicine_info")
    warnings = []
    if trace:
        trace.step("의약품 주의사항 검색 시작", {
            "입력의약품": medicines,
            "유사도기준": threshold,
            "검색행수": len(df),
        })
    for med in medicines:
        scored = []
        for row_index, row in df.iterrows():
            name = row.get("의약품명", "")
            score = max(_similarity(med, name), _similarity(med, row.get("효능효과", "")))
            if score >= threshold:
                scored.append((score, row_index, row))
        scored = sorted(scored, key=lambda x: x[0], reverse=True)[:3]
        if trace:
            trace.step("의약품별 매칭 결과", {
                "입력의약품": med,
                "매칭수": len(scored),
                "매칭후보": [{"점수": int(score), "행번호": int(row_index), "의약품명": row.get("의약품명", "")} for score, row_index, row in scored],
            })
        for score, row_index, row in scored:
            warnings.append({
                "type": "medicine",
                "category": "medicine_warning",
                "row_index": int(row_index),
                "item_a": med,
                "item_b": row.get("의약품명", med),
                "warning": row.get("주의사항", ""),
                "interaction": row.get("상호작용", ""),
                "evidence": row.get("주의사항", "") or row.get("상호작용", ""),
                "severity": "주의",
                "match_score": score,
                "source": "공공데이터포털(MFDS)_의약품개요정보(e약은요) / 공공데이터포털(MFDS)_의약품 제품 허가정보",
            })
    if trace:
        trace.step("의약품 주의사항 검색 완료", {"주의사항수": len(warnings), "주의사항": warnings})
    return warnings


def get_stage_nutrient_status(stage, nutrients):
    return {n: {"status": "추천가능", "warning": ""} for n in nutrients or []}


def get_cautions(medicines, supplements, nutrients, caution_items, stage=None, recommendations=None, trace=None):
    cautions = []
    recommendations = recommendations or []
    if trace:
        trace.step("주의사항 통합 검사 시작", {
            "복용의약품": medicines or [],
            "복용영양제": supplements or [],
            "추천영양소": nutrients or [],
            "주의조건": caution_items or [],
            "임신단계": stage,
            "추천후보수": len(recommendations),
        })

    # CSV의 긴 근거문장(raw_evidences)에서 증상/영양소/생활습관/주의 관련 원문 문장만 추출해
    # 주의사항 근거로 사용한다. LLM이 생성한 주의사항 문장을 근거로 복사하지 않는다.
    chunk_caution_evidence = _dedupe_evidence_lines(
        extract_combined_caution_evidence(recommendations, user_context_items=caution_items, max_sentences=6)
    )
    if chunk_caution_evidence and chunk_caution_evidence != "해당 없음":
        item = {
            "type": "nutrient",
            "category": "nutrient_lifestyle_caution_evidence",
            "item_a": ", ".join(nutrients or []),
            "item_b": "증상/영양소/생활습관 원문 근거",
            "warning": "추천 영양소와 생활습관에 대한 주의사항은 아래 원문 근거를 바탕으로 요약되었습니다.",
            "evidence": chunk_caution_evidence,
            "severity": "주의",
            "source": "국가건강정보포털(질병관리청)_정상임신관리(임신의 진단과 관리) / 국가건강정보포털(질병관리청)_식이영양(임산부)",
        }
        cautions.append(item)
        if trace:
            trace.step("원문 chunk 기반 주의사항 근거 추가", item)

    med_warnings = get_medicine_warnings(medicines, trace=trace)
    cautions.extend(med_warnings)

    for supp in supplements or []:
        for nutrient in nutrients or []:
            if contains_match(supp, nutrient) or contains_match(nutrient, supp):
                item = {
                    "type": "supplement_duplicate",
                    "category": "duplicate_intake",
                    "item_a": supp,
                    "item_b": nutrient,
                    "warning": f"현재 복용 중인 영양제({supp})와 추천 영양소({nutrient})가 중복될 수 있어 총 섭취량 확인이 필요합니다.",
                    "evidence": f"현재 복용 중인 영양제({supp})와 추천 영양소({nutrient})가 중복될 수 있습니다.",
                    "severity": "주의",
                    "source": "공공데이터포털(MFDS)_건강기능식품 품목제조 신고사항 현황",
                }
                cautions.append(item)
                if trace:
                    trace.step("중복 복용 가능성 주의사항 추가", item)

    seen, out = set(), []
    duplicate_removed = 0
    for c in cautions:
        c["evidence"] = _dedupe_evidence_lines(c.get("evidence", ""))
        key = (c.get("type"), c.get("item_a"), c.get("item_b"), c.get("warning"), c.get("evidence"))
        if key not in seen:
            out.append(c)
            seen.add(key)
        else:
            duplicate_removed += 1
    out = out[:12]
    if trace:
        trace.step("주의사항 통합 검사 완료", {
            "전체주의사항수": len(cautions),
            "중복제거수": duplicate_removed,
            "최종주의사항수": len(out),
            "최종주의사항": out,
        })
    return out
