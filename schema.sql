PRAGMA foreign_keys = ON;

-- ============================================================
-- schema.sql
-- ------------------------------------------------------------
-- 최종 RDB 적재 기준
--
-- 1) KDCA raw JSON
--    - RDB에 직접 적재하지 않음
--    - symptom_nutrient_with_validation.csv 생성/검증에 사용한 원천 데이터
--
-- 2) symptom_nutrient_with_validation.csv / symptom_nutrient.csv
--    - RDB의 핵심 추천 규칙 데이터
--    - recommendation_rule / lifestyle_weight_rule / evidence 구성
--
-- 3) mfds_supplement_raw.json
--    - supplement_info / supplement_ingredient 구성
--
-- 4) mfds_medicine_raw.json
--    - medicine_info 구성
-- ============================================================


-- ============================================================
-- 1. CSV 기반 근거문장
-- ============================================================

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_sentence TEXT NOT NULL,
    source_page INTEGER,
    source_name TEXT,
    evidence_type TEXT,
    source_chunk_id TEXT,
    source_chunk_hash TEXT,
    evidence_exact_match TEXT,
    evidence_similarity REAL,
    lifestyle_evidence_exact_match TEXT,
    lifestyle_evidence_similarity REAL,
    validation_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(evidence_sentence, source_page, source_name)
);


-- ============================================================
-- 2. 추천 규칙
-- ============================================================

CREATE TABLE IF NOT EXISTS recommendation_rule (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregnancy_stage TEXT,
    week_start INTEGER,
    week_end INTEGER,
    symptom TEXT NOT NULL,
    symptom_description TEXT,
    recommended_nutrient TEXT,
    lifestyle_condition TEXT,
    base_score REAL DEFAULT 1.0,
    relation_type TEXT DEFAULT 'recommend',
    reason TEXT,
    caution_text TEXT,
    evidence_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
);

CREATE TABLE IF NOT EXISTS lifestyle_weight_rule (
    weight_rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lifestyle_check TEXT NOT NULL,
    symptom TEXT,
    pregnancy_stage TEXT,
    week_start INTEGER,
    week_end INTEGER,
    nutrient TEXT,
    weight_delta REAL DEFAULT 0.0,
    weight_reason TEXT,
    lifestyle_evidence TEXT,
    evidence_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
);


-- ============================================================
-- 3. 건강기능식품
-- ============================================================

CREATE TABLE IF NOT EXISTS supplement_info (
    supplement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    company_name TEXT,
    report_no TEXT,
    registration_date TEXT,
    source TEXT DEFAULT 'mfds_supplement_raw.json',
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_name, company_name, report_no)
);

CREATE TABLE IF NOT EXISTS supplement_ingredient (
    supplement_ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplement_id INTEGER NOT NULL,
    ingredient_name TEXT NOT NULL,
    standard_nutrient TEXT,
    amount TEXT,
    unit TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplement_id) REFERENCES supplement_info(supplement_id) ON DELETE CASCADE,
    UNIQUE(supplement_id, ingredient_name)
);


-- ============================================================
-- 4. 의약품
-- ============================================================

CREATE TABLE IF NOT EXISTS medicine_info (
    medicine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_name TEXT NOT NULL,
    efficacy TEXT,
    usage TEXT,
    warning TEXT,
    interaction TEXT,
    side_effect TEXT,
    storage TEXT,
    manufacturer TEXT,
    ingredient TEXT,
    source TEXT DEFAULT 'mfds_medicine_raw.json',
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(medicine_name, manufacturer)
);


-- ============================================================
-- 5. 영양소 표준명 alias
-- ============================================================

CREATE TABLE IF NOT EXISTS nutrient_alias (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_nutrient TEXT NOT NULL,
    alias_name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(standard_nutrient, alias_name)
);


-- ============================================================
-- 6. 검색용 통합 문서
-- ============================================================

CREATE TABLE IF NOT EXISTS search_document (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_type TEXT NOT NULL,
    target_table TEXT,
    target_id TEXT,
    title TEXT,
    summary TEXT,
    body_text TEXT,
    keyword_text TEXT,
    source_name TEXT,
    priority_score REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 7. 추천 검증 테스트셋
-- ============================================================

CREATE TABLE IF NOT EXISTS recommendation_test_case (
    test_id TEXT PRIMARY KEY,
    test_type TEXT,
    pregnancy_week INTEGER,
    symptom TEXT,
    lifestyle_check TEXT,
    user_input_text TEXT,
    expected_include_nutrients TEXT,
    expected_exclude_nutrients TEXT,
    expected_guidance_keywords TEXT,
    expected_supplement_keywords TEXT,
    expected_medicine_keywords TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 8. Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source_name, source_page);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_validation ON evidence(validation_status);

CREATE INDEX IF NOT EXISTS idx_recommendation_rule_lookup
ON recommendation_rule(symptom, week_start, week_end);

CREATE INDEX IF NOT EXISTS idx_recommendation_rule_nutrient
ON recommendation_rule(recommended_nutrient);

CREATE INDEX IF NOT EXISTS idx_recommendation_rule_relation_type
ON recommendation_rule(relation_type);

CREATE INDEX IF NOT EXISTS idx_lifestyle_weight_lookup
ON lifestyle_weight_rule(lifestyle_check, symptom, week_start, week_end);

CREATE INDEX IF NOT EXISTS idx_lifestyle_weight_nutrient
ON lifestyle_weight_rule(nutrient);

CREATE INDEX IF NOT EXISTS idx_supplement_product_name
ON supplement_info(product_name);

CREATE INDEX IF NOT EXISTS idx_supplement_report_no
ON supplement_info(report_no);

CREATE INDEX IF NOT EXISTS idx_supplement_ingredient_name
ON supplement_ingredient(ingredient_name);

CREATE INDEX IF NOT EXISTS idx_supplement_ingredient_standard
ON supplement_ingredient(standard_nutrient);

CREATE INDEX IF NOT EXISTS idx_medicine_name
ON medicine_info(medicine_name);

CREATE INDEX IF NOT EXISTS idx_medicine_ingredient
ON medicine_info(ingredient);

CREATE INDEX IF NOT EXISTS idx_alias_name
ON nutrient_alias(alias_name);

CREATE INDEX IF NOT EXISTS idx_alias_standard
ON nutrient_alias(standard_nutrient);

CREATE INDEX IF NOT EXISTS idx_search_document_type
ON search_document(document_type);

CREATE INDEX IF NOT EXISTS idx_search_document_target
ON search_document(target_table, target_id);
