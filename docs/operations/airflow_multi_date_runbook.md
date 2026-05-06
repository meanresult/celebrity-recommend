## Airflow에서 여러 날짜를 실행하는 방법

이 문서는 현재 운영 기준인 `configs/brands.yaml` 기반 v5 DAG에서 여러 날짜 실행을 검토할 때의 기준을 정리합니다.

중요:

- 예전 `scripts/airflow_multi_date_runner.py`는 삭제했습니다.
- 삭제 이유는 v4 DAG 세 개만 하드코딩했고, 현재 source of truth인 `configs/brands.yaml`을 읽지 않았기 때문입니다.
- 현재 공식 기준은 개별 Airflow trigger 또는 Airflow UI 수동 실행입니다.

---

## 1. 현재 기준 source of truth

여러 날짜 실행을 검토할 때 가장 먼저 볼 파일은 [brands.yaml](/Users/jeehun/Desktop/insta_pipeline/configs/brands.yaml)입니다.

여기서 확인할 값:

1. `dag_id`
2. `schedule`
3. `enabled`

예:

- `insta_to_snowflake_dag_v5_amomento`
- `schedule: "0 15 * * *"` -> KST `00:00`

주의:

- `schedule`은 UTC cron입니다.
- 한국 시간 기준 날짜로 실행하고 싶으면 반드시 KST -> UTC logical_date 변환을 같이 봐야 합니다.

---

## 2. 현재 권장 방식

현재 권장 방식은 아래 두 가지입니다.

1. 소량 실행:
   Airflow UI에서 해당 DAG를 수동 trigger
2. CLI 실행:
   `airflow dags trigger -e <UTC_LOGICAL_DATE> <DAG_ID>`를 직접 사용

대량 backfill helper가 다시 필요해지면, 반드시 `configs/brands.yaml`을 읽는 방식으로 새로 작성합니다.

---

## 3. CLI 템플릿

브랜드 하나를 특정 logical_date로 직접 실행할 때 기본 형식은 아래입니다.

```bash
docker compose exec -T airflow airflow dags trigger -e <UTC_LOGICAL_DATE> <DAG_ID>
```

예:

```bash
docker compose exec -T airflow airflow dags trigger -e 2026-05-05T15:00:00+00:00 insta_to_snowflake_dag_v5_amomento
```

이 예시는 KST `2026-05-06 00:00` 수집분에 해당합니다.

---

## 4. 새 helper를 다시 만든다면

다중 날짜 실행 도구를 다시 만든다면 최소 조건은 아래입니다.

1. `configs/brands.yaml`을 읽는다.
2. `enabled: true` 브랜드만 실행한다.
3. `schedule`의 UTC 시각을 기준으로 logical_date를 계산한다.
4. `--dry-run`으로 실행 전 DAG ID와 logical_date를 출력한다.
5. 존재하지 않는 DAG나 비활성 브랜드는 실행하지 않는다.

---

## 5. 한 줄 요약

현재 여러 날짜 실행은 수동 trigger 기준으로 운영하고, bulk runner는 필요할 때 `brands.yaml` 기반으로 새로 작성합니다.
