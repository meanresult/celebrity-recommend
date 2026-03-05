# insta_pipeline

Instagram 태그 데이터를 수집해 Snowflake에 적재하고, dbt로 변환한 뒤 Streamlit 대시보드로 조회하는 데이터 파이프라인입니다.

## 1. 프로젝트 개요

- Orchestration: Airflow (Docker)
- Extract: Playwright 기반 Instagram 크롤러
- Load: Snowflake `RAW_DATA.INSTAGRAM_POSTS` 적재
- Transform: dbt 모델 (`transform/insta_dbt`)
- Serve: Streamlit 대시보드

현재 운영 흐름은 대략 아래와 같습니다.

1. 브랜드별 Airflow DAG가 Instagram 태그 게시물을 수집
2. CSV 임시 파일 생성 후 Snowflake에 `MERGE` 업서트
3. 브랜드 DAG 완료 후 dbt `run/test` 실행
4. Streamlit에서 변환 테이블 조회

## 2. 디렉터리 구조

```text
.
├── dags/                      # Airflow DAG
├── extractors/                # Playwright 크롤러
├── transform/insta_dbt/       # dbt 프로젝트
├── streamlit/                 # Streamlit 앱
├── docker/                    # 서비스별 Dockerfile
├── docker-compose.yaml        # 로컬 통합 실행
└── secrets/                   # 세션 파일 등 민감 파일(커밋 금지)
```

## 3. 사전 준비

- Docker Desktop
- Docker Compose v2
- Snowflake 계정/권한
- Instagram 로그인 정보(크롤러용)

## 4. 환경변수(.env) 관리 원칙

`.env`에는 **실제 비밀번호/토큰이 들어가므로 절대 커밋하지 않습니다.**

실무에서는 보통 아래 두 파일을 운영합니다.

- `.env` : 실제 값 (로컬 전용, Git 제외)
- `.env.example` : 키만 공개 (샘플/플레이스홀더)

예시(`.env.example`):

```env
# Snowflake
SNOWFLAKE_ACCOUNT=<your_account>
SNOWFLAKE_USER=<your_user>
SNOWFLAKE_PASSWORD=<your_password>
SNOWFLAKE_ROLE=<your_role>
SNOWFLAKE_WAREHOUSE=<your_warehouse>
SNOWFLAKE_DATABASE=<your_database>
SNOWFLAKE_SCHEMA=<your_schema>

# Instagram crawler
ID=<instagram_username_or_email>
PW=<instagram_password>

# Airflow/Docker
HOST_PROJECT_ROOT=/absolute/path/to/insta_pipeline
AIRFLOW_PROJ_DIR=.
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
```

## 5. 실행 방법

### 5.1 컨테이너 시작

```bash
docker compose up -d --build
```

### 5.2 접속

- Airflow: `http://localhost:8082`
- Streamlit: `http://localhost:8501`

### 5.3 컨테이너 상태 확인

```bash
docker compose ps
```

## 6. Airflow Connection 설정

이 프로젝트 DAG는 Snowflake 연결 ID로 `snowflake_conn`을 사용합니다.

Airflow UI에서 아래 경로로 설정합니다.

1. `Admin` -> `Connections`
2. `+` 버튼으로 신규 Connection 생성
3. `Conn Id`: `snowflake_conn`
4. `Conn Type`: `Snowflake`
5. 계정/유저/비밀번호/Role/Warehouse/Database/Schema 입력

## 7. 주요 DAG

- `insta_to_snowflake_dag_v4_amomento`
- `insta_to_snowflake_dag_v4_cos`
- `insta_to_snowflake_dag_v4_lemaire`
- `transform_dbt_after_all_brands`

## 8. 트러블슈팅

- IDE에서 `import airflow`가 빨간 줄:
  - 정상일 수 있습니다. 런타임은 Docker 컨테이너이고, IDE는 로컬 인터프리터를 보기 때문입니다.
- Snowflake 연결 실패:
  - Airflow `Connections`에 `snowflake_conn` 존재 여부 확인
  - `.env`의 Snowflake 변수 오타 확인
- 크롤링 실패:
  - Instagram 로그인 상태(`secrets/storage_state.json`) 만료 여부 확인
  - 페이지 구조 변경 시 selector 업데이트 필요

## 9. 보안 가이드

- `.env`, `secrets/`, 로그 파일에 민감정보가 남지 않도록 관리
- 실제 계정 비밀번호는 README/이슈/채팅에 공유 금지
- 가능하면 비밀번호 대신 시크릿 매니저 또는 Airflow Secret Backend 사용
