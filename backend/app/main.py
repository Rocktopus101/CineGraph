from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin,
    auth,
    eval_routes,
    history,
    import_routes,
    lists,
    movies,
    profile,
    recommendations,
    reviews,
    watchlist,
)
from app.core.config import get_settings
from app.core.security import init_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield


app = FastAPI(title="CineGraph API", version="0.1.0", lifespan=lifespan)

_settings = get_settings()
_cors_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]

_cors_middleware_kwargs: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if _cors_origins:
    _cors_middleware_kwargs["allow_origins"] = _cors_origins
if _settings.cors_origin_regex:
    _cors_middleware_kwargs["allow_origin_regex"] = _settings.cors_origin_regex

app.add_middleware(CORSMiddleware, **_cors_middleware_kwargs)

app.include_router(auth.router)
app.include_router(import_routes.router)
app.include_router(movies.router)
app.include_router(history.router)
app.include_router(profile.router)
app.include_router(recommendations.router)
app.include_router(reviews.router)
app.include_router(watchlist.router)
app.include_router(lists.router)
app.include_router(admin.router)
app.include_router(eval_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
