## insta_pipeline 설치 및 실행 가이드

이 문서는 현재 공식 운영 구조인 `DuckDB + Airflow + dbt + TagScope` 기준으로 로컬 실행 방법을 정리한 안내서입니다.

현재 공식 흐름:

1. Instagram tagged post 수집
2. DuckDB raw 적재
3. dbt 변환
4. TagScope 조회

중요:

- 현재 공식 조회 경로는 `TagScope`입니다.
- 과거 `Snowflake` / `Streamlit` 문서는 현재 런타임 설명이 아닙니다.

---

## 1. 먼저 준비할 것

필수 준비물:

1. Docker Desktop
2. Instagram 로그인 정보
3. 이 프로젝트 폴더

왜 필요한가:

- Docker가 없으면 Airflow / dbt / TagScope가 안 뜹니다.
- Instagram 로그인 정보와 세션이 없으면 tagged 페이지 접근이 막힙니다.

현재 공식 런타임에는 Snowflake 계정이 필요하지 않습니다.

---

## 2. `.env` 파일 만들기

프로젝트 루트에 `.env` 파일을 만듭니다.

예시:

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

- `ID`, `PW`
  Instagram 로그인 정보입니다.
- `HOST_PROJECT_ROOT`
  Airflow 안에서 dbt DockerOperator가 호스트 경로를 mount 할 때 사용합니다.
- `AIRFLOW_UID`
  Airflow 컨테이너 파일 권한용입니다.

중요:

- 현재 공식 런타임에서 `SNOWFLAKE_*` 값은 필요하지 않습니다.
- `.env`는 절대 Git에 커밋하지 않습니다.

---

## 3. Instagram 세션 파일 준비

이 프로젝트는 [storage_state.json](/Users/jeehun/Desktop/insta_pipeline/secrets/storage_state.json)을 사용합니다.

이 파일은 Instagram 로그인 상태를 저장하는 파일입니다.

처음 세팅하거나 세션이 만료된 경우 직접 만들어야 합니다.

### 3-1. 프로젝트 폴더로 이동

```bash
cd /Users/jeehun/Desktop/insta_pipeline
```

### 3-2. 로컬에서 한 번만 필요한 패키지 설치

`save_state.py`는 로컬 브라우저를 직접 띄우는 스크립트입니다.

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

### 3-3. `.env` 확인

`save_state.py`는 프로젝트 루트의 `.env`에서 아래 값을 읽습니다.

```env
ID=<instagram_username_or_email>
PW=<instagram_password>
```

이 값이 비어 있으면 세션 파일을 만들 수 없습니다.

### 3-4. 세션 저장 실행

```bash
python3 secrets/save_state.py
```

정상 완료 메시지 예시:

```bash
✅ 저장 완료: /Users/jeehun/Desktop/insta_pipeline/secrets/storage_state.json
```

실패 시 확인할 파일:

- [login_failed.png](/Users/jeehun/Desktop/insta_pipeline/secrets/login_failed.png)

세션 파일이 없거나 만료되면:

- tagged 페이지가 로그인 화면으로 리다이렉트될 수 있습니다.
- 크롤링이 실패할 수 있습니다.

---

## 4. 브랜드 설정 확인

현재 운영 브랜드와 스케줄의 source of truth는 [brands.yaml](/Users/jeehun/Desktop/insta_pipeline/configs/brands.yaml)입니다.

여기서 확인할 값:

- `brand_key`
- `instagram_id`
- `dag_id`
- `schedule`
- `enabled`

주의:

- `schedule`은 UTC cron입니다.
- 한국 시간(KST)은 `+9시간`으로 해석합니다.
- `enabled: false`인 브랜드는 DAG이 생성되지 않습니다.

---

## 5. Docker로 서비스 실행

터미널에서 프로젝트 루트로 이동한 뒤 실행합니다.

```bash
cd /Users/jeehun/Desktop/insta_pipeline
docker compose up -d --build
```

상태 확인:

```bash
docker compose ps
```

현재 공식적으로 확인할 서비스:

- `airflow`
- `dbt`
- `tagscope-backend`
- `tagscope-frontend`

참고:

- 저장소 정리 전이라 Compose에 레거시 서비스가 일부 남아 있을 수 있습니다.
- 그래도 현재 확인 기준 URL은 항상 `3000/8000/8082`입니다.

---

## 6. 접속 URL

현재 운영 기준 URL:

1. Airflow: [http://localhost:8082](http://localhost:8082)
2. TagScope UI: [http://localhost:3000/taggers](http://localhost:3000/taggers)
3. TagScope Co-Brands: [http://localhost:3000/co-brands](http://localhost:3000/co-brands)
4. TagScope API health: [http://localhost:8000/health](http://localhost:8000/health)

중요:

- [http://localhost:8000/](http://localhost:8000/)는 API 루트라서 `404 Not Found`가 정상입니다.
- UI 확인은 반드시 `3000` 포트 기준으로 봅니다.

---

## 7. Airflow에서 확인할 것

### 7-1. DAG 목록 확인

```bash
docker compose exec -T airflow airflow dags list
```

브랜드 DAG와 transform DAG가 보여야 합니다.

예:

- `insta_to_snowflake_dag_v5_amomento`
- `insta_to_snowflake_dag_v5_cos`
- `transform_dbt_after_all_brands`

주의:

- DAG ID prefix에 `snowflake`가 남아 있어도 실제 적재 대상은 DuckDB입니다.
- 실제 load task 이름은 `load_to_duckdb`입니다.

### 7-2. 로그 확인

```bash
docker compose logs -f airflow
```

브랜드 DAG 안에서는 아래 순서를 확인합니다.

1. `print_run_date`
2. `extract_instagram_data`
3. `load_to_duckdb`

transform DAG 안에서는 아래를 확인합니다.

1. 각 `wait__...__load_to_duckdb` sensor
2. `dbt_run`
3. `dbt_test`

---

## 8. dbt 수동 실행

필요하면 아래처럼 직접 실행할 수 있습니다.

```bash
docker compose run --rm dbt run
docker compose run --rm dbt test
```

dbt는 [profiles.yml](/Users/jeehun/Desktop/insta_pipeline/transform/insta_dbt/profiles.yml)을 통해 DuckDB를 사용합니다.

기본 경로:

- `/opt/airflow/data/insta_pipeline.duckdb`

---

## 9. 데이터 위치

현재 공식 저장 위치는 아래 파일입니다.

- [insta_pipeline.duckdb](/Users/jeehun/Desktop/insta_pipeline/data/insta_pipeline.duckdb)

이 파일을 아래 컴포넌트가 함께 사용합니다.

1. Airflow ETL
2. dbt
3. TagScope backend

즉, 현재 구조는 "중앙 분석 DB 한 개"가 아니라 "공유 DuckDB 파일 한 개"를 기준으로 움직입니다.

---

## 10. TagScope에서 확인할 것

화면에서 먼저 확인할 경로:

1. [http://localhost:3000/taggers](http://localhost:3000/taggers)
2. [http://localhost:3000/co-brands](http://localhost:3000/co-brands)

정상 기준:

- 상단 freshness 영역이 보인다.
- 브랜드 목록이 로드된다.
- 태거 / 공통 태그 브랜드 테이블이 응답한다.

백엔드 헬스체크:

```bash
curl http://localhost:8000/health
```

정상 응답:

```json
{"status":"ok"}
```

---

## 11. 자주 헷갈리는 포인트

### 11-1. 왜 `localhost:8000`에서 화면이 안 보이나?

`8000`은 TagScope backend API 포트입니다. 웹 화면은 `3000`에서 봅니다.

### 11-2. 왜 DAG 이름에 `snowflake`가 들어가나?

과거 DAG naming 흔적입니다. 현재 실제 적재는 DuckDB입니다.

### 11-3. 현재 운영 기준에서 Streamlit을 써야 하나?

아닙니다. 현재 공식 조회 경로는 TagScope입니다.

### 11-4. 현재 운영 기준에서 Snowflake 준비가 필요한가?

아닙니다. 현재 공식 저장소는 DuckDB 파일입니다.

---

## 12. Troubleshooting Quick Checks

### 문제 1. 크롤링이 로그인 페이지로 튄다

확인:

1. `secrets/storage_state.json`이 있는지
2. 세션이 만료되지 않았는지
3. `python3 secrets/save_state.py`를 다시 실행했는지

### 문제 2. TagScope UI는 뜨는데 데이터가 비어 있다

확인:

1. Airflow 브랜드 DAG의 `load_to_duckdb`가 성공했는지
2. transform DAG의 `dbt_run`, `dbt_test`가 성공했는지
3. backend가 올바른 DuckDB 파일을 보고 있는지

### 문제 3. `http://localhost:8000/`가 404다

정상입니다.

확인 경로:

- [http://localhost:8000/health](http://localhost:8000/health)

---

## 13. 한 줄 요약

현재 이 프로젝트는 Instagram 데이터를 Airflow로 DuckDB에 적재하고, dbt로 변환한 뒤, TagScope에서 조회하는 구조입니다.
