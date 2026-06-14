# ==========================================
# 1. 파이썬 내장 표준 라이브러리
# ==========================================
import ast
import os
import re
from collections import Counter

# ==========================================
# 2. 외부 라이브러리
# ==========================================
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
from pathlib import Path

# 시각화 한글 폰트 및 마이너스 기호 환경 설정
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False


def determine_stage(row):
    """제목과 본문의 주차/개월 키워드를 기반으로 임신 단계를 분류하는 함수"""
    text = str(row['title']) + " " + str(row['content'])
    weeks = re.findall(r'(\d+)\s*주', text)
    if weeks:
        w = int(weeks[0])
        if w <= 13: return '초기'
        elif w <= 27: return '중기'
        else: return '후기'
    months = re.findall(r'(\d+)\s*개월', text)
    if months:
        m = int(months[0])
        if m <= 3: return '초기'
        elif m <= 7: return '중기'
        else: return '후기'
    if '초기' in text or '7주' in text or '8주' in text or '엽산' in text: return '초기'
    if '중기' in text or '철분' in text or '임당' in text: return '중기'
    if '후기' in text or '막달' in text or '출산' in text or '만삭' in text: return '후기'
    return '초기'


def calculate_neg_sentiment(text, neg_words_list):
    """본문 내 부정 감성 단어의 출현 빈도를 계산하는 함수"""
    return sum(1 for w in neg_words_list if w in str(text))


# ==========================================
# 3. 메인 프로세스 실행부
# ==========================================
if __name__ == "__main__":
    print("[시스템] 6조 데이터 마이닝 및 통계 분석 파이프라인을 가동합니다.")

    # -------------------------------------------------------------
    # BLOCK 1: 데이터 로드 및 전처리 결합
    # -------------------------------------------------------------
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    data_dir = PROJECT_ROOT / "data_analysis" / "data"
    input_filename = os.path.join(data_dir, "momcafe_final_purified.csv")

    if not os.path.exists(input_filename):
        raise FileNotFoundError(f"[오류] 전 단계의 결과물인 '{input_filename}' 파일을 찾을 수 없습니다. 03번 파일을 먼저 실행하세요.")

    df = pd.read_csv(input_filename)
    print(f"[로드 완료] 최종 유효 데이터 표본 개수: {df.shape[0]}개")

    # CSV에 텍스트(문자열)로 저장된 리스트를 실제 파이썬 리스트 객체로 복원
    df['content_keywords'] = df['content_keywords'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
    df['comments_keywords'] = df['comments_keywords'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

    # 글 1개당 전체 문맥 파악을 위해 본문 및 댓글 키워드 병합
    df['all_keywords'] = df['content_keywords'] + df['comments_keywords']
    # 중복 카운트 방지를 위한 고유 키워드 셋 생성
    df['unique_keywords'] = df.apply(lambda row: set(row['content_keywords'] + row['comments_keywords']), axis=1)
    # TF-IDF 벡터화용 텍스트 문장 생성
    df['joined_keywords'] = df['all_keywords'].apply(lambda x: " ".join(x) if isinstance(x, list) else "")

    # -------------------------------------------------------------
    # BLOCK 2: 탐색적 데이터 분석 (워드클라우드)
    # -------------------------------------------------------------
    print("\n[분석 1] 핵심 키워드 기반 시각화 워드클라우드 생성 중...")
    all_words = [word for keywords in df['all_keywords'] if isinstance(keywords, list) for word in keywords]
    counter = Counter(all_words)

    font_path = 'c:/Windows/Fonts/malgun.ttf'
    wc = WordCloud(font_path=font_path, background_color='white', width=1000, height=600, max_words=100, colormap='Set2')
    cloud = wc.generate_from_frequencies(counter)

    plt.figure(figsize=(12, 8))
    plt.imshow(cloud, interpolation='bilinear')
    plt.axis('off')
    plt.title('맘카페 임산부 키워드 워드클라우드', fontsize=18)
    plt.show()

    # -------------------------------------------------------------
    # BLOCK 3: 고급 머신러닝 데이터 마이닝 (K-Means 및 단계별 분석)
    # -------------------------------------------------------------
    print("\n[분석 2] TF-IDF 기반 가상 페르소나 설정을 위한 유저 군집화 분할 중...")
    vectorizer = TfidfVectorizer(max_features=100)
    X = vectorizer.fit_transform(df['joined_keywords'])

    kmeans = KMeans(n_clusters=4, random_state=42)
    df['cluster'] = kmeans.fit_predict(X)

    order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
    terms = vectorizer.get_feature_names_out()

    cluster_names = {
        0: "Cluster 0 [변비/유산균 루틴 해결형 - 중기 시나리오 매핑]",
        1: "Cluster 1 [빈혈 수치 집중 의료케어형 - 후기 시나리오 매핑]",
        2: "Cluster 2 [초기 입덧/처방 고충형 - 초기 시나리오 매핑]",
        3: "Cluster 3 [복합 영양제 웰니스 관리형 - 최다 검색 일상 질의군]"
    }

    print(" -> K-Means 알고리즘 기반 소비자 세분화 및 페르소나 매핑 결과:")
    for i in range(4):
        top_terms = [terms[ind] for ind in order_centroids[i, :6]]
        cluster_size = len(df[df['cluster'] == i])
        print(f"   * 군집 번호 {i} (데이터 표본 수: {cluster_size}개)")
        print(f"     -> 임시 설정 명칭: {cluster_names[i]}")
        print(f"     -> 도출된 핵심 형태소: {', '.join(top_terms)}")
        print("-" * 60)

    print("\n[분석 3] 주차별 텍스트 정제 기반 임신 단계별 관심사 교차 분석 중...")
    df['stage'] = df.apply(determine_stage, axis=1)

    # [수정] 분석 대상 키워드 목록에서 '다리', '저림' 파편을 '다리저림' 단일 명사로 통합 세팅
    symptoms = ['입덧', '변비', '불면', '다리저림', '빈혈', '소화불량']
    nutrients = ['철분', '엽산', '오메가', '비타민', '유산균', '마그네슘']
    target_analysis_keywords = symptoms + nutrients

    stage_data = []
    for stage in ['초기', '중기', '후기']:
        sub_df = df[df['stage'] == stage]
        stage_counts = {s: 0 for s in target_analysis_keywords}
        for kw_set in sub_df['unique_keywords']:
            if isinstance(kw_set, set):
                for s in target_analysis_keywords:
                    if s in kw_set:
                        stage_counts[s] += 1
        stage_counts['stage'] = stage
        stage_data.append(stage_counts)

    df_stage = pd.DataFrame(stage_data).set_index('stage')
    df_stage_norm = df_stage.div(df_stage.sum(axis=1), axis=0)

    # 시각화 2: 임신 단계별 관심사 교차 분석 히트맵
    plt.figure(figsize=(14, 5.5))
    sns.heatmap(df_stage_norm, annot=df_stage, fmt='d', cmap='YlGnBu', linewidths=.5)
    plt.title('임신 단계별(초기/중기/후기) 주요 증상 및 영양소 교차 분석 빈도', fontsize=14, pad=15)
    plt.xlabel('정제 형태소 키워드', fontsize=11, labelpad=10)
    plt.ylabel('임신 단계', fontsize=11)
    plt.tight_layout()
    plt.show()

    # -------------------------------------------------------------
    # BLOCK 4: 추천 가이드 룰셋 구축 및 리스크 마이닝 (Apriori & 심층 통계)
    # -------------------------------------------------------------
    print("\n[분석 4] 복약 가이드 구축을 위한 연관 규칙 분석(Apriori) 가동 중...")
    transactions = df['all_keywords'].apply(lambda x: list(set(x)) if isinstance(x, list) else []).tolist()

    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df_trans = pd.DataFrame(te_ary, columns=te.columns_)

    frequent_itemsets = apriori(df_trans, min_support=0.01, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.5)

    # [수정] Apriori 타깃 검색 키워드 리스트에서도 '다리', '저림'을 '다리저림'으로 병합 완료
    target_keywords = [
        '입덧', '변비', '불면', '다리저림', '빈혈', 
        '철분', '엽산', '오메가', '오메가3', '비타민D', '유산균', '마그네슘', 
        '부작용', '추천'
    ]

    all_rules_list = []
    print(" -> 타깃 증상/성분별 매핑 룰셋 추출 결과:")
    for keyword in target_keywords:
        keyword_rules = rules[rules['antecedents'].apply(lambda x: keyword in x)]
        top_rules = keyword_rules.sort_values(by='lift', ascending=False).head(5)
        
        if not top_rules.empty:
            print(f"   * [{keyword}] 연관 규칙 검색 성공 (상위 {len(top_rules)}개 매핑 완료)")
            top_rules['target_keyword'] = keyword
            all_rules_list.append(top_rules)

    if all_rules_list:
        final_rules_df = pd.concat(all_rules_list, ignore_index=True)
        final_rules_df = final_rules_df[['target_keyword', 'antecedents', 'consequents', 'support', 'confidence', 'lift']]
        
        rules_save_path = os.path.join(data_dir, "momcafe_apriori_ruleset.csv")
        final_rules_df.to_csv(rules_save_path, index=False, encoding='utf-8-sig')
        print(f" -> 시나리오 연동용 데이터베이스 룰셋 저장 완료: {rules_save_path}")

    print("\n======================================================================")
    print("[종료] 데이터 분석가 파트의 모든 알고리즘 파이프라인 빌드가 정상 완료되었습니다.")
    print("======================================================================")