# -*- coding: utf-8 -*-
"""
mfds_raw_to_csv.py

로컬 실행용 MFDS 의약품/영양제 raw JSON -> CSV 변환 스크립트

권장 폴더 구조:
data/
├─ code/
│  └─ mfds_raw_to_csv.py
├─ raw/
│  ├─ mfds_medicine_raw.json
│  └─ mfds_supplement_raw.json
├─ processed/
└─ log/

실행 위치:
python data/code/mfds_raw_to_csv.py

출력:
data/processed/medicine_info.csv
data/processed/supplement_info.csv
data/log/mfds_raw_to_csv_YYYYMMDD_HHMMSS.log
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd


# ============================================================
# 1. 로컬 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
LOG_DIR = PROJECT_ROOT / "log"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

MEDICINE_JSON_PATH = RAW_DIR / "mfds_medicine_raw.json"
SUPPLEMENT_JSON_PATH = RAW_DIR / "mfds_supplement_raw.json"

MEDICINE_CSV_PATH = PROCESSED_DIR / "medicine_info.csv"
SUPPLEMENT_CSV_PATH = PROCESSED_DIR / "supplement_info.csv"


# ============================================================
# 2. 로그 설정
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = LOG_DIR / f"mfds_raw_to_csv_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def log_step(step_name, data=None):
    logger.info("\n" + "=" * 90)
    logger.info(f"[STEP] {step_name}")

    if data is not None:
        try:
            logger.info(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            logger.info(str(data))


log_step("로컬 경로 설정", {
    "PROJECT_ROOT": str(PROJECT_ROOT),
    "RAW_DIR": str(RAW_DIR),
    "PROCESSED_DIR": str(PROCESSED_DIR),
    "LOG_DIR": str(LOG_DIR),
    "LOG_PATH": str(LOG_PATH),
    "MEDICINE_JSON_PATH": str(MEDICINE_JSON_PATH),
    "SUPPLEMENT_JSON_PATH": str(SUPPLEMENT_JSON_PATH)
})


# ============================================================
# 3. JSON 로드 함수
# ============================================================

def load_json_file(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    log_step("JSON 로드 완료", {
        "path": str(path),
        "type": type(data).__name__
    })

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["data", "items", "results", "body", "response"]:
            if key in data and isinstance(data[key], list):
                log_step("JSON 내부 list 키 발견", {
                    "path": str(path),
                    "list_key": key,
                    "row_count": len(data[key])
                })
                return data[key]

        for key, value in data.items():
            if isinstance(value, list):
                log_step("JSON 내부 첫 번째 list 자동 탐색", {
                    "path": str(path),
                    "list_key": key,
                    "row_count": len(value)
                })
                return value

    log_step("JSON에서 list 데이터 탐색 실패", {
        "path": str(path),
        "return_rows": 0
    })

    return []


# ============================================================
# 4. CSV 변환 함수
# ============================================================

def create_medicine_csv():
    medicine_data = load_json_file(MEDICINE_JSON_PATH)
    medicine_df = pd.DataFrame(medicine_data)

    log_step("의약품 원본 DataFrame 생성", {
        "raw_rows": len(medicine_df),
        "raw_columns": list(medicine_df.columns)
    })

    column_mapping = {
        "medicine_name": "의약품명",
        "efficacy": "효능효과",
        "usage": "복용방법",
        "warning": "주의사항",
        "interaction": "상호작용"
    }

    for eng_col in column_mapping.keys():
        if eng_col not in medicine_df.columns:
            medicine_df[eng_col] = ""
            logger.warning(f"의약품 컬럼 없음 -> 빈 컬럼 생성: {eng_col}")

    medicine_df = medicine_df[list(column_mapping.keys())]
    medicine_df = medicine_df.rename(columns=column_mapping)
    medicine_df = medicine_df.fillna("")
    before_drop = len(medicine_df)
    medicine_df = medicine_df.drop_duplicates()
    after_drop = len(medicine_df)

    medicine_df.to_csv(
        MEDICINE_CSV_PATH,
        index=False,
        encoding="utf-8-sig"
    )

    log_step("medicine_info.csv 저장 완료", {
        "output_path": str(MEDICINE_CSV_PATH),
        "rows_before_drop_duplicates": before_drop,
        "rows_after_drop_duplicates": after_drop,
        "columns": list(medicine_df.columns),
        "preview": medicine_df.head(5).to_dict("records")
    })

    return medicine_df


def create_supplement_csv():
    supplement_data = load_json_file(SUPPLEMENT_JSON_PATH)
    supplement_df = pd.DataFrame(supplement_data)

    log_step("영양제 원본 DataFrame 생성", {
        "raw_rows": len(supplement_df),
        "raw_columns": list(supplement_df.columns)
    })

    column_mapping = {
        "product_name": "제품명",
        "company_name": "제조사",
        "ingredients": "성분"
    }

    for eng_col in column_mapping.keys():
        if eng_col not in supplement_df.columns:
            supplement_df[eng_col] = ""
            logger.warning(f"영양제 컬럼 없음 -> 빈 컬럼 생성: {eng_col}")

    supplement_df = supplement_df[list(column_mapping.keys())]
    supplement_df = supplement_df.rename(columns=column_mapping)
    supplement_df = supplement_df.fillna("")
    before_drop = len(supplement_df)
    supplement_df = supplement_df.drop_duplicates()
    after_drop = len(supplement_df)

    supplement_df.to_csv(
        SUPPLEMENT_CSV_PATH,
        index=False,
        encoding="utf-8-sig"
    )

    log_step("supplement_info.csv 저장 완료", {
        "output_path": str(SUPPLEMENT_CSV_PATH),
        "rows_before_drop_duplicates": before_drop,
        "rows_after_drop_duplicates": after_drop,
        "columns": list(supplement_df.columns),
        "preview": supplement_df.head(5).to_dict("records")
    })

    return supplement_df


# ============================================================
# 5. 실행
# ============================================================

def main():
    file_check = {
        "medicine_exists": MEDICINE_JSON_PATH.exists(),
        "supplement_exists": SUPPLEMENT_JSON_PATH.exists(),
        "raw_files": [f.name for f in RAW_DIR.glob("*")]
    }

    log_step("입력 파일 확인", file_check)

    missing = []
    if not MEDICINE_JSON_PATH.exists():
        missing.append(str(MEDICINE_JSON_PATH))
    if not SUPPLEMENT_JSON_PATH.exists():
        missing.append(str(SUPPLEMENT_JSON_PATH))

    if missing:
        raise FileNotFoundError(
            "다음 raw JSON 파일이 존재하지 않습니다:\n"
            + "\n".join(missing)
            + "\n\n파일을 data/raw 폴더에 넣은 뒤 다시 실행하세요."
        )

    medicine_df = create_medicine_csv()
    supplement_df = create_supplement_csv()

    output_files = [f.name for f in PROCESSED_DIR.glob("*")]

    log_step("전체 변환 완료", {
        "medicine_rows": len(medicine_df),
        "supplement_rows": len(supplement_df),
        "processed_files": output_files
    })

    print("\n저장 완료 파일")
    print("-", MEDICINE_CSV_PATH)
    print("-", SUPPLEMENT_CSV_PATH)

    print("\n로그 파일")
    print(LOG_PATH)


if __name__ == "__main__":
    main()
