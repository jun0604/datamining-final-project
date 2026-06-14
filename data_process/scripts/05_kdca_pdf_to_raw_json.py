
import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise ImportError(
        "PyMuPDF가 설치되어 있지 않습니다. 아래 명령어로 설치하세요:\n"
        "pip install pymupdf"
    ) from e


# ============================================================
# 1. 로컬 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESS_DIR = PROJECT_ROOT / "data_process"

PDF_DIR = DATA_PROCESS_DIR / "data" / "pdf"
RAW_DIR = DATA_PROCESS_DIR / "data" / "raw"
PROCESSED_DIR = DATA_PROCESS_DIR / "data" / "processed"
LOG_DIR = DATA_PROCESS_DIR / "data" / "log"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 로그 설정
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = LOG_DIR / f"kdca_pdf_to_raw_json_{timestamp}.log"

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
    "LOG_PATH": str(LOG_PATH)
})


# ============================================================
# 3. 텍스트 정리 함수
# ============================================================

def clean_text(text):
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\x00", " ")
    text = text.replace("\u200b", " ")
    text = text.replace("\ufeff", " ")
    text = text.replace("ㆍ", " ")
    text = text.replace("˚", " ")
    text = text.replace("■", " ")
    text = text.replace("•", " ")
    text = text.replace("·", " ")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def safe_filename(name):
    name = Path(name).stem
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


# ============================================================
# 4. PDF 자동 탐색
# ============================================================

def find_target_pdfs(raw_dir):
    pdf_paths = []

    for path in raw_dir.glob("*.pdf"):
        name = path.name

        if ("정상임신관리" in name) or ("식이영양" in name) or ("임산부" in name):
            pdf_paths.append(path)

    pdf_paths = sorted(pdf_paths, key=lambda p: p.name)

    return pdf_paths


PDF_PATHS = find_target_pdfs(PDF_DIR)

log_step("PDF 파일 자동 탐색", {
    "pdf_count": len(PDF_PATHS),
    "pdf_files": [str(p) for p in PDF_PATHS]
})

if not PDF_PATHS:
    raise FileNotFoundError(
        f"PDF 파일을 찾지 못했습니다.\n"
        f"다음 경로에 PDF를 넣어주세요:\n{RAW_DIR}\n\n"
        f"파일명 예시:\n"
        f"- 정상임신관리(임신의 진단과 관리) _ 국가건강정보포털 _ 질병관리청.pdf\n"
        f"- 식이영양(임산부) _ 국가건강정보포털 _ 질병관리청.pdf"
    )


# ============================================================
# 5. PDF -> raw JSON 변환
# ============================================================

def pdf_to_raw_json(pdf_path):
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))

    pages = []
    all_page_texts = []

    log_step("PDF 변환 시작", {
        "pdf_name": pdf_path.name,
        "pdf_path": str(pdf_path),
        "page_count": len(doc)
    })

    for page_idx, page in enumerate(doc, start=1):
        page_text = clean_text(page.get_text("text"))
        all_page_texts.append(page_text)

        blocks = []
        raw_blocks = page.get_text("blocks")

        for block_idx, block in enumerate(raw_blocks, start=1):
            x0, y0, x1, y1, block_text, block_no, block_type = block[:7]
            block_text = clean_text(block_text)

            if not block_text:
                continue

            blocks.append({
                "block_id": block_idx,
                "block_no": int(block_no),
                "block_type": int(block_type),
                "bbox": {
                    "x0": float(x0),
                    "y0": float(y0),
                    "x1": float(x1),
                    "y1": float(y1)
                },
                "text": block_text
            })

        pages.append({
            "page": page_idx,
            "text": page_text,
            "blocks": blocks
        })

        logger.info(
            f"page={page_idx} | text_len={len(page_text)} | block_count={len(blocks)}"
        )

    raw_json = {
        "source_file": pdf_path.name,
        "source_path": str(pdf_path),
        "page_count": len(doc),
        "full_text": "\n\n".join(all_page_texts),
        "pages": pages
    }

    doc.close()

    return raw_json


# ============================================================
# 6. 변환 실행 및 저장
# ============================================================

def main():
    saved_files = []

    for pdf_path in PDF_PATHS:
        try:
            raw_data = pdf_to_raw_json(pdf_path)

            out_name = safe_filename(pdf_path.name) + "_raw.json"
            out_path = RAW_DIR / out_name

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)

            saved_files.append(str(out_path))

            log_step("RAW JSON 저장 완료", {
                "source_pdf": str(pdf_path),
                "output_json": str(out_path),
                "page_count": raw_data.get("page_count"),
                "full_text_length": len(raw_data.get("full_text", "")),
                "first_page_preview": raw_data["pages"][0]["text"][:500] if raw_data.get("pages") else ""
            })

        except Exception as e:
            logger.exception(f"PDF 변환 실패: {pdf_path}")

    log_step("전체 변환 완료", {
        "saved_count": len(saved_files),
        "saved_files": saved_files
    })

    print("\n저장 완료 파일")
    for path in saved_files:
        print("-", path)

    print("\n로그 파일")
    print(LOG_PATH)


if __name__ == "__main__":
    main()
