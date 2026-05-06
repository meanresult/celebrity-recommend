Airflow 수동 실행 및 재실행 명령어

# 이 문서는 현재 운영 기준인 v5 브랜드 DAG를 터미널에서 실행하거나,
# 실패한 DAG / 실패한 task만 다시 실행할 때 쓰는 명령어를 모아둔 가이드다.
# 아래 명령어는 모두 프로젝트 루트(`/Users/jeehun/Desktop/insta_pipeline`)에서 실행한다고 가정한다.

# ------------------------------------------------------------
# 0. 먼저 알아둘 것
# ------------------------------------------------------------
# 1) 현재 source of truth는 `configs/brands.yaml`이다.
#    DAG ID, schedule, enabled 여부는 여기서 먼저 확인한다.
#
# 2) DAG ID prefix에 `snowflake`가 남아 있어도 실제 적재 대상은 DuckDB다.
#    현재 load task 이름은 `load_to_duckdb`다.
#
# 3) schedule은 UTC cron 기준이다.
#    KST 하루치를 다시 돌릴 때는 logical_date의 UTC 날짜를 같이 확인해야 한다.
#
# 4) 예전 다중 날짜 runner는 삭제했다.
#    새 bulk runner가 필요하면 반드시 `configs/brands.yaml` 기반으로 다시 작성한다.


# ------------------------------------------------------------
# 1. DAG 목록 / 상태 확인
# ------------------------------------------------------------

# 1-1. 전체 DAG 목록 확인
docker compose exec -T airflow airflow dags list

# 1-2. 현재 브랜드 DAG만 보기
docker compose exec -T airflow airflow dags list | awk '/insta_to_snowflake_dag_v5_/ {print $1}'

# 1-3. 특정 DAG의 최근 run 확인
docker compose exec -T airflow airflow dags list-runs -d insta_to_snowflake_dag_v5_amomento --no-backfill


# ------------------------------------------------------------
# 2. 전체 수동 실행 방법
# ------------------------------------------------------------

# 설명:
# - 특정 DAG 하나를 원하는 UTC logical_date로 직접 trigger 한다.
# - Airflow UI에서 수동 실행하는 것과 같은 효과다.

# 예시:
# - KST 2026-05-06 00:00 수집분 -> UTC 2026-05-05T15:00:00+00:00

docker compose exec -T airflow airflow dags trigger -e 2026-05-05T15:00:00+00:00 insta_to_snowflake_dag_v5_amomento


# ------------------------------------------------------------
# 3. 실패한 DAG만 전체 재실행 방법
# ------------------------------------------------------------

# 설명:
# - 특정 날짜의 v5 브랜드 DAG 중 마지막 상태가 failed 인 DAG만 골라서,
#   그 DAG의 task 전체를 clear 한다.
# - clear 는 새 DAG run 을 만드는 것이 아니라,
#   기존 failed run 의 task 상태를 지워 scheduler 가 다시 실행하게 만든다.

# 3-1. 먼저 어떤 DAG run 이 failed 인지 확인
docker compose exec -T airflow bash -lc '
for dag in $(airflow dags list | awk "/insta_to_snowflake_dag_v5_/ {print \$1}"); do
  if airflow dags list-runs -d "$dag" --no-backfill | grep -E "failed[[:space:]]+\\|[[:space:]]+2026-05-05T" >/dev/null; then
    echo "$dag -> failed"
  fi
done
'

# 3-2. failed 인 DAG만 task 전체 clear
docker compose exec -T airflow bash -lc '
for dag in $(airflow dags list | awk "/insta_to_snowflake_dag_v5_/ {print \$1}"); do
  if airflow dags list-runs -d "$dag" --no-backfill | grep -E "failed[[:space:]]+\\|[[:space:]]+2026-05-05T" >/dev/null; then
    echo "CLEAR DAG -> $dag"
    airflow tasks clear "$dag" -s 2026-05-05 -e 2026-05-06 -y
  fi
done
'

# 참고:
# - 위 명령은 DAG 안의 task 를 전체 clear 한다.
# - print_run_date, extract_instagram_data, load_to_duckdb 모두 다시 실행될 수 있다.


# ------------------------------------------------------------
# 4. 실패한 task만 전체 재실행 방법
# ------------------------------------------------------------

# 설명:
# - failed DAG 전체가 아니라, 실패한 task 인스턴스만 다시 실행하고 싶을 때 쓴다.
# - Airflow 기본 옵션 `-f` / `--only-failed` 를 사용한다.

# 4-1. 특정 날짜의 모든 v5 DAG에서 failed task 만 clear
docker compose exec -T airflow bash -lc '
for dag in $(airflow dags list | awk "/insta_to_snowflake_dag_v5_/ {print \$1}"); do
  echo "CLEAR FAILED TASKS -> $dag"
  airflow tasks clear "$dag" -s 2026-05-05 -e 2026-05-06 -f -y
done
'

# 4-2. 특정 날짜의 모든 v5 DAG에서 extract_instagram_data 실패분만 clear
docker compose exec -T airflow bash -lc '
for dag in $(airflow dags list | awk "/insta_to_snowflake_dag_v5_/ {print \$1}"); do
  echo "CLEAR FAILED EXTRACT -> $dag.extract_instagram_data"
  airflow tasks clear "$dag" -t extract_instagram_data -s 2026-05-05 -e 2026-05-06 -f -y
done
'

# 4-3. 특정 DAG 하나에서 load_to_duckdb 실패분만 clear
docker compose exec -T airflow airflow tasks clear insta_to_snowflake_dag_v5_amomento -t load_to_duckdb -s 2026-05-05 -e 2026-05-06 -f -y


# ------------------------------------------------------------
# 5. transform DAG 재실행
# ------------------------------------------------------------

# 설명:
# - 브랜드 DAG는 성공했고 dbt run/test 만 다시 태우고 싶을 때 사용한다.

docker compose exec -T airflow airflow tasks clear transform_dbt_after_all_brands -t dbt_run -s 2026-05-05 -e 2026-05-06 -y
docker compose exec -T airflow airflow tasks clear transform_dbt_after_all_brands -t dbt_test -s 2026-05-05 -e 2026-05-06 -y


# ------------------------------------------------------------
# 6. 운영 시 추천 순서
# ------------------------------------------------------------
# 1) 먼저 `configs/brands.yaml`에서 DAG ID와 enabled 여부 확인
# 2) 새 날짜를 실행할 때는 trigger 사용
# 3) 이미 있는 날짜 run 을 복구할 때는 trigger 가 아니라 clear 사용
# 4) 대부분의 경우는 "실패한 extract task만 clear" 가 가장 안전하다
# 5) load_to_duckdb 와 dbt_run / dbt_test 는 필요할 때만 선별적으로 재실행


# ------------------------------------------------------------
# 7. 빠른 선택 가이드
# ------------------------------------------------------------
# - 새 날짜를 실행하고 싶다
#   -> 2번 명령 사용
#
# - 이미 있는 날짜 run 중 failed DAG만 다시 돌리고 싶다
#   -> 3-2 명령 사용
#
# - 이미 있는 날짜 run 중 failed task만 다시 돌리고 싶다
#   -> 4-1 명령 사용
#
# - extract 실패만 다시 돌리고 싶다
#   -> 4-2 명령 사용
#
# - load_to_duckdb 하나만 다시 돌리고 싶다
#   -> 4-3 명령 사용
#
# - dbt만 다시 돌리고 싶다
#   -> 5번 명령 사용
