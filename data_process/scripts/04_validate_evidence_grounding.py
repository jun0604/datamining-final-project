from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESS_DIR = PROJECT_ROOT / "data_process"

DB_PATH = PROJECT_ROOT / "pregnancy_nutrition.db"


def normalize_flag(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def is_truthy(value: object) -> bool:
    text = normalize_flag(value)

    return text in {"true", "1", "yes", "y", "일치", "원문일치", "match", "matched"}


def has_value(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB not found: {DB_PATH}\n"
            "먼저 python scripts/create_schema.py 와 python scripts/load_relational_db.py 를 실행하세요."
        )

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        evidence_total = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]

        empty_sentence = conn.execute(
            """
            SELECT COUNT(*)
            FROM evidence
            WHERE IFNULL(TRIM(evidence_sentence), '') = ''
            """
        ).fetchone()[0]

        missing_source = conn.execute(
            """
            SELECT COUNT(*)
            FROM evidence
            WHERE IFNULL(TRIM(source_name), '') = ''
            """
        ).fetchone()[0]

        missing_page = conn.execute(
            """
            SELECT COUNT(*)
            FROM evidence
            WHERE source_page IS NULL
            """
        ).fetchone()[0]

        missing_validation_status = conn.execute(
            """
            SELECT COUNT(*)
            FROM evidence
            WHERE IFNULL(TRIM(validation_status), '') = ''
            """
        ).fetchone()[0]

        evidence_rows = conn.execute(
            """
            SELECT
                evidence_id,
                evidence_sentence,
                source_name,
                source_page,
                evidence_exact_match,
                evidence_similarity,
                validation_status
            FROM evidence
            """
        ).fetchall()

        exact_match_count = sum(is_truthy(row["evidence_exact_match"]) for row in evidence_rows)
        similarity_count = sum(has_value(row["evidence_similarity"]) for row in evidence_rows)

        evidence_id_missing_rules = conn.execute(
            """
            SELECT COUNT(*)
            FROM recommendation_rule
            WHERE evidence_id IS NULL
            """
        ).fetchone()[0]

        broken_fk_rules = conn.execute(
            """
            SELECT COUNT(*)
            FROM recommendation_rule rr
            LEFT JOIN evidence e ON e.evidence_id = rr.evidence_id
            WHERE rr.evidence_id IS NOT NULL
              AND e.evidence_id IS NULL
            """
        ).fetchone()[0]

        rules_total = conn.execute("SELECT COUNT(*) FROM recommendation_rule").fetchone()[0]

        relation_counts = conn.execute(
            """
            SELECT relation_type, COUNT(*) AS cnt
            FROM recommendation_rule
            GROUP BY relation_type
            ORDER BY cnt DESC
            """
        ).fetchall()

        evidence_without_rule = conn.execute(
            """
            SELECT COUNT(*)
            FROM evidence e
            LEFT JOIN recommendation_rule rr ON rr.evidence_id = e.evidence_id
            WHERE rr.rule_id IS NULL
            """
        ).fetchone()[0]

    failed_checks = []

    if empty_sentence:
        failed_checks.append(f"evidence_sentence 빈 값: {empty_sentence}")

    if evidence_id_missing_rules:
        failed_checks.append(f"recommendation_rule.evidence_id 누락: {evidence_id_missing_rules}")

    if broken_fk_rules:
        failed_checks.append(f"깨진 evidence FK: {broken_fk_rules}")

    print("[EVIDENCE GROUNDING VALIDATION]")
    print("  - scope: evidence 테이블의 근거문장 연결성과 recommendation_rule의 evidence_id 연결성 검증")
    print("  - note: 원본 PDF/JSON을 다시 대조하는 완전 OCR 검증은 아님")
    print("  - note: CSV에 저장된 evidence_exact_match / evidence_similarity / validation_status 값을 기준으로 점검")

    print("\n[SUMMARY]")
    print(f"- evidence_total: {evidence_total}")
    print(f"- evidence_exact_match_true: {exact_match_count}")
    print(f"- evidence_similarity_available: {similarity_count}")
    print(f"- evidence_empty_sentence: {empty_sentence}")
    print(f"- evidence_missing_source_name: {missing_source}")
    print(f"- evidence_missing_source_page: {missing_page}")
    print(f"- evidence_missing_validation_status: {missing_validation_status}")
    print(f"- recommendation_rule_total: {rules_total}")
    print(f"- recommendation_rule_missing_evidence_id: {evidence_id_missing_rules}")
    print(f"- recommendation_rule_broken_evidence_fk: {broken_fk_rules}")
    print(f"- evidence_without_recommendation_rule: {evidence_without_rule}")

    print("\n[RELATION TYPE COUNTS]")
    for row in relation_counts:
        print(f"- {row['relation_type'] or 'NULL'}: {row['cnt']}")

    print("\n[CHECK RESULT]")
    if failed_checks:
        print("- FAIL")
        for item in failed_checks:
            print(f"  · {item}")
    else:
        print("- PASS")
        print("  · evidence_sentence가 비어 있지 않고, recommendation_rule의 evidence_id 연결이 정상입니다.")

    print("\n[INTERPRETATION]")
    print("- 이 검증은 DB에 저장된 근거문장과 추천 규칙의 연결성을 확인합니다.")
    print("- evidence_exact_match / evidence_similarity 값은 CSV 생성 단계에서 계산된 값을 점검합니다.")
    print("- 원본 문서를 다시 열어 문장 단위로 재검증하는 완전한 원문 대조 검증은 아닙니다.")


if __name__ == "__main__":
    main()
