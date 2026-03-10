## Airflow에서 여러 날짜를 한 번에 실행하는 방법

이 문서는 Airflow DAG를 하루씩 수동으로 누르지 않고, 여러 날짜를 한 번에 실행하는 가장 쉬운 방법을 설명합니다.

이제는 긴 명령어를 직접 입력하지 않아도 됩니다.

프로젝트에 아래 실행 파일을 추가해 두었습니다.

- [airflow_multi_date_runner.py](/Users/jeehun/Desktop/insta_pipeline/scripts/airflow_multi_date_runner.py)

이 파일은:

1. KST 기준 시작일과 종료일을 받음
2. 각 날짜를 Airflow `logical_date`용 UTC 시각으로 자동 변환
3. `docker compose exec -T airflow airflow dags trigger ...`를 대신 실행

---

## 1. 먼저 알아둘 것

이 프로젝트의 v4 DAG는 한국 시간(KST) 기준 날짜를 수집하도록 설정되어 있습니다.

하지만 Airflow 내부 `logical_date`는 UTC로 들어갑니다.

브랜드별 실행 기준:

- `amomento`: `00:05 KST`
- `cos`: `00:10 KST`
- `lemaire`: `00:20 KST`

즉, 사용자는 KST 날짜만 입력하면 되고, UTC 계산은 스크립트가 대신 합니다.

---

## 2. 가장 쉬운 실행 방법

터미널에서 프로젝트 루트로 이동합니다.

```bash
cd /Users/jeehun/Desktop/insta_pipeline
```

그 다음 아래 형식으로 실행합니다.

```bash
python3 scripts/airflow_multi_date_runner.py --brand <브랜드> --start <시작일> --end <종료일>
```

예시:

```bash
python3 scripts/airflow_multi_date_runner.py --brand amomento --start 2026-03-08 --end 2026-03-10
```

이 명령은:

- `2026-03-08`
- `2026-03-09`
- `2026-03-10`

KST 데이터를 순서대로 trigger 합니다.

---

## 3. 브랜드별 예시

### amomento

```bash
python3 scripts/airflow_multi_date_runner.py --brand amomento --start 2026-03-08 --end 2026-03-10
```

### cos

```bash
python3 scripts/airflow_multi_date_runner.py --brand cos --start 2026-03-08 --end 2026-03-10
```

### lemaire

```bash
python3 scripts/airflow_multi_date_runner.py --brand lemaire --start 2026-03-08 --end 2026-03-10
```

### 세 브랜드 모두 한 번에 실행

```bash
python3 scripts/airflow_multi_date_runner.py --brand all --start 2026-03-08 --end 2026-03-10
```

---

## 4. 먼저 확인만 하고 싶을 때

실제 실행 전에 어떤 날짜로 trigger 될지만 보고 싶으면 `--dry-run`을 붙입니다.

```bash
python3 scripts/airflow_multi_date_runner.py --brand amomento --start 2026-03-08 --end 2026-03-10 --dry-run
```

이 경우:

- 실제 Airflow 실행은 하지 않고
- 어떤 `logical_date`로 실행될지만 출력합니다.

---

## 5. 실행 후 확인할 것

Airflow UI에서 아래를 확인합니다.

1. 날짜별 DAG Run이 생성되었는지
2. `print_run_date` 로그에 `DATE_TO_PROCESS KST`가 내가 의도한 날짜인지
3. `extract_instagram_data`가 성공했는지
4. `load_to_snowflake`가 성공했는지

예:

```text
DATE_TO_PROCESS KST: 2026-03-10
```

이 값이 내가 넣은 날짜와 같아야 합니다.

---

## 6. 자주 묻는 질문

### Q1. 왜 그냥 Airflow UI에서 여러 번 누르지 않나?

가능은 하지만 추천하지 않습니다.

이유:

- 날짜가 많아지면 실수하기 쉽고
- KST/UTC 계산을 직접 해야 하며
- 브랜드마다 분 단위 스케줄이 달라서 헷갈리기 쉽습니다.

### Q2. 날짜를 다시 돌려도 되나?

대체로 가능합니다.

현재 적재는 `post_id` 기준 `MERGE`라서, 같은 날짜를 다시 돌리면 기존 데이터를 업데이트하는 방향으로 동작합니다.

### Q3. 인사담당자나 비개발자도 할 수 있나?

이 스크립트는 그 목적에 맞게 만든 것입니다.

필요한 건 사실상 3개뿐입니다.

1. 터미널 열기
2. 프로젝트 폴더로 이동
3. 날짜 넣어서 실행

---

## 7. 한 줄 요약

이제 여러 날짜 실행은 아래처럼 하면 됩니다.

```bash
python3 scripts/airflow_multi_date_runner.py --brand amomento --start 2026-03-08 --end 2026-03-10
```

긴 Airflow CLI 명령어와 UTC 계산은 스크립트가 대신 처리합니다.
