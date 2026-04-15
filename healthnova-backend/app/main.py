import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.modules.retriever import warm_retrieval_assets
from app.routes.analyze import router as analyze_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.doctors import router as doctors_router
from app.routes.ingest import router as ingest_router
from app.routes.translate_live import router as translate_router
from app.routes.workspace import router as workspace_router

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(ingest_router)
app.include_router(analyze_router)
app.include_router(chat_router)
app.include_router(doctors_router)
app.include_router(translate_router)


@app.on_event("startup")
async def warm_runtime_caches() -> None:
    threading.Thread(target=warm_retrieval_assets, daemon=True).start()


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
