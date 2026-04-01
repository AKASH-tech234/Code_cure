import logging
import time
from fastapi import APIRouter
from ..schemas import QueryRequest, QueryResponse, FollowUp, SlotStatus, VerificationStatus, ExecutionStep
from ..session import session_manager
from ..services.agent_runner import run_agent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=QueryResponse)
async def query(body: QueryRequest):
    """
    /query endpoint — routes to LangGraph agent with session memory.

    Flow:
    1. Look up or create session
    2. Inject memory into agent
    3. Run graph
    4. Persist updated memory
    5. Return structured response
    """
    started_at = time.perf_counter()
    request_payload = body.model_dump(exclude_none=True)

    # 1. Get or create session
    session_id, memory = session_manager.get_or_create(body.session_id)
    logger.info(
        "[QUERY][REQ] session=%s query_len=%d has_region=%s has_intervention=%s",
        session_id,
        len(body.query),
        body.region_id is not None,
        body.intervention is not None,
    )
    logger.debug("[QUERY][REQ_PAYLOAD] payload=%s", request_payload)

    # 2. Run agent with memory
    context = {}
    if body.region_id:
        context["region_id"] = body.region_id.upper()
    if body.intervention:
        context["intervention"] = body.intervention.model_dump()

    result = run_agent(
        query=body.query,
        memory=memory,
        context=context or None
    )

    # 3. Persist memory updates
    if result.get("memory_updates"):
        session_manager.update_memory(session_id, result["memory_updates"])

    # 4. Build response
    followup = None
    if result.get("followup"):
        followup = FollowUp(
            question=result["followup"]["question"],
            missing_fields=result["followup"]["missing_fields"]
        )

    slot_status = None
    if result.get("slot_status"):
        slot_status = SlotStatus(**result["slot_status"])

    verification = None
    if result.get("verification"):
        verification = VerificationStatus(**result["verification"])

    execution_steps = [
        ExecutionStep(**step)
        for step in (result.get("execution_steps") or [])
    ]

    response = QueryResponse(
        session_id=session_id,
        answer=result.get("answer"),
        intent=result.get("intent"),
        tool=result.get("tool"),
        reasoning=result.get("reasoning"),
        sources=result.get("sources") or [],
        structured_data=result.get("structured_data"),
        followup=followup,
        slot_status=slot_status,
        verification=verification,
        execution_steps=execution_steps,
        fallback_used=bool(result.get("fallback_used", False)),
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[QUERY][RESP] session=%s intent=%s tool=%s fallback_used=%s latency_ms=%.2f",
        session_id,
        response.intent,
        response.tool,
        response.fallback_used,
        latency_ms,
    )
    logger.debug("[QUERY][RESP_PAYLOAD] payload=%s", response.model_dump())
    return response
