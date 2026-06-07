from recommendation.pregnancy_stage import get_pregnancy_stage
from recommendation.symptom_engine import get_symptom_recommendations, get_symptom_rows
from recommendation.caution_engine import get_cautions, find_supplements_for_nutrients, get_stage_nutrient_status
from recommendation.llm_client import normalize_intake_text, generate_result_summary, generate_caution_summary
from recommendation.utils import unique_list, merge_recommendations, get_fixed_public_sources, get_fixed_public_sources_text, force_fixed_references
from recommendation.csv_loader import load_csv, contains_match
from recommendation.trace_logger import create_trace_logger


def _fallback_parse_intake(intake_text, trace=None):
    text = intake_text or ""
    supplements, medicines = [], []
    med_df = load_csv("medicine_info")
    supp_df = load_csv("supplement_info")
    common_supp_terms = ["엽산", "철분", "철", "칼슘", "마그네슘", "비타민D", "비타민 D", "비타민 B6", "비타민 B12", "비타민C", "오메가3", "유산균", "프로바이오틱스", "DHA", "EPA"]
    common_med_terms = ["타이레놀", "감기약", "진통제", "제산제", "아세트아미노펜", "활명수"]

    if trace:
        trace.step("복용 정보 fallback 파싱 시작", {
            "입력문장": text,
            "영양제_공통키워드수": len(common_supp_terms),
            "의약품_공통키워드수": len(common_med_terms),
            "영양제DB_검색상한": 5000,
            "의약품DB_검색상한": 5000,
        })

    for term in common_supp_terms:
        if contains_match(term, text):
            supplements.append(term)
    for _, row in supp_df.head(5000).iterrows():
        if contains_match(row.get("제품명", ""), text) or contains_match(row.get("성분", ""), text):
            supplements.append(row.get("제품명") or row.get("성분"))
    for term in common_med_terms:
        if contains_match(term, text):
            medicines.append(term)
    for _, row in med_df.head(5000).iterrows():
        if contains_match(row.get("의약품명", ""), text):
            medicines.append(row.get("의약품명"))

    supplements, medicines, cautions = unique_list(supplements), unique_list(medicines), []
    if trace:
        trace.step("복용 정보 fallback 파싱 결과", {
            "추출영양제": supplements,
            "추출의약품": medicines,
            "추출주의조건": cautions,
        })
    return supplements, medicines, cautions


def get_default_recommendations(stage=None):
    stage_name = (stage or {}).get("stage_name", "")
    if stage_name == "초기":
        nutrients = [("엽산", "임신 초기 기본 관리 영양소입니다."), ("비타민 B6", "입덧 관련 입력이 없을 때 참고할 수 있는 영양소입니다."), ("비타민 D", "임신 중 식이영양 관리에서 확인할 수 있는 기본 영양소입니다.")]
    elif stage_name in ["중기", "후기"]:
        nutrients = [("철분", "임신 중기 이후 빈혈 관리와 관련됩니다."), ("칼슘", "임신 중 칼슘 섭취 관리와 관련됩니다."), ("비타민 D", "칼슘 이용과 관련됩니다.")]
    else:
        nutrients = [("엽산", "기본 추천"), ("철분", "기본 추천"), ("비타민 D", "기본 추천")]
    return [{"nutrient": n, "score": 0.2, "reasons": [r], "triggers": ["기본 추천"], "sources": ["국가건강정보포털(질병관리청)_식이영양(임산부)"], "nutrient_cautions": [], "supplements": [], "filter_status": "추천가능"} for n, r in nutrients]

# ============================================================
# 현재 복용 중인 영양소 재추천 방지 로직
# ============================================================
# 목적
# - 사용자가 이미 복용 중이라고 입력한 영양성분은 최종 TOP 3에서 제외한다.
# - 예: "철분제 복용 중" + 추천 후보 "철" → 중복으로 판단하여 제외
# - 예: "엽산 복용 중" + 추천 후보 "엽산" → 중복으로 판단하여 제외
# - 제외된 후보는 result["excluded_recommendations"]와 trace log에 남겨 검증 가능하게 한다.

_NUTRIENT_ALIASES = {
    "철": ["철", "철분", "철분제", "iron"],
    "엽산": ["엽산", "folicacid", "folate"],
    "비타민C": ["비타민c", "비타민 C", "vitaminc", "vitamin c"],
    "비타민D": ["비타민d", "비타민 D", "vitamind", "vitamin d"],
    "비타민B6": ["비타민b6", "비타민 B6", "vitaminb6", "vitamin b6"],
    "비타민B12": ["비타민b12", "비타민 B12", "vitaminb12", "vitamin b12"],
    "칼슘": ["칼슘", "calcium"],
    "마그네슘": ["마그네슘", "magnesium"],
    "오메가3": ["오메가3", "오메가 3", "omega3", "omega 3", "dha", "epa"],
    "프로바이오틱스": ["프로바이오틱스", "유산균", "probiotics", "probiotic"],
    "식이섬유": ["식이섬유", "파이버", "fiber", "fibre"],
    "단백질": ["단백질", "프로틴", "protein"],
}


def _compact_text(text):
    return str(text or "").replace(" ", "").replace("-", "").replace("_", "").lower().strip()


def _nutrient_aliases(nutrient):
    key = _compact_text(nutrient)
    aliases = {nutrient, key}
    for canonical, vals in _NUTRIENT_ALIASES.items():
        compact_vals = {_compact_text(v) for v in vals + [canonical]}
        if key in compact_vals:
            aliases.update(vals)
            aliases.add(canonical)
            aliases.update(compact_vals)
    return {_compact_text(a) for a in aliases if a}


def _is_currently_taken_nutrient(nutrient, supplements):
    """추천 영양소가 현재 복용 중인 영양제/성분과 중복되는지 판단한다."""
    nutrient_aliases = _nutrient_aliases(nutrient)
    for supp in supplements or []:
        supp_text = _compact_text(supp)
        supp_aliases = _nutrient_aliases(supp)

        # 별칭 기반 완전 일치
        if nutrient_aliases & supp_aliases:
            return True, supp

        # 부분 문자열 기반 일치: 철 ↔ 철분, 비타민D ↔ 비타민 D 제품명 등
        for alias in nutrient_aliases:
            if alias and (alias in supp_text or supp_text in alias):
                return True, supp
    return False, ""


def _apply_current_intake_filter(recommendations, current_supplements, trace=None):
    """현재 복용 중인 영양소는 최종 추천 후보에서 제외한다."""
    kept, excluded = [], []
    for rec in recommendations or []:
        nutrient = rec.get("nutrient", "")
        is_dup, matched_supplement = _is_currently_taken_nutrient(nutrient, current_supplements)
        if is_dup:
            rec = dict(rec)
            rec["filter_status"] = "제외"
            rec["excluded_reason"] = "현재 복용 중인 영양소와 중복"
            rec["matched_current_supplement"] = matched_supplement
            excluded.append(rec)
        else:
            kept.append(rec)

    if trace:
        trace.step("현재 복용 영양제 기반 중복 추천 제거", {
            "현재복용영양제": current_supplements or [],
            "필터전_후보수": len(recommendations or []),
            "제외후보수": len(excluded),
            "통과후보수": len(kept),
            "제외후보": [
                {
                    "영양소": r.get("nutrient"),
                    "매칭된_복용영양제": r.get("matched_current_supplement"),
                    "제외이유": r.get("excluded_reason"),
                    "원점수": r.get("score"),
                    "트리거": r.get("triggers"),
                }
                for r in excluded
            ],
            "통과후보": [r.get("nutrient") for r in kept],
        })
    return kept, excluded


def _build_duplicate_exclusion_cautions(excluded_recommendations, trace=None):
    cautions = []
    for rec in excluded_recommendations or []:
        nutrient = rec.get("nutrient", "")
        supp = rec.get("matched_current_supplement", "")
        item = {
            "type": "supplement_duplicate_excluded",
            "category": "duplicate_intake_prevented",
            "item_a": supp,
            "item_b": nutrient,
            "warning": f"현재 복용 중인 영양제({supp})와 추천 후보 영양소({nutrient})가 중복될 수 있어 최종 추천에서 제외했습니다. 총 섭취량은 의사 또는 약사와 상담해 확인하세요.",
            "evidence": f"사용자 복용 정보에 {supp}가 포함되어 있어 {nutrient} 재추천을 방지했습니다.",
            "severity": "주의",
            "source": "사용자 입력 복용 정보 / 중복 복용 방지 규칙",
        }
        cautions.append(item)
    if trace and cautions:
        trace.step("중복 추천 제거 기반 주의사항 추가", {"추가주의사항수": len(cautions), "주의사항": cautions})
    return cautions


def _apply_stage_filter(recommendations, stage, trace=None):
    statuses = get_stage_nutrient_status(stage, [r.get("nutrient") for r in recommendations])
    before = []
    for rec in recommendations:
        status = statuses.get(rec.get("nutrient"), {}).get("status", "추천가능")
        rec["filter_status"] = status
        before.append({"영양소": rec.get("nutrient"), "점수": rec.get("score"), "필터상태": status})
    filtered = [r for r in recommendations if r.get("filter_status") != "제외"]
    if trace:
        trace.step("임신단계 기반 영양소 필터링", {
            "임신단계": stage,
            "필터전_후보수": len(recommendations),
            "필터후_후보수": len(filtered),
            "후보별상태": before,
        })
    return filtered


def _attach_supplement_products(recommendations, eaten_supplements, trace=None):
    nutrients = [rec.get("nutrient") for rec in recommendations]
    product_map = find_supplements_for_nutrients(nutrients, eaten_supplements=eaten_supplements, limit_per_nutrient=3, trace=trace)
    for rec in recommendations:
        rec["supplements"] = product_map.get(rec.get("nutrient"), [])
    if trace:
        trace.step("추천 영양소별 제품 후보 연결", {
            "현재복용영양제": eaten_supplements,
            "추천영양소": nutrients,
            "제품후보요약": {k: [p.get("product_name", "") for p in v] for k, v in product_map.items()},
        })
    return recommendations


def run_recommendation(
    week,
    symptoms=None,
    diets=None,
    intake_text="",
    use_llm_intake=True,
    use_llm_summary=True,
    use_llm_caution=True,
    enable_trace=True,
    trace_log_dir=None,
):
    trace = create_trace_logger(enabled=enable_trace, log_dir=trace_log_dir)
    trace.step("추천엔진 실행 시작", {
        "입력임신주차": week,
        "입력증상": symptoms or [],
        "입력생활습관": diets or [],
        "복용정보원문": intake_text or "",
        "LLM_복용정보분석_사용": use_llm_intake,
        "LLM_추천이유_사용": use_llm_summary,
        "LLM_주의사항_사용": use_llm_caution,
    })

    symptoms = symptoms or []
    lifestyles = diets or []
    intake_text = intake_text or ""
    supplements, medicines, caution_items = [], [], []
    intake_parse_meta = {"llm_used": False, "fallback_used": False, "error": ""}

    if intake_text and use_llm_intake:
        trace.step("복용 정보 LLM 분석 요청", {"입력문장": intake_text})
        parsed = normalize_intake_text(intake_text, trace=trace)
        supplements = unique_list(parsed.get("supplements", []))
        medicines = unique_list(parsed.get("medicines", []))
        caution_items = unique_list(parsed.get("cautions", []))
        intake_parse_meta = {"llm_used": parsed.get("llm_used", False), "fallback_used": parsed.get("fallback_used", False), "error": parsed.get("error", "")}
        trace.step("복용 정보 LLM 분석 결과", {
            "추출영양제": supplements,
            "추출의약품": medicines,
            "추출주의조건": caution_items,
            "분석메타": intake_parse_meta,
        })
        if not supplements and not medicines:
            supplements, medicines, caution_items = _fallback_parse_intake(intake_text, trace=trace)
            intake_parse_meta["fallback_used"] = True
    elif intake_text:
        supplements, medicines, caution_items = _fallback_parse_intake(intake_text, trace=trace)
        intake_parse_meta["fallback_used"] = True
    else:
        trace.step("복용 정보 없음", {"처리결과": "복용 영양제/의약품/주의조건 없음으로 처리"})

    stage = get_pregnancy_stage(int(week))
    trace.step("임신 주차 기반 단계 판정", stage)

    symptom_recs = get_symptom_recommendations(symptoms, lifestyles=lifestyles, stage_name=stage.get("stage_name"), trace=trace)
    trace.step("증상/생활습관 기반 1차 추천 후보", {
        "후보수": len(symptom_recs),
        "후보": symptom_recs,
    })

    recommendations = merge_recommendations(symptom_recs, trace=trace)
    trace.step("영양소 기준 후보 병합 결과", {
        "병합후보수": len(recommendations),
        "병합후보": recommendations,
    })

    if not recommendations:
        recommendations = get_default_recommendations(stage)
        trace.step("기본 추천 적용", {
            "적용사유": "증상/생활습관 매칭 후보 없음",
            "기본추천": recommendations,
        })

    recommendations, excluded_recommendations = _apply_current_intake_filter(
        recommendations,
        supplements,
        trace=trace,
    )

    if not recommendations:
        trace.step("중복 추천 제거 후 추천 후보 없음", {
            "처리결과": "현재 복용 중인 영양소와 중복되지 않는 기본 추천 후보를 보완 검색",
            "제외후보": [r.get("nutrient") for r in excluded_recommendations],
        })
        fallback_candidates, fallback_excluded = _apply_current_intake_filter(
            get_default_recommendations(stage),
            supplements,
            trace=trace,
        )
        recommendations = fallback_candidates
        excluded_recommendations.extend(fallback_excluded)

    recommendations = _apply_stage_filter(recommendations, stage, trace=trace)[:3]
    trace.step("최종 상위 영양소 후보 선택", {
        "선택기준": "점수 내림차순, 임신단계 필터 통과 후 상위 3개",
        "선택후보": recommendations,
    })

    recommendations = _attach_supplement_products(recommendations, supplements, trace=trace)

    nutrient_names = [rec["nutrient"] for rec in recommendations]
    caution_input_items = unique_list(caution_items + symptoms + lifestyles)
    trace.step("주의사항 검사 입력 구성", {
        "복용의약품": medicines,
        "복용영양제": supplements,
        "추천영양소": nutrient_names,
        "주의조건_증상_생활습관": caution_input_items,
    })

    cautions = get_cautions(
        medicines=medicines,
        supplements=supplements,
        nutrients=nutrient_names,
        caution_items=caution_input_items,
        stage=stage,
        recommendations=recommendations,
        trace=trace,
    )
    cautions.extend(_build_duplicate_exclusion_cautions(excluded_recommendations, trace=trace))

    symptom_rows = get_symptom_rows(symptoms, trace=trace)
    result = {
        "stage": stage,
        "symptom_rows": symptom_rows,
        "input": {"week": int(week), "symptoms": symptoms, "diets": lifestyles, "health_status": lifestyles, "intake_text": intake_text, "supplements": supplements, "medicines": medicines, "caution_items": caution_items, "intake_parse_meta": intake_parse_meta},
        "recommendations": recommendations,
        "excluded_recommendations": excluded_recommendations,
        "cautions": cautions,
        "llm_cautions": [],
        "references": get_fixed_public_sources(),
        "references_text": get_fixed_public_sources_text(),
        "reference_sources": get_fixed_public_sources(),
    }

    trace.step("LLM 추천이유 생성 입력", {
        "LLM사용여부": use_llm_summary,
        "추천영양소": [r.get("nutrient") for r in recommendations],
        "중복으로_제외된_영양소": [
            {"영양소": r.get("nutrient"), "매칭된_복용영양제": r.get("matched_current_supplement"), "제외이유": r.get("excluded_reason")}
            for r in excluded_recommendations
        ],
        "추천근거": [{"영양소": r.get("nutrient"), "이유": r.get("reasons"), "근거문장": r.get("evidences"), "출처": r.get("sources")} for r in recommendations],
    })
    result["llm_summary"] = generate_result_summary(result, trace=trace) if use_llm_summary else ""
    trace.step("추천이유 생성 결과", {"추천이유": result["llm_summary"]})

    trace.step("LLM 주의사항 생성 입력", {
        "LLM사용여부": use_llm_caution,
        "주의사항근거수": len(cautions),
        "주의사항근거": cautions,
    })
    result["llm_cautions"] = generate_caution_summary(result, trace=trace) if use_llm_caution else []
    trace.step("주의사항 생성 결과", {"주의사항": result["llm_cautions"]})

    trace.step("최종 추천 결과 반환", {
        "임신단계": result.get("stage"),
        "추천영양소": [r.get("nutrient") for r in recommendations],
        "중복제외영양소": [{"영양소": r.get("nutrient"), "매칭복용영양제": r.get("matched_current_supplement")} for r in excluded_recommendations],
        "제품후보": {r.get("nutrient"): [p.get("product_name", "") for p in r.get("supplements", [])] for r in recommendations},
        "추천이유": result.get("llm_summary"),
        "주의사항": result.get("llm_cautions"),
        "주의사항근거": cautions,
    })

    result.update(trace.to_result_meta())
    return force_fixed_references(result)
