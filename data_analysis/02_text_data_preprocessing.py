# ==========================================
# 1. 파이썬 내장 표준 라이브러리
# ==========================================
import json
import os
import re
from datetime import datetime
from pathlib import Path

# ==========================================
# 2. 외부 라이브러리
# ==========================================
import pandas as pd
from kiwipiepy import Kiwi

def clean_text(text):
    """URL 및 특수문자 제거와 구어체 표현을 분석용 핵심 도메인 명사로 표준 정규화하는 함수"""
    if pd.isna(text): 
        return ""
    text = str(text)
    
    # [보완] 구어체 서술어 및 유저 변형 표현을 통계 집계용 명사 키워드로 강제 치환
    text = re.sub(r'소화\s*가?\s*안\s*되|소화\s*가?\s*안\s*돼|소화\s*못\s*시|속이\s*더부룩', '소화불량', text)
    text = re.sub(r'다리\s*가?\s*저|다리\s*쥐|다리\s*저림', '다리저림', text)
    text = re.sub(r'오메가\s*3|오메가\s*쓰리', '오메가3', text)
    text = re.sub(r'칼슘\s*마그네슘\s*비타민\s*d|칼\s*마\s*디', '칼마디', text)
    text = re.sub(r'푸룬\s*즙|푸룬\s*주스', '푸룬주스', text)
    
    # 기본 정규식 노이즈 정제
    text = re.sub(r'http\S+', '', text) 
    text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text) 
    text = re.sub(r'\s+', ' ', text).strip() 
    return text

def get_keywords_kiwi(text, kiwi_instance, stop_words_list):
    """Kiwi 형태소 분석기를 사용하여 일반명사(NNG) 및 고유명사(NNP) 중 2글자 이상의 핵심어만 추출"""
    if not text:
        return []
        
    # Kiwi 토큰화 실행
    tokens = kiwi_instance.tokenize(text)
    
    # 일반명사(NNG), 고유명사(NNP) 태그만 필터링
    nouns = [t.form for t in tokens if t.tag in ['NNG', 'NNP']]
    
    # 1글자 단어 및 정의된 불용어 리스트 제외
    final_nouns = [word for word in nouns if len(word) > 1 and word not in stop_words_list]
    return final_nouns

# ==========================================
# 3. 메인 프로세스 실행부
# ==========================================
if __name__ == "__main__":
    print("[시스템] 텍스트 정제 및 형태소 분석 프로세스를 시작합니다.")

    # 데이터 입출력 폴더 설정
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    data_dir = PROJECT_ROOT / "data_analysis" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # 01번 파일에서 생성한 원본 데이터 파일 경로 설정
    input_filename = "momcafe_target_data.csv"
    
    if not os.path.exists(input_filename):
        input_filename = os.path.join(data_dir, "momcafe_target_data.csv")

    if not os.path.exists(input_filename):
        raise FileNotFoundError(f"[오류] 전 단계의 결과물인 '{input_filename}' 파일을 찾을 수 없습니다. 01번 파일을 먼저 실행하세요.")

    # 원본 데이터 로드
    df = pd.read_csv(input_filename)
    print(f"[로드 완료] 분석 대상 데이터 개수: {len(df)}개")

    # 1. 리스트 형태의 댓글 데이터를 하나의 문자열로 결합
    if 'comments' in df.columns:
        df['comments'] = df['comments'].apply(lambda x: ' | '.join(eval(x)) if isinstance(x, str) and x.startswith('[') else (' | '.join(x) if isinstance(x, list) else x))

    # 2. 본문 및 댓글의 화이트스페이스 노이즈 정제
    if 'content' in df.columns:
        df['content'] = df['content'].str.replace(r'\n|\t|\r', ' ', regex=True).str.strip()
    if 'comments' in df.columns:
        df['comments'] = df['comments'].str.replace(r'\n|\t|\r', ' ', regex=True).str.strip()

    # 3. 특수문자 및 동의어 정제 컬럼 생성
    df['clean_content'] = df['content'].apply(clean_text)
    df['clean_comments'] = df['comments'].apply(clean_text)

    # 4. Kiwi 형태소 분석기 초기화 및 사용자 정의 사전 등록
    kiwi = Kiwi()
    
    # [보완] 형태소 분석기가 단어를 강제로 쪼개는 현상을 방지하기 위해 도메인 핵심 명사 박제
    kiwi.add_user_word("소화불량", "NNG")
    kiwi.add_user_word("다리저림", "NNG")
    kiwi.add_user_word("오메가3", "NNP")
    kiwi.add_user_word("칼마디", "NNP")
    kiwi.add_user_word("마그밀", "NNP")
    kiwi.add_user_word("푸룬주스", "NNP")
    
    # [보완] 공공기관 가이드라인 싱크 극대화 및 파편화된 노이즈 단어 제거 목록 확장
    stop_words = [
        '진짜', '너무', '요즘', '그냥', '혹시', '추천', '부탁', '오늘', '어제', '생각', 
        '정도', '이거', '저희', '어떻게', '주차', '개월', '임신', '임산부', '병원', '원장', '감사',
        '마디', '오메', '가요', '가지', '하루', '하나', '부분', '시간', '때문', '관련'
    ]

    print("[동작] 명사 추출 및 자연어 처리(NLP) 스크립트를 수행 중입니다...")
    df['content_keywords'] = df['clean_content'].apply(lambda x: get_keywords_kiwi(x, kiwi, stop_words))
    df['comments_keywords'] = df['clean_comments'].apply(lambda x: get_keywords_kiwi(x, kiwi, stop_words))

    # 5. 데이터 처리 확인용 CLI 출력
    print("\n[정제 결과 데이터 일부 보기]")
    print(df[['title', 'content_keywords', 'comments_keywords']].head(3))

    # ==========================================
    # 4. 차기 단계 데이터 파이프라인 연결을 위한 파일 저장
    # ==========================================
    output_csv_path = os.path.join(data_dir, "momcafe_nlp_ready.csv")
    output_json_path = os.path.join(data_dir, f"momcafe_nlp_ready_{datetime.now().strftime('%Y%m%d')}.json")

    # CSV 저장 (인코딩 깨짐 방지 및 엑셀 호환 세팅)
    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    
    # JSON 백업 저장
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(df.to_dict(orient='records'), f, ensure_ascii=False, indent=4)

    print(f"\n[완료] NLP 정제 파일이 저장되었습니다.")
    print(f"  -> CSV 경로: {output_csv_path}")
    print(f"  -> JSON 경로: {output_json_path}")
    print("[안내] 다음 단계인 03_ad_post_filtering.py 파일로 진행하세요.")