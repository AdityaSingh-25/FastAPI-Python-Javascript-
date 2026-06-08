from fastapi import APIRouter

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
