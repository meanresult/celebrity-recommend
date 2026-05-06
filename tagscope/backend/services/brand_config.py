from __future__ import annotations

import os
from functools import lru_cache

import yaml

BRANDS_YAML_PATH = os.getenv("BRANDS_YAML_PATH", "/opt/airflow/configs/brands.yaml")


@lru_cache(maxsize=1)
def load_brand_ids() -> list[str]:
    with open(BRANDS_YAML_PATH) as f:
        config = yaml.safe_load(f)
    return [
        b["instagram_id"]
        for b in config.get("brands", [])
        if b.get("enabled", False)
    ]
