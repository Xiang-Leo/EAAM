from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .api import endpoints

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EAAM API", description="Ancient Chinese Dental Calculus Microbiome API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix="/api", tags=["eaam"])

@app.get("/")
def read_root():
    return {"message": "Welcome to EAAM API"}
