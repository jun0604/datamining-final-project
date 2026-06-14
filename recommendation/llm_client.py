import os
import json
import re
from pathlib import Path

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

HALLYM_API_KEY = os.getenv("HALLYM_API_KEY")
HALLYM_MODEL = os.getenv("HALLYM_MODEL", "claude-sonnet-4-6")
HALLYM_BASE_URL = os.getenv("HALLYM_BASE_URL", "https://factchat-cloud.mindlogic.ai/v1/gateway")

from .utils import FIXED_PUBLIC_SOURCES, FIXED_PUBLIC_SOURCES_TEXT, get_fixed_public_sources


def get_llm_status():
    return {"env_path": str(ENV_PATH), "env_exists": ENV_PATH.exists(), "api_key_loaded": bool(HALLYM_API_KEY), "model": HALLYM_MODEL, "base_url": HALLYM_BASE_URL}


def get_client():
    if not HALLYM_API_KEY or OpenAI is None:
        return None
    return OpenAI(api_key=HALLYM_API_KEY, base_url=HALLYM_BASE_URL)


def _extract_json(text):
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _empty_intake_result(error_message=""):
    return {"supplements": [], "medicines": [], "cautions": [], "llm_used": False, "fallback_used": False, "error": error_message}


def normalize_intake_text(intake_text, trace=None):
    if not intake_text or not intake_text.strip():
        if trace:
            trace.step("LLM 복용 정보 분석 생략", {"사유": "입력 문장 없음"})
        return _empty_intake_result()

    client = get_client()
    if client is None:
        msg = "HALLYM_API_KEY가 로드되지 않았습니다. .env 파일을 확인하세요."
        if trace:
            trace.step("LLM 복용 정보 분석 불가", {"사유": msg, "llm_status": get_llm_status()})
        return _empty_intake_result(msg)

    prompt = f"""
다음 사용자의 복용 정보 문장에서 임산부 영양 추천 서비스에 필요한 키워드만 추출하세요.
반드시 JSON만 출력하세요.

출력 JSON 형식:
{{"supplements": [], "medicines": [], "cautions": []}}

분류 규칙:
- supplements: 영양제, 건강기능식품, 영양성분명. 예: 엽산, 철분, 비타민D, 칼슘, 유산균, 오메가3
- medicines: 의약품명. 예: 타이레놀, 감기약, 진통제, 제산제, 활명수, 아세트아미노펜
- cautions: 질환, 알레르기, 섭취 주의 조건. 예: 고혈압, 당뇨, 알레르기, 생선 알레르기

사용자 입력:
{intake_text}
"""
    try:
        if trace:
            trace.step("LLM 복용 정보 분석 프롬프트", {"model": HALLYM_MODEL, "base_url": HALLYM_BASE_URL, "temperature": 0, "prompt": prompt})
        response = client.chat.completions.create(
            model=HALLYM_MODEL,
            messages=[{"role": "system", "content": "너는 복용 정보 분석기다. 반드시 JSON만 출력한다."}, {"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response.choices[0].message.content
        data = _extract_json(content) or {}
        result = {"supplements": data.get("supplements", []) or [], "medicines": data.get("medicines", []) or [], "cautions": data.get("cautions", []) or [], "llm_used": True, "fallback_used": False, "error": ""}
        if trace:
            trace.step("LLM 복용 정보 분석 응답", {"raw_response": content, "parsed_result": result})
        return result
    except Exception as e:
        if trace:
            trace.error("LLM 복용 정보 분석 실패", e)
        return _empty_intake_result(str(e))


def _fallback_result_summary(result):
    recs = result.get("recommendations", [])
    inp = result.get("input", {})
    if not recs:
        return "입력 정보와 DB 근거를 기준으로 추천 가능한 영양소를 찾지 못했습니다."
    nutrients = ", ".join([r.get("nutrient", "") for r in recs])
    symptoms = ", ".join(inp.get("symptoms", [])) or "선택 증상 없음"
    lifestyles = ", ".join(inp.get("diets", [])) or "선택 생활습관 없음"
    return f"선택한 증상({symptoms})과 생활습관({lifestyles})이 DB 추천 규칙과 원문 근거에 매칭되어 {nutrients}를 우선 추천했습니다."


def generate_result_summary(result, trace=None):
    client = get_client()
    if client is None:
        summary = _fallback_result_summary(result)
        if trace:
            trace.step("추천이유 fallback 생성", {"사유": "LLM client 없음", "추천이유": summary, "llm_status": get_llm_status()})
        return summary

    rec_payload = []
    for r in result.get("recommendations", []):
        rec_payload.append({
            "영양소": r.get("nutrient"),
            "추천근거": r.get("reasons", [])[:3],
            "입력매칭": r.get("triggers", []),
            "주의사항": r.get("nutrient_cautions", [])[:2],
            "근거문장": r.get("evidences", [])[:3],
            "근거행": r.get("trace_rows", []),
            "제품후보": [p.get("product_name", "") for p in r.get("supplements", [])[:3]],
        })

    excluded_payload = []
    for r in result.get("excluded_recommendations", []):
        excluded_payload.append({
            "영양소": r.get("nutrient"),
            "매칭된복용영양제": r.get("matched_current_supplement"),
            "제외이유": r.get("excluded_reason"),
            "입력매칭": r.get("triggers", []),
        })

    search_doc_payload = []
    for d in result.get("search_documents", [])[:6]:
        search_doc_payload.append({
            "title": d.get("title"),
            "summary": d.get("summary"),
            "body_text": d.get("body_text"),
            "keyword_text": d.get("keyword_text"),
            "source_name": d.get("source_name"),
            "matched_keyword": d.get("matched_keyword"),
        })

    prompt = f"""
너는 임산부 영양 추천 서비스의 결과 설명 생성기다.
아래 DB 기반 추천 결과와 search_document 추가 원문 근거만 바탕으로 추천 이유를 3~5문장으로 작성하라.
마크다운 기호를 사용하지 말고, 과장된 의학적 단정은 하지 마라.
의사/약사 상담이 필요한 상황은 부드럽게 안내하라.
현재 복용 중인 영양소와 중복되어 제외된 항목은 추천했다고 쓰지 말고, 중복 섭취 방지를 위해 제외되었다고만 설명하라.

사용자 입력:
{json.dumps(result.get('input', {}), ensure_ascii=False)}

추천 결과:
{json.dumps(rec_payload, ensure_ascii=False)}

중복 섭취 방지를 위해 최종 추천에서 제외된 항목:
{json.dumps(excluded_payload, ensure_ascii=False)}

search_document 추가 원문 근거:
{json.dumps(search_doc_payload, ensure_ascii=False)}
"""
    try:
        if trace:
            trace.step("추천이유 LLM 프롬프트", {"model": HALLYM_MODEL, "base_url": HALLYM_BASE_URL, "temperature": 0.2, "prompt": prompt, "추천근거payload": rec_payload, "중복제외payload": excluded_payload})
        response = client.chat.completions.create(
            model=HALLYM_MODEL,
            messages=[{"role": "system", "content": "너는 데이터 근거 기반 추천 이유 생성기다."}, {"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()
        summary = content or _fallback_result_summary(result)
        if trace:
            trace.step("추천이유 LLM 응답", {"raw_response": content, "최종추천이유": summary})
        return summary
    except Exception as e:
        summary = _fallback_result_summary(result)
        if trace:
            trace.error("추천이유 LLM 생성 실패", e, {"fallback_summary": summary})
        return summary


def _fallback_caution_summary(result):
    cautions = result.get("cautions", [])
    if not cautions:
        return ["권장 섭취량을 초과하지 않도록 주의하세요.", "임신 중 의약품과 영양제를 함께 복용하는 경우 의사 또는 약사와 상담하세요."]
    lines = []
    for c in cautions[:3]:
        warning = c.get("warning") or c.get("interaction") or c.get("evidence")
        if warning:
            lines.append(str(warning).replace("\n", " ")[:220])
    return lines or ["임신 중 의약품과 영양제 복용은 전문가와 상담 후 결정하세요."]


def generate_caution_summary(result, trace=None):
    client = get_client()
    if client is None:
        cautions = _fallback_caution_summary(result)
        if trace:
            trace.step("주의사항 fallback 생성", {"사유": "LLM client 없음", "주의사항": cautions, "llm_status": get_llm_status()})
        return cautions

    prompt = f"""
너는 임산부 영양 추천 서비스의 최종 주의사항 생성기다.
아래 데이터에 포함된 주의사항 근거만 사용하여 최종 주의사항을 2~3개 문장으로 요약하라.
반드시 JSON만 출력하라. 형식: {{"cautions": ["..."]}}
주의사항 근거에 없는 내용을 새로 만들지 마라.
진단/처방처럼 단정하지 말고, 필요한 경우 의사 또는 약사 상담을 안내하라.
중복 섭취 방지를 위해 제외된 영양소가 있으면, 해당 영양소는 추가 섭취 추천이 아니라 중복 주의 항목으로만 작성하라.

고정 출처:
{FIXED_PUBLIC_SOURCES_TEXT}

사용자 입력:
{json.dumps(result.get('input', {}), ensure_ascii=False)}

추천 결과:
{json.dumps(result.get('recommendations', []), ensure_ascii=False)}

주의사항 근거:
{json.dumps(result.get('cautions', []), ensure_ascii=False)}

주의사항 근거에 포함된 search_document 원문 chunk:
{json.dumps([c for c in result.get('cautions', []) if c.get('category') == 'search_document_caution_evidence'], ensure_ascii=False)}
"""
    try:
        if trace:
            trace.step("주의사항 LLM 프롬프트", {"model": HALLYM_MODEL, "base_url": HALLYM_BASE_URL, "temperature": 0.1, "prompt": prompt})
        response = client.chat.completions.create(
            model=HALLYM_MODEL,
            messages=[{"role": "system", "content": "너는 데이터 근거 기반 주의사항 생성기다. JSON만 출력한다."}, {"role": "user", "content": prompt}],
            temperature=0.1,
        )
        raw = response.choices[0].message.content
        data = _extract_json(raw) or {}
        cautions = data.get("cautions", [])
        final_cautions = cautions[:3] if isinstance(cautions, list) and cautions else _fallback_caution_summary(result)[:3]
        if trace:
            trace.step("주의사항 LLM 응답", {"raw_response": raw, "parsed_cautions": cautions, "최종주의사항": final_cautions})
        return final_cautions
    except Exception as e:
        cautions = _fallback_caution_summary(result)
        if trace:
            trace.error("주의사항 LLM 생성 실패", e, {"fallback_cautions": cautions})
        return cautions
