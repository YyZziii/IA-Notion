from fastapi import APIRouter
from schemas import QueryRequest, RoutingResponse
from llm_router import route_question

router = APIRouter()

@router.post("/route", response_model=RoutingResponse)
async def route_query(request: QueryRequest):
    domain = route_question(request.question)
    return RoutingResponse(domain=domain)
