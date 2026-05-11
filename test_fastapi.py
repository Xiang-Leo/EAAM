from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient

app = FastAPI()
router = APIRouter()

@router.get("")
def summary():
    return {"ok": True}

app.include_router(router, prefix="/api/summary")

client = TestClient(app)
print("GET /api/summary:", client.get("/api/summary").status_code)
print("GET /api/summary/:", client.get("/api/summary/").status_code)
