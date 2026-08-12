from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, KnowledgeRetrievalServiceDep
from app.schemas.knowledge_retrieval import KnowledgeRetrievalRequest, KnowledgeRetrievalResponse

router = APIRouter(tags=["bot knowledge"])


@router.post(
    "/bots/{bot_id}/knowledge/retrieve",
    response_model=KnowledgeRetrievalResponse,
    summary="Retrieve knowledge chunks relevant to a query (full-text, bot-scoped)",
)
async def retrieve_bot_knowledge(
    bot_id: UUID,
    user: CurrentUser,
    service: KnowledgeRetrievalServiceDep,
    body: KnowledgeRetrievalRequest,
) -> KnowledgeRetrievalResponse:
    return await service.retrieve_for_bot(
        user,
        bot_id,
        query=body.query,
        limit=body.limit,
        max_context_chunks=body.max_context_chunks,
        max_context_estimated_tokens=body.max_context_estimated_tokens,
    )
