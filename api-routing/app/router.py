from fastapi import APIRouter
from llm_router import route_question
from schemas import QuestionRequest, QuestionResponse

router = APIRouter()

@router.post("/route", response_model=QuestionResponse)
async def route_question_endpoint(request: QuestionRequest):
    matched_collection = await route_question(request.question)
    if matched_collection:
        return QuestionResponse(collection=matched_collection)
    return QuestionResponse(collection="aucun")
