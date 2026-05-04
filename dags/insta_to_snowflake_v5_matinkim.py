from airflow import DAG  # noqa: F401
from instagram_brand_factory import create_instagram_brand_dag, load_brand_configs

# Keep DAG symbol in this module so Airflow safe mode discovers the file.
dag = create_instagram_brand_dag(load_brand_configs()["matinkim"])
