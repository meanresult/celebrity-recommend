# TagScope Only Cleanup Plan

이 문서는 현재 저장소를 `DuckDB + Airflow + dbt + TagScope` 기준으로 정리하기 위한 실행 전 체크리스트입니다.

목표는 아래 세 가지입니다.

1. 현재 운영 경로가 아닌 Streamlit / Snowflake 계열 코드를 메인 경로에서 제거한다.
2. 로컬 산출물과 캐시를 코드 저장소에서 분리한다.
3. 문서를 `architecture`, `operations`, `product`, `history` 맥락으로 재배치한다.

주의:

- 이 문서는 삭제 실행 문서가 아니라 삭제 전 검토 문서입니다.
- `data/insta_pipeline.duckdb`와 `secrets/storage_state.json`은 운영에 필요한 로컬 파일이므로 삭제 대상이 아닙니다.

---

## 1. 현재 공식 유지 대상

아래는 현재 런타임 기준으로 유지해야 하는 파일 / 디렉토리입니다.

```text
configs/brands.yaml
dags/brand_dags.py
dags/instagram_brand_factory.py
dags/dbt_orchestrator.py
dags/utils/
extractors/instagram_scraper.py
transform/insta_dbt/
tagscope/backend/
tagscope/frontend/
docker/Dockerfile
docker/DbtDockerfile
docker/TagscopeBackendDockerfile
docker/TagscopeFrontendDockerfile
requirements.txt
requirements_dbt.txt
tagscope/backend/requirements.txt
tagscope/frontend/package.json
tagscope/frontend/package-lock.json
secrets/save_state.py
secrets/.gitkeep
README.md
GPT.md
docs/architecture/current_architecture.md
docs/architecture/project_summary.md
docs/operations/setup_and_run.md
docs/operations/dependency_policy.md
docs/operations/airflow_manual_runbook.md
docs/operations/airflow_multi_date_runbook.md
docs/product/tagscope_storyboard.pdf
docs/product/tagscope_ui_reference/
docs/history/legacy_streamlit_snowflake.md
data/.gitkeep
```

로컬에는 유지하지만 Git 추적은 피해야 하는 파일:

```text
.env
data/insta_pipeline.duckdb
secrets/storage_state.json
secrets/login_failed.png
logs/
tagscope/frontend/node_modules/
tagscope/frontend/.next/
transform/insta_dbt/target/
transform/insta_dbt/logs/
```

---

## 2. 이미 삭제된 것으로 보이는 대상

현재 워크트리 기준으로 아래 항목들은 이미 삭제 상태로 잡혀 있습니다.

```text
airflow_commaned.txt
main.py
legacy/
output/playwright/
```

세부 삭제 상태:

```text
legacy/__init__.py
legacy/extractors/README.txt
legacy/extractors/__init__.py
legacy/extractors/insta_crwal copy.ipynb
legacy/extractors/insta_crwal.py
legacy/extractors/instagram_posts.xlsx
legacy/extractors/main.py
legacy/extractors/main_mini.py
legacy/extractors/main_mini_test.py
legacy/extractors/main_mini_v2.py
legacy/extractors/main_mini_v3.py
legacy/extractors/main_mini_v4.py
legacy/extractors/main_mini_v5.py
legacy/extractors/main_mini_v6.py
legacy/extractors/main_mini_v7.py
legacy/extractors/main_mini_v8.py
legacy/extractors/main_mini_v9.py
legacy/extractors/main_mini_v10.py
output/playwright/dashboard-dark-theme.png
output/playwright/dashboard-redesign-final.png
output/playwright/dashboard-redesign-python.png
```

판단:

- 유지할 이유가 없습니다.
- `docs/history/legacy_streamlit_snowflake.md`와 Git history가 레거시 맥락을 보존합니다.

---

## 3. 삭제 완료 대상

아래 항목은 현재 공식 런타임에서 사용하지 않는 코드 / 의존성이어서 삭제했습니다.

```text
streamlit/
docker/StreamlitDockerfile
requirements_streamlit.txt
```

삭제 이유:

- 현재 공식 조회 경로는 `tagscope/`입니다.
- `streamlit/admin_service.py`는 `insta_to_snowflake_dag_v4_*`를 하드코딩합니다.
- `streamlit/query_service.py`, `streamlit/domain.py`, `streamlit/presentation.py`는 더 이상 공식 조회 레이어가 아닙니다.
- `requirements_streamlit.txt`는 Streamlit 전용 의존성입니다.

함께 수정한 대상:

```text
docker-compose.yaml
README.md
GPT.md
docs/operations/dependency_policy.md
```

적용한 수정:

- `docker-compose.yaml`에서 `streamlit` 서비스 제거
- README / GPT / docs에서 `requirements_streamlit.txt`를 "남아 있는 레거시"로 언급하는 부분 제거

---

## 4. 삭제 완료 대상

아래 파일은 현재 그대로 쓰면 위험해서 삭제했습니다.

```text
scripts/airflow_multi_date_runner.py
```

삭제 전 문제:

- `insta_to_snowflake_dag_v4_*`만 하드코딩합니다.
- 브랜드가 `amomento`, `cos`, `lemaire` 세 개로 고정되어 있습니다.
- 현재 source of truth인 `configs/brands.yaml`을 읽지 않습니다.

향후 여러 날짜 실행이 실제 운영에 필요해지면 `brands.yaml` 기반으로 새로 작성합니다.

---

## 5. 수정 완료 대상

아래는 삭제가 아니라 현재 기준으로 맞춘 파일입니다.

```text
pyproject.toml
```

수정 전 문제:

- `requires-python = ">=3.13"`로 되어 있지만 컨테이너 기준은 Python 3.11입니다.
- dependency에 `dbt-snowflake==1.9.0`이 남아 있습니다.

적용한 수정:

```toml
requires-python = ">=3.11,<3.14"
dependencies = [
    "dbt-core==1.9.0",
    "dbt-duckdb==1.9.1",
]
```

주의:

- 실제 런타임은 `requirements*.txt`와 `tagscope/*`의 런타임 파일이 기준입니다.
- `pyproject.toml`은 로컬 개발환경 재현용으로만 정리합니다.

---

## 6. 로컬 산출물 삭제 후보

아래 항목은 코드가 아니라 캐시 / 로그 / 빌드 산출물입니다.

```text
.DS_Store
docs/.DS_Store
dags/.DS_Store
transform/.DS_Store
__pycache__/
.pytest_cache/
.playwright-cli/
logs/
tagscope/backend/__pycache__/
tagscope/frontend/.next/
tagscope/frontend/node_modules/
tagscope/frontend/tsconfig.tsbuildinfo
transform/insta_dbt/target/
transform/insta_dbt/logs/
transform/logs/
scripts/__pycache__/
secrets/__pycache__/
extractors/__pycache__/
dags/__pycache__/
dags/utils/__pycache__/
```

삭제 이유:

- 재생성 가능한 파일입니다.
- 리뷰와 커밋 노이즈를 크게 만듭니다.
- 특히 `logs/`는 현재 약 `3.3G`로 가장 큽니다.

주의:

- `logs/`는 디버깅 증거가 더 필요 없을 때만 비웁니다.
- `node_modules/`는 삭제 후 `npm ci`로 복구 가능합니다.

---

## 7. Gitignore 보강 후보

현재 `.gitignore`에 추가하는 편이 좋은 항목입니다.

```gitignore
# Local data
data/*.duckdb
data/*.duckdb.*

# Frontend build artifacts
tagscope/frontend/.next/
tagscope/frontend/node_modules/
tagscope/frontend/tsconfig.tsbuildinfo

# dbt artifacts
transform/insta_dbt/target/
transform/insta_dbt/logs/
transform/logs/

# Local tool artifacts
.playwright-cli/
.pytest_cache/

# Assistant-local files
.claude/
.gpt/
.codex/
CLAUDE.md
GPT.md
AGENTS.md

# Runtime screenshots / local notebooks in secrets
secrets/login_failed.png
secrets/*.ipynb
secrets/app_memo.py
```

주의:

- `secrets/*`는 이미 ignore 되어 있고 `!secrets/.gitkeep`만 예외입니다.
- 위 항목은 의도를 더 명확히 하기 위한 보강입니다.

---

## 8. 새 디렉토리 구조안

정리 후 목표 구조는 아래처럼 둡니다.

```text
.
├── README.md
├── GPT.md
├── docker-compose.yaml
├── .dockerignore
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── requirements.txt
├── requirements_dbt.txt
├── configs/
│   └── brands.yaml
├── dags/
│   ├── brand_dags.py
│   ├── dbt_orchestrator.py
│   ├── instagram_brand_factory.py
│   └── utils/
│       ├── __init__.py
│       └── db.py
├── extractors/
│   └── instagram_scraper.py
├── transform/
│   └── insta_dbt/
│       ├── dbt_project.yml
│       ├── profiles.yml
│       ├── macros/
│       ├── models/
│       └── tests/
├── tagscope/
│   ├── backend/
│   │   ├── main.py
│   │   ├── queries/
│   │   ├── routers/
│   │   ├── services/
│   │   └── requirements.txt
│   └── frontend/
│       ├── app/
│       ├── components/
│       ├── lib/
│       ├── stores/
│       ├── types/
│       ├── package.json
│       └── package-lock.json
├── docker/
│   ├── Dockerfile
│   ├── DbtDockerfile
│   ├── TagscopeBackendDockerfile
│   └── TagscopeFrontendDockerfile
├── docs/
│   ├── architecture/
│   ├── operations/
│   ├── product/
│   ├── history/
│   └── tagscope_only_cleanup_plan.md
├── data/
│   └── .gitkeep
└── secrets/
    ├── .gitkeep
    └── save_state.py
```

로컬에서만 존재하는 파일:

```text
.env
data/insta_pipeline.duckdb
secrets/storage_state.json
logs/
tagscope/frontend/node_modules/
tagscope/frontend/.next/
```

---

## 9. 문서 이동 완료 후 현재 위치

현재 문서는 아래 기준으로 정리했습니다.

### 9-1. Architecture

```text
docs/architecture/current_architecture.md
docs/architecture/project_summary.md
```

### 9-2. Operations

```text
docs/operations/setup_and_run.md
docs/operations/dependency_policy.md
docs/operations/airflow_manual_runbook.md
docs/operations/airflow_multi_date_runbook.md
```

### 9-3. Product / UI references

```text
docs/product/tagscope_storyboard.pdf
docs/product/tagscope_ui_reference/
```

### 9-4. History

```text
docs/history/legacy_streamlit_snowflake.md
docs/history/troubleshooting/legacy_instagram_popup_failure.md
docs/history/retrospectives/
docs/history/assets/
```

주의:

- 한글 파일명 자체가 문제는 아니지만, 운영 runbook은 CLI에서 자주 열기 때문에 영문 snake_case가 더 다루기 쉽습니다.
- 회고 문서는 운영 문서와 섞이지 않도록 history 아래로 내립니다.

---

## 10. 실행 순서 추천

1. 현재 변경사항을 먼저 한 번 커밋하거나 최소한 `git diff`로 보존 범위를 확인합니다.
2. Streamlit 런타임 제거 완료:
   `streamlit/`, `docker/StreamlitDockerfile`, `requirements_streamlit.txt`, Compose `streamlit` 서비스 제거
3. 레거시 스크립트 삭제 완료:
   `scripts/airflow_multi_date_runner.py` 제거
4. `pyproject.toml`을 DuckDB 기준으로 수정 완료
5. `.gitignore` 보강 완료
6. docs를 `architecture`, `operations`, `product`, `history`로 이동 완료
7. 로컬 산출물 정리:
   `logs/`, `__pycache__/`, `.next/`, `node_modules/`, dbt `target/`
8. 검증 실행

---

## 11. 검증 체크리스트

삭제 / 이동 후 최소 검증은 아래 순서로 진행합니다.

```bash
docker compose config
```

```bash
python3 -m py_compile dags/brand_dags.py dags/instagram_brand_factory.py dags/dbt_orchestrator.py extractors/instagram_scraper.py
```

```bash
docker build -f docker/TagscopeFrontendDockerfile .
```

```bash
docker compose run --rm dbt parse
```

```bash
cd tagscope/frontend
npm run build
```

브라우저 확인:

```text
http://localhost:3000/taggers
http://localhost:3000/co-brands
http://localhost:8000/health
```

---

## 12. 최종 판단

삭제해도 되는 핵심 레거시는 아래입니다.

```text
streamlit/
docker/StreamlitDockerfile
requirements_streamlit.txt
legacy/
output/playwright/
main.py
airflow_commaned.txt
scripts/airflow_multi_date_runner.py
```

삭제하면 안 되는 핵심 파일은 아래입니다.

```text
data/insta_pipeline.duckdb
secrets/storage_state.json
configs/brands.yaml
dags/
extractors/instagram_scraper.py
transform/insta_dbt/
tagscope/
```

가장 중요한 원칙:

```text
현재 운영 truth는 configs/brands.yaml + DuckDB + dbt + TagScope다.
```
