from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import brands, co_brands, freshness, taggers

app = FastAPI(title="TagScope API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(brands.router)
app.include_router(freshness.router)
app.include_router(taggers.router)
app.include_router(co_brands.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
