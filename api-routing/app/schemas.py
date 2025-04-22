from pydantic import BaseModel

class QueryRequest(BaseModel):
    question: str

class RoutingResponse(BaseModel):
    domain: str
