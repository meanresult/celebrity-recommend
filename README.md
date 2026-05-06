# insta_pipeline

Instagram tagged post 데이터를 수집하고, 브랜드 간 관심사 겹침을 분석한 뒤, TagScope에서 탐색할 수 있게 만드는 데이터 파이프라인입니다.

현재 공식 운영 기준은 `DuckDB + Airflow + dbt + TagScope`입니다.

- 저장: DuckDB 파일 `data/insta_pipeline.duckdb`
- 오케스트레이션: Airflow
- 변환: dbt
- 조회: TagScope (`FastAPI + Next.js`)

`Streamlit` / `Snowflake` 관련 설명은 현재 런타임이 아니라 과거 구조입니다. 레거시 맥락은 `docs/history/legacy_streamlit_snowflake.md`에만 남깁니다.

주요 문서:

- 현재 아키텍처: `docs/architecture/current_architecture.md`
- 설치 / 실행: `docs/operations/setup_and_run.md`
- 의존성 정책: `docs/operations/dependency_policy.md`
- 로컬 외부 공유: `docs/operations/local_public_share.md`

## 1. What Problem It Solves

이 프로젝트는 아래 질문에 답하기 위한 구조입니다.

- 특정 브랜드를 태그하는 유저들은 어떤 다른 브랜드에도 반응하는가
- 브랜드 간 잠재 고객층이 얼마나 겹치는가
- 공통 유저들이 추가로 자주 태그하는 브랜드는 무엇인가

핵심 아이디어는 단순 게시물 수집이 아니라, "누가 어떤 브랜드들을 함께 태그했는가"를 관계 데이터로 바꾸는 데 있습니다.

## 2. Official Architecture

```text
Instagram Tagged Posts
        |
        v
Playwright Extractor
        |
        v
Airflow Brand DAGs
        |
        v
DuckDB RAW_DATA.INSTAGRAM_POSTS
        |
        v
dbt models (STAGE / MART)
        |
        v
TagScope API
        |
        v
TagScope Web UI
```

현재 기준에서 중요한 점은 아래 4가지입니다.

1. Airflow 브랜드 DAG는 `configs/brands.yaml`을 읽어 동적으로 생성됩니다.
2. 적재 대상은 Snowflake가 아니라 DuckDB 파일입니다.
3. dbt도 같은 DuckDB 파일을 읽고 `STAGE`, `MART` 레이어를 만듭니다.
4. 최종 조회 경로는 Streamlit이 아니라 TagScope입니다.

## 3. Pipeline Flow

현재 파이프라인은 아래 순서로 동작합니다.

1. `configs/brands.yaml`에서 활성화된 브랜드 목록을 읽습니다.
2. Airflow가 브랜드별 DAG를 생성하고 스케줄링합니다.
3. `extractors/instagram_scraper.py`가 tagged post를 수집합니다.
4. 수집 결과를 임시 CSV로 저장한 뒤 DuckDB `RAW_DATA.INSTAGRAM_POSTS`에 UPSERT 합니다.
5. `transform_dbt_after_all_brands` DAG가 모든 활성 브랜드 DAG 완료를 기다립니다.
6. dbt `run/test`가 DuckDB 안의 `STAGE`, `MART` 모델을 갱신합니다.
7. TagScope backend가 DuckDB를 read-only로 조회하고, frontend가 이를 시각화합니다.

참고:

- DAG ID는 여전히 `insta_to_snowflake_dag_v5_*` 형태를 유지하지만, 실제 load task는 `load_to_duckdb`입니다.
- 이름은 과거 흔적이고, 현재 저장 대상은 DuckDB입니다.

## 4. Runtime Components

- Airflow UI: `http://localhost:8082`
- TagScope UI: `http://localhost:3000`
- TagScope API: `http://localhost:8000`
- API health check: `http://localhost:8000/health`

주의:

- `http://localhost:8000/`는 API 루트라서 `404`가 정상입니다.
- 화면 확인은 항상 `http://localhost:3000/taggers` 또는 `http://localhost:3000/co-brands` 기준으로 합니다.

## 5. Core Modules

- `configs/brands.yaml`
  현재 운영 브랜드와 스케줄의 source of truth
- `dags/brand_dags.py`
  브랜드 DAG 자동 등록
- `dags/instagram_brand_factory.py`
  브랜드별 ETL DAG 생성
- `dags/dbt_orchestrator.py`
  모든 활성 브랜드 DAG 완료 후 dbt `run/test` 실행
- `dags/utils/db.py`
  DuckDB 연결, CSV 적재, raw 테이블 초기화 유틸
- `extractors/instagram_scraper.py`
  현재 운영 기준 Instagram 크롤러
- `transform/insta_dbt/`
  DuckDB 대상 dbt 프로젝트
- `tagscope/backend/`
  FastAPI 조회 API
- `tagscope/frontend/`
  Next.js 기반 TagScope UI
- `secrets/save_state.py`
  Instagram 로그인 세션 저장 스크립트

## 6. Data Modeling

현재 모델 계층은 아래처럼 봅니다.

- `RAW_DATA.INSTAGRAM_POSTS`
  크롤러 원천 데이터
- `STAGE.group_by_tagged_post`
  한 게시물 안의 tagged account를 행 단위로 정규화
- `MART.account_tagged_accounts`
  계정별 태그 브랜드 집계
- `MART.cross_brand_accounts`
  공통 계정 기반 교차 브랜드 분석
- `MART.mart_brand_monthly_tagging`
  브랜드 월별 태깅 추이
- `MART.mart_co_brand_stats`
  브랜드별 태거 수 / 태그 수 사전 집계

즉, `RAW -> STAGE -> MART` 분리를 유지하면서 크롤러 로직과 분석 로직을 분리하는 구조입니다.

## 7. Repository Structure

```text
.
├── configs/brands.yaml          # 브랜드/스케줄 설정 source of truth
├── dags/                        # Airflow DAG 및 DuckDB 적재 로직
├── extractors/                  # 현재 운영 기준 Instagram crawler
├── transform/insta_dbt/         # dbt 프로젝트
├── tagscope/backend/            # FastAPI API
├── tagscope/frontend/           # Next.js UI
├── docker/                      # 서비스별 Dockerfile
├── data/                        # DuckDB 파일 저장 위치
├── docs/
│   ├── architecture/            # 현재 아키텍처 / 프로젝트 요약
│   ├── operations/              # 설치, 실행, Airflow runbook, 의존성 정책
│   ├── product/                 # TagScope 스토리보드 / UI 레퍼런스
│   └── history/                 # 레거시 기록 / 회고 / 과거 트러블슈팅
└── secrets/                     # storage_state.json 등 민감 파일
```

## 8. Local Setup

사전 준비:

- Docker Desktop
- Docker Compose v2
- Instagram 로그인 정보

현재 공식 흐름에는 Snowflake 계정이 필요하지 않습니다.

루트 `.env` 예시:

```env
ID=<instagram_username_or_email>
PW=<instagram_password>

HOST_PROJECT_ROOT=/absolute/path/to/insta_pipeline
AIRFLOW_PROJ_DIR=.
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
```

설명:

- `ID`, `PW`: Instagram 세션 저장용 로그인 정보
- `HOST_PROJECT_ROOT`: Airflow의 DockerOperator가 호스트 경로를 mount 할 때 사용
- `AIRFLOW_UID`: Airflow 컨테이너 파일 권한 정합성용

현재 공식 런타임에서 `SNOWFLAKE_*` 값은 필요하지 않습니다.

## 9. How To Run

Instagram 세션 저장:

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 secrets/save_state.py
```

전체 서비스 시작:

```bash
docker compose up -d --build
```

상태 확인:

```bash
docker compose ps
```

Airflow DAG 목록 확인:

```bash
docker compose exec -T airflow airflow dags list
```

dbt 수동 실행:

```bash
docker compose run --rm dbt run
docker compose run --rm dbt test
```

## 10. Operational Notes

- `configs/brands.yaml`이 DAG 생성과 TagScope 브랜드 목록의 공통 기준입니다.
- `schedule`은 UTC cron 문자열이며, 한국 시간은 `+9시간`으로 해석합니다.
- transform DAG는 활성 브랜드 중 가장 늦은 ETL 시각보다 `30분 뒤`에 실행됩니다.
- TagScope backend는 `data/insta_pipeline.duckdb`를 read-only로 읽습니다.
- `secrets/storage_state.json`은 민감 세션 파일이므로 커밋하면 안 됩니다.

## 11. Legacy Boundary

Streamlit / Snowflake 구조는 현재 운영 기준이 아니며, 관련 히스토리는 `docs/history/legacy_streamlit_snowflake.md`에만 남깁니다.
