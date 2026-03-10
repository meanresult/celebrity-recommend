# insta_pipeline

Instagram 태그 데이터를 수집해 브랜드 간 관심사 겹침과 연관 브랜드를 분석하는 데이터 파이프라인 프로젝트입니다.  
단순 크롤링 스크립트가 아니라, `수집 -> 적재 -> 변환 -> 조회` 흐름을 Airflow, Snowflake, dbt, Streamlit으로 분리해 실무형 데이터 파이프라인 구조를 직접 구성하는 데 초점을 뒀습니다.

## 1. What Problem It Solves

브랜드 마케팅이나 콘텐츠 분석에서는 아래 질문이 자주 나옵니다.

- 특정 브랜드를 태그하는 유저들은 어떤 다른 브랜드에도 반응하는가
- 브랜드 간 잠재 고객층이 얼마나 겹치는가
- 자사와 비슷한 취향군이 함께 언급하는 브랜드는 무엇인가

이 프로젝트는 Instagram tagged post 데이터를 기반으로 위 질문에 답할 수 있는 분석용 데이터셋을 만드는 것을 목표로 합니다.

핵심 아이디어는 다음과 같습니다.

1. 브랜드 계정을 태그한 게시물을 수집한다.
2. 게시물 작성 계정과 함께 태그된 브랜드 정보를 정규화한다.
3. 브랜드 교집합 계정과 연관 브랜드를 계산한다.
4. Streamlit 대시보드에서 탐색형 분석이 가능하도록 제공한다.

## 2. Why This Project Matters

이 프로젝트는 작은 규모이지만, 실무 데이터 엔지니어링에서 자주 나오는 고민을 담고 있습니다.

- 외부 서비스 데이터를 안정적으로 수집하는 방법
- 스케줄링과 적재를 분리해서 운영하는 방법
- raw 데이터와 분석용 모델을 분리하는 방법
- 분석 결과를 단순 테이블이 아닌 데이터 제품 형태로 보여주는 방법

즉, "데이터를 모았다"보다 "분석 가능한 구조로 운영해보려 했다"에 더 가깝습니다.

## 3. Architecture

```text
Instagram Tagged Posts
        |
        v
Playwright Extractor
        |
        v
Airflow DAGs
        |
        v
Snowflake RAW_DATA.INSTAGRAM_POSTS
        |
        v
dbt models (stage / marts)
        |
        v
Streamlit Dashboard
```

구성 요소는 아래와 같습니다.

- Orchestration: Airflow
- Extract: Playwright 기반 Instagram crawler
- Load: Snowflake 적재
- Transform: dbt 모델링
- Serve: Streamlit 대시보드

## 4. Pipeline Flow

현재 파이프라인은 아래 순서로 동작합니다.

1. 브랜드별 Airflow DAG가 tagged post를 수집합니다.
2. 크롤러 결과를 CSV 임시 파일로 저장합니다.
3. Snowflake raw 테이블에 적재합니다.
4. 모든 브랜드 DAG 완료 후 dbt `run/test`를 수행합니다.
5. Streamlit에서 변환된 결과를 조회합니다.

주요 DAG:

- `insta_to_snowflake_dag_v4_amomento`
- `insta_to_snowflake_dag_v4_cos`
- `insta_to_snowflake_dag_v4_lemaire`
- `transform_dbt_after_all_brands`

## 5. Data Modeling Intent

이 프로젝트는 raw와 analytics 레이어를 분리하려고 설계했습니다.

- Raw:
  수집한 Instagram post 원본 성격의 데이터 저장
- Stage:
  tagged account 기준 정리, 중복 제거, 분석 전처리
- Mart:
  cross-brand account, 연관 브랜드 집계 등 분석 목적 테이블 제공

이 구조를 통해 크롤러 로직과 분석 로직을 분리하고, dbt에서 비즈니스 로직을 관리하려고 했습니다.

## 6. Dashboard Intent

대시보드는 단순 조회보다 아래 질문을 빠르게 확인하기 위한 용도입니다.

- 선택한 브랜드를 함께 태그한 계정은 누구인가
- 그 계정들이 추가로 자주 태그하는 브랜드는 무엇인가
- 브랜드 간 audience overlap을 어떤 방향으로 해석할 수 있는가

즉, 최종 사용자는 raw 데이터가 아니라 "비슷한 취향의 사람들은 무엇을 같이 좋아하는가"라는 질문에 가까운 결과를 보게 됩니다.

## 7. Engineering Decisions

이 프로젝트에서 실무적으로 가져가려 했던 의사결정은 아래와 같습니다.

### 7.1 수집 / 적재 / 변환 / 조회 분리

한 파일에서 모든 작업을 처리하지 않고 역할을 나눴습니다.

- 크롤링: `extractors/`
- 스케줄링: `dags/`
- 모델링: `transform/insta_dbt/`
- 대시보드: `streamlit/`

이렇게 분리하면 각 레이어를 독립적으로 수정하거나 교체하기 쉽습니다.

### 7.2 브랜드별 DAG 분리

브랜드별 크롤링 실패가 전체 파이프라인 장애로 바로 이어지지 않도록 DAG를 나눴습니다.  
이후 transform DAG에서 모든 브랜드 적재 완료를 기다린 뒤 dbt를 실행하는 흐름을 구성했습니다.

### 7.3 dbt로 분석 로직 분리

집계 SQL을 애플리케이션 코드에 직접 넣기보다 dbt 모델로 분리하려고 했습니다.  
이 접근은 이후 테스트 추가, 모델 문서화, lineage 파악에 유리합니다.

### 7.4 컨테이너별 런타임 분리

Airflow, dbt, Streamlit은 성격이 다른 런타임이므로 의존성을 별도 파일로 관리합니다.

- `requirements.txt`
- `requirements_dbt.txt`
- `requirements_streamlit.txt`

반면 `pyproject.toml`과 `uv.lock`은 로컬 개발환경 재현용으로만 사용합니다.

## 8. Practical Improvements I Worked Toward

실무적인 완성도를 높이기 위해 아래 방향으로 구조를 다듬고 있습니다.

- 현재 운영 extractor만 `extractors/`에 남기고, 과거 버전은 `legacy/`로 분리
- Streamlit 앱을 query/service, domain, presentation 레이어로 분리
- 의존성 기준을 컨테이너 런타임과 로컬 개발환경으로 구분
- 수집/적재 로직에서 중복 체크, staging 적재, dbt 후속 실행 흐름 반영

아직 개선 중인 영역도 분명합니다.

- SQL 문자열 조합을 더 안전하게 바꾸기
- 구조화 로그와 알림 체계 추가
- dbt test 확대
- 크롤러 retry / screenshot / selector version 관리 강화
- CI/CD와 secret 관리 표준화

즉, 이 프로젝트는 완성된 production system이라기보다, production에 가깝게 설계하려는 방향성과 개선 흔적을 보여주는 프로젝트입니다.

## 9. Repository Structure

```text
.
├── dags/                      # Airflow DAG
├── extractors/                # 현재 운영 기준 extractor
├── legacy/                    # 과거 버전 및 실험본 보관
├── transform/insta_dbt/       # dbt 프로젝트
├── streamlit/                 # Streamlit 앱
├── docker/                    # 서비스별 Dockerfile
├── docker-compose.yaml        # 로컬 통합 실행
├── docs/                      # 리뷰 및 정책 문서
└── secrets/                   # 세션 파일 등 민감 파일(커밋 금지)
```

## 10. Local Setup

사전 준비:

- Docker Desktop
- Docker Compose v2
- Snowflake 계정/권한
- Instagram 로그인 정보

`.env` 예시:

```env
SNOWFLAKE_ACCOUNT=<your_account>
SNOWFLAKE_USER=<your_user>
SNOWFLAKE_PASSWORD=<your_password>
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=FSH
SNOWFLAKE_SCHEMA=STAGE

ID=<instagram_username_or_email>
PW=<instagram_password>

HOST_PROJECT_ROOT=/absolute/path/to/insta_pipeline
AIRFLOW_PROJ_DIR=.
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
```

위 Snowflake 값은 현재 프로젝트 기준의 예시 기본값입니다.

- `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`는 각자 환경에 맞게 변경할 수 있습니다.
- 개발 편의상 `ACCOUNTADMIN`을 예시로 적었지만, 실제 운영이나 협업 환경에서는 필요한 권한만 가진 전용 role 사용을 권장합니다.
- 실제 비밀번호나 계정 값이 들어간 `.env`는 커밋하지 않고, 문서에는 변수명과 예시값만 남깁니다.

의존성 관리 기준:

- `requirements*.txt`는 각 Docker 컨테이너의 런타임 의존성 기준입니다.
- `pyproject.toml`과 `uv.lock`은 로컬 개발환경 재현용입니다.
- 런타임 패키지 변경 시에는 먼저 해당 `requirements*.txt`를 수정합니다.

## 11. How To Run

컨테이너 시작:

```bash
docker compose up -d --build
```

접속:

- Airflow: `http://localhost:8082`
- Streamlit: `http://localhost:8501`

상태 확인:

```bash
docker compose ps
```

## 12. Airflow Connection

이 프로젝트는 Snowflake 연결 ID로 `snowflake_conn`을 사용합니다.

1. Airflow UI `Admin -> Connections`
2. 신규 Connection 생성
3. `Conn Id`: `snowflake_conn`
4. `Conn Type`: `Snowflake`
5. account / user / password / role / warehouse / database / schema 입력

## 13. Operational Considerations

운영 관점에서 특히 신경 쓴 부분은 아래와 같습니다.

- 크롤러 세션 파일을 `secrets/`로 분리
- raw 적재 후 dbt를 후속 단계로 분리
- 브랜드별 DAG 분리로 장애 범위 축소
- legacy 코드와 운영 코드를 분리해 기준 코드 명확화

추가 보완이 필요한 부분:

- Airflow 및 crawler 로그 구조화
- 장애 알림
- data quality test 확대
- secret backend 도입
- 배포 자동화

## 14. Limitations

이 프로젝트는 공개 API가 아닌 웹 UI 기반 크롤링을 사용하므로 아래 제약이 있습니다.

- 외부 서비스 구조 변경에 민감함
- 로그인 세션 만료 가능성 존재
- selector 변경 시 수집 실패 가능
- 운영 환경에서는 재시도, 스크린샷, 실패 증적 관리가 더 강화되어야 함

이 한계를 인지하고, 수집 로직과 분석 레이어를 분리해 영향 범위를 줄이는 방향으로 설계했습니다.

## 15. What This Project Shows

이 프로젝트를 통해 보여주고 싶은 역량은 아래와 같습니다.

- 외부 데이터 수집 파이프라인 설계
- Airflow 기반 orchestration
- Snowflake 적재 및 dbt 모델링 분리
- 분석 결과를 대시보드로 제공하는 end-to-end 흐름
- 실무형 구조로 리팩터링하고 운영 관점 문제를 식별하는 능력

완벽한 운영 시스템을 만들었다기보다,  
"단순 분석 스크립트"에서 출발해 "운영 가능한 데이터 파이프라인"에 가깝게 옮겨가려는 엔지니어링 판단과 개선 과정을 담은 프로젝트입니다.
