# Legacy Architecture Note

이 문서는 현재 공식 운영 구조가 아니라, 과거 문서가 어떤 전제를 갖고 있었는지 기록해 두는 히스토리 노트입니다.

## 1. 과거 공식 문서가 설명하던 구조

이 저장소는 한동안 아래 구조를 기준으로 문서화되어 있었습니다.

- 저장: Snowflake
- 조회: Streamlit
- DAG 구성: 브랜드별 고정 DAG 파일

대표적으로 아래 같은 표현이 과거 문서에 있었습니다.

- `Snowflake RAW_DATA.INSTAGRAM_POSTS`
- `Streamlit Dashboard`
- `insta_to_snowflake_dag_v4_*`

## 2. 현재 구조와 달라진 점

지금 공식 운영 기준은 아래와 같습니다.

- 저장: DuckDB 파일 `data/insta_pipeline.duckdb`
- 조회: TagScope (`FastAPI + Next.js`)
- DAG 구성: `configs/brands.yaml` 기반 동적 DAG 생성

즉, 현재는 `DuckDB + Airflow + dbt + TagScope`가 기준입니다.

## 3. 왜 이 문서를 따로 남기나

레거시 흔적이 현재 이름이나 history 문서 안에 일부 남아 있기 때문입니다.

현재 남아 있는 대표 흔적:

- DAG ID의 `insta_to_snowflake_*` prefix
- `docs/history/retrospectives/` 아래의 과거 회고
- `docs/history/troubleshooting/` 아래의 과거 트러블슈팅

아래 런타임 파일은 현재 공식 구조에서 삭제되었습니다.

- `streamlit/`
- `requirements_streamlit.txt`
- `docker/StreamlitDockerfile`

이 흔적들이 "현재 공식 구조"로 읽히지 않도록, 과거 전제는 이 문서로만 모읍니다.

## 4. 지금 무엇을 기준으로 봐야 하나

현재 운영과 협업 기준은 아래 문서만 보면 됩니다.

- `README.md`
- `GPT.md`
- `docs/architecture/current_architecture.md`
- `docs/operations/setup_and_run.md`
- `docs/operations/dependency_policy.md`

## 5. 한 줄 요약

Snowflake / Streamlit 문서는 과거 구조의 기록이고, 현재 공식 구조는 DuckDB / TagScope입니다.
