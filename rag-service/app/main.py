from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from app.routers import retrieve

app = FastAPI(title="RAG Service")

app.include_router(retrieve.router, prefix="/retrieve")
