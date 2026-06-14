import os
import re
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed"

DB_DATASETS = {
    "symptom_nutrient": "symptom_nutrient.csv",
    "medicine_info": "medicine_info.csv",
    "supplement_info": "supplement_info.csv",
}

DB_CANDIDATES = [
    Path(os.environ.get("PREGNANCY_NUTRITION_DB", "")) if os.environ.get("PREGNANCY_NUTRITION_DB") else None,
    BASE_DIR / "pregnancy_nutrition.db",
    BASE_DIR / "data" / "pregnancy_nutrition.db",
    BASE_DIR / "data" / "processed" / "pregnancy_nutrition.db",
]

FIXED_PUBLIC_SOURCES = [
    "국가건강정보포털(질병관리청)_정상임신관리(임신의 진단과 관리)",
    "국가건강정보포털(질병관리청)_식이영양(임산부)",
    "공공데이터포털(MFDS)_의약품개요정보(e약은요)",
    "공공데이터포털(MFDS)_의약품 제품 허가정보",
    "공공데이터포털(MFDS)_건강기능식품 품목제조 신고사항 현황",
]


def get_db_path() -> Path | None:
    """추천엔진에서 사용할 SQLite DB 경로를 찾는다.

    우선순위
    1) 환경변수 PREGNANCY_NUTRITION_DB
    2) 프로젝트 루트/pregnancy_nutrition.db
    3) 프로젝트 루트/data/pregnancy_nutrition.db
    4) 프로젝트 루트/data/processed/pregnancy_nutrition.db
    5) Colab/ChatGPT 작업 경로 /mnt/data/pregnancy_nutrition(6).db
    """
    for path in DB_CANDIDATES:
        if path and str(path) and Path(path).exists():
            return Path(path)
    return None


def _connect() -> sqlite3.Connection:
    db_path = get_db_path()
    if not db_path:
        raise FileNotFoundError(
            "pregnancy_nutrition.db를 찾을 수 없습니다. "
            "프로젝트 루트 또는 data/ 폴더에 DB를 두거나 "
            "PREGNANCY_NUTRITION_DB 환경변수로 경로를 지정하세요."
        )
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def db_available() -> bool:
    return get_db_path() is not None


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


@lru_cache(maxsize=None)
def _load_symptom_from_db() -> pd.DataFrame:
    """DB의 추천 규칙/생활습관 가중치/근거를 기존 symptom_nutrient.csv 형태로 변환."""
    with _connect() as con:
        rule_sql = """
        SELECT
            rr.rule_id AS row_id,
            rr.pregnancy_stage AS 임신단계,
            rr.week_start AS 시작주차,
            rr.week_end AS 종료주차,
            rr.symptom AS 증상,
            '' AS 증상설명,
            rr.recommended_nutrient AS 추천영양소,
            COALESCE(rr.lifestyle_condition, '') AS 생활습관,
            '' AS 생활습관추천이유,
            '' AS 생활습관근거,
            '' AS 주의사항,
            COALESCE(e.evidence_sentence, '') AS 근거문장,
            COALESCE(e.source_page, '') AS 출처페이지,
            COALESCE(e.source_name, '') AS 출처PDF,
            COALESCE(rr.base_score, 1.0) AS base_score,
            0.0 AS weight_delta,
            'recommendation_rule' AS rule_source
        FROM recommendation_rule rr
        LEFT JOIN evidence e ON rr.evidence_id = e.evidence_id
        WHERE COALESCE(rr.relation_type, 'recommend') = 'recommend'
        """
        weight_sql = """
        SELECT
            lw.weight_rule_id AS row_id,
            lw.pregnancy_stage AS 임신단계,
            lw.week_start AS 시작주차,
            lw.week_end AS 종료주차,
            lw.symptom AS 증상,
            '' AS 증상설명,
            lw.nutrient AS 추천영양소,
            COALESCE(lw.lifestyle_check, '') AS 생활습관,
            COALESCE(lw.weight_reason, '') AS 생활습관추천이유,
            COALESCE(e.evidence_sentence, '') AS 생활습관근거,
            '' AS 주의사항,
            COALESCE(e.evidence_sentence, '') AS 근거문장,
            COALESCE(e.source_page, '') AS 출처페이지,
            COALESCE(e.source_name, '') AS 출처PDF,
            0.0 AS base_score,
            COALESCE(lw.weight_delta, 0.0) AS weight_delta,
            'lifestyle_weight_rule' AS rule_source
        FROM lifestyle_weight_rule lw
        LEFT JOIN evidence e ON lw.evidence_id = e.evidence_id
        """
        df_rule = pd.read_sql_query(rule_sql, con)
        df_weight = pd.read_sql_query(weight_sql, con)
    df = pd.concat([df_rule, df_weight], ignore_index=True)
    return _clean_df(df)


@lru_cache(maxsize=None)
def _load_supplement_from_db() -> pd.DataFrame:
    """DB의 supplement_info + supplement_ingredient를 기존 supplement_info.csv 형태로 변환."""
    with _connect() as con:
        sql = """
        SELECT
            s.supplement_id AS supplement_id,
            s.product_name AS 제품명,
            s.company_name AS 제조사,
            s.report_no AS 신고번호,
            s.registration_date AS 등록일자,
            GROUP_CONCAT(DISTINCT COALESCE(si.standard_nutrient, si.ingredient_name)) AS 성분,
            GROUP_CONCAT(DISTINCT si.ingredient_name) AS 원재료,
            s.source AS source
        FROM supplement_info s
        LEFT JOIN supplement_ingredient si ON s.supplement_id = si.supplement_id
        GROUP BY s.supplement_id, s.product_name, s.company_name, s.report_no, s.registration_date, s.source
        """
        df = pd.read_sql_query(sql, con)
    return _clean_df(df)


@lru_cache(maxsize=None)
def _load_medicine_from_db() -> pd.DataFrame:
    """DB의 medicine_info를 기존 medicine_info.csv 형태로 변환."""
    with _connect() as con:
        sql = """
        SELECT
            medicine_id,
            medicine_name AS 의약품명,
            efficacy AS 효능효과,
            usage AS 용법용량,
            warning AS 주의사항,
            interaction AS 상호작용,
            side_effect AS 부작용,
            storage AS 보관방법,
            manufacturer AS 제조사,
            ingredient AS 성분,
            source
        FROM medicine_info
        """
        df = pd.read_sql_query(sql, con)
    return _clean_df(df)


@lru_cache(maxsize=None)
def load_table(name: str) -> pd.DataFrame:

    if name not in DB_DATASETS:
        raise KeyError(f"지원하지 않는 데이터 이름입니다: {name}")

    if db_available():
        if name == "symptom_nutrient":
            return _load_symptom_from_db().copy()
        if name == "supplement_info":
            return _load_supplement_from_db().copy()
        if name == "medicine_info":
            return _load_medicine_from_db().copy()

    path = DATA_DIR / DB_DATASETS[name]
    if not path.exists():
        raise FileNotFoundError(f"DB와 CSV 파일을 모두 찾을 수 없습니다: {name}, {path}")
    return _clean_df(pd.read_csv(path, dtype=str))


@lru_cache(maxsize=None)
def load_nutrient_alias_map() -> dict[str, set[str]]:

    alias_map: dict[str, set[str]] = {}
    if db_available():
        try:
            with _connect() as con:
                rows = con.execute("SELECT standard_nutrient, alias_name FROM nutrient_alias").fetchall()
            for row in rows:
                std = str(row["standard_nutrient"] or "").strip()
                alias = str(row["alias_name"] or "").strip()
                if not std:
                    continue
                alias_map.setdefault(std, set()).add(std)
                if alias:
                    alias_map[std].add(alias)
        except Exception:
            pass
    return alias_map


def norm(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower().strip()


def contains_match(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    return na in nb or nb in na


def split_items(text: str) -> list[str]:
    if not text:
        return []
    s = str(text)
    for sep in ["|", "/", "，", "\n", ";", "ㆍ"]:
        s = s.replace(sep, ",")
    return [x.strip() for x in s.split(",") if x.strip()]


def unique_list(items):
    return list(dict.fromkeys([str(x).strip() for x in items if str(x).strip()]))


# ============================================================
# search_document 조회 유틸
# ============================================================

def _table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def search_related_documents(keywords, limit: int = 6) -> list[dict]:

    keywords = unique_list([str(k).strip() for k in (keywords or []) if str(k).strip() and str(k).strip() != "해당 없음"])
    if not keywords or not db_available():
        return []

    scored = {}
    try:
        with _connect() as con:
            if not _table_exists(con, "search_document"):
                return []
            for kw in keywords:
                like = f"%{kw}%"
                rows = con.execute(
                    """
                    SELECT
                        search_id,
                        document_type,
                        target_table,
                        target_id,
                        title,
                        summary,
                        body_text,
                        keyword_text,
                        source_name,
                        priority_score
                    FROM search_document
                    WHERE COALESCE(body_text, '') LIKE ?
                       OR COALESCE(keyword_text, '') LIKE ?
                       OR COALESCE(title, '') LIKE ?
                    ORDER BY priority_score DESC, search_id ASC
                    LIMIT ?
                    """,
                    (like, like, like, max(limit * 2, 10)),
                ).fetchall()
                for row in rows:
                    d = dict(row)
                    sid = d.get("search_id")
                    hit_score = float(d.get("priority_score") or 0) + 1.0
                    text = f"{d.get('title','')} {d.get('body_text','')} {d.get('keyword_text','')}"
                    # 입력 키워드가 여러 개 겹칠수록 상위 노출
                    hit_score += sum(1 for k in keywords if contains_match(k, text)) * 0.25
                    if sid not in scored or hit_score > scored[sid][0]:
                        d["matched_keyword"] = kw
                        d["score"] = round(hit_score, 3)
                        scored[sid] = (hit_score, d)
    except Exception:
        return []

    ranked = [v[1] for v in sorted(scored.values(), key=lambda x: (-x[0], x[1].get("search_id", 0)))]

    # 특정 키워드 하나가 결과를 독점하지 않도록 키워드별 대표 문서 1개를 우선 보존한다.
    diversified = []
    seen_ids = set()
    for kw in keywords:
        for item in ranked:
            if item.get("search_id") in seen_ids:
                continue
            text = f"{item.get('title','')} {item.get('body_text','')} {item.get('keyword_text','')}"
            if contains_match(kw, text):
                item = dict(item)
                item["matched_keyword"] = kw
                diversified.append(item)
                seen_ids.add(item.get("search_id"))
                break
    for item in ranked:
        if item.get("search_id") not in seen_ids:
            diversified.append(item)
            seen_ids.add(item.get("search_id"))
        if len(diversified) >= limit:
            break
    return diversified[:limit]
