from pydantic import BaseModel
from typing import List

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 2

class RetrieveResponse(BaseModel):
    context: str
    sources: List[str]


class IngestSourceStatus(BaseModel):
    source_id: str
    connector_type: str
    status: str
    chunks: int = 0
    message: str = ""


class IngestResponse(BaseModel):
    run_status: str
    message: str
    total_chunks: int
    source_status: List[IngestSourceStatus]
    
    