insta_pipeline 의존성 관리 기준

이 프로젝트는 현재 `Airflow + dbt + TagScope backend + TagScope frontend`를 각각 다른 런타임으로 운영한다.
따라서 런타임 의존성과 로컬 개발 의존성을 역할별로 분리해서 관리한다.

==================================================
1. 현재 공식 기준
==================================================

1) Python 런타임 의존성
- `requirements.txt`
  - Airflow 이미지와 Instagram crawler 런타임 기준
  - Playwright, dotenv, DuckDB 등 ETL 실행에 필요한 패키지 포함
- `requirements_dbt.txt`
  - dbt 컨테이너 런타임 기준
  - 현재 타깃은 `dbt-duckdb`
- `tagscope/backend/requirements.txt`
  - FastAPI backend 런타임 기준
  - FastAPI, Uvicorn, DuckDB, pandas, pyyaml 포함

2) Frontend 런타임 의존성
- `tagscope/frontend/package.json`
  - Next.js frontend 런타임 / 개발 의존성 기준
- `tagscope/frontend/package-lock.json`
  - Node 패키지 잠금 파일

3) 로컬 개발환경 의존성
- `pyproject.toml`
  - 로컬 Python 개발 메타데이터와 Python 버전 기준
- `uv.lock`
  - 로컬 Python 개발환경 재현용 잠금 파일

==================================================
2. 왜 이렇게 나누는가
==================================================

[이유 1. 런타임 역할이 서로 다르다]
- Airflow / crawler는 스케줄링, Playwright, CSV 적재, DuckDB write가 필요하다.
- dbt는 transform만 수행하면 된다.
- TagScope backend는 DuckDB read-only query와 API 응답만 책임진다.
- TagScope frontend는 Node / Next.js 런타임이 필요하다.

즉, 하나의 공통 의존성 파일로 묶는 순간 이미지가 불필요하게 커지고 충돌 가능성도 커진다.

[이유 2. Python과 Node를 같은 규칙으로 보면 안 된다]
- backend / Airflow / dbt는 Python 패키지 체계를 따른다.
- frontend는 `package.json` / `package-lock.json` 체계를 따른다.

[이유 3. 로컬 개발 도구와 컨테이너 런타임은 목적이 다르다]
- 로컬 개발에서는 버전 고정, 도구 통일, 환경 재현이 중요하다.
- 컨테이너 런타임에서는 실제 서비스 실행에 필요한 패키지만 안정적으로 설치되는 것이 더 중요하다.

==================================================
3. 이 기준을 안 지키면 생기는 문제
==================================================

- 어떤 파일이 진짜 기준인지 헷갈린다.
- Docker에서는 되는데 로컬 개발환경에서는 안 되거나, 그 반대 상황이 생긴다.
- 팀원이 의존성을 추가할 때 어디를 수정해야 하는지 몰라 중복 수정이 발생한다.
- Python과 Node 변경이 한 파일에 섞여 리뷰 범위가 불필요하게 커진다.
- 나중에 CI를 붙일 때 설치 기준이 여러 군데로 갈라져 파이프라인이 복잡해진다.

==================================================
4. 앞으로의 수정 규칙
==================================================

[Airflow / crawler 런타임 패키지를 추가하거나 수정할 때]
- `requirements.txt`를 수정한다.

[dbt 패키지를 추가하거나 수정할 때]
- `requirements_dbt.txt`를 수정한다.

[TagScope backend 패키지를 추가하거나 수정할 때]
- `tagscope/backend/requirements.txt`를 수정한다.

[TagScope frontend 패키지를 추가하거나 수정할 때]
- `tagscope/frontend/package.json`을 수정한다.
- 설치 후 `package-lock.json`도 함께 갱신한다.

[로컬 Python 개발환경만 바꿀 때]
- `pyproject.toml`을 수정한다.
- 필요하면 `uv.lock`도 함께 갱신한다.

[Python 버전을 바꿀 때]
- `pyproject.toml`
- `.python-version`
- 관련 Dockerfile 베이스 이미지
- CI 설정
위 네 곳이 서로 일치하는지 확인한다.

==================================================
5. 현재 프로젝트에 적용한 기준
==================================================

- Airflow / extractor는 `requirements.txt`
- dbt는 `requirements_dbt.txt`
- TagScope backend는 `tagscope/backend/requirements.txt`
- TagScope frontend는 `tagscope/frontend/package.json`
- 로컬 Python 개발 메타데이터는 `pyproject.toml`

즉, 현재 공식 런타임 기준은 이미 `Python multiple runtimes + Node frontend runtime`으로 분리되어 있다.

==================================================
6. 한 줄 요약
==================================================

- ETL은 `requirements.txt`
- dbt는 `requirements_dbt.txt`
- API는 `tagscope/backend/requirements.txt`
- UI는 `tagscope/frontend/package.json`
- 로컬 Python 개발환경은 `pyproject.toml` + `uv.lock`
