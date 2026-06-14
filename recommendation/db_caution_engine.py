from difflib import SequenceMatcher
import re
from recommendation.db_repository import load_table, contains_match
from recommendation.db_symptom_engine import extract_combined_caution_evidence


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



def _clean_search_document_body(text):
    text = " ".join(str(text or "").split()).strip()
    # recommendation_rule 인덱스는 body_text 앞에 단계/주차/relation_type 메타가 붙을 수 있으므로 제거한다.
    text = re.sub(r"^(초기|중기|후기)\s+\d+\s+\d+\s+(recommend|caution)\s+", "", text).strip()
    text = re.sub(r"^(recommend|caution)\s+", "", text).strip()
    return text

def _similarity(a, b):
    a, b = str(a or ""), str(b or "")
    if not a or not b:
        return 0
    if contains_match(a, b):
        return 100
    return int(SequenceMatcher(None, a, b).ratio() * 100)


def find_supplements_for_nutrients(nutrients, eaten_supplements=None, limit_per_nutrient=3, trace=None):
    eaten_supplements = eaten_supplements or []
    df = load_table("supplement_info")
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
    df = load_table("medicine_info")
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


def _build_search_document_caution_evidence(search_documents, nutrients=None, caution_items=None, trace=None):
    """search_document 검색 결과를 최종 주의사항 생성용 원문 근거로 변환한다.

    search_document는 추천 점수 계산용이 아니라 원문 chunk 검색용 테이블이다.
    따라서 여기서는 body_text/summary를 그대로 근거(evidence)로 보존하고,
    최종 주의사항 문장은 llm_client.generate_caution_summary가 이 evidence만 바탕으로 생성한다.
    """
    docs = search_documents or []
    if not docs:
        return []

    required_terms = [x for x in list(nutrients or []) + list(caution_items or []) if str(x or "").strip()]
    # 생활습관 문장은 원문에 그대로 나오지 않을 수 있으므로 핵심어를 보강한다.
    for item in caution_items or []:
        text = str(item or "")
        if "한 번에" in text or "많은 양" in text:
            required_terms.extend(["입덧", "소량", "수분"])
        if "식이섬유" in text:
            required_terms.extend(["변비", "식이섬유", "섬유소", "수분"])
        if "철분" in text:
            required_terms.extend(["빈혈", "철분"])
    required_terms = list(dict.fromkeys([t for t in required_terms if str(t).strip()]))

    evidence_lines = []
    used_docs = []
    for doc in docs:
        body = _clean_search_document_body(doc.get("body_text", ""))
        if not body:
            continue

        # 너무 일반적인 문서보다 입력/추천/생활관리와 직접 맞는 문서를 우선 사용한다.
        searchable = f"{doc.get('title','')} {doc.get('summary','')} {doc.get('body_text','')} {doc.get('keyword_text','')}"
        if required_terms and not any(contains_match(term, searchable) for term in required_terms):
            continue

        line = " ".join(body.split())
        if line and line not in evidence_lines:
            evidence_lines.append(line)
            used_docs.append({
                "search_id": doc.get("search_id"),
                "title": doc.get("title"),
                "matched_keyword": doc.get("matched_keyword"),
                "source_name": doc.get("source_name"),
                "priority_score": doc.get("priority_score"),
                "body_text": doc.get("body_text"),
            })
        if len(evidence_lines) >= 6:
            break

    if not evidence_lines:
        return []

    item = {
        "type": "search_document",
        "category": "search_document_caution_evidence",
        "item_a": ", ".join(nutrients or []),
        "item_b": "search_document 원문 근거",
        "warning": "search_document 원문 근거를 바탕으로 최종 주의사항을 생성합니다.",
        "evidence": _dedupe_evidence_lines("\n".join(evidence_lines)),
        "severity": "주의",
        "source": "search_document / 국가건강정보포털(질병관리청) 원문 chunk",
        "search_documents": used_docs,
    }
    if trace:
        trace.step("search_document 기반 주의사항 근거 추가", item)
    return [item]


def get_cautions(medicines, supplements, nutrients, caution_items, stage=None, recommendations=None, search_documents=None, trace=None):
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

    cautions.extend(_build_search_document_caution_evidence(
        search_documents,
        nutrients=nutrients,
        caution_items=caution_items,
        trace=trace,
    ))

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
