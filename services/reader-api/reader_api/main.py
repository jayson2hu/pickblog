from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from codepick_l3.provider import (
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderUnavailable,
)
from codepick_l3.readiness import l3_readiness

from .routers import admin, api_keys, auth, billing, briefs, companion, events, feed, library, me, read, taxonomy


app = FastAPI(title="CodePick Reader API")


@app.exception_handler(ProviderConfigurationError)
async def provider_configuration_error(
    _request: Request, exc: ProviderConfigurationError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "l2_configuration_error",
                "message": str(exc),
                "retryable": False,
            }
        },
    )


@app.exception_handler(ProviderRequestError)
async def provider_request_error(
    _request: Request, exc: ProviderRequestError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": {"code": "invalid_request", "message": str(exc)}},
    )


@app.exception_handler(ProviderUnavailable)
async def provider_unavailable(_request: Request, exc: ProviderUnavailable) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "l2_unavailable",
                "message": str(exc),
                "retryable": True,
            }
        },
        headers={"Retry-After": "2"},
    )
app.include_router(auth.router, prefix="/api")
app.include_router(feed.router, prefix="/api")
app.include_router(read.router, prefix="/api")
app.include_router(briefs.router, prefix="/api")
app.include_router(companion.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(library.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(api_keys.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(taxonomy.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "reader-api"}


@app.get("/api/ready")
def ready() -> dict:
    readiness = l3_readiness()
    readiness["service"] = "reader-api"
    return readiness
