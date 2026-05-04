from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.python import get_current_context

from utils import db as util


# 브랜드 설정 파일 경로 (dags/ 기준으로 한 단계 위 → 프로젝트 루트/configs/brands.yaml)
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "brands.yaml"

# 인스타그램 수집 데이터의 컬럼 순서 (CSV 저장 및 DataFrame 생성 시 기준)
POST_COLUMNS = [
    "post_id",
    "insta_id",
    "insta_name",
    "brand_name",
    "brand_id",
    "full_link",
    "img_src",
    "post_date",
    "tagged_insta_id",
    "tagged_insta_id_cnt",
]


# ──────────────────────────────────────────
# YAML 파서
# ──────────────────────────────────────────

def _parse_scalar(value: str):
    """
    YAML 값 문자열을 Python 타입으로 변환합니다.
    (pyyaml 대신 직접 파싱 — Docker 이미지 의존성 최소화 목적)
    """
    value = value.strip()
    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def load_brand_records(config_path: Path) -> list[dict[str, object]]:
    """
    brands.yaml을 읽어 브랜드별 dict 리스트로 반환합니다.
    YAML 라이브러리 없이 직접 파싱하며, 리스트 항목(- key: value) 형태만 처리합니다.
    """
    records: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()

        # 빈 줄, 주석, 최상위 키는 무시
        if not stripped or stripped.startswith("#") or stripped == "brands:":
            continue

        # 새 브랜드 항목 시작 (- 으로 시작)
        if stripped.startswith("- "):
            if current:
                records.append(current)
            current = {}
            stripped = stripped[2:]

        if current is None or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        current[key.strip()] = _parse_scalar(value)

    if current:
        records.append(current)

    return records


# ──────────────────────────────────────────
# 브랜드 설정 데이터 클래스
# ──────────────────────────────────────────

@dataclass(frozen=True)
class BrandDagConfig:
    brand_key:    str
    instagram_id: str
    dag_id:       str
    schedule:     str
    enabled:      bool
    schema:       str = "RAW_DATA"
    table:        str = "INSTAGRAM_POSTS"

    @property
    def utc_schedule(self) -> tuple[int, int]:
        """cron 문자열에서 (hour, minute) UTC 시각을 추출합니다."""
        minute_str, hour_str, *_ = self.schedule.split()
        return int(hour_str), int(minute_str)

    @property
    def kst_run_time(self) -> str:
        """UTC 스케줄을 KST(+9) 기준 HH:MM 문자열로 반환합니다."""
        hour, minute = self.utc_schedule
        kst_hour = (hour + 9) % 24
        return f"{kst_hour:02d}:{minute:02d}"


def load_brand_configs(config_path: Path = CONFIG_PATH) -> dict[str, BrandDagConfig]:
    """brands.yaml → {brand_key: BrandDagConfig} 딕셔너리로 변환합니다."""
    configs: dict[str, BrandDagConfig] = {}

    for item in load_brand_records(config_path):
        config = BrandDagConfig(
            brand_key=item["brand_key"],
            instagram_id=item["instagram_id"],
            dag_id=item["dag_id"],
            schedule=item["schedule"],
            enabled=bool(item.get("enabled", True)),
            schema=item.get("schema", "RAW_DATA"),
            table=item.get("table", "INSTAGRAM_POSTS"),
        )
        configs[config.brand_key] = config

    return configs


# ──────────────────────────────────────────
# DAG 생성 팩토리
# ──────────────────────────────────────────

def create_instagram_brand_dag(config: BrandDagConfig) -> DAG | None:
    """
    브랜드 설정 하나를 받아 Airflow DAG을 생성합니다.
    enabled=False 이면 None을 반환해 DAG 등록을 건너뜁니다.

    태스크 흐름:
      print_run_date → extract_instagram_data → load_to_duckdb
    """
    if not config.enabled:
        return None

    # ── 태스크 1: 실행 날짜 출력 (디버깅용) ──────────────────────

    @task(task_id="print_run_date")
    def print_run_date() -> None:
        context = get_current_context()
        logical_date       = context["logical_date"]
        data_interval_start = context["data_interval_start"]
        data_interval_end   = context["data_interval_end"]
        logical_date_kst   = logical_date.in_timezone("Asia/Seoul")

        print("LOGICAL_DATE raw :", logical_date,        "tz:", logical_date.tzinfo)
        print("START raw        :", data_interval_start, "tz:", data_interval_start.tzinfo)
        print("END   raw        :", data_interval_end,   "tz:", data_interval_end.tzinfo)
        print("LOGICAL_DATE KST :", logical_date_kst)
        print("START KST        :", data_interval_start.in_timezone("Asia/Seoul"))
        print("END   KST        :", data_interval_end.in_timezone("Asia/Seoul"))
        print("DATE_TO_PROCESS  :", logical_date_kst.strftime("%Y-%m-%d"))

    # ── 태스크 2: 인스타그램 데이터 수집 → CSV 저장 ──────────────

    @task(
        task_id="extract_instagram_data",
        pool="instagram_extract_pool",
        pool_slots=1,
        execution_timeout=timedelta(minutes=40),
    )
    def extract_instagram_data(debug: bool = True) -> str:
        from extractors.instagram_scraper import run

        context          = get_current_context()
        logical_date_kst = context["logical_date"].in_timezone("Asia/Seoul")
        date_to_process  = logical_date_kst.strftime("%Y-%m-%d")

        if debug:
            print(f"수집 대상 날짜: {date_to_process}")

        posts = run(
            brand_id=config.instagram_id,
            brand_name=config.brand_key,
            headless=True,
            target_day=date_to_process,
        )

        dataframe = pd.DataFrame(posts, columns=POST_COLUMNS)
        tmp_dir   = Variable.get("data_dir", default_var="/tmp/")
        file_path = util.get_file_path(tmp_dir, config.brand_key, context)

        dataframe.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(
            f"\n[EXTRACT 완료]"
            f"\n  brand   : {config.brand_key}"
            f"\n  date    : {date_to_process}"
            f"\n  rows    : {len(posts)}"
            f"\n  saved   : {file_path}"
        )
        return file_path

    # ── 태스크 3: CSV → DuckDB UPSERT ────────────────────────────

    @task(task_id="load_to_duckdb")
    def load_to_duckdb(brand_key: str) -> None:
        # brand_key + 실행 날짜로 파일 경로를 재구성합니다.
        # (XCom 의존 없이 load 태스크가 단독으로 재실행 가능하게 설계)
        staging_table   = f"temp_{config.table}"
        qualified_table = f"{config.schema}.{config.table}"
        conn            = util.get_conn()
        tmp_dir         = Variable.get("data_dir", "/tmp/")
        file_path       = util.get_file_path(tmp_dir, brand_key, get_current_context())

        try:
            # 테이블이 없으면 생성
            util.ensure_instagram_posts_table(conn, config.schema, config.table)

            # 임시 스테이징 테이블에 CSV를 먼저 올린 뒤 검증 후 본 테이블에 MERGE
            conn.execute(
                f"""
                CREATE TEMP TABLE {staging_table} (
                    post_id             VARCHAR,
                    insta_id            VARCHAR,
                    insta_name          VARCHAR,
                    brand_name          VARCHAR,
                    brand_id            VARCHAR,
                    full_link           VARCHAR,
                    img_src             VARCHAR,
                    post_date           VARCHAR,
                    tagged_insta_id     VARCHAR,
                    tagged_insta_id_cnt INTEGER
                );
                """
            )

            util.load_csv_to_table(conn, staging_table, file_path)

            # ── 검증 ──────────────────────────────────────────────

            row_count = conn.execute(f"SELECT COUNT(*) FROM {staging_table}").fetchone()[0]
            if row_count == 0:
                raise ValueError("스테이징에 적재된 데이터가 없습니다")

            duplicate_rows = conn.execute(
                f"""
                SELECT post_id, COUNT(*) AS cnt
                FROM {staging_table}
                GROUP BY post_id
                HAVING COUNT(*) > 1;
                """
            ).fetchall()
            if duplicate_rows:
                sample = ", ".join(f"{r[0]}({r[1]})" for r in duplicate_rows[:5])
                raise ValueError(f"post_id 중복 발견: {sample} (총 {len(duplicate_rows)}건)")

            invalid_count = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {staging_table}
                WHERE post_id IS NULL OR TRIM(post_id) = '';
                """
            ).fetchone()[0]
            if invalid_count > 0:
                raise ValueError(f"비어있는 post_id가 {invalid_count}건 존재합니다.")

            # ── MERGE (UPSERT) ────────────────────────────────────
            # 기존 post_id 있으면 UPDATE, 없으면 INSERT

            upsert_sql = f"""
                MERGE INTO {qualified_table} AS target
                USING {staging_table} AS stage
                ON target.post_id = stage.post_id
                WHEN MATCHED THEN
                    UPDATE SET
                        insta_id            = stage.insta_id,
                        insta_name          = stage.insta_name,
                        last_seen_at        = CURRENT_TIMESTAMP,
                        active              = TRUE,
                        tagged_insta_id     = stage.tagged_insta_id,
                        tagged_insta_id_cnt = stage.tagged_insta_id_cnt
                WHEN NOT MATCHED THEN
                    INSERT (
                        post_id, insta_id, insta_name, brand_name, brand_id,
                        full_link, img_src, post_date,
                        first_seen_at, last_seen_at, active,
                        tagged_insta_id, tagged_insta_id_cnt
                    )
                    VALUES (
                        stage.post_id, stage.insta_id, stage.insta_name,
                        stage.brand_name, stage.brand_id,
                        stage.full_link, stage.img_src, stage.post_date,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE,
                        stage.tagged_insta_id, stage.tagged_insta_id_cnt
                    );
            """

            conn.execute("BEGIN;")
            conn.execute(upsert_sql)
            conn.execute("COMMIT;")
            print(f"[LOAD 완료] {qualified_table} ← {file_path} ({row_count}행)")

        except Exception as exc:
            conn.execute("ROLLBACK;")
            print(f"[LOAD 실패] {exc}")
            raise

        finally:
            conn.close()

    # ── DAG 정의 ─────────────────────────────────────────────────

    with DAG(
        dag_id=config.dag_id,
        description=f"Instagram → DuckDB ETL ({config.brand_key})",
        start_date=datetime(2026, 1, 8),
        catchup=False,
        tags=["ETL", "Instagram", "DuckDB", "incremental"],
        schedule=config.schedule,
    ) as dag:
        print_run_date() >> extract_instagram_data(debug=True) >> load_to_duckdb(config.brand_key)

    return dag
