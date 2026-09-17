from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from codepick_l3.provider import (
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderUnavailable,
)
from codepick_l3.readiness import l3_readiness
from codepick_l3.usage import require_api_key_identity

from .routers import v1


app = FastAPI(title="CodePick Public API")


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/docs", status_code=307)


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
async def provider_unavailable(
    _request: Request, exc: ProviderUnavailable
) -> JSONResponse:
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


app.include_router(v1.router, prefix="/v1")


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "public-api"}


@app.get("/v1/ready", dependencies=[Depends(require_api_key_identity)])
def ready() -> dict:
    readiness = l3_readiness()
    readiness["service"] = "public-api"
    return readiness
