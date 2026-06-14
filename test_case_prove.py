from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from recommendation.db_repository import get_db_path
from recommendation.db_recommendation_engine import run_recommendation


TEST_TABLE = "recommendation_test_case"


def _norm(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower().strip()


def _contains(a: Any, b: Any) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    return na in nb or nb in na


def _split_expected(text: Any) -> list[str]:
    """DB의 기대값 문자열을 리스트로 변환한다.

    지원 구분자: |, /, 쉼표, 세미콜론, 줄바꿈, ㆍ
    특수값: 비움, 없음, -, null, None은 검증 조건 없음으로 처리한다.
    """
    if text is None:
        return []

    s = str(text).strip()
    if not s:
        return []

    empty_tokens = {"비움", "없음", "-", "null", "none", "None", "NULL"}
    if s in empty_tokens:
        return []

    for sep in ["|", "/", "，", "\n", ";", "ㆍ"]:
        s = s.replace(sep, ",")

    items = [x.strip() for x in s.split(",") if x.strip()]
    return list(dict.fromkeys([x for x in items if x not in empty_tokens]))


def _table_columns(con: sqlite3.Connection, table_name: str) -> list[str]:
    return [str(row[1]) for row in con.execute(f"PRAGMA table_info({table_name})").fetchall()]


def load_test_cases() -> list[dict[str, Any]]:

    db_path = get_db_path()
    if not db_path:
        raise FileNotFoundError(
            "pregnancy_nutrition.db를 찾을 수 없습니다. "
            "프로젝트 루트 또는 data 폴더에 DB를 두거나 PREGNANCY_NUTRITION_DB를 지정하세요."
        )

    with sqlite3.connect(str(db_path)) as con:
        con.row_factory = sqlite3.Row
        exists = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TEST_TABLE,),
        ).fetchone()
        if not exists:
            raise RuntimeError(f"DB에 {TEST_TABLE} 테이블이 없습니다.")

        cols = _table_columns(con, TEST_TABLE)
        rows = con.execute(f"SELECT * FROM {TEST_TABLE} ORDER BY test_id").fetchall()

    cases: list[dict[str, Any]] = []
    default_keys = [
        "test_id",
        "test_type",
        "pregnancy_week",
        "symptom",
        "lifestyle_check",
        "user_input_text",
        "expected_include_nutrients",
        "expected_exclude_nutrients",
        "expected_guidance_keywords",
        "expected_supplement_keywords",
        "expected_medicine_keywords",
        "note",
        "created_at",
    ]
    for row in rows:
        d = dict(row)
        for key in default_keys:
            d.setdefault(key, "")
        d["_db_columns"] = cols
        cases.append(d)
    return cases


def _append_text(parts: list[str], value: Any) -> None:
    """검증 대상 텍스트를 누락 없이 수집하기 위한 보조 함수."""
    if value is None:
        return

    if isinstance(value, dict):
        for v in value.values():
            _append_text(parts, v)
        return

    if isinstance(value, (list, tuple, set)):
        for v in value:
            _append_text(parts, v)
        return

    s = str(value).strip()
    if s:
        parts.append(s)


def _collect_result_text(result: dict[str, Any]) -> str:
    """키워드 PASS 검증에 사용할 최종 결과 텍스트를 합친다.

    T02처럼 기대 키워드가 추천 이유, 주의사항 근거, 입력 생활습관,
    search_document 원문 중 어느 위치에 있어도 검증되도록 주요 결과 필드를 폭넓게 수집한다.
    """
    parts: list[str] = []

    # LLM 생성 결과
    _append_text(parts, result.get("llm_summary", ""))
    _append_text(parts, result.get("llm_cautions", []))

    # 사용자 입력 및 LLM 복용 정보 분석 결과
    input_info = result.get("input", {}) or {}
    for key in [
        "week",
        "stage",
        "stage_name",
        "symptoms",
        "diets",
        "lifestyle",
        "lifestyle_check",
        "supplements",
        "medicines",
        "caution_items",
        "intake_text",
    ]:
        _append_text(parts, input_info.get(key))

    # 임신 단계 정보
    _append_text(parts, result.get("stage"))

    # 최종 추천 영양소와 제품 후보
    for rec in result.get("recommendations", []) or []:
        for key in [
            "nutrient",
            "reason",
            "reasons",
            "evidence",
            "evidences",
            "raw_evidence",
            "raw_evidences",
            "lifestyle_evidence",
            "lifestyle_evidences",
            "management",
            "managements",
            "nutrient_caution",
            "nutrient_cautions",
            "feature",
            "features",
            "triggers",
            "sources",
            "matched_health_status",
            "filter_status",
            "score_details",
        ]:
            _append_text(parts, rec.get(key))

        for product in rec.get("supplements", []) or []:
            _append_text(parts, product)

    # 중복 복용 등으로 최종 추천에서 제외된 후보
    for rec in result.get("excluded_recommendations", []) or []:
        _append_text(parts, rec)

    # 주의사항 및 원문 근거
    for caution in result.get("cautions", []) or []:
        _append_text(parts, caution)

    # search_document 검색 결과
    for doc in result.get("search_documents", []) or []:
        _append_text(parts, doc)

    return " ".join(parts)


def _collect_parsed_supplements(result: dict[str, Any]) -> list[str]:
    return [str(x) for x in ((result.get("input", {}) or {}).get("supplements", []) or [])]


def _collect_parsed_medicines(result: dict[str, Any]) -> list[str]:
    return [str(x) for x in ((result.get("input", {}) or {}).get("medicines", []) or [])]


def evaluate_result(result: dict[str, Any], test_case: dict[str, Any]) -> dict[str, Any]:

    recommended_nutrients = [str(r.get("nutrient", "")) for r in result.get("recommendations", []) or []]
    excluded_nutrients = [str(r.get("nutrient", "")) for r in result.get("excluded_recommendations", []) or []]
    parsed_supplements = _collect_parsed_supplements(result)
    parsed_medicines = _collect_parsed_medicines(result)
    result_text = _collect_result_text(result)

    checks: list[dict[str, Any]] = []

    for nutrient in _split_expected(test_case.get("expected_include_nutrients")):
        in_recommended = any(_contains(nutrient, rec) or _contains(rec, nutrient) for rec in recommended_nutrients)
        in_excluded = any(_contains(nutrient, rec) or _contains(rec, nutrient) for rec in excluded_nutrients)

        passed = in_recommended or in_excluded

        if in_recommended:
            message = f"추천영양소에 {nutrient} 포함"
        elif in_excluded:
            message = f"{nutrient} 추천 후보 생성 후 현재 복용 정보에 의해 최종 추천에서 제외"
        else:
            message = f"추천 후보 또는 제외영양소에 {nutrient} 없음"

        checks.append({
            "type": "include_or_policy_excluded_nutrient",
            "target": nutrient,
            "passed": passed,
            "message": message,
        })

    for nutrient in _split_expected(test_case.get("expected_exclude_nutrients")):
        passed = not any(_contains(nutrient, rec) or _contains(rec, nutrient) for rec in recommended_nutrients)
        checks.append({
            "type": "exclude_nutrient",
            "target": nutrient,
            "passed": passed,
            "message": f"추천영양소에 {nutrient} 미포함",
        })

    for keyword in _split_expected(test_case.get("expected_guidance_keywords")):
        passed = _contains(keyword, result_text)
        checks.append({
            "type": "guidance_keyword",
            "target": keyword,
            "passed": passed,
            "message": f"추천 이유/주의사항/근거에 {keyword} 관련 내용 포함",
        })

    for keyword in _split_expected(test_case.get("expected_supplement_keywords")):
        haystack = " ".join(parsed_supplements + [result_text])
        passed = _contains(keyword, haystack)
        checks.append({
            "type": "parsed_supplement_keyword",
            "target": keyword,
            "passed": passed,
            "message": f"복용 영양제 분석 결과에 {keyword} 관련 내용 포함",
        })

    for keyword in _split_expected(test_case.get("expected_medicine_keywords")):
        haystack = " ".join(parsed_medicines + [result_text])
        passed = _contains(keyword, haystack)
        checks.append({
            "type": "parsed_medicine_keyword",
            "target": keyword,
            "passed": passed,
            "message": f"복용 의약품/주의사항 분석 결과에 {keyword} 관련 내용 포함",
        })

    status = "PASS" if checks and all(check["passed"] for check in checks) else ("NO_CHECK" if not checks else "FAIL")
    return {
        "test_id": test_case.get("test_id", ""),
        "status": status,
        "recommended_nutrients": recommended_nutrients,
        "excluded_nutrients": excluded_nutrients,
        "parsed_supplements": parsed_supplements,
        "parsed_medicines": parsed_medicines,
        "checks": checks,
    }


def run_single_test_case(test_case: dict[str, Any], use_llm: bool = False) -> dict[str, Any]:

    week = int(test_case.get("pregnancy_week") or 0)
    symptom = str(test_case.get("symptom") or "").strip()
    lifestyle = str(test_case.get("lifestyle_check") or "").strip()
    intake_text = str(test_case.get("user_input_text") or "").strip()

    result = run_recommendation(
        week=week,
        symptoms=[symptom] if symptom else [],
        diets=[lifestyle] if lifestyle else [],
        intake_text=intake_text,
        use_llm_intake=use_llm,
        use_llm_summary=use_llm,
        use_llm_caution=use_llm,
        enable_trace=False,
    )
    validation = evaluate_result(result, test_case)
    return {
        "test_case": test_case,
        "validation": validation,
        "result_summary": {
            "stage": result.get("stage"),
            "intake_text": intake_text,
            "parsed_supplements": validation["parsed_supplements"],
            "parsed_medicines": validation["parsed_medicines"],
            "recommendations": [
                {"nutrient": r.get("nutrient"), "score": r.get("score")}
                for r in result.get("recommendations", []) or []
            ],
            "excluded_recommendations": [
                {
                    "nutrient": r.get("nutrient"),
                    "reason": r.get("excluded_reason"),
                    "matched_current_supplement": r.get("matched_current_supplement"),
                }
                for r in result.get("excluded_recommendations", []) or []
            ],
            "search_document_count": len(result.get("search_documents", []) or []),
            "caution_count": len(result.get("cautions", []) or []),
        },
    }


def run_all_test_cases(use_llm: bool = False) -> dict[str, Any]:

    cases = load_test_cases()
    results = [run_single_test_case(case, use_llm=use_llm) for case in cases]
    summary = {
        "db_path": str(get_db_path()),
        "total": len(results),
        "pass": sum(1 for r in results if r["validation"]["status"] == "PASS"),
        "fail": sum(1 for r in results if r["validation"]["status"] == "FAIL"),
        "no_check": sum(1 for r in results if r["validation"]["status"] == "NO_CHECK"),
    }
    return {"summary": summary, "results": results}


def print_report(report: dict[str, Any]) -> None:

    summary = report["summary"]
    print("=" * 80)
    print("recommendation_test_case 검증 결과")
    print("=" * 80)
    print(f"DB: {summary['db_path']}")
    print(f"TOTAL: {summary['total']} / PASS: {summary['pass']} / FAIL: {summary['fail']} / NO_CHECK: {summary['no_check']}")

    for item in report["results"]:
        case = item["test_case"]
        validation = item["validation"]
        result_summary = item["result_summary"]
        print("\n" + "-" * 80)
        print(f"[{case.get('test_id')}] {case.get('pregnancy_week')}주 / {case.get('symptom')} / {case.get('lifestyle_check')}")
        if case.get("user_input_text"):
            print(f"복용정보: {case.get('user_input_text')}")
        print(f"STATUS: {validation['status']}")
        print(f"추천영양소: {', '.join(validation['recommended_nutrients']) or '-'}")
        print(f"제외영양소: {', '.join(validation['excluded_nutrients']) or '-'}")
        print(f"분석영양제: {', '.join(validation['parsed_supplements']) or '-'}")
        print(f"분석의약품: {', '.join(validation['parsed_medicines']) or '-'}")
        print(f"search_document: {result_summary['search_document_count']}건 / 주의사항근거: {result_summary['caution_count']}건")
        for check in validation["checks"]:
            mark = "✓" if check["passed"] else "✗"
            print(f"{mark} {check['message']}")


def main() -> None:
    # T02처럼 복용 정보 문장에서 "엽산제" → "엽산" 추출과
    # 추천 이유/주의사항 LLM 생성 결과까지 검증하려면 LLM 사용이 필요하다.
    report = run_all_test_cases(use_llm=True)
    print_report(report)

    out_path = Path("test_case_prove_result.json")
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON 저장: {out_path.resolve()}")


if __name__ == "__main__":
    main()
