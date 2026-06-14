# ==========================================
# 1. 파이썬 내장 표준 라이브러리
# ==========================================
import ast
import os
import re
from pathlib import Path

# ==========================================
# 2. 외부 라이브러리
# ==========================================
import pandas as pd

def clean_boilerplate(text):
    """반복되는 카페 제휴 광고 및 안내 문구를 제거하는 정규식 함수"""
    if pd.isna(text): 
        return text
    text_str = str(text)
    
    # 패턴 1: 원본 내용(content) 노이즈 제거
    pattern1 = r'게시판 안내를 확인해 주세요!.*?71554695(\s*더 보기)?\s*'
    text_str = re.sub(pattern1, '', text_str, flags=re.DOTALL)
    
    # 패턴 2: 특수문자가 제거된 내용(clean_content) 노이즈 제거
    pattern2 = r'게시판 안내를 확인해 주세요.*?제휴 기념(\s*더 보기)?\s*'
    text_str = re.sub(pattern2, '', text_str, flags=re.DOTALL)

    return text_str.strip()

def clean_keywords(kw_str, noise_words_set):
    """추출된 형태소 명사 중 홍보 및 이벤트 관련 노이즈 키워드를 필터링하는 함수"""
    if pd.isna(kw_str): 
        return kw_str
    try:
        # 문자열 형태의 리스트 표기법을 실제 파이썬 리스트 객체로 변환
        kws = ast.literal_eval(kw_str)
        if isinstance(kws, list):
            # 홍보 관련 단어가 제거된 순수 증상 및 영양소 키워드만 보존
            cleaned = [kw for kw in kws if kw not in noise_words_set]
            return str(cleaned)
    except:
        pass
    return kw_str

# ==========================================
# 3. 메인 프로세스 실행부
# ==========================================
if __name__ == "__main__":
    print("[시스템] 홍보성 게시글 및 노이즈 문구 필터링을 시작합니다.")

    # 데이터 입출력 폴더 설정
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    data_dir = PROJECT_ROOT / "data_analysis" / "data"
    input_filename = os.path.join(data_dir, "momcafe_nlp_ready.csv")

    if not os.path.exists(input_filename):
        raise FileNotFoundError(f"[오류] 전 단계의 결과물인 '{input_filename}' 파일을 찾을 수 없습니다. 02번 파일을 먼저 실행하세요.")

    # 데이터 로드
    df = pd.read_csv(input_filename)
    print(f"[로드 완료] 필터링 대상 데이터 개수: {len(df)}개")

    # 1. 본문 및 정제 본문의 광고 문구 제거
    df['content'] = df['content'].apply(clean_boilerplate)
    if 'clean_content' in df.columns:
        df['clean_content'] = df['clean_content'].apply(clean_boilerplate)

    # 2. 형태소 분석 결과 내 광고 노이즈 단어 정의 (공공기관 시나리오와 매핑율 향상 목적)
    noise_words = {
        '게시판', '안내', '확인', '압타클럽', '에그', '스카이', '휴대', '유모차', '당첨', '행운', 
        '사전', '등록', '맘스', '홀릭', '베이비', '페어', '이벤트', '코엑스', '마곡', '카톡', 
        '상담', '현대해상', '맘스홀릭', '회원', '자녀', '보험', '특별', '혜택', '축하', '박스', 
        '구성', '무료', '증정', '만삭', '촬영', '체험', '파스텔', '제휴', '기념', '감사'
    }

    # 3. 키워드 컬럼의 노이즈 제거 진행
    if 'content_keywords' in df.columns:
        df['content_keywords'] = df['content_keywords'].apply(lambda x: clean_keywords(x, noise_words))
    if 'comments_keywords' in df.columns:
        df['comments_keywords'] = df['comments_keywords'].apply(lambda x: clean_keywords(x, noise_words))

    # 4. 광고 제거 프로세스 진행 후 본문이 비어버린 무의미한 데이터 행 제외
    df = df.dropna(subset=['content'])
    df = df[df['content'].str.strip() != ""]
    
    print(f"[필터링 완료] 노이즈 제거 후 최종 유효 데이터 개수: {len(df)}개")

    # 5. 정제 데이터 결과 터미널 출력 확인
    print("\n[광고 필터링 결과 데이터 일부 보기]")
    print(df[['title', 'content_keywords', 'comments_keywords']].head(3))

    # ==========================================
    # 4. 차기 단계 데이터 파이프라인 연결을 위한 파일 저장
    # ==========================================
    output_filename = os.path.join(data_dir, "momcafe_final_purified.csv")
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')

    print(f"\n[완료] 고순도 정제 데이터 파일 저장이 완료되었습니다.")
    print(f"  -> 최종 CSV 저장 경로: {output_filename}")
    print("[안내] 다음 단계인 04_data_mining_clustering.py 파일로 진행하세요.")