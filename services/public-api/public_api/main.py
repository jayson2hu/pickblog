from fastapi import Depends, FastAPI
from codepick_l3.readiness import l3_readiness
from codepick_l3.usage import require_api_key_identity

from .routers import v1


app = FastAPI(title="CodePick Public API")
app.include_router(v1.router, prefix="/v1")


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "public-api"}


@app.get("/v1/ready", dependencies=[Depends(require_api_key_identity)])
def ready() -> dict:
    readiness = l3_readiness()
    readiness["service"] = "public-api"
    return readiness
