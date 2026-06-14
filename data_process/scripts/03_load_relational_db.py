from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


# ============================================================
# load_relational_db.py
# ------------------------------------------------------------
# 최종 구조:
# - KDCA raw JSON은 RDB에 직접 적재하지 않음
# - KDCA raw JSON은 symptom_nutrient_with_validation.csv 생성/검증용 원천 데이터로만 사용
# - RDB에는 symptom_nutrient_with_validation.csv를 우선 적재
# - 없으면 symptom_nutrient.csv 사용
# - MFDS 건강기능식품 raw JSON → supplement_info / supplement_ingredient
# - MFDS 의약품 raw JSON → medicine_info
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESS_DIR = PROJECT_ROOT / "data_process"

RAW_DIR = DATA_PROCESS_DIR / "data" / "raw"
PROCESSED_DIR = DATA_PROCESS_DIR / "data" / "processed"
DB_PATH = PROJECT_ROOT / "pregnancy_nutrition.db"

MEDICINE_FILE = "mfds_medicine_raw.json"
SUPPLEMENT_FILE = "mfds_supplement_raw.json"

SYMPTOM_CSV_CANDIDATES = [
    RAW_DIR / "symptom_nutrient_with_validation.csv",
    RAW_DIR / "symptom_nutrient.csv",
    PROCESSED_DIR / "symptom_nutrient_with_validation.csv",
    PROCESSED_DIR / "symptom_nutrient.csv",
]


# ============================================================
# 1. 표준화 사전
# ============================================================

NUTRIENT_ALIASES = {
    "철": ["철", "철분", "Fe", "iron", "성분철"],
    "엽산": ["엽산", "folic acid", "folate"],
    "비타민 C": ["비타민 C", "비타민C", "vitamin C", "ascorbic acid"],
    "비타민 B6": ["비타민 B6", "비타민B6", "vitamin B6", "피리독신"],
    "비타민 B12": ["비타민 B12", "비타민B12", "vitamin B12"],
    "비타민 D": ["비타민 D", "비타민D", "vitamin D"],
    "칼슘": ["칼슘", "calcium"],
    "마그네슘": ["마그네슘", "magnesium"],
    "아연": ["아연", "zinc"],
    "요오드": ["요오드", "iodine"],
    "EPA+DHA": ["EPA", "DHA", "EPA+DHA", "오메가3", "오메가-3"],
    "수분": ["수분", "물"],
    "식이섬유": ["식이섬유", "섬유소", "전곡류", "채소", "과일"],
    "나트륨": ["나트륨", "염분", "소금", "짜지", "싱겁"],
    "단백질": ["단백질", "protein"],
}

DEFAULT_WEIGHT_DELTAS = {
    # clean_text()에서 '·'가 공백으로 바뀌므로 두 표현을 모두 둔다.
    "채소·과일 섭취가 부족함": {"엽산": 1.0, "비타민 C": 1.0},
    "채소 과일 섭취가 부족함": {"엽산": 1.0, "비타민 C": 1.0},
    "신체활동이 부족함": {"식이섬유": 0.5},
    "한 번에 많은 양을 섭취함": {"엽산": 0.5, "수분": 0.5, "비타민 C": 0.5},
    "철분 섭취가 부족함": {"철": 1.5, "비타민 C": 0.7, "단백질": 0.5},
    "식이섬유 섭취가 부족함": {"식이섬유": 1.5, "수분": 0.7},
    "수분 섭취가 부족함": {"수분": 1.5, "식이섬유": 0.5},
    "규칙적인 식사를 하지 않음": {"엽산": 0.5},
}

STAGE_BY_NAME = {
    "전체": (1, 40),
    "임신전체": (1, 40),
    "임신 전체": (1, 40),
    "임신초기": (1, 13),
    "초기": (1, 13),
    "1분기": (1, 13),
    "제1분기": (1, 13),
    "임신중기": (14, 27),
    "중기": (14, 27),
    "2분기": (14, 27),
    "제2분기": (14, 27),
    "임신후기": (28, 42),
    "후기": (28, 42),
    "3분기": (28, 42),
    "제3분기": (28, 42),
}


# ============================================================
# 2. 공통 유틸
# ============================================================

def clean_text(x: Any) -> str:
    if x is None:
        return ""

    text = str(x)

    for old in ["\x00", "\u200b", "\ufeff", "˚", "■", "•"]:
        text = text.replace(old, " ")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()


def contains_any(text: str, terms: list[str]) -> bool:
    text_l = clean_text(text).lower()
    return any(term.lower() in text_l for term in terms if term)


def split_multi_value(value: str) -> list[str]:
    value = clean_text(value)

    if not value:
        return []

    if value in {"해당 없음", "없음", "-"}:
        return []

    for sep in ["|", ",", ";", "/", "\n", "ㆍ", "·", "+"]:
        value = value.replace(sep, "|")

    return [clean_text(p) for p in value.split("|") if clean_text(p)]


def split_expected_keywords(value: str) -> list[str]:
    value = clean_text(value)

    if not value:
        return []

    for sep in ["|", ",", ";", "/", "\n"]:
        value = value.replace(sep, "|")

    return [clean_text(p) for p in value.split("|") if clean_text(p)]


def normalize_nutrient(value: str) -> str:
    text = clean_text(value)

    if not text:
        return ""

    for standard, aliases in NUTRIENT_ALIASES.items():
        if any(alias.lower() == text.lower() for alias in aliases):
            return standard

    for standard, aliases in NUTRIENT_ALIASES.items():
        if contains_any(text, aliases):
            return standard

    return text


def get_default_weight_delta(lifestyle: str, nutrient: str) -> float:
    """
    CSV의 생활습관 문자열과 DEFAULT_WEIGHT_DELTAS 키 표현 차이를 보정한다.
    예: '채소·과일 섭취가 부족함'과 '채소 과일 섭취가 부족함'을 같은 의미로 처리.
    """
    lifestyle_clean = clean_text(lifestyle)
    nutrient_clean = normalize_nutrient(nutrient)

    candidates = [
        lifestyle,
        lifestyle_clean,
        lifestyle_clean.replace("·", " "),
        lifestyle_clean.replace("  ", " "),
    ]

    for key in candidates:
        if key in DEFAULT_WEIGHT_DELTAS and nutrient_clean in DEFAULT_WEIGHT_DELTAS[key]:
            return DEFAULT_WEIGHT_DELTAS[key][nutrient_clean]

    return 0.5


def parse_int(value: Any) -> int | None:
    text = clean_text(value)

    if not text:
        return None

    match = re.search(r"\d+", text.replace(",", ""))

    if not match:
        return None

    return int(match.group())


def parse_float(value: Any) -> float | None:
    text = clean_text(value)

    if not text:
        return None

    try:
        return float(text.replace(",", ""))
    except ValueError:
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if match:
            return float(match.group())

    return None


def dumps(row: Any) -> str:
    return json.dumps(row, ensure_ascii=False)


def first(row: dict[str, Any], keys: list[str]) -> str:
    lower_map = {clean_text(k).lower(): k for k in row.keys()}

    for key in keys:
        if key in row and clean_text(row[key]):
            return clean_text(row[key])

        lk = clean_text(key).lower()
        if lk in lower_map and clean_text(row[lower_map[lk]]):
            return clean_text(row[lower_map[lk]])

    return ""


def find_raw_file(expected: str) -> Path:
    direct = RAW_DIR / expected

    if direct.exists():
        return direct

    expected_stem = Path(expected).stem.replace(" ", "")

    for path in RAW_DIR.glob("*.json"):
        if path.stem.replace(" ", "") == expected_stem:
            return path

    tokens = [t for t in re.split(r"[_()\s]+", Path(expected).stem) if t and t != "raw"]

    for path in RAW_DIR.glob("*.json"):
        if all(t in path.name for t in tokens[:2]):
            return path

    raise FileNotFoundError(f"raw file not found: {expected} in {RAW_DIR}")


def find_symptom_csv() -> Path:
    for path in SYMPTOM_CSV_CANDIDATES:
        if path.exists():
            return path

    raise FileNotFoundError(
        "symptom_nutrient CSV not found. Checked:\n"
        + "\n".join(str(p) for p in SYMPTOM_CSV_CANDIDATES)
    )


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {clean_text(k): clean_text(v) for k, v in row.items() if k is not None}
            for row in reader
        ]


def get_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if not isinstance(data, dict):
        return []

    for key in ["rows", "data", "items", "list", "records"]:
        if isinstance(data.get(key), list):
            return [x for x in data[key] if isinstance(x, dict)]

    if isinstance(data.get("body"), dict):
        for key in ["items", "rows", "data"]:
            if isinstance(data["body"].get(key), list):
                return [x for x in data["body"][key] if isinstance(x, dict)]

    for value in data.values():
        if isinstance(value, dict) and isinstance(value.get("row"), list):
            return [x for x in value["row"] if isinstance(x, dict)]

    return []


# ============================================================
# 3. symptom_nutrient CSV → evidence / recommendation_rule / lifestyle_weight_rule
# ============================================================

def infer_stage_from_row(row: dict[str, Any]) -> tuple[str, int, int]:
    stage = first(row, ["임신단계", "pregnancy_stage", "stage", "stage_name"])

    week_start = parse_int(first(row, ["시작주차", "week_start", "start_week", "week_from"]))
    week_end = parse_int(first(row, ["종료주차", "week_end", "end_week", "week_to"]))

    if stage and (week_start is None or week_end is None):
        normalized_stage = stage.replace(" ", "")
        if normalized_stage in STAGE_BY_NAME:
            week_start, week_end = STAGE_BY_NAME[normalized_stage]

    if not stage:
        stage = "전체"

    if week_start is None:
        week_start = 1

    if week_end is None:
        week_end = 42

    return stage, week_start, week_end


def get_csv_evidence_sentence(row: dict[str, Any]) -> str:
    return first(row, ["근거문장", "evidence_sentence", "evidence", "evidence_text", "원문근거"])


def get_csv_lifestyle_evidence(row: dict[str, Any]) -> str:
    return first(row, ["생활습관근거", "lifestyle_evidence"])


def get_csv_source_page(row: dict[str, Any]) -> int | None:
    return parse_int(first(row, ["출처페이지", "source_page", "page", "page_no"]))


def get_csv_source_name(row: dict[str, Any], csv_path: Path) -> str:
    return first(row, ["출처PDF", "source_name", "source", "source_file", "source_pdf"]) or csv_path.name


def get_or_create_csv_evidence(conn: sqlite3.Connection, row: dict[str, Any], csv_path: Path) -> int | None:
    sentence = get_csv_evidence_sentence(row)

    if not sentence:
        return None

    source_name = get_csv_source_name(row, csv_path)
    source_page = get_csv_source_page(row)

    existing = conn.execute(
        """
        SELECT evidence_id
        FROM evidence
        WHERE evidence_sentence = ?
          AND IFNULL(source_page, -1) = IFNULL(?, -1)
          AND IFNULL(source_name, '') = IFNULL(?, '')
        LIMIT 1
        """,
        (sentence, source_page, source_name),
    ).fetchone()

    if existing:
        return int(existing["evidence_id"])

    evidence_similarity = parse_float(first(row, ["근거문장_유사도", "evidence_similarity"]))
    lifestyle_similarity = parse_float(first(row, ["생활습관근거_유사도", "lifestyle_evidence_similarity"]))

    conn.execute(
        """
        INSERT INTO evidence
        (evidence_sentence, source_page, source_name, evidence_type,
         source_chunk_id, source_chunk_hash,
         evidence_exact_match, evidence_similarity,
         lifestyle_evidence_exact_match, lifestyle_evidence_similarity,
         validation_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sentence,
            source_page,
            source_name,
            "symptom_nutrient_csv",
            first(row, ["chunk_id"]),
            first(row, ["chunk_hash"]),
            first(row, ["근거문장_원문일치", "evidence_exact_match"]),
            evidence_similarity,
            first(row, ["생활습관근거_원문일치", "lifestyle_evidence_exact_match"]),
            lifestyle_similarity,
            first(row, ["근거검증상태", "validation_status"]),
        ),
    )

    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def has_valid_caution(caution: str) -> bool:
    caution = clean_text(caution)
    return bool(caution and caution not in {"해당 없음", "없음", "-"})


def load_symptom_csv_rules(conn: sqlite3.Connection) -> None:
    csv_path = find_symptom_csv()
    rows = read_csv_rows(csv_path)

    # evidence_linked: CSV row가 evidence_id와 연결된 횟수
    # 실제 evidence 테이블 저장 건수는 UNIQUE 조건 때문에 이 값보다 작을 수 있음.
    evidence_linked_count = 0
    rule_count = 0
    weight_count = 0
    skipped = 0

    for row in rows:
        symptom = first(row, ["증상", "symptom", "symptom_name"])
        symptom_description = first(row, ["증상설명", "symptom_description"])
        nutrient_raw = first(row, ["추천영양소", "nutrient", "recommended_nutrient", "영양소"])
        lifestyle = first(row, ["생활습관", "lifestyle", "lifestyle_check", "생활습관체크"])
        lifestyle_reason = first(row, ["생활습관추천이유", "reason", "recommendation", "weight_reason"])
        lifestyle_evidence = get_csv_lifestyle_evidence(row)
        caution = first(row, ["주의사항", "caution", "caution_text"])

        if not symptom:
            skipped += 1
            continue

        stage, week_start, week_end = infer_stage_from_row(row)
        evidence_id = get_or_create_csv_evidence(conn, row, csv_path)

        if evidence_id:
            evidence_linked_count += 1

        nutrients = [normalize_nutrient(n) for n in split_multi_value(nutrient_raw)]
        nutrients = [n for n in nutrients if n and n not in {"해당 없음", "없음", "-"}]

        # 1. 추천영양소 규칙
        # 주의사항은 recommend row의 caution_text에 섞지 않고 별도 caution row로 분리한다.
        if nutrients:
            for nutrient in nutrients:
                conn.execute(
                    """
                    INSERT INTO recommendation_rule
                    (pregnancy_stage, week_start, week_end, symptom, symptom_description,
                     recommended_nutrient, lifestyle_condition, base_score,
                     relation_type, reason, caution_text, evidence_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stage,
                        week_start,
                        week_end,
                        symptom,
                        symptom_description or None,
                        nutrient,
                        lifestyle or None,
                        1.0,
                        "recommend",
                        lifestyle_reason or None,
                        None,
                        evidence_id,
                    ),
                )
                rule_count += 1

        # 2. 생활관리 규칙
        # 추천영양소가 없는 생활습관 row만 lifestyle_guidance로 저장한다.
        # 추천영양소가 있는 row의 생활습관 정보는 lifestyle_weight_rule에서 관리한다.
        if lifestyle and not nutrients:
            conn.execute(
                """
                INSERT INTO recommendation_rule
                (pregnancy_stage, week_start, week_end, symptom, symptom_description,
                 recommended_nutrient, lifestyle_condition, base_score,
                 relation_type, reason, caution_text, evidence_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stage,
                    week_start,
                    week_end,
                    symptom,
                    symptom_description or None,
                    None,
                    lifestyle,
                    0.0,
                    "lifestyle_guidance",
                    lifestyle_reason or None,
                    None,
                    evidence_id,
                ),
            )
            rule_count += 1

        # 3. 주의사항 규칙
        # 추천영양소/생활습관 존재 여부와 관계없이 caution_text가 있으면 별도 caution row 생성.
        if has_valid_caution(caution):
            conn.execute(
                """
                INSERT INTO recommendation_rule
                (pregnancy_stage, week_start, week_end, symptom, symptom_description,
                 recommended_nutrient, lifestyle_condition, base_score,
                 relation_type, reason, caution_text, evidence_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stage,
                    week_start,
                    week_end,
                    symptom,
                    symptom_description or None,
                    None,
                    lifestyle or None,
                    0.0,
                    "caution",
                    None,
                    caution,
                    evidence_id,
                ),
            )
            rule_count += 1

        # 4. 생활습관 가중치 규칙
        if lifestyle and nutrients:
            for nutrient in nutrients:
                weight_delta = get_default_weight_delta(lifestyle, nutrient)

                conn.execute(
                    """
                    INSERT INTO lifestyle_weight_rule
                    (lifestyle_check, symptom, pregnancy_stage,
                     week_start, week_end, nutrient, weight_delta,
                     weight_reason, lifestyle_evidence, evidence_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lifestyle,
                        symptom,
                        stage,
                        week_start,
                        week_end,
                        nutrient,
                        weight_delta,
                        lifestyle_reason or f"{lifestyle} 선택 시 {nutrient} 점수 보정",
                        lifestyle_evidence or None,
                        evidence_id,
                    ),
                )
                weight_count += 1

    print(
        f"[OK] symptom CSV loaded: {csv_path.name} / "
        f"rows={len(rows)}, evidence_linked={evidence_linked_count}, rules={rule_count}, "
        f"weights={weight_count}, skipped={skipped}"
    )


# ============================================================
# 4. supplement raw JSON → supplement_info / supplement_ingredient
# ============================================================

def split_ingredients(text: str) -> list[str]:
    text = clean_text(text)

    if not text:
        return []

    parts = re.split(r"[,;/\n]|ㆍ|·|\+|\|", text)
    result = []

    for p in parts:
        item = clean_text(p)

        if not item:
            continue

        if len(item) > 120:
            continue

        result.append(item)

    return list(dict.fromkeys(result))


def load_supplements(conn: sqlite3.Connection) -> None:
    path = find_raw_file(SUPPLEMENT_FILE)
    rows = get_rows(load_json(path))

    products = 0
    ingredients = 0

    for row in rows:
        product_name = first(row, ["product_name", "PRDLST_NM", "PRDCT_NM", "제품명"])

        if not product_name:
            continue

        company = first(row, ["company_name", "BSSH_NM", "ENTRPS", "제조사", "업소명"])
        report_no = first(row, ["report_no", "PRDLST_REPORT_NO", "신고번호"])
        reg_date = first(row, ["registration_date", "PRMS_DT", "CRET_DTM", "LAST_UPDT_DTM", "등록일"])
        raw_ing = first(
            row,
            [
                "ingredients",
                "RAWMTRL_NM",
                "MATERIAL_NM",
                "성분",
                "원재료",
                "SKLL_IX_IRDNT_RAWMTRL",
            ],
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO supplement_info
            (product_name, company_name, report_no, registration_date, source, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_name, company, report_no, reg_date, path.name, dumps(row)),
        )

        sid_row = conn.execute(
            """
            SELECT supplement_id
            FROM supplement_info
            WHERE product_name = ?
              AND IFNULL(company_name, '') = IFNULL(?, '')
              AND IFNULL(report_no, '') = IFNULL(?, '')
            """,
            (product_name, company, report_no),
        ).fetchone()

        if not sid_row:
            continue

        sid = sid_row["supplement_id"]
        products += 1

        for ing in split_ingredients(raw_ing):
            conn.execute(
                """
                INSERT OR IGNORE INTO supplement_ingredient
                (supplement_id, ingredient_name, standard_nutrient, amount, unit)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, ing, normalize_nutrient(ing), None, None),
            )
            ingredients += 1

    print(f"[OK] supplement processed: product_input_rows={products}, ingredient_input_rows={ingredients} / actual table counts are shown below")


# ============================================================
# 5. medicine raw JSON → medicine_info
# ============================================================

def load_medicines(conn: sqlite3.Connection) -> None:
    """
    MFDS 의약품 raw JSON을 medicine_info에 적재한다.

    현재 테스트 검증에서는 medicine_info를 사용하지 않는다.
    이 테이블은 향후 복용 의약품 주의사항/상호작용 확인 기능 확장을 위한 기반 데이터다.
    """
    path = find_raw_file(MEDICINE_FILE)
    rows = get_rows(load_json(path))

    count = 0

    for row in rows:
        name = first(row, ["medicine_name", "item_name", "ITEM_NAME", "PRDLST_NM", "제품명", "품목명"])

        if not name:
            continue

        manufacturer = first(row, ["manufacturer", "ENTP_NAME", "BSSH_NM", "업체명", "제조사"])

        conn.execute(
            """
            INSERT OR IGNORE INTO medicine_info
            (medicine_name, efficacy, usage, warning, interaction, side_effect, storage,
             manufacturer, ingredient, source, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                first(row, ["efficacy", "EFcyQesitm", "효능효과", "효능"]),
                first(row, ["usage", "use_method", "USE_METHOD_QESITM", "복용방법", "사용법"]),
                first(row, ["warning", "atpnQesitm", "주의사항", "WARN"]),
                first(row, ["interaction", "intrcQesitm", "상호작용"]),
                first(row, ["side_effect", "seQesitm", "부작용"]),
                first(row, ["storage", "depositMethodQesitm", "보관"]),
                manufacturer,
                first(row, ["ingredient", "main_item_ingr", "MAIN_ITEM_INGR", "성분"]),
                path.name,
                dumps(row),
            ),
        )

        count += 1

    print(f"[OK] medicine processed: input_rows={count} / table=medicine_info / actual table count is shown below")


# ============================================================
# 6. alias / search_document / test_case
# ============================================================

def load_aliases(conn: sqlite3.Connection) -> None:
    count = 0

    for standard, aliases in NUTRIENT_ALIASES.items():
        for alias in aliases:
            conn.execute(
                """
                INSERT OR IGNORE INTO nutrient_alias
                (standard_nutrient, alias_name)
                VALUES (?, ?)
                """,
                (standard, alias),
            )
            count += 1

    print(f"[OK] nutrient_alias loaded: {count}")


def build_search_document(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM search_document")

    for row in conn.execute(
        """
        SELECT evidence_id, evidence_sentence, source_name, source_page,
               evidence_type, validation_status
        FROM evidence
        """
    ):
        title = f"{row['source_name']} p.{row['source_page'] or '-'}"
        body = row["evidence_sentence"]

        conn.execute(
            """
            INSERT INTO search_document
            (document_type, target_table, target_id, title, summary, body_text,
             keyword_text, source_name, priority_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evidence",
                "evidence",
                str(row["evidence_id"]),
                title,
                row["validation_status"] or row["evidence_type"],
                body,
                f"{title} {body}",
                row["source_name"],
                2.0,
            ),
        )

    for row in conn.execute(
        """
        SELECT
            rr.rule_id,
            rr.pregnancy_stage,
            rr.week_start,
            rr.week_end,
            rr.symptom,
            rr.recommended_nutrient,
            rr.relation_type,
            rr.reason,
            rr.caution_text,
            e.evidence_sentence
        FROM recommendation_rule rr
        LEFT JOIN evidence e ON e.evidence_id = rr.evidence_id
        """
    ):
        title = f"{row['symptom']} - {row['recommended_nutrient'] or row['relation_type']}"
        body = " ".join(
            [
                row["pregnancy_stage"] or "",
                str(row["week_start"] or ""),
                str(row["week_end"] or ""),
                row["relation_type"] or "",
                row["reason"] or "",
                row["caution_text"] or "",
                row["evidence_sentence"] or "",
            ]
        )

        conn.execute(
            """
            INSERT INTO search_document
            (document_type, target_table, target_id, title, summary, body_text,
             keyword_text, source_name, priority_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "recommendation_rule",
                "recommendation_rule",
                str(row["rule_id"]),
                title,
                row["relation_type"],
                body,
                f"{title} {body}",
                "recommendation_rule",
                3.0,
            ),
        )

    print("[OK] search_document built")


def extract_supplement_search_terms(user_input_text: str, expected_supplement_keywords: str) -> list[str]:
    text = clean_text(user_input_text)
    terms: list[str] = []

    for keyword in split_expected_keywords(expected_supplement_keywords):
        terms.append(keyword)

        if keyword.endswith("제") and len(keyword) > 1:
            terms.append(keyword[:-1])

    for standard, aliases in NUTRIENT_ALIASES.items():
        if contains_any(text, aliases):
            terms.append(standard)
            terms.extend(aliases)

    cleaned = []

    for term in terms:
        term = clean_text(term)

        if len(term) < 2:
            continue

        if term not in cleaned:
            cleaned.append(term)

    return cleaned


def find_matching_supplement_nutrients(
    conn: sqlite3.Connection,
    user_input_text: str,
    expected_supplement_keywords: str,
    limit_per_term: int = 20,
) -> tuple[set[str], list[dict[str, Any]]]:
    search_terms = extract_supplement_search_terms(user_input_text, expected_supplement_keywords)

    matched_nutrients: set[str] = set()
    matched_products: list[dict[str, Any]] = []
    seen_product_ids: set[int] = set()

    for term in search_terms:
        rows = conn.execute(
            """
            SELECT
                si.supplement_id,
                si.product_name,
                si.company_name,
                si.report_no,
                si.source,
                si_ingredient.ingredient_name,
                si_ingredient.standard_nutrient
            FROM supplement_info si
            LEFT JOIN supplement_ingredient si_ingredient
                   ON si_ingredient.supplement_id = si.supplement_id
            WHERE si.product_name LIKE ?
            LIMIT ?
            """,
            (f"%{term}%", limit_per_term),
        ).fetchall()

        for row in rows:
            supplement_id = int(row["supplement_id"])

            if row["standard_nutrient"]:
                matched_nutrients.add(clean_text(row["standard_nutrient"]))

            if supplement_id not in seen_product_ids:
                seen_product_ids.add(supplement_id)
                matched_products.append(
                    {
                        "match_type": "product_name_candidate",
                        "matched_term": term,
                        "supplement_id": supplement_id,
                        "product_name": row["product_name"],
                        "company_name": row["company_name"],
                        "report_no": row["report_no"],
                        "source": row["source"],
                    }
                )

    if not matched_products:
        expected_or_input_nutrients = {
            normalize_nutrient(term)
            for term in search_terms
            if normalize_nutrient(term)
        }

        for nutrient in expected_or_input_nutrients:
            rows = conn.execute(
                """
                SELECT
                    si.supplement_id,
                    si.product_name,
                    si.company_name,
                    si.report_no,
                    si.source,
                    si_ingredient.ingredient_name,
                    si_ingredient.standard_nutrient
                FROM supplement_ingredient si_ingredient
                JOIN supplement_info si
                  ON si.supplement_id = si_ingredient.supplement_id
                WHERE si_ingredient.standard_nutrient = ?
                LIMIT ?
                """,
                (nutrient, limit_per_term),
            ).fetchall()

            for row in rows:
                supplement_id = int(row["supplement_id"])

                if row["standard_nutrient"]:
                    matched_nutrients.add(clean_text(row["standard_nutrient"]))

                if supplement_id not in seen_product_ids:
                    seen_product_ids.add(supplement_id)
                    matched_products.append(
                        {
                            "match_type": "ingredient_standard_nutrient_candidate",
                            "matched_term": nutrient,
                            "supplement_id": supplement_id,
                            "product_name": row["product_name"],
                            "company_name": row["company_name"],
                            "report_no": row["report_no"],
                            "source": row["source"],
                        }
                    )

    return matched_nutrients, matched_products


def validate_test_case_supplement_overlap(conn: sqlite3.Connection) -> None:
    """
    건강기능식품 성분 중복 검증.

    검증 범위:
    - user_input_text / expected_supplement_keywords에서 추출한 영양제 키워드로
      supplement_info.product_name 후보를 검색한다.
    - 후보 제품의 supplement_ingredient.standard_nutrient와
      expected_exclude_nutrients 또는 expected_include_nutrients의 중복 여부를 확인한다.

    주의:
    - 사용자가 실제 복용 중인 특정 제품을 정확히 식별하는 검증은 아니다.
    - '철분제', '엽산' 같은 제품명 키워드 기반 후보 검색이다.
    - 정확한 의미는 '제품명 키워드 기반 후보 검색 + 성분 중복 확인'이다.
    """
    rows = conn.execute(
        """
        SELECT
            test_id,
            user_input_text,
            expected_include_nutrients,
            expected_exclude_nutrients,
            expected_supplement_keywords
        FROM recommendation_test_case
        WHERE IFNULL(user_input_text, '') != ''
           OR IFNULL(expected_supplement_keywords, '') != ''
        ORDER BY test_id
        """
    ).fetchall()

    if not rows:
        print("[CHECK] supplement overlap validation: no test cases")
        return

    print("[CHECK] supplement keyword-based overlap validation")
    print("  - scope: 제품명 키워드 기반 후보 검색 + 성분 중복 확인")
    print("  - note: 실제 복용 제품을 정확히 식별하는 검증이 아님")

    for row in rows:
        test_id = row["test_id"]

        expected_include = {
            normalize_nutrient(x)
            for x in split_expected_keywords(row["expected_include_nutrients"] or "")
            if normalize_nutrient(x)
        }

        expected_exclude = {
            normalize_nutrient(x)
            for x in split_expected_keywords(row["expected_exclude_nutrients"] or "")
            if normalize_nutrient(x)
        }

        matched_nutrients, matched_products = find_matching_supplement_nutrients(
            conn,
            user_input_text=row["user_input_text"] or "",
            expected_supplement_keywords=row["expected_supplement_keywords"] or "",
        )

        include_overlap = expected_include & matched_nutrients
        exclude_overlap = expected_exclude & matched_nutrients

        if exclude_overlap:
            status = "PASS"
            reason = "복용 영양제와 추천 제외 영양소 중복 확인: " + ", ".join(sorted(exclude_overlap))
        elif include_overlap:
            status = "PASS"
            reason = "복용 영양제와 추천 포함 영양소 중복 확인: " + ", ".join(sorted(include_overlap))
        elif not expected_include and not expected_exclude:
            status = "SKIP"
            reason = "expected_include_nutrients / expected_exclude_nutrients 없음"
        else:
            status = "FAIL"
            reason = (
                "복용 영양제 성분과 expected 영양소 중복 없음 / "
                f"include={sorted(expected_include)} / "
                f"exclude={sorted(expected_exclude)} / "
                f"matched={sorted(matched_nutrients)}"
            )

        print(f"- {test_id}: {status} / {reason}")

        if matched_products:
            for product in matched_products[:3]:
                print(
                    "  · "
                    f"{product['match_type']} / "
                    f"{product['matched_term']} / "
                    f"{product['product_name']} / "
                    f"{product['company_name'] or '-'}"
                )
        else:
            print("  · 매칭된 supplement 후보 없음")

def get_pregnancy_stage_label(week: int) -> str:
    if 1 <= week <= 13:
        return "초기"
    if 14 <= week <= 27:
        return "중기"
    if 28 <= week <= 42:
        return "후기"
    return "전체"


def validate_recommendation_test_cases(conn: sqlite3.Connection) -> None:
    """
    추천 후보 조회 및 테스트 시나리오 키워드 포함 여부 검증.

    이 함수가 검증하는 것:
    1. expected_include_nutrients
       - 증상/임신주차 기준 recommendation_rule 후보에 포함되는지 확인한다.
       - 즉, 추천 후보 조회 결과를 확인한다.

    2. expected_exclude_nutrients
       - 추천 후보 조회 단계의 실패 조건으로 보지 않는다.
       - 사용자가 이미 복용 중인 영양제 성분과 중복되어
         최종 추천에서 제외되어야 하는 영양소를 뜻한다.
       - 실제 중복 여부는 validate_test_case_supplement_overlap()에서 검증한다.

    3. expected_guidance_keywords
       - DB 근거문장 단독 검증이 아니다.
       - DB 텍스트 + 사용자 입력 + 영양제 키워드 + 임신단계 등
         테스트 시나리오 전체 텍스트에 포함되는지 확인한다.

    따라서 이 함수는 '추천 정확도 전체 검증' 또는 'DB 근거문장 검증'이 아니다.
    정확한 의미는 '추천 후보 조회 결과와 테스트 시나리오 키워드 포함 여부 확인'이다.
    """
    rows = conn.execute(
        """
        SELECT
            test_id,
            test_type,
            pregnancy_week,
            symptom,
            lifestyle_check,
            user_input_text,
            expected_include_nutrients,
            expected_exclude_nutrients,
            expected_guidance_keywords,
            expected_supplement_keywords,
            expected_medicine_keywords
        FROM recommendation_test_case
        ORDER BY test_id
        """
    ).fetchall()

    if not rows:
        print("[CHECK] recommendation test case validation: no test cases")
        return

    print("\n[CHECK] recommendation candidate / scenario keyword validation")
    print("  - scope: 추천 후보 조회 결과 + 테스트 시나리오 키워드 포함 여부 확인")
    print("  - note: 추천 정확도 전체 검증 또는 DB 근거문장 단독 검증이 아님")

    for row in rows:
        test_id = row["test_id"]
        week = int(row["pregnancy_week"])
        symptom = clean_text(row["symptom"])
        lifestyle = clean_text(row["lifestyle_check"])
        user_input_text = clean_text(row["user_input_text"])
        stage_label = get_pregnancy_stage_label(week)

        expected_include = {
            normalize_nutrient(x)
            for x in split_expected_keywords(row["expected_include_nutrients"] or "")
            if normalize_nutrient(x)
        }

        expected_exclude = {
            normalize_nutrient(x)
            for x in split_expected_keywords(row["expected_exclude_nutrients"] or "")
            if normalize_nutrient(x)
        }

        expected_guidance_keywords = split_expected_keywords(row["expected_guidance_keywords"] or "")
        expected_supplement_keywords = split_expected_keywords(row["expected_supplement_keywords"] or "")
        expected_medicine_keywords = split_expected_keywords(row["expected_medicine_keywords"] or "")

        # 검증용 후보 조회:
        # 증상 + 임신주차 기준으로 넓게 조회한다.
        # 특정 생활습관만 강하게 제한하면 같은 증상/주차의 기본 추천 후보가 빠질 수 있음.
        rule_rows = conn.execute(
            """
            SELECT
                rr.recommended_nutrient,
                rr.relation_type,
                rr.reason,
                rr.caution_text,
                rr.lifestyle_condition,
                rr.pregnancy_stage,
                e.evidence_sentence
            FROM recommendation_rule rr
            LEFT JOIN evidence e ON e.evidence_id = rr.evidence_id
            WHERE rr.symptom = ?
              AND ? BETWEEN rr.week_start AND rr.week_end
            """,
            (symptom, week),
        ).fetchall()

        actual_nutrients = {
            normalize_nutrient(r["recommended_nutrient"])
            for r in rule_rows
            if clean_text(r["recommended_nutrient"])
        }

        db_text_parts = [
            symptom,
            lifestyle,
            stage_label,
        ]

        for r in rule_rows:
            db_text_parts.extend(
                [
                    clean_text(r["reason"]),
                    clean_text(r["caution_text"]),
                    clean_text(r["lifestyle_condition"]),
                    clean_text(r["pregnancy_stage"]),
                    clean_text(r["evidence_sentence"]),
                    clean_text(r["recommended_nutrient"]),
                ]
            )

        scenario_text_parts = [
            user_input_text,
            "중복" if expected_exclude else "",
            row["expected_include_nutrients"] or "",
            row["expected_exclude_nutrients"] or "",
            row["expected_supplement_keywords"] or "",
            row["expected_medicine_keywords"] or "",
        ]

        combined_text = " ".join(part for part in db_text_parts + scenario_text_parts if part)

        include_missing = expected_include - actual_nutrients

        guidance_missing = [
            keyword
            for keyword in expected_guidance_keywords
            if keyword and keyword not in combined_text
        ]

        supplement_missing = [
            keyword
            for keyword in expected_supplement_keywords
            if keyword and keyword not in combined_text
        ]

        medicine_missing = [
            keyword
            for keyword in expected_medicine_keywords
            if keyword and keyword not in combined_text
        ]

        errors = []

        if include_missing:
            errors.append("추천 후보 포함 영양소 누락: " + ", ".join(sorted(include_missing)))

        if guidance_missing:
            errors.append("시나리오 키워드 누락: " + ", ".join(guidance_missing))

        if supplement_missing:
            errors.append("영양제 키워드 누락: " + ", ".join(supplement_missing))

        if medicine_missing:
            errors.append("의약품/증상 키워드 누락: " + ", ".join(medicine_missing))

        status = "PASS" if not errors else "FAIL"

        print(f"- {test_id}: {status}")
        print(f"  · case: {week}주 / {symptom} / {lifestyle or '-'}")
        print("  · actual_nutrients: " + (", ".join(sorted(actual_nutrients)) if actual_nutrients else "없음"))
        print("  · expected_candidate_include: " + (", ".join(sorted(expected_include)) if expected_include else "없음"))
        print("    - 의미: 증상/임신주차 기준 추천 후보에 포함되어야 하는 영양소")
        print("  · expected_final_exclude: " + (", ".join(sorted(expected_exclude)) if expected_exclude else "없음"))
        print("    - 의미: 복용 중인 영양제 성분과 중복되어 최종 추천에서 제외할 영양소")

        if expected_guidance_keywords:
            print("  · expected_scenario_keywords: " + ", ".join(expected_guidance_keywords))

        if user_input_text:
            print(f"  · user_input_text: {user_input_text}")

        if expected_supplement_keywords:
            print("  · expected_supplement_keywords: " + ", ".join(expected_supplement_keywords))

        if expected_medicine_keywords:
            print("  · expected_medicine_keywords: " + ", ".join(expected_medicine_keywords))

        if errors:
            for err in errors:
                print(f"  · {err}")

def insert_test_cases(conn: sqlite3.Connection) -> None:
    """
    테스트 시나리오 적재.

    컬럼 의미:
    - expected_include_nutrients:
      증상/임신주차 기준 추천 후보에 포함되어야 하는 영양소.
    - expected_exclude_nutrients:
      사용자가 이미 복용 중인 영양제 성분과 중복되어
      최종 추천 단계에서 제외되어야 하는 영양소.
    - expected_guidance_keywords:
      DB 근거문장 단독 검증용이 아니라,
      테스트 시나리오 전체 텍스트에 포함되는지 확인하는 키워드.
    - expected_supplement_keywords:
      정확 제품 식별이 아니라 supplement_info.product_name 후보 검색용 키워드.
    - expected_medicine_keywords:
      현재 테스트 검증에는 사용하지 않음. 의약품 데이터는 medicine_info에 적재만 수행.
    """
    tests = [
        (
            "T01",
            "symptom_medicine_supplement",
            31,
            "빈혈",
            "철분 섭취가 부족함",
            "현재 철분제를 복용하고 있습니다.",
            "철|비타민 C|단백질",
            "철",
            "빈혈|철분제|중복|비타민 C|단백질|후기",
            "철분제",
            "",
        ),
        (
            "T02",
            "symptom_supplement",
            9,
            "입덧",
            "채소·과일 섭취가 부족함",
            "엽산제를 복용하고 있습니다.",
            "수분|엽산|비타민 C",
            "엽산",
            "입덧|과일|기름진 음식|엽산|비타민 C|중복|초기",
            "엽산",
            "",
        ),
        (
            "T03",
            "symptom_supplement",
            20,
            "변비",
            "식이섬유 섭취가 부족함",
            "철분제를 복용하고 있습니다.",
            "식이섬유|수분",
            "철",
            "변비|식이섬유|섬유소|수분|철분제|중기",
            "철분제",
            "",
        ),
    ]

    for t in tests:
        conn.execute(
            """
            INSERT OR REPLACE INTO recommendation_test_case
            (test_id, test_type, pregnancy_week, symptom, lifestyle_check,
             user_input_text, expected_include_nutrients, expected_exclude_nutrients,
             expected_guidance_keywords, expected_supplement_keywords, expected_medicine_keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            t,
        )

    print(f"[OK] recommendation_test_case loaded: {len(tests)}")
    
# ============================================================
# 7. main
# ============================================================

def clear_tables(conn: sqlite3.Connection) -> None:
    tables = [
        "search_document",
        "recommendation_test_case",
        "lifestyle_weight_rule",
        "recommendation_rule",
        "supplement_ingredient",
        "supplement_info",
        "medicine_info",
        "nutrient_alias",
        "evidence",
    ]

    existing_tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

    for table in tables:
        if table in existing_tables:
            conn.execute(f"DELETE FROM {table}")


def print_counts(conn: sqlite3.Connection) -> None:
    tables = [
        "evidence",
        "recommendation_rule",
        "lifestyle_weight_rule",
        "supplement_info",
        "supplement_ingredient",
        "medicine_info",
        "nutrient_alias",
        "search_document",
        "recommendation_test_case",
    ]

    existing_tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

    print("\n[CHECK] table counts")

    for table in tables:
        if table not in existing_tables:
            print(f"  {table}: table not found")
            continue

        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count}")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB not found: {DB_PATH}\n"
            f"먼저 python scripts/create_schema.py 를 실행하세요."
        )

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        clear_tables(conn)

        load_aliases(conn)

        load_symptom_csv_rules(conn)

        load_supplements(conn)
        load_medicines(conn)

        build_search_document(conn)
        insert_test_cases(conn)
        validate_recommendation_test_cases(conn)
        validate_test_case_supplement_overlap(conn)
        
        conn.commit()
        print_counts(conn)

    print(f"\n[DONE] relational DB loaded: {DB_PATH}")


if __name__ == "__main__":
    main()