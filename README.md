# 2026-1학기 데이터마이닝 6팀 기말프로젝트

서비스명 : 임산부 맞춤 증상 기반 영양소 및 영양제 추천 서비스

국가건강정보포털(KDCA)의 임산부 건강정보와 식품의약품안전처(MFDS) 공공데이터를 기반으로 임신 주차, 증상, 생활습관, 복용 중인 영양제 및 의약품 정보를 분석하여 맞춤형 영양소와 주의사항을 추천하는 서비스입니다.

# 프로젝트 개요
본 프로젝트는 임산부의 건강 상태에 따라 필요한 영양소를 추천하고, 복용 중인 영양제 및 의약품과의 중복 섭취를 방지하기 위해 개발되었습니다.

주요 기능은 다음과 같습니다.

○ 임신 주차 기반 임신 단계 판정 <br>
○ 증상 기반 영양소 추천 <br> 
○ 생활습관 기반 가중치 반영 <br>
○ 복용 중인 영양제·의약품 분석 <br>
○ 추천 이유 생성 <br>
○ 주의사항 생성 <br>
○ 추천 결과 PDF 저장 <br> 

# 프로젝트 구조 

```text
final_project/ 
│ 
├── .env                                         # OpenAI API Key 및 환경변수 설정 파일
├── README.md							         # 프로젝트 설명 문서
├── app.py 								         # Gradio 기반 임산부 영양 추천 서비스 실행 파일
├── requirement.txt 							 # 프로젝트 의존성 패키지 목록
├── pregnancy_nutrition.db 				         # 추천 규칙, 근거, 의약품, 영양제 등 모든 정보를 저장한 SQLite DB
├── test_case_prove.py 						     # 추천 서비스 엔진 자동 검증 모듈
├── test_case_prove_result.json		             # 추천 엔진 자동 검증 결과(PASS/FAIL) 저장 파일
├── schema.sql							         # SQLite 관계형 DB 테이블 구조 정의 및 초기 스키마 생성 파일
│
├── data_anlaysis/ 
│	 ├── data/
│	 │	 ├── momcafe_target_data.csv 			# STEP 1: 카페 크롤링 수집 원본 데이터셋 (98건)
│	 │	 ├── momcafe_nlp_ready.csv			    # STEP 2: 도메인 사전 기반 형태소 분석 완료본
│	 │	 ├── momcafe_final_purified.csv			# STEP 3: 광고성 노이즈 제거 최종 정제 분석본
│	 │	 └── momcafe_apriori_ruleset.csv		# STEP 4: 추천 엔진 매핑용 연관규칙 룰셋 DB
│	 │
│	 ├── images/
│	 │	 ├── Figure1.png			      # 최상위 단어 빈도 워드클라우드 이미지
│	 │	 └── Figure.png					  # 임신 주차별 카테고리 교차분석 히트맵 이미지
│	 │
│	 ├── 01_data_collection_crawling.py			# 안티크롤링 우회형 네이버 카페 데이터 수집 모듈
│	 ├── 02_text_data_preprocessing.py			# 사용자 정의 사전 기반 구어체 표준화 NLP 모듈
│	 ├── 03_ad_post_filtering.py				# 정규표현식 기반 상업성 스팸 데이터 격리 차단 모듈
│	 └── 04_data_mining_clustering.py			# K-Means 소비자 세분화 및 Apriori 알고리즘 모델링 모듈
│
├── data_process/ 
│	 ├── data/
│	 │	 ├──pdf/
│	 │	 │	 ├── 식이영양(임산부)_국가건강정보포털_질병관리청.pdf					        # 식이영양 원본  PDF 파일
│	 │	 │	 └── 정상임신관리(임신의 진단과 관리)_국가건강정보포털_질병관리청.pdf	        # 정상임신관리 원본 PDF 파일
│	 │	 │
│	 │	 └── raw/
│	 │	 	 ├── mfds_medicine_easy_drug_original.json								     # 공공데이터포털(e약은요) 의약품개요정보 원본 JSON 데이터
│	 │	 	 ├── mfds_medicine_permission_original.json							         # 공공데이터포털 의약품 제품 허가정보 원본 JSON 데이터
│	 │	 	 ├── mfds_medicine_raw.json										               # 식약처 의약품개요정보 및 의약품 허가정보 원본 데이터
│	 │	 	 ├── mfds_supplement_raw.json										               # 식약처 건강기능식품 품목제조 신고사항 원본 데이터
│	 │	 	 ├── 식이영양(임산부)_국가건강정보포털_질병관리청_raw.json					  # 임산부 식이영양 관리 정보 관련 json 파일
│	 │	 	 ├── 정상임신관리(임신의_진단과_관리)_국가건강정보포털_질병관리청_raw.json		   # 정상임신관리 관련 json 파일
│	 │	 	 ├── symptom_nutrient.csv										           # 근거 검증(PASS) 완료된 최종 증상-영양소 추천 데이터
│	 │	 	 └── symptom_nutrient_with_validation.csv								   # 근거 검증 결과(PASS/CHECK) 포함 전처리 검증용 데이터
│	 │	 
│	 │	 
│	 └── scripts/
│	 	 ├── 01_collect_data.py				        # 식약처 의약품 및 건강기능식품 공공데이터 수집·정제 모듈
│	 	 ├── 02_create_schema.py				      # SQLite DB 생성 및 schema.sql 기반 테이블 초기화 모듈
│	 	 ├── 03_load_relational_db.py			    # 전처리 완료 데이터를 관계형 DB 테이블에 적재하는 모듈
│	 	 ├── 04_validate_evidence.py			    # 추천 근거 문장 원문 일치 및 유사도 검증 모듈
│		 ├── 05_kdca_pdf_to_raw_json.py		    # 식이영양/정상임신관리 PDF 파일에서 json으로 변환 모듈
│		 └── 06_symptom_raw_to_csv.py			    # 임산부 원문 데이터를 분석하여 증상·영양소 추천 데이터 및 검증용 CSV 생성 모듈
│
├── recommendation/ 
│ 	 ├── db_repository.py 					      # SQLite DB 조회 및 데이터 로드 모듈
│ 	 ├── db_recommendation_engine.py 	    # 임산부 맞춤 영양소 추천 엔진 메인 모듈
│ 	 ├── db_symptom_engine.py 				    # 증상/생활습관 기반 영양소 추천 규칙 처리 모듈
│ 	 ├── db_caution_engine.py 				    # 주의사항 생성 및 영양제 추천 모듈
│ 	 ├── pregnancy_stage.py 					    # 임신 주차 기반 임신 단계 판정 모듈
│ 	 ├── llm_client.py 						        # LLM 기반 복용 정보 분석 및 결과 생성 모듈
│ 	 ├── pdf_exporter.py 					        # 추천 결과 PDF 저장 모듈
│ 	 ├── trace_logger.py 					        # 추천 과정 추적 및 로그 기록 모듈
│  	 └── utils.py 							          # 공통 유틸리티 함수 모음
│ 
├── ui/ 
│ 	 ├── gradio_ui.py 						        # 사용자 입력 및 결과 출력 UI 구성
│ 	 └── logo.png 						            # 홈페이지 첫 화면 로고 이미지
│ 	 
├── exports/ 								              # PDF 추천 결과 저장 폴더
└── logs/								                  # 추천 과정 Trace 로그 저장 폴더
```
