# ==========================================
# 1. 파이썬 내장 표준 라이브러리
# ==========================================
import json
import os
import random
import re
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import parse_qs, quote, urlparse

# ==========================================
# 2. 외부 라이브러리
# ==========================================
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def init_driver():
    """네이버 카페 크롤링을 위한 안티 크롤링 우회 설정 포함 크롬 드라이버 초기화"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    
    # 백그라운드 실행을 원할 시 주석 해제 (생략 가능)
    # options.add_argument('--headless') 

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def crawl_smart_wait_posts(driver, keyword, start_page=1, end_page=5):
    """특정 키워드로 카페 게시글 목록 및 링크 수집"""
    post_links = []
    encoded_keyword = quote(keyword) 
    
    for page in range(start_page, end_page + 1):
        print(f"--- ['{keyword}'] {page}/{end_page} 페이지 검색 결과 수집 중 ---")
        
        try:
            driver.get("about:blank")
            time.sleep(1.0)
        except:
            pass
            
        # 6조 타깃 맘카페 주소 반영
        target_url = f"https://cafe.naver.com/f-e/cafes/10094499/menus/392?ta=SUBJECT&q={encoded_keyword}&page={page}"
        driver.get(target_url)
        
        try:
            try:
                driver.switch_to.alert.accept()
                time.sleep(1)
            except:
                pass
                
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.article"))
            )
            time.sleep(random.uniform(1.0, 2.0))  # 렌더링 후 안정적인 휴식
            
        except Exception as e:
            print(f"'{keyword}' {page}페이지 렌더링 지연 감지!")
            print("  [안내] 강제 새로고침(F5)으로 재시도 중...")
            driver.refresh()
            try:
                time.sleep(3)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.article"))
                )
            except:
                print("실패. 다음 페이지로 건너뜁니다.")
                continue
                
        # HTML 파싱
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        articles = soup.select('a.article')
             
        page_count = 0
        for title_element in articles:
            title = title_element.text.strip()
            if not title:
                continue
                
            raw_href = title_element.get('href', '')
            
            try:
                parsed_url = urlparse(raw_href)
                params = parse_qs(parsed_url.query)
                article_id = params.get('articleid', [None])[0]
                full_link = f"https://cafe.naver.com/f-e/{article_id}" if article_id else f"https://cafe.naver.com{raw_href}"
            except:
                full_link = f"https://cafe.naver.com{raw_href}"
            
            post_links.append({"title": title, "link": full_link})
            page_count += 1
                
        print(f"{page}페이지에서 '{keyword}' 관련 게시글 {page_count}개 확보 완료")
        
    return post_links


def crawl_pc_post_detail(driver, post_url):
    """게시글 상세 페이지 진입 후 본문, 작성일, 조회수, 댓글 데이터 추출"""
    detail_data = {"date": "", "view_count": "0", "content": "", "comments": []}
    
    try:
        driver.get(post_url)
        time.sleep(random.uniform(3.0, 4.5))  # 상세 글 진입 안전 대기 시간
        
        try:
            driver.switch_to.frame("cafe_main")
        except:
            pass
            
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 1. 메타 정보 (작성일 및 조회수) 추출
        date_el = soup.select_one('.article_date') or soup.select_one('.date')
        if date_el: 
            detail_data["date"] = date_el.text.strip()
        
        view_el = soup.select_one('.view_count') or soup.select_one('.count')
        if view_el: 
            detail_data["view_count"] = view_el.text.strip()
        
        # 2. 본문 텍스트 데이터 추출
        content_el = soup.select_one('.article_viewer') or soup.select_one('.ContentRenderer') or soup.select_one('div.se-component-content')
        if content_el: 
            detail_data["content"] = content_el.text.strip()
        
        # 3. 댓글 데이터 수집
        comment_els = soup.select('.comment_text_box') or soup.select('.text_comment') or soup.select('.comment_info')
        for comment in comment_els:
            comment_text = comment.text.strip()
            if comment_text:
                detail_data["comments"].append(comment_text)
                
    except Exception as e:
        print(f"{post_url} 예외 발생 (건너뜀): {e}")
        
    finally:
        try:
            driver.switch_to.default_content()
        except:
            pass
            
    return detail_data


# ==========================================
# 3. 메인 프로세스 실행부
# ==========================================
if __name__ == "__main__":
    driver = init_driver()
    print("[시스템] 크롬 브라우저가 성공적으로 실행되었습니다.")

    # 공공기관 시나리오(Pain-point 및 영양 성분) 기반 타깃 키워드
    target_keywords = [
        '입덧', '변비', '불면', '다리 저림', '빈혈', 
        '철분', '엽산', '오메가3', '비타민D', '유산균', '마그네슘', 
        '부작용', '같이 먹어도', '영양제 추천'
    ]
    all_posts = []

    print("[시작] [STEP 1] 게시글 목록 검색 및 링크 수집 시작")
    for kw in target_keywords:
        print(f"\n'{kw}' 키워드 검색 시작...")
        kw_posts = crawl_smart_wait_posts(driver, keyword=kw, start_page=1, end_page=5) 
        all_posts.extend(kw_posts)

    # 링크 기준 중복 게시글 제거
    unique_posts = list({post['link']: post for post in all_posts}.values())
    print(f"\n[완료] 중복 제거 후 최종 고순도 게시글 주소 {len(unique_posts)}개 확보 완료")

    # [STEP 2] 상세 내용 수집 진행
    final_dataset = []
    print(f"\n[시작] [STEP 2] 총 {len(unique_posts)}개 게시글 상세 내용 수집을 시작합니다.")

    for idx, post in enumerate(unique_posts):
        original_link = post['link']

        # 중복 URL 프로토콜 노이즈 정제
        if original_link.count("https://cafe.naver.com") >= 2:
            cleaned_link = "https://cafe.naver.com" + original_link.split("https://cafe.naver.com")[-1]
        else:
            cleaned_link = original_link

        print(f"[{idx+1}/{len(unique_posts)}] 수집 중: {post['title']}")
        detail = crawl_pc_post_detail(driver, cleaned_link)
        
        final_dataset.append({
            "title": post['title'],
            "url": cleaned_link,
            "date": detail['date'],
            "view_count": detail['view_count'],
            "content": detail['content'],
            "comments": detail['comments']  # 리스트 형태로 저장
        })

    # 브라우저 종료
    driver.quit()
    print("\n[완료] 전체 카페 데이터 수집 완료 및 브라우저 종료")

    # ==========================================
    # 4. 데이터 파이프라인 연결을 위한 파일 저장
    # ==========================================
    print("\n[저장] [STEP 3] 차기 정제 단계를 위한 데이터 저장 프로세스")
    df = pd.DataFrame(final_dataset)
    
    # 깃허브 협업 및 후속 스크립트 로드를 위해 파일명 명시
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    DATA_DIR = PROJECT_ROOT / "data_analysis" / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    output_filename = DATA_DIR / "momcafe_target_data.csv"
    
    # 리스트 데이터(comments)를 온전하게 보존하고, 인코딩 깨짐을 방지하기 위해 utf-8-sig 사용
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"[성공] 데이터가 '{output_filename}' 파일로 저장되었습니다. 02번 정제 파일로 진행하세요.")