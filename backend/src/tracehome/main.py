"""The TraceHome API. Every route lives under /api, because CloudFront sends /api/* to the load
balancer and passes the full path through (decision 72)."""

from fastapi import FastAPI, Request

import tracehome.models  # noqa: F401  (registers every table)
from tracehome.config import get_settings
from tracehome.modules.accounts.router import router as accounts_router
from tracehome.modules.credits.router import router as credits_router
from tracehome.modules.listings.router import router as listings_router
from tracehome.modules.uploads.router import router as uploads_router

get_settings()  # fail fast on bad configuration

app = FastAPI(
    title="TraceHome API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(accounts_router)
app.include_router(listings_router)
app.include_router(credits_router)
app.include_router(uploads_router)


@app.middleware("http")
async def no_caching_by_default(request: Request, call_next):
    # Rule: if a response depends on who is asking, it is never cached (ARCHITECTURE.md, Edge).
    # The safe default is "don't cache"; public paths can opt in later, on purpose.
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/api/health", tags=["health"])
def health():
    # Shallow on purpose: it does not touch the database. If RDS fails over for a minute, the load
    # balancer should not decide every API task is broken and have ECS replace them all.
    return {"status": "ok"}
