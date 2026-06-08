from fastapi import APIRouter

from app.observability import counters, uptime_seconds

router = APIRouter(tags=["meta"])


@router.get("/")
def greet():
    return {
        "name": "SaaS Product Management Dashboard",
        "status": "ready",
        "docs": "/docs",
    }


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.get("/metrics")
def metrics():
    return {"uptime_seconds": uptime_seconds(), "counters": counters.snapshot()}
