from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import agents, activity, approvals, chat, conversation, settings as settings_router

app = FastAPI(title="Personal AI Operations Platform API", version="0.1.0")

origins = [o.strip() for o in settings.FRONTEND_ORIGIN.split(",")] if settings.FRONTEND_ORIGIN != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(approvals.router)
app.include_router(settings_router.router)
app.include_router(activity.router)
app.include_router(conversation.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "pia-backend"}


@app.get("/")
def root():
    return {"service": "Personal AI Operations Platform API", "docs": "/docs"}
