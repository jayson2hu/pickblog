from fastapi import FastAPI
from codepick_l3.readiness import l3_readiness

from .routers import admin, api_keys, auth, billing, briefs, companion, events, feed, library, me, read, taxonomy


app = FastAPI(title="CodePick Reader API")
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
