from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

load_dotenv()
LOG_LEVEL = os.getenv("BACKEND_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from .routers import forecast, simulate, risk, query
from .middleware.error_handler import error_handler_middleware

app = FastAPI(
    title="Epidemic Intelligence Gateway",
    description="Backend gateway for the Regional Epidemic Intelligence System",
    version="1.0.0"
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware
app.middleware("http")(error_handler_middleware)

# Mount routes
app.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
app.include_router(simulate.router, prefix="/simulate", tags=["Simulate"])
app.include_router(risk.router, prefix="/risk", tags=["Risk"])
app.include_router(query.router, prefix="/query", tags=["Query"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}
