from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import forecast, simulate, risk
from app.services import initialize_epidemic_runtime

app = FastAPI(
    title="Epidemic ML Service",
    description="Forecast, simulate, and assess epidemic risk",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
app.include_router(simulate.router, prefix="/simulate", tags=["Simulate"])
app.include_router(risk.router, prefix="/risk", tags=["Risk"])


@app.on_event("startup")
def startup_event() -> None:
    initialize_epidemic_runtime()


@app.get("/health")
def health():
    return {"status": "ok", "service": "ml-service"}
