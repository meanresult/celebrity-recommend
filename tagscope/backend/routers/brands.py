from fastapi import APIRouter

from services.brand_config import load_brand_ids

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.get("")
def get_brands() -> list[str]:
    return load_brand_ids()
