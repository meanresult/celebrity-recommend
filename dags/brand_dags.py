"""
brand_dags.py

이 파일 하나에서 모든 브랜드의 Airflow DAG을 자동으로 만들어 등록합니다.

동작 방식:
  1. configs/instagram_brands.yaml 에서 브랜드 목록을 읽어옵니다.
  2. 브랜드마다 DAG 객체를 생성합니다 (실제 수집 로직은 instagram_brand_factory.py에 있음).
  3. globals()에 DAG을 등록하면 Airflow가 자동으로 발견해 UI에 표시합니다.

결과:
  Airflow UI에서 각 브랜드가 독립된 DAG으로 보이고,
  스케줄·수동 실행·재실행 모두 브랜드별로 따로 동작합니다.
"""

from airflow import DAG  # noqa: F401 — Airflow가 이 파일을 DAG 파일로 인식하려면 필요
from instagram_brand_factory import create_instagram_brand_dag, load_brand_configs

# configs/instagram_brands.yaml에서 전체 브랜드 설정을 불러옵니다.
# 각 브랜드에는 instagram_id, 실행 스케줄, 활성화 여부 등이 담겨 있습니다.
_brand_configs = load_brand_configs()

for _config in _brand_configs.values():
    # enabled: false 인 브랜드는 DAG을 만들지 않고 건너뜁니다.
    _dag = create_instagram_brand_dag(_config)

    if _dag is not None:
        # globals()에 등록해야 Airflow가 이 DAG을 인식합니다.
        # 키(dag_id)가 곧 Airflow UI에 표시되는 DAG 이름입니다.
        globals()[_dag.dag_id] = _dag
