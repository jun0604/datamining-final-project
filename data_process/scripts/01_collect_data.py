# collect_mfds_api.py

import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# 1. 기본 경로 및 인증키 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESS_DIR = PROJECT_ROOT / "data_process"

load_dotenv(PROJECT_ROOT / ".env")
RAW_DIR = DATA_PROCESS_DIR / "data" / "raw"

FOODSAFETY_KEY = os.getenv("FOODSAFETY_KEY", "")
DATA_GO_KR_KEY = os.getenv("DATA_GO_KR_KEY", "")


# ============================================================
# 2. API 서비스 설정
# ============================================================

FOODSAFETY_SERVICES = {
    "mfds_supplement_raw.json": {
        "service_code": "I0030",
        "description": "건강기능식품 품목제조 신고사항 현황"
    },
}

FOODSAFETY_BASE_URL = "https://openapi.foodsafetykorea.go.kr/api"
FOODSAFETY_SOURCE_URL = "https://www.foodsafetykorea.go.kr"

# 1) 의약품개요정보(e약은요)
EASY_DRUG_ENDPOINT = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService"
EASY_DRUG_LIST_OPERATION = "getDrbEasyDrugList"

# 2) 의약품 제품 허가정보
DRUG_PERMISSION_ENDPOINT = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService07"
DRUG_PERMISSION_LIST_OPERATION = "getDrugPrdtPrmsnInq07"
DRUG_PERMISSION_DETAIL_OPERATION = "getDrugPrdtPrmsnDtlInq06"
DRUG_PERMISSION_INGREDIENT_OPERATION = "getDrugPrdtMcpnDtlInq07"


# ============================================================
# 3. 요청 안정화 설정
# ============================================================

REQUEST_TIMEOUT = (10, 90)
MAX_RETRY = 5
RETRY_SLEEP = 2

# 상세 API는 전체 품목마다 호출하면 오래 걸릴 수 있으므로 약간 쉬어감
DETAIL_REQUEST_SLEEP = 0.15


# ============================================================
# 4. 공통 유틸 함수
# ============================================================

def save_json(data, filename):
    output_path = RAW_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] 저장 완료: {output_path}")


def find_items(obj):
    """
    JSON 안에서 list[dict] 형태 데이터를 최대한 찾아냄.
    식품안전나라: row
    공공데이터포털: response > body > items > item
    """

    if obj is None:
        return []

    if isinstance(obj, list):
        if all(isinstance(x, dict) for x in obj):
            return obj
        return []

    if isinstance(obj, dict):
        for key in ["row", "items", "item", "data", "list"]:
            value = obj.get(key)

            if isinstance(value, list):
                return value

            if isinstance(value, dict):
                found = find_items(value)
                if found:
                    return found

        for value in obj.values():
            found = find_items(value)
            if found:
                return found

    return []


def find_value_by_key(obj: Any, target_key: str):
    """
    dict/list 내부에서 특정 key 값을 재귀적으로 찾음.
    """

    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() == target_key.lower():
                return value

        for value in obj.values():
            found = find_value_by_key(value, target_key)
            if found is not None:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = find_value_by_key(item, target_key)
            if found is not None:
                return found

    return None


def to_int(value, default=0):
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return default


def clean_text(value):
    if value is None:
        return ""

    text = str(value).strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
    return text


def pick(item, candidates, default=""):
    if not isinstance(item, dict):
        return default

    for key in candidates:
        value = item.get(key)

        if value not in [None, ""]:
            return clean_text(value)

    return default


def join_non_empty(*values, sep="\n"):
    cleaned = []

    for value in values:
        text = clean_text(value)

        if text and text not in cleaned:
            cleaned.append(text)

    return sep.join(cleaned)


def make_failure_response(source, message, raw_text="", error=""):
    """
    API 실패 시 가짜 샘플을 만들지 않고 실패 상태만 저장.
    """

    return {
        "fallback": True,
        "success": False,
        "source": source,
        "message": message,
        "error": error,
        "raw_text_preview": raw_text[:2000] if raw_text else "",
        "items": []
    }


def merge_foodsafety_response(service_code, rows, result=None):
    return {
        service_code: {
            "total_count": str(len(rows)),
            "row": rows,
            "RESULT": result or {
                "MSG": "정상처리되었습니다.",
                "CODE": "INFO-000"
            }
        }
    }


# ============================================================
# 5. 식품안전나라 API 공통 수집
# ============================================================

def request_foodsafety_json(url, debug=False):
    last_error = None

    for attempt in range(1, MAX_RETRY + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            text = response.text

            if debug:
                print("[DEBUG] 식품안전나라 status:", response.status_code)
                print("[DEBUG] 식품안전나라 url:", url)
                print("[DEBUG] 식품안전나라 text preview:")
                print(text[:1000])

            if "인증키가 유효하지" in text or "alert" in text:
                print("[ERROR] 식품안전나라 인증키 오류 응답")
                print(text[:500])
                return make_failure_response(
                    source="식품안전나라",
                    message="식품안전나라 인증키 오류",
                    raw_text=text
                )

            try:
                return response.json()
            except Exception:
                print("[ERROR] 식품안전나라 JSON 변환 실패")
                print("[DEBUG] 응답 일부:")
                print(text[:1000])
                return make_failure_response(
                    source="식품안전나라",
                    message="JSON 변환 실패",
                    raw_text=text
                )

        except Exception as e:
            last_error = e
            print(f"[WARN] 식품안전나라 API 요청 실패 {attempt}/{MAX_RETRY}")
            print(f"URL: {url}")
            print(f"이유: {e}")

            if attempt < MAX_RETRY:
                time.sleep(RETRY_SLEEP * attempt)

    return make_failure_response(
        source="식품안전나라",
        message="요청 재시도 최종 실패",
        error=str(last_error)
    )


def get_foodsafety_total_count(data, service_code):
    try:
        service_data = data.get(service_code, {})
        total_count = service_data.get("total_count", 0)
        return int(str(total_count).replace(",", ""))
    except Exception:
        total_count = find_value_by_key(data, "total_count")
        return to_int(total_count)


def get_foodsafety_result(data, service_code):
    if isinstance(data, dict):
        service_data = data.get(service_code, {})
        if isinstance(service_data, dict):
            return service_data.get("RESULT")

    return None


def make_foodsafety_url(api_key, service_code, start, end):
    return (
        f"{FOODSAFETY_BASE_URL}/"
        f"{api_key}/{service_code}/json/{start}/{end}"
    )


def collect_foodsafety_all(service_code, api_key, page_size=1000):
    if "여기에" in api_key or not api_key.strip():
        print(f"[FAIL] {service_code} 인증키가 입력되지 않았습니다.")
        return make_failure_response(
            source=f"식품안전나라 {service_code}",
            message="인증키가 입력되지 않았습니다."
        )

    first_url = make_foodsafety_url(
        api_key=api_key,
        service_code=service_code,
        start=1,
        end=page_size
    )

    first_data = request_foodsafety_json(first_url, debug=True)

    if isinstance(first_data, dict) and first_data.get("fallback") is True:
        return first_data

    total_count = get_foodsafety_total_count(first_data, service_code)
    result = get_foodsafety_result(first_data, service_code)
    first_rows = find_items(first_data)

    if total_count == 0:
        print(f"[WARN] {service_code} total_count 확인 실패. 첫 요청 row만 저장합니다.")
        return merge_foodsafety_response(service_code, first_rows, result)

    print(f"[INFO] {service_code} total_count: {total_count}")
    print(f"[INFO] {service_code} 1차 수집 완료 / {len(first_rows)} rows")

    all_rows = []
    all_rows.extend(first_rows)

    failed_ranges: List[Tuple[int, int]] = []

    for start in range(page_size + 1, total_count + 1, page_size):
        end = min(start + page_size - 1, total_count)

        url = make_foodsafety_url(
            api_key=api_key,
            service_code=service_code,
            start=start,
            end=end
        )

        print(f"[INFO] {service_code} 수집 중: {start}~{end}")

        data = request_foodsafety_json(url)

        if isinstance(data, dict) and data.get("fallback") is True:
            print(f"[WARN] {service_code} {start}~{end} 구간 수집 실패. 재수집 목록에 추가.")
            failed_ranges.append((start, end))
            continue

        rows = find_items(data)

        if not rows:
            print(f"[WARN] {service_code} {start}~{end} 구간에서 row를 찾지 못함. 재수집 목록에 추가.")
            failed_ranges.append((start, end))
            continue

        all_rows.extend(rows)
        time.sleep(0.2)

    if failed_ranges:
        print()
        print(f"[INFO] {service_code} 실패 구간 재수집 시작: {failed_ranges}")

        still_failed = []

        for start, end in failed_ranges:
            url = make_foodsafety_url(
                api_key=api_key,
                service_code=service_code,
                start=start,
                end=end
            )

            print(f"[INFO] {service_code} 실패 구간 재수집 중: {start}~{end}")

            data = request_foodsafety_json(url, debug=True)

            if isinstance(data, dict) and data.get("fallback") is True:
                print(f"[ERROR] {service_code} {start}~{end} 재수집 최종 실패")
                still_failed.append((start, end))
                continue

            rows = find_items(data)

            if not rows:
                print(f"[ERROR] {service_code} {start}~{end} 재수집했지만 row 없음")
                still_failed.append((start, end))
                continue

            all_rows.extend(rows)
            print(f"[OK] {service_code} {start}~{end} 재수집 완료 / {len(rows)} rows")
            time.sleep(1)

        if still_failed:
            save_json(still_failed, f"{service_code}_failed_ranges.json")
            print(f"[WARN] {service_code} 최종 실패 구간 저장 완료")

    print(f"[OK] {service_code} 전체 수집 완료 / {len(all_rows)} rows")

    return merge_foodsafety_response(service_code, all_rows, result)


# ============================================================
# 6. 건강기능식품 JSON 정규화
# ============================================================

def normalize_supplement_raw(raw_data):
    """
    mfds_supplement_raw.json

    출처 : 공공데이터포털(MFDS)

    사용 OpenAPI 서비스명
    - 건강기능식품 품목제조 신고사항 현황

    컬럼매칭
    product_name -> PRDLST_NM
    company_name -> BSSH_NM
    report_no -> PRDLST_REPORT_NO
    ingredients -> RAWMTRL_NM
    registration_date -> PRMS_DT
    product_type -> PRDLST_CDNM

    status 제거
    """

    items = find_items(raw_data)
    rows = []
    seen = set()

    for item in items:
        product_name = pick(item, ["PRDLST_NM"])
        company_name = pick(item, ["BSSH_NM"])
        report_no = pick(item, ["PRDLST_REPORT_NO"])
        ingredients = pick(item, ["RAWMTRL_NM"])
        registration_date = pick(item, ["PRMS_DT"])
        product_type = pick(item, ["PRDLST_CDNM"])

        if not product_name and not report_no:
            continue

        dedup_key = (
            product_name,
            company_name,
            report_no,
            ingredients,
            registration_date,
            product_type
        )

        if dedup_key in seen:
            continue

        seen.add(dedup_key)

        rows.append({
            "product_name": product_name,
            "company_name": company_name,
            "report_no": report_no,
            "ingredients": ingredients,
            "registration_date": registration_date,
            "product_type": product_type
        })

    if rows:
        print(f"[OK] I0030 정규화 완료 / {len(rows)} rows")
    else:
        print("[WARN] I0030 raw에서 row 파싱 실패 또는 필요한 컬럼 없음")

    return rows

def collect_foodsafety_service(filename, service_code, api_key, description):
    print(f"[INFO] 식품안전나라 API 사용: {service_code} / {description}")

    data = collect_foodsafety_all(
        service_code=service_code,
        api_key=api_key,
        page_size=1000
    )

    original_filename = filename.replace(".json", "_original.json")
    save_json(data, original_filename)

    if isinstance(data, dict) and data.get("fallback") is True:
        print(f"[FAIL] {service_code} 수집 실패로 정규화 파일도 실패 상태로 저장합니다.")
        save_json(data, filename)
        return

    if filename == "mfds_supplement_raw.json":
        normalized_data = normalize_supplement_raw(data)
        save_json(normalized_data, filename)

    else:
        save_json(data, filename)

# ============================================================
# 7. 공공데이터포털 의약품 API 공통 수집
# ============================================================

def request_data_go_kr_json(url, params, debug=False):
    last_error = None

    for attempt in range(1, MAX_RETRY + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            text = response.text

            if debug:
                print("[DEBUG] 공공데이터포털 status:", response.status_code)
                print("[DEBUG] 공공데이터포털 request url:", response.url)
                print("[DEBUG] 공공데이터포털 text preview:")
                print(text[:2000])

            error_keywords = [
                "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
                "SERVICE_KEY_IS_NOT_REGISTERED",
                "INVALID_REQUEST_PARAMETER_ERROR",
                "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR",
                "SERVICE_ACCESS_DENIED_ERROR",
                "등록되지 않은 서비스키",
                "유효하지 않은 인증키",
                "SERVICE ERROR",
                "APPLICATION_ERROR",
                "DB_ERROR"
            ]

            if any(keyword in text for keyword in error_keywords):
                print("[ERROR] 공공데이터포털 API 오류 응답")
                print(text[:1000])
                return make_failure_response(
                    source="공공데이터포털 의약품 API",
                    message="공공데이터포털 API 오류 응답",
                    raw_text=text
                )

            try:
                return response.json()
            except Exception:
                print("[ERROR] 공공데이터포털 JSON 변환 실패")
                print("[DEBUG] 응답 일부:")
                print(text[:2000])
                return make_failure_response(
                    source="공공데이터포털 의약품 API",
                    message="JSON 변환 실패",
                    raw_text=text
                )

        except Exception as e:
            last_error = e
            print(f"[WARN] 공공데이터포털 API 요청 실패 {attempt}/{MAX_RETRY}")
            print(f"URL: {url}")
            print(f"params: {params}")
            print(f"이유: {e}")

            if attempt < MAX_RETRY:
                time.sleep(RETRY_SLEEP * attempt)

    return make_failure_response(
        source="공공데이터포털 의약품 API",
        message="요청 재시도 최종 실패",
        error=str(last_error)
    )


def get_data_go_kr_total_count(data):
    if not isinstance(data, dict):
        return 0

    try:
        if "body" in data and isinstance(data["body"], dict):
            return to_int(data["body"].get("totalCount", 0))

        if "response" in data:
            return to_int(data["response"]["body"].get("totalCount", 0))

    except Exception:
        pass

    total_count = (
        find_value_by_key(data, "totalCount")
        or find_value_by_key(data, "total_count")
        or find_value_by_key(data, "totalcount")
    )

    return to_int(total_count)


def collect_data_go_kr_all(
    endpoint,
    operation,
    source_name,
    num_rows=500,
    extra_params=None,
    max_pages=None
):
    """
    공공데이터포털 목록형 API 전체 수집.
    """

    if "여기에" in DATA_GO_KR_KEY or not DATA_GO_KR_KEY.strip():
        print(f"[FAIL] {source_name} 인증키가 입력되지 않았습니다.")
        return make_failure_response(
            source=source_name,
            message="공공데이터포털 인증키가 입력되지 않았습니다."
        )

    url = f"{endpoint}/{operation}"

    print(f"[INFO] {source_name} 전체 수집 시작")
    print(f"[INFO] URL: {url}")

    base_params = {
        "serviceKey": DATA_GO_KR_KEY,
        "pageNo": 1,
        "numOfRows": num_rows,
        "type": "json"
    }

    if extra_params:
        base_params.update(extra_params)

    first_data = request_data_go_kr_json(
        url,
        base_params,
        debug=True
    )

    if isinstance(first_data, dict) and first_data.get("fallback") is True:
        print(f"[FAIL] {source_name} 첫 요청 실패")
        return first_data

    total_count = get_data_go_kr_total_count(first_data)
    first_rows = find_items(first_data)

    if total_count == 0:
        print(f"[WARN] {source_name} totalCount 확인 실패. 첫 요청 row만 사용합니다.")
        return first_rows

    print(f"[INFO] {source_name} totalCount: {total_count}")
    print(f"[INFO] {source_name} 1페이지 수집 완료 / {len(first_rows)} rows")

    all_rows = []
    all_rows.extend(first_rows)

    total_pages = math.ceil(total_count / num_rows)

    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    failed_pages = []

    for page_no in range(2, total_pages + 1):
        params = {
            "serviceKey": DATA_GO_KR_KEY,
            "pageNo": page_no,
            "numOfRows": num_rows,
            "type": "json"
        }

        if extra_params:
            params.update(extra_params)

        print(f"[INFO] {source_name} 수집 중: page {page_no}/{total_pages}")

        data = request_data_go_kr_json(url, params)

        if isinstance(data, dict) and data.get("fallback") is True:
            print(f"[WARN] {source_name} page {page_no} 수집 실패. 재수집 목록에 추가.")
            failed_pages.append(page_no)
            continue

        rows = find_items(data)

        if not rows:
            print(f"[WARN] {source_name} page {page_no}에서 rows를 찾지 못함. 재수집 목록에 추가.")
            failed_pages.append(page_no)
            continue

        all_rows.extend(rows)
        time.sleep(0.2)

    if failed_pages:
        print()
        print(f"[INFO] {source_name} 실패 페이지 재수집 시작: {failed_pages}")

        still_failed = []

        for page_no in failed_pages:
            params = {
                "serviceKey": DATA_GO_KR_KEY,
                "pageNo": page_no,
                "numOfRows": num_rows,
                "type": "json"
            }

            if extra_params:
                params.update(extra_params)

            print(f"[INFO] {source_name} 실패 page 재수집 중: {page_no}")

            data = request_data_go_kr_json(
                url,
                params,
                debug=True
            )

            if isinstance(data, dict) and data.get("fallback") is True:
                print(f"[ERROR] {source_name} page {page_no} 재수집 최종 실패")
                still_failed.append(page_no)
                continue

            rows = find_items(data)

            if not rows:
                print(f"[ERROR] {source_name} page {page_no} 재수집했지만 rows 없음")
                still_failed.append(page_no)
                continue

            all_rows.extend(rows)
            print(f"[OK] {source_name} page {page_no} 재수집 완료 / {len(rows)} rows")
            time.sleep(1)

        if still_failed:
            failed_filename = source_name.replace(" ", "_").replace("/", "_") + "_failed_pages.json"
            save_json(still_failed, failed_filename)
            print(f"[WARN] {source_name} 최종 실패 페이지 저장 완료")

    print(f"[OK] {source_name} 전체 수집 완료 / {len(all_rows)} rows")

    return all_rows


# ============================================================
# 8. 의약품 상세 API 조회
# ============================================================

def collect_drug_permission_detail_by_item_seq(item_seq):
    """
    의약품 제품 허가 상세정보 조회
    /getDrugPrdtPrmsnDtlInq06

    ingredient는 이 상세 API의 main_item_ingr에서 가져옴.
    예:
    main_item_ingr = [M040702]포도당|[M040426]염화나트륨
    """

    if not item_seq:
        return {}

    url = f"{DRUG_PERMISSION_ENDPOINT}/{DRUG_PERMISSION_DETAIL_OPERATION}"

    params = {
        "serviceKey": DATA_GO_KR_KEY,
        "type": "json",
        "item_seq": item_seq
    }

    data = request_data_go_kr_json(url, params)

    if isinstance(data, dict) and data.get("fallback") is True:
        return {}

    rows = find_items(data)

    if not rows:
        return {}

    return rows[0]


def collect_drug_ingredient_detail_by_item_seq(item_seq):
    """
    의약품 제품 주성분 상세정보 조회
    /getDrugPrdtMcpnDtlInq07

    현재 최종 ingredient는 /getDrugPrdtPrmsnDtlInq06의 main_item_ingr를 우선 사용.
    이 함수는 필요할 때 추가 확인용으로 사용.
    """

    if not item_seq:
        return []

    url = f"{DRUG_PERMISSION_ENDPOINT}/{DRUG_PERMISSION_INGREDIENT_OPERATION}"

    params = {
        "serviceKey": DATA_GO_KR_KEY,
        "type": "json",
        "item_seq": item_seq
    }

    data = request_data_go_kr_json(url, params)

    if isinstance(data, dict) and data.get("fallback") is True:
        return []

    return find_items(data)


def build_permission_detail_map(permission_rows):
    """
    허가 목록에서 item_seq를 뽑아 상세 API를 호출하고,
    item_seq -> 상세 row 형태로 저장.
    """

    detail_map = {}
    total = len(permission_rows)

    for idx, item in enumerate(permission_rows, start=1):
        item_seq = pick(item, ["ITEM_SEQ", "itemSeq", "item_seq"])

        if not item_seq:
            continue

        if item_seq in detail_map:
            continue

        print(f"[INFO] 의약품 허가 상세 조회 중: {idx}/{total} item_seq={item_seq}")

        detail_item = collect_drug_permission_detail_by_item_seq(item_seq)
        detail_map[item_seq] = detail_item

        time.sleep(DETAIL_REQUEST_SLEEP)

    print(f"[OK] 의약품 허가 상세 조회 완료 / {len(detail_map)}건")
    return detail_map


# ============================================================
# 9. 의약품 데이터 정규화
# ============================================================

def normalize_easy_drug_item(item):
    """
    의약품개요정보(e약은요)

    medicine_name -> itemName
    efficacy -> efcyQesitm
    usage -> useMethodQesitm
    warning -> atpnWarnQesitm + atpnQesitm
    interaction -> intrcQesitm
    side_effect -> seQesitm
    storage -> depositMethodQesitm
    manufacturer -> entpName
    """

    medicine_name = pick(item, ["itemName", "item_name"])
    manufacturer = pick(item, ["entpName", "entp_name"])

    warning = join_non_empty(
        pick(item, ["atpnWarnQesitm", "atpn_warn_qesitm"]),
        pick(item, ["atpnQesitm", "atpn_qesitm"]),
        sep="\n"
    )

    return {
        "medicine_name": medicine_name,
        "efficacy": pick(item, ["efcyQesitm", "efcy_qesitm"]),
        "usage": pick(item, ["useMethodQesitm", "use_method_qesitm"]),
        "warning": warning,
        "interaction": pick(item, ["intrcQesitm", "intrc_qesitm"]),
        "side_effect": pick(item, ["seQesitm", "se_qesitm"]),
        "storage": pick(item, ["depositMethodQesitm", "deposit_method_qesitm"]),
        "manufacturer": manufacturer,
        "ingredient": "",
        "item_seq": pick(item, ["itemSeq", "item_seq"]),
        "source_api": "의약품개요정보(e약은요)"
    }


def normalize_permission_item(item, detail_item=None):
    """
    의약품 제품 허가정보

    목록 API:
    /getDrugPrdtPrmsnInq07

    상세 API:
    /getDrugPrdtPrmsnDtlInq06

    컬럼매칭
    medicine_name -> ITEM_NAME 또는 item_name
    ingredient -> main_item_ingr
    storage -> STORAGE_METHOD 또는 storage_method
    manufacturer -> ENTP_NAME 또는 entp_name

    주의:
    ingredient는 목록 API가 아니라 상세 API의 main_item_ingr를 우선 사용.
    """

    detail_item = detail_item or {}

    item_seq = (
        pick(item, ["ITEM_SEQ", "itemSeq", "item_seq"])
        or pick(detail_item, ["ITEM_SEQ", "itemSeq", "item_seq"])
    )

    medicine_name = (
        pick(detail_item, ["ITEM_NAME", "itemName", "item_name"])
        or pick(item, ["ITEM_NAME", "itemName", "item_name"])
    )

    manufacturer = (
        pick(detail_item, ["ENTP_NAME", "entpName", "entp_name"])
        or pick(item, ["ENTP_NAME", "entpName", "entp_name"])
    )

    storage = (
        pick(detail_item, ["STORAGE_METHOD", "storageMethod", "storage_method"])
        or pick(item, ["STORAGE_METHOD", "storageMethod", "storage_method"])
    )

    ingredient = (
        pick(detail_item, ["main_item_ingr", "MAIN_ITEM_INGR", "mainItemIngr"])
        or pick(item, ["main_item_ingr", "MAIN_ITEM_INGR", "mainItemIngr"])
    )

    return {
        "medicine_name": medicine_name,
        "efficacy": "",
        "usage": "",
        "warning": "",
        "interaction": "",
        "side_effect": "",
        "storage": storage,
        "manufacturer": manufacturer,
        "ingredient": ingredient,
        "item_seq": item_seq,
        "item_permit_date": (
            pick(detail_item, ["ITEM_PERMIT_DATE", "itemPermitDate", "item_permit_date"])
            or pick(item, ["ITEM_PERMIT_DATE", "itemPermitDate", "item_permit_date"])
        ),
        "permit_no": (
            pick(detail_item, ["PERMIT_NO", "permitNo", "permit_no"])
            or pick(item, ["PERMIT_NO", "permitNo", "permit_no"])
        ),
        "source_api": "의약품 제품 허가정보"
    }


def merge_medicine_rows(easy_rows, permission_rows):
    """
    e약은요와 의약품 제품 허가정보를 병합.

    1차 병합 기준:
    - item_seq가 같으면 item_seq 기준 병합

    2차 병합 기준:
    - item_seq가 없으면 medicine_name 기준 병합

    같은 약이 있으면 e약은요 설명 컬럼을 우선 유지하고,
    허가정보에서 ingredient, storage, manufacturer를 보강.
    """

    merged_by_key: Dict[str, Dict[str, str]] = {}

    def make_key(row):
        item_seq = row.get("item_seq", "").strip()
        medicine_name = row.get("medicine_name", "").strip()

        if item_seq:
            return f"item_seq:{item_seq}"

        if medicine_name:
            return f"name:{medicine_name}"

        return ""

    for row in easy_rows:
        key = make_key(row)

        if not key:
            continue

        merged_by_key[key] = row.copy()

    for row in permission_rows:
        key = make_key(row)

        if not key:
            continue

        if key not in merged_by_key:
            merged_by_key[key] = row.copy()
            continue

        current = merged_by_key[key]

        # 허가정보에서 보강할 컬럼
        for col in [
            "ingredient",
            "storage",
            "manufacturer",
            "item_seq",
            "item_permit_date",
            "permit_no"
        ]:
            if not current.get(col) and row.get(col):
                current[col] = row.get(col)

        current["source_api"] = "의약품개요정보(e약은요) + 의약품 제품 허가정보"

    result = list(merged_by_key.values())

    print(f"[OK] 의약품 병합 완료 / {len(result)} rows")
    return result


def collect_medicine_data(num_rows=500):
    """
    mfds_medicine_raw.json

    출처 : 공공데이터포털(MFDS)

    사용 OpenAPI 서비스명 및 컬럼매칭

    1) 의약품개요정보(e약은요)
    medicine_name -> itemName
    efficacy -> efcyQesitm
    usage -> useMethodQesitm
    warning -> atpnWarnQesitm + atpnQesitm
    interaction -> intrcQesitm
    side_effect -> seQesitm
    storage -> depositMethodQesitm
    manufacturer -> entpName

    2) 의약품 제품 허가정보
    medicine_name -> ITEM_NAME 또는 item_name
    ingredient -> main_item_ingr
    storage -> STORAGE_METHOD 또는 storage_method
    manufacturer -> ENTP_NAME 또는 entp_name

    ingredient는 의약품 제품 허가 상세정보
    /getDrugPrdtPrmsnDtlInq06의 main_item_ingr에서 보강.
    """

    print("========== 의약품개요정보(e약은요) 수집 시작 ==========")

    easy_drug_raw_rows = collect_data_go_kr_all(
        endpoint=EASY_DRUG_ENDPOINT,
        operation=EASY_DRUG_LIST_OPERATION,
        source_name="의약품개요정보(e약은요)",
        num_rows=num_rows
    )

    if isinstance(easy_drug_raw_rows, dict) and easy_drug_raw_rows.get("fallback") is True:
        save_json(easy_drug_raw_rows, "mfds_medicine_easy_drug_failed.json")
        easy_rows = []
    else:
        save_json(easy_drug_raw_rows, "mfds_medicine_easy_drug_original.json")
        easy_rows = [
            normalize_easy_drug_item(item)
            for item in easy_drug_raw_rows
            if isinstance(item, dict)
        ]

    print()
    print("========== 의약품 제품 허가 목록 수집 시작 ==========")

    permission_raw_rows = collect_data_go_kr_all(
        endpoint=DRUG_PERMISSION_ENDPOINT,
        operation=DRUG_PERMISSION_LIST_OPERATION,
        source_name="의약품 제품 허가 목록",
        num_rows=num_rows
    )

    if isinstance(permission_raw_rows, dict) and permission_raw_rows.get("fallback") is True:
        save_json(permission_raw_rows, "mfds_medicine_permission_failed.json")
        permission_rows = []
    else:
        save_json(permission_raw_rows, "mfds_medicine_permission_original.json")

        print()
        print("========== 의약품 제품 허가 상세정보 수집 시작 ==========")

        permission_detail_map = build_permission_detail_map(permission_raw_rows)
        save_json(permission_detail_map, "mfds_medicine_permission_detail_original.json")

        permission_rows = []

        for item in permission_raw_rows:
            item_seq = pick(item, ["ITEM_SEQ", "itemSeq", "item_seq"])
            detail_item = permission_detail_map.get(item_seq, {})

            normalized = normalize_permission_item(
                item=item,
                detail_item=detail_item
            )

            permission_rows.append(normalized)

    merged_rows = merge_medicine_rows(
        easy_rows=easy_rows,
        permission_rows=permission_rows
    )

    if not merged_rows:
        failure_data = make_failure_response(
            source="공공데이터포털 의약품 API",
            message="e약은요와 의약품 제품 허가정보 모두 정상 row를 만들지 못했습니다."
        )
        save_json(failure_data, "mfds_medicine_raw.json")
        return

    save_json(merged_rows, "mfds_medicine_raw.json")


# ============================================================
# 10. 실행부
# ============================================================

def main():
    print("========== 1. 식품안전나라 건강기능식품 API 전체 수집 시작 ==========")

    for filename, config in FOODSAFETY_SERVICES.items():
        collect_foodsafety_service(
            filename=filename,
            service_code=config["service_code"],
            api_key=FOODSAFETY_KEY,
            description=config["description"]
        )

    print()
    print("========== 2. 공공데이터포털 의약품 API 전체 수집 시작 ==========")

    collect_medicine_data(num_rows=500)

    print()
    print("========== raw 데이터 전체 수집 완료 ==========")


if __name__ == "__main__":
    main()