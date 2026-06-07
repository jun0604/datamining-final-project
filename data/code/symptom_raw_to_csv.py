import os
import re
import json
import time
import logging
import traceback
import hashlib
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

import pandas as pd
from tqdm import tqdm
from openai import OpenAI

try:
    from IPython.display import display
except Exception:
    def display(x):
        print(x)

# ============================================================
# 0. 기본 설정
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
LOG_DIR = PROJECT_ROOT / "log"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

RAW_JSON_PATHS = [
    RAW_DIR / "식이영양(임산부)_국가건강정보포털_질병관리청_raw.json",
    RAW_DIR / "정상임신관리(임신의_진단과_관리)_국가건강정보포털_질병관리청_raw.json",
]

MODEL = os.getenv("HAI_GPT_MODEL", "claude-sonnet-4-6")
BASE_URL = os.getenv("HAI_GPT_BASE_URL", "https://factchat-cloud.mindlogic.ai/v1/gateway")
MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "6000"))
REQUEST_SLEEP_SEC = float(os.getenv("REQUEST_SLEEP_SEC", "0.5"))
FUZZY_THRESHOLD = float(os.getenv("EVIDENCE_FUZZY_THRESHOLD", "0.80"))

# 기존 symptom_nutrient_first.csv와 동일한 최종 컬럼 형식
FINAL_OUTPUT_COLS = [
    "임신단계",
    "시작주차",
    "종료주차",
    "증상",
    "증상설명",
    "추천영양소",
    "생활습관",
    "생활습관추천이유",
    "생활습관근거",
    "주의사항",
    "근거문장",
    "출처페이지",
    "출처PDF",
]

# 검증/로그용 확장 컬럼
VALIDATION_COLS = [
    "chunk_id",
    "chunk_hash",
    "근거문장_원문일치",
    "근거문장_유사도",
    "생활습관근거_원문일치",
    "생활습관근거_유사도",
    "근거검증상태",
]

FULL_DEBUG_COLS = FINAL_OUTPUT_COLS + VALIDATION_COLS

# ============================================================
# 1. 로그 유틸
# ============================================================

def now_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_json_dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def normalize_text(text):
    return re.sub(r"\s+", "", str(text or "")).strip()


def short_hash(text):
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()[:12]


class PreprocessTraceLogger:
    """LLM 전처리 과정을 TXT 로그와 JSONL 로그로 동시에 저장합니다."""

    def __init__(self, log_dir: Path):
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir
        self.run_id = now_str()
        self.text_log_path = log_dir / f"preprocess_trace_{self.run_id}.log"
        self.jsonl_log_path = log_dir / f"preprocess_trace_{self.run_id}.jsonl"

        self.logger = logging.getLogger(f"preprocess_trace_{self.run_id}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.propagate = False

        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

        file_handler = logging.FileHandler(self.text_log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

    def log(self, step, data=None, level="info"):
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "step": step,
            "data": data,
        }

        with open(self.jsonl_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        message = f"\n{'=' * 90}\n[STEP] {step}\n"
        if data is not None:
            message += safe_json_dump(data)

        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)


trace = PreprocessTraceLogger(LOG_DIR)

trace.log("로컬 경로 설정", {
    "PROJECT_ROOT": str(PROJECT_ROOT),
    "RAW_DIR": str(RAW_DIR),
    "PROCESSED_DIR": str(PROCESSED_DIR),
    "LOG_DIR": str(LOG_DIR),
    "text_log_path": str(trace.text_log_path),
    "jsonl_log_path": str(trace.jsonl_log_path),
})

print("PROJECT_ROOT:", PROJECT_ROOT)
print("RAW_DIR:", RAW_DIR)
print("PROCESSED_DIR:", PROCESSED_DIR)
print("LOG_DIR:", LOG_DIR)


# ============================================================
# 2. API 설정
# ============================================================

HAI_GPT_API_KEY = os.getenv("HAI_GPT_API_KEY", "ewp1YnAH7gk6woxiXyfIoK65WIsWg9ed")

if not HAI_GPT_API_KEY:
    raise ValueError(
        "HAI_GPT_API_KEY 환경변수가 비어 있습니다.\n"
        "Windows CMD: set HAI_GPT_API_KEY=본인_API_KEY\n"
        "PowerShell: $env:HAI_GPT_API_KEY='본인_API_KEY'\n"
        "macOS/Linux: export HAI_GPT_API_KEY='본인_API_KEY'"
    )

client = OpenAI(
    api_key=HAI_GPT_API_KEY,
    base_url=BASE_URL,
)

trace.log("API 설정 완료", {
    "MODEL": MODEL,
    "base_url": BASE_URL,
    "api_key_loaded": bool(HAI_GPT_API_KEY),
    "api_key_logged": False,
})


# ============================================================
# 3. RAW JSON 확인 및 로드
# ============================================================

trace.log("RAW JSON 파일 확인", [
    {"path": str(path), "exists": path.exists()} for path in RAW_JSON_PATHS
])

missing_files = [str(path) for path in RAW_JSON_PATHS if not path.exists()]
if missing_files:
    raise FileNotFoundError(
        "다음 RAW JSON 파일이 존재하지 않습니다. data/raw 경로와 파일명을 확인하세요:\n"
        + "\n".join(missing_files)
    )


def load_raw_json(path: Path):
    trace.log("RAW JSON 로드 시작", {"path": str(path)})

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    pages = data.get("pages", [])

    for page in pages:
        rows.append({
            "source_file": data.get("source_file", path.name),
            "source_page": page.get("page", ""),
            "text": page.get("text", ""),
        })

    trace.log("RAW JSON 로드 완료", {
        "path": str(path),
        "source_file": data.get("source_file", path.name),
        "page_count": len(rows),
        "text_char_total": sum(len(str(r["text"])) for r in rows),
    })

    return rows


raw_rows = []
for path in RAW_JSON_PATHS:
    raw_rows.extend(load_raw_json(path))

raw_df = pd.DataFrame(raw_rows)

trace.log("RAW DataFrame 생성", {
    "shape": raw_df.shape,
    "columns": list(raw_df.columns),
    "sample": raw_df.head(3).to_dict("records"),
})

print("raw_df shape:", raw_df.shape)
print(raw_df.head())


# ============================================================
# 4. 텍스트 청크 생성
# ============================================================

def clean_text(text):
    text = re.sub(r"\s+", " ", str(text or ""))
    return text.strip()


def make_chunks(raw_df: pd.DataFrame, max_chars=6000):
    chunks = []

    for row_idx, row in raw_df.iterrows():
        text = clean_text(row["text"])
        source_file = row["source_file"]
        source_page = row["source_page"]

        if not text:
            continue

        if len(text) <= max_chars:
            chunks.append({
                "chunk_id": f"{len(chunks) + 1:04d}",
                "row_idx": int(row_idx),
                "source_file": source_file,
                "source_page": source_page,
                "chunk_index_in_page": 1,
                "text": text,
                "text_hash": short_hash(text),
                "char_len": len(text),
            })
        else:
            page_chunk_idx = 1
            for i in range(0, len(text), max_chars):
                chunk_text = text[i:i + max_chars]
                chunks.append({
                    "chunk_id": f"{len(chunks) + 1:04d}",
                    "row_idx": int(row_idx),
                    "source_file": source_file,
                    "source_page": source_page,
                    "chunk_index_in_page": page_chunk_idx,
                    "text": chunk_text,
                    "text_hash": short_hash(chunk_text),
                    "char_len": len(chunk_text),
                })
                page_chunk_idx += 1

    return chunks


chunks = make_chunks(raw_df, max_chars=MAX_CHARS)

trace.log("텍스트 청크 생성 완료", {
    "chunk_count": len(chunks),
    "max_chars": MAX_CHARS,
    "max_char_len": max([c["char_len"] for c in chunks], default=0),
    "min_char_len": min([c["char_len"] for c in chunks], default=0),
    "sample_chunks": [
        {
            "chunk_id": c["chunk_id"],
            "source_file": c["source_file"],
            "source_page": c["source_page"],
            "chunk_index_in_page": c["chunk_index_in_page"],
            "char_len": c["char_len"],
            "text_hash": c["text_hash"],
            "text_preview": c["text"][:300],
        }
        for c in chunks[:3]
    ],
})

print("chunk 수:", len(chunks))


# ============================================================
# 5. 근거문장 검증 함수
# ============================================================

def evidence_exact_match(evidence, source_text):
    evidence_norm = normalize_text(evidence)
    source_norm = normalize_text(source_text)
    if not evidence_norm:
        return False
    return evidence_norm in source_norm


def evidence_fuzzy_score(evidence, source_text):
    evidence_norm = normalize_text(evidence)
    source_norm = normalize_text(source_text)

    if not evidence_norm or not source_norm:
        return 0.0

    if evidence_norm in source_norm:
        return 1.0

    win = max(len(evidence_norm) * 2, 80)
    best = 0.0
    step = max(len(evidence_norm) // 2, 30)

    if len(source_norm) <= win:
        return round(SequenceMatcher(None, evidence_norm, source_norm).ratio(), 4)

    for i in range(0, len(source_norm) - win + 1, step):
        part = source_norm[i:i + win]
        best = max(best, SequenceMatcher(None, evidence_norm, part).ratio())
        if best >= 0.9:
            break

    return round(best, 4)


def validate_row_evidence(row, source_text, fuzzy_threshold=0.80):
    evidence = str(row.get("근거문장", "") or "").strip()
    lifestyle_evidence = str(row.get("생활습관근거", "") or "").strip()

    evidence_exact = evidence_exact_match(evidence, source_text)
    evidence_score = evidence_fuzzy_score(evidence, source_text)

    if lifestyle_evidence and lifestyle_evidence != "해당 없음":
        lifestyle_exact = evidence_exact_match(lifestyle_evidence, source_text)
        lifestyle_score = evidence_fuzzy_score(lifestyle_evidence, source_text)
    else:
        lifestyle_exact = None
        lifestyle_score = None

    evidence_status = "PASS" if evidence_exact or evidence_score >= fuzzy_threshold else "CHECK"

    return {
        "근거문장_원문일치": evidence_exact,
        "근거문장_유사도": evidence_score,
        "생활습관근거_원문일치": lifestyle_exact,
        "생활습관근거_유사도": lifestyle_score,
        "근거검증상태": evidence_status,
    }


# ============================================================
# 5-1. 추출값 정규화 / 안전 후처리 함수
# ============================================================

NUTRIENT_SPLIT_PATTERN = re.compile(r"\s*[,，/·]\s*")

NUTRIENT_ALIASES = {
    "철": "철분",
    "섬유소": "식이섬유",
}

PRECAUTION_KEYWORDS = [
    "주의", "피하", "제한", "줄", "금", "필요 없", "권장하지",
    "상담", "위험", "방해", "과도", "반드시", "익혀", "말아",
    "않도록", "최대", "섭취하지", "보충할 필요"
]


def split_nutrients(nutrient_text):
    """추천영양소 문자열을 분리합니다. 빈 값/해당 없음은 빈 리스트로 처리합니다."""
    text = str(nutrient_text or "").strip()
    if not text or text.lower() == "nan" or text == "해당 없음":
        return []

    parts = []
    for part in NUTRIENT_SPLIT_PATTERN.split(text):
        part = part.strip()
        if not part:
            continue
        parts.append(part)

    return parts


def normalize_nutrient_name(name):
    """철/철분, 섬유소/식이섬유처럼 동일 성분이 다른 이름으로 추출되는 경우 대표명으로 통합합니다."""
    name = str(name or "").strip()
    return NUTRIENT_ALIASES.get(name, name)


def normalize_nutrient_list(nutrient_text):
    """추천영양소 목록을 대표명으로 통합하고 중복 제거합니다."""
    normalized = []
    seen = set()

    for item in split_nutrients(nutrient_text):
        item = normalize_nutrient_name(item)
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)

    return ", ".join(normalized)


def contains_precaution_keyword(text):
    text = str(text or "")
    return any(keyword in text for keyword in PRECAUTION_KEYWORDS)


def enforce_precaution_from_evidence(row):
    """
    주의사항은 근거문장에 의해 직접 뒷받침되는 내용만 유지합니다.
    - LLM이 근거문장 밖의 내용을 주의사항에 섞어 넣으면 제거합니다.
    - 근거문장 자체에 주의/제한/상담/위험 관련 표현이 있으면 근거문장을 주의사항으로 사용합니다.
    - 근거문장에 주의성 표현이 없으면 '해당 없음'으로 정리합니다.
    """
    caution = str(row.get("주의사항", "") or "").strip()
    evidence = str(row.get("근거문장", "") or "").strip()

    if not caution or caution == "해당 없음":
        row["주의사항"] = "해당 없음"
        return row, None

    if not evidence:
        old = caution
        row["주의사항"] = "해당 없음"
        return row, {
            "type": "주의사항 제거",
            "reason": "근거문장 없음",
            "before": old,
            "after": row["주의사항"],
        }

    caution_norm = normalize_text(caution)
    evidence_norm = normalize_text(evidence)

    # 주의사항이 근거문장에 직접 포함되어 있으면 유지
    if caution_norm and caution_norm in evidence_norm:
        return row, None

    # 근거문장에 주의/제한/상담/위험 표현이 있으면 근거문장만 주의사항으로 사용
    if contains_precaution_keyword(evidence):
        old = caution
        row["주의사항"] = evidence
        return row, {
            "type": "주의사항 근거문장 기반 치환",
            "reason": "주의사항이 근거문장 밖 내용까지 포함하여 근거문장으로 제한",
            "before": old,
            "after": row["주의사항"],
        }

    # 근거문장에 주의사항 성격이 없으면 주의사항 제거
    old = caution
    row["주의사항"] = "해당 없음"
    return row, {
        "type": "주의사항 제거",
        "reason": "근거문장에 주의사항 성격의 표현 없음",
        "before": old,
        "after": row["주의사항"],
    }


def remove_early_iron_when_not_recommended(row):
    """
    임신 첫 4개월에는 철분제 보충이 구역/구토를 유발할 수 있어 보충 필요가 없다는
    근거문장이 있는 경우, 해당 row의 추천영양소에서 철분을 제거합니다.

    단, 모든 초기 빈혈 행에서 철분을 제거하는 것이 아니라,
    '첫 4개월 + 철분제 + 보충할 필요 없음/구역/구토 유발' 근거가 있는 행에만 적용합니다.
    """
    nutrients_before = str(row.get("추천영양소", "") or "").strip()
    nutrients = split_nutrients(nutrients_before)

    normalized_nutrients = [normalize_nutrient_name(n) for n in nutrients]
    if "철분" not in normalized_nutrients:
        row["추천영양소"] = normalize_nutrient_list(nutrients_before)
        return row, None

    stage = str(row.get("임신단계", "") or "").strip()
    start_week = pd.to_numeric(row.get("시작주차", ""), errors="coerce")
    evidence_bundle = " ".join([
        str(row.get("근거문장", "") or ""),
        str(row.get("주의사항", "") or ""),
        str(row.get("생활습관근거", "") or ""),
    ])

    is_early = stage == "초기" or (pd.notna(start_week) and int(start_week) <= 13)
    has_first_4_month_rule = (
        ("첫 4개월" in evidence_bundle or "4개월" in evidence_bundle)
        and "철분제" in evidence_bundle
        and (
            "보충할 필요가 없" in evidence_bundle
            or "권장하지" in evidence_bundle
            or "구역" in evidence_bundle
            or "구토" in evidence_bundle
        )
    )

    if not (is_early and has_first_4_month_rule):
        row["추천영양소"] = normalize_nutrient_list(nutrients_before)
        return row, None

    filtered = []
    for n in normalized_nutrients:
        if n == "철분":
            continue
        if n not in filtered:
            filtered.append(n)

    row["추천영양소"] = ", ".join(filtered) if filtered else "해당 없음"

    return row, {
        "type": "초기 철분 추천 제거",
        "reason": "근거문장에 임신 첫 4개월 철분제 보충 필요 없음/구역·구토 유발 내용이 존재",
        "before": nutrients_before,
        "after": row["추천영양소"],
    }


def postprocess_extracted_row(row):
    """LLM 추출 row에 안전 후처리를 적용합니다."""
    changes = []

    before_nutrients = str(row.get("추천영양소", "") or "")
    row["추천영양소"] = normalize_nutrient_list(before_nutrients)
    if before_nutrients != row["추천영양소"]:
        changes.append({
            "type": "추천영양소 대표명 통합",
            "reason": "철/철분은 철분으로, 섬유소/식이섬유는 식이섬유로 통합",
            "before": before_nutrients,
            "after": row["추천영양소"],
        })

    row, change = remove_early_iron_when_not_recommended(row)
    if change:
        changes.append(change)

    row, change = enforce_precaution_from_evidence(row)
    if change:
        changes.append(change)

    return row, changes


# ============================================================
# 6. HAI GPT 호출 함수
# ============================================================

SYSTEM_PROMPT = """
You are a medical document information extraction engine.

Your goal is to convert Korean pregnancy-related documents into structured datasets.

Rules:

1. Use only information explicitly supported by the source text.
2. Never hallucinate or infer unsupported facts.
3. Do not use external medical knowledge.
4. Do not fill missing values using common sense.
5. If evidence is absent, do not output the row.
6. Every extracted row must include an original Korean evidence sentence from the source document.
7. Maximize recall only within source-supported information.
8. Extract every relevant item that has textual support.
9. Do not summarize aggressively.
10. Preserve as much detail as possible.
11. If multiple valid rows exist, return all rows.
12. Keep evidence sentences close to the original wording.
13. If multiple symptoms are described in a paragraph, create separate rows for each symptom.
14. If multiple nutrients are mentioned, include all supported nutrients.
15. If multiple pregnancy stages are mentioned, create separate rows for each stage.
16. Preserve detailed management instructions and precautions whenever possible.
17. Output valid JSON only.
18. The output schema must follow the user prompt exactly.

No markdown.
No explanations.
No comments.
No notes.
No code blocks.

Return JSON only.
"""


def strip_code_block(content):
    content = str(content or "").strip()
    if content.startswith("```json"):
        content = content.replace("```json", "", 1)
        content = content.replace("```", "").strip()
    elif content.startswith("```"):
        content = content.replace("```", "").strip()
    return content


def call_haigpt(prompt, chunk_meta, temperature=0):
    trace.log("LLM 호출 전", {
        "chunk_id": chunk_meta.get("chunk_id"),
        "source_file": chunk_meta.get("source_file"),
        "source_page": chunk_meta.get("source_page"),
        "chunk_index_in_page": chunk_meta.get("chunk_index_in_page"),
        "text_hash": chunk_meta.get("text_hash"),
        "text_char_len": chunk_meta.get("char_len"),
        "temperature": temperature,
        "model": MODEL,
        "system_prompt": SYSTEM_PROMPT.strip(),
        "user_prompt": prompt,
        "source_text": chunk_meta.get("text"),
    })

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )

        raw_content = response.choices[0].message.content.strip()
        content = strip_code_block(raw_content)

        trace.log("LLM 원본 응답 수신", {
            "chunk_id": chunk_meta.get("chunk_id"),
            "raw_response": raw_content,
            "cleaned_response": content,
            "response_char_len": len(raw_content),
        })

        try:
            parsed = json.loads(content)
        except Exception as parse_error:
            trace.log("LLM JSON 파싱 실패", {
                "chunk_id": chunk_meta.get("chunk_id"),
                "error": str(parse_error),
                "raw_response_preview": raw_content[:3000],
                "traceback": traceback.format_exc(),
            }, level="error")
            raise

        rows = parsed.get("rows", []) if isinstance(parsed, dict) else []
        trace.log("LLM JSON 파싱 완료", {
            "chunk_id": chunk_meta.get("chunk_id"),
            "row_count": len(rows),
            "rows": rows,
        })

        return parsed

    except Exception as api_error:
        trace.log("LLM 호출 실패", {
            "chunk_id": chunk_meta.get("chunk_id"),
            "source_file": chunk_meta.get("source_file"),
            "source_page": chunk_meta.get("source_page"),
            "error": str(api_error),
            "traceback": traceback.format_exc(),
        }, level="error")
        raise


# ============================================================
# 7. symptom_nutrient.csv 추출 프롬프트
# ============================================================

def build_symptom_nutrient_prompt(text, source_file, source_page):
    return f"""
You are an expert medical and nutrition document information extraction system.

Your task is to extract symptom-related, nutrient-related, and lifestyle-related information for pregnant women from the following Korean document and convert it into structured JSON.

Output valid JSON only.

Important:
- Extract newly from the given Document only.
- Do not imitate or copy any previous CSV content.
- Use the exact output schema below.
- The final CSV will preserve the 13-column format:
  임신단계, 시작주차, 종료주차, 증상, 증상설명, 추천영양소, 생활습관, 생활습관추천이유, 생활습관근거, 주의사항, 근거문장, 출처페이지, 출처PDF.
- Validation columns will be added later by code, not by the LLM.

Schema:

{{
  "rows":[
    {{
      "임신단계":"초기|중기|후기",
      "시작주차":1,
      "종료주차":13,
      "증상":"Symptom name explicitly mentioned or clearly described in the source text",
      "증상설명":"Detailed symptom description explicitly supported by the source text",
      "추천영양소":"Comma-separated nutrient list explicitly supported by the source text",
      "생활습관":"One normalized lifestyle category explicitly supported by the source text",
      "생활습관추천이유":"Reason why this lifestyle category is related to the symptom or nutrient recommendation",
      "생활습관근거":"Original Korean evidence sentence supporting the lifestyle category",
      "주의사항":"Detailed precautions, warnings, restrictions, or medical-attention conditions explicitly supported by the source text",
      "근거문장":"Original Korean evidence sentence from the source document",
      "출처페이지":{source_page}
    }}
  ]
}}

Instructions:

1. 증상 must use concise Korean symptom names, such as 입덧, 구토, 빈혈, 변비, 부종, 임신중독증, 임신고혈압, 임신당뇨, 소화불량, 속쓰림, 피로, 탈수, 체중증가, 조산, 난산.
2. 증상설명 must be detailed and informative.
3. 추천영양소 must include only nutrients, food components, or dietary factors explicitly supported by the source text, such as 엽산, 철분, 비타민 C, 비타민 B6, 비타민 B12, 단백질, 수분, 식이섬유, 칼슘, 비타민 D, 탄수화물, 지방, 오메가-3, EPA, DHA, 무기질, 나트륨 제한.
   - Normalize 철 and 철분 as 철분.
   - Normalize 섬유소 and 식이섬유 as 식이섬유.
   - Do not output 철 separately.
   - Do not output 섬유소 separately.
   - If the source says iron supplements are not needed during the first 4 months of pregnancy or may worsen nausea/vomiting, do not use 철분 as 추천영양소 for that row; keep it only as a 주의사항 if supported by 근거문장.
4. 생활습관 must use only one of the following normalized categories if explicitly supported:
   - 수분 섭취가 부족함
   - 신체활동이 부족함
   - 한 번에 많은 양을 섭취함
   - 철분 섭취가 부족함
   - 식이섬유 섭취가 부족함
   - 자극적인 음식을 자주 섭취함
5. 생활습관추천이유 must explain how the lifestyle category relates to the symptom or nutrient recommendation.
6. 생활습관근거 must be an original Korean sentence from the document supporting 생활습관.
7. If no lifestyle category is explicitly supported, use "해당 없음".
8. 주의사항 must include only restrictions, warnings, risk factors, foods to avoid, excessive intake warnings, medication/supplement cautions, or conditions requiring medical consultation that are directly supported by 근거문장.
   - Do not combine caution details from outside 근거문장.
   - If 근거문장 does not contain a caution, warning, restriction, risk, or consultation condition, set 주의사항 to "해당 없음".
9. 근거문장 must be an original Korean sentence from the document.
10. Normalize pregnancy stages:
    - 초기 = 1~13 weeks
    - 중기 = 14~27 weeks
    - 후기 = 28~42 weeks
11. Use only one of these values for 임신단계: 초기, 중기, 후기.
12. If the text mentions a specific week range, map it to the closest pregnancy stage.
13. If the symptom or nutrient applies to pregnancy in general, assign the most relevant stage based on context only when the document provides contextual support.
14. If no relevant information exists, return:
    {{"rows":[]}}
15. Do not infer symptoms, nutrients, lifestyle categories, precautions, or stages that are not supported by the document.
16. Each row must be traceable to 근거문장. Rows without 근거문장 must not be generated.
17. Do not output chunk_id, chunk_hash, evidence validation values, or any extra fields.

Source File: {source_file}
Source Page: {source_page}

Document:

{text}
"""


# ============================================================
# 8. symptom_nutrient.csv 자동 생성 + LLM 추론/검증 로그
# ============================================================

symptom_rows = []
failed_chunks = []

for chunk in tqdm(chunks, desc="LLM symptom_nutrient extraction"):
    prompt = build_symptom_nutrient_prompt(
        text=chunk["text"],
        source_file=chunk["source_file"],
        source_page=chunk["source_page"],
    )

    try:
        result = call_haigpt(prompt, chunk_meta=chunk, temperature=0)
        rows = result.get("rows", []) if isinstance(result, dict) else []

        validated_rows = []
        for row_idx, r in enumerate(rows):
            if not isinstance(r, dict):
                trace.log("비정상 row 형식 발견", {
                    "chunk_id": chunk["chunk_id"],
                    "row_idx": row_idx,
                    "row_value": r,
                }, level="warning")
                continue

            # LLM이 스키마 외 필드를 생성해도 최종/검증 스키마에 필요한 값만 유지
            clean_row = {col: r.get(col, "") for col in FINAL_OUTPUT_COLS if col != "출처PDF"}
            clean_row["출처PDF"] = chunk["source_file"]
            clean_row["근거문장"] = chunk["text"]

            clean_row, postprocess_changes = postprocess_extracted_row(clean_row)
            if postprocess_changes:
                trace.log("row 후처리 적용", {
                    "chunk_id": chunk["chunk_id"],
                    "row_idx": row_idx,
                    "source_file": chunk["source_file"],
                    "source_page": chunk["source_page"],
                    "증상": clean_row.get("증상"),
                    "changes": postprocess_changes,
                    "row_after": clean_row,
                })

            clean_row["chunk_id"] = chunk["chunk_id"]
            clean_row["chunk_hash"] = chunk["text_hash"]

            validation = validate_row_evidence(clean_row, chunk["text"], fuzzy_threshold=FUZZY_THRESHOLD)
            clean_row.update(validation)

            validated_rows.append(clean_row)
            symptom_rows.append(clean_row)

        trace.log("chunk 추출 row 검증 완료", {
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "source_page": chunk["source_page"],
            "extracted_row_count": len(rows),
            "validated_row_count": len(validated_rows),
            "pass_count": sum(1 for r in validated_rows if r.get("근거검증상태") == "PASS"),
            "check_count": sum(1 for r in validated_rows if r.get("근거검증상태") == "CHECK"),
            "validated_rows": validated_rows,
        })

        time.sleep(REQUEST_SLEEP_SEC)

    except Exception as e:
        failed = {
            "chunk_id": chunk.get("chunk_id"),
            "source_file": chunk.get("source_file"),
            "source_page": chunk.get("source_page"),
            "error": str(e),
        }
        failed_chunks.append(failed)
        print("symptom 추출 실패:", chunk["source_file"], chunk["source_page"], e)
        trace.log("symptom 추출 실패", failed, level="error")


# ============================================================
# 9. DataFrame 정리
# ============================================================

full_df = pd.DataFrame(symptom_rows)

for col in FULL_DEBUG_COLS:
    if col not in full_df.columns:
        full_df[col] = ""

full_df = full_df[FULL_DEBUG_COLS]

before_dedup = len(full_df)
full_df = full_df.drop_duplicates()
after_dedup = len(full_df)

# 검증 컬럼이 포함된 전체 추출 결과는 별도 파일로 저장합니다.
# 이 파일은 검증 상태 확인용이며, CHECK 행도 보존합니다.
symptom_nutrient_with_validation_df = full_df[FULL_DEBUG_COLS].copy()

# 최종 추천서비스용 symptom_nutrient.csv는 검증 완료(PASS) 행만 사용합니다.
# 즉, symptom_nutrient_with_validation 기준으로 근거검증상태가 CHECK인 행은 제거합니다.
check_mask = symptom_nutrient_with_validation_df["근거검증상태"] == "CHECK"
pass_mask = symptom_nutrient_with_validation_df["근거검증상태"] == "PASS"

check_removed_count = int(check_mask.sum()) if len(symptom_nutrient_with_validation_df) else 0
pass_count = int(pass_mask.sum()) if len(symptom_nutrient_with_validation_df) else 0

symptom_nutrient_df = symptom_nutrient_with_validation_df.loc[pass_mask, FINAL_OUTPUT_COLS].copy()

trace.log("DataFrame 정리 완료", {
    "before_dedup": before_dedup,
    "after_dedup": after_dedup,
    "duplicate_removed": before_dedup - after_dedup,
    "final_output_columns": FINAL_OUTPUT_COLS,
    "validation_columns": VALIDATION_COLS,
    "evidence_pass_count": pass_count,
    "evidence_check_count": check_removed_count,
    "check_rows_removed_from_final_symptom_nutrient": check_removed_count,
    "final_symptom_nutrient_row_count": len(symptom_nutrient_df),
    "with_validation_row_count": len(symptom_nutrient_with_validation_df),
    "failed_chunk_count_logged_only": len(failed_chunks),
    "note": "failed_chunks.csv와 symptom_nutrient_validation_report.csv는 생성하지 않음",
})


# ============================================================
# 10. CSV / Excel 저장
# ============================================================

symptom_nutrient_path = PROCESSED_DIR / "symptom_nutrient.csv"
symptom_nutrient_xlsx_path = PROCESSED_DIR / "symptom_nutrient.xlsx"
symptom_nutrient_with_validation_path = PROCESSED_DIR / "symptom_nutrient_with_validation.csv"

symptom_nutrient_df.to_csv(
    symptom_nutrient_path,
    index=False,
    encoding="utf-8-sig",
)

try:
    symptom_nutrient_df.to_excel(
        symptom_nutrient_xlsx_path,
        index=False,
    )
except Exception as excel_error:
    trace.log("Excel 저장 실패", {
        "path": str(symptom_nutrient_xlsx_path),
        "error": str(excel_error),
        "note": "openpyxl 설치가 필요할 수 있습니다. pip install openpyxl",
    }, level="warning")

symptom_nutrient_with_validation_df.to_csv(
    symptom_nutrient_with_validation_path,
    index=False,
    encoding="utf-8-sig",
)

trace.log("파일 저장 완료", {
    "symptom_nutrient_csv_13cols_pass_only": str(symptom_nutrient_path),
    "symptom_nutrient_xlsx_13cols_pass_only": str(symptom_nutrient_xlsx_path),
    "symptom_nutrient_with_validation_csv_all_rows": str(symptom_nutrient_with_validation_path),
    "validation_report_csv": "생성하지 않음",
    "failed_chunks_csv": "생성하지 않음",
    "check_rows_removed_from_final_symptom_nutrient": check_removed_count,
    "text_log_path": str(trace.text_log_path),
    "jsonl_log_path": str(trace.jsonl_log_path),
})

print("저장 완료")
print("최종 CSV 13컬럼(PASS만 저장):", symptom_nutrient_path)
print("최종 XLSX 13컬럼(PASS만 저장):", symptom_nutrient_xlsx_path)
print("검증 컬럼 포함 CSV(CHECK 포함 전체):", symptom_nutrient_with_validation_path)
print("검증 리포트: 생성하지 않음")
print("실패 chunk CSV: 생성하지 않음")
print("제거된 CHECK 행 수:", check_removed_count)
print("TXT 로그:", trace.text_log_path)
print("JSONL 로그:", trace.jsonl_log_path)

print("\nsymptom_nutrient.csv 미리보기")
print(symptom_nutrient_df.head())
print("\nsymptom_nutrient_with_validation.csv 미리보기")
print(symptom_nutrient_with_validation_df.head())
print("\n저장 폴더:", PROCESSED_DIR)
print("로그 폴더:", LOG_DIR)
