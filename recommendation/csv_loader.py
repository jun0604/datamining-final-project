from functools import lru_cache
from pathlib import Path
import re
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed"

CSV_FILES = {
    "symptom_nutrient": "symptom_nutrient.csv",
    "medicine_info": "medicine_info.csv",
    "supplement_info": "supplement_info.csv",
}

FIXED_PUBLIC_SOURCES = [
    "국가건강정보포털(질병관리청)_정상임신관리(임신의 진단과 관리)",
    "국가건강정보포털(질병관리청)_식이영양(임산부)",
    "공공데이터포털(MFDS)_의약품개요정보(e약은요)",
    "공공데이터포털(MFDS)_의약품 제품 허가정보",
    "공공데이터포털(MFDS)_건강기능식품 품목제조 신고사항 현황",
]

@lru_cache(maxsize=None)
def load_csv(name: str) -> pd.DataFrame:
    if name not in CSV_FILES:
        raise KeyError(f"지원하지 않는 CSV 이름입니다: {name}")
    path = DATA_DIR / CSV_FILES[name]
    if not path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {path}")
    df = pd.read_csv(path, dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df

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
