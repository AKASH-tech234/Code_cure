from pydantic import BaseModel
from typing import List

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 2

class RetrieveResponse(BaseModel):
    context: str
    sources: List[str]
    
    