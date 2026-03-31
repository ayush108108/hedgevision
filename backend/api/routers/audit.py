"""
API router for AI audit framework
Provides endpoints to trigger and view audits
"""
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, ValidationError, field_validator
from typing import Literal

from api.audit.orchestrator import run_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["AI Audit"])


class AuditRequest(BaseModel):
    """Request model for triggering an audit"""

    audit_type: Literal["full", "codebase", "data", "logs", "calculations"] = "full"
    async_mode: bool = True  # Run in background or wait for completion

    @field_validator('audit_type')
    @classmethod
    def validate_audit_type(cls, v):
        """Validate that audit type is one of the allowed values"""
        if not isinstance(v, str):
            raise ValueError("Audit type must be a string")
        v = v.strip().lower()  # Sanitize: strip whitespace and lowercase
        allowed_types = ["full", "codebase", "data", "logs", "calculations"]
        if v not in allowed_types:
            raise ValueError(f"Audit type must be one of: {', '.join(allowed_types)}")
        return v


class AuditResponse(BaseModel):
    """Response model for audit requests"""

    status: str
    message: str
    job_id: Optional[str] = None
    report_path: Optional[str] = None
    trace_id: Optional[str] = None


def handle_audit_error(error: Exception) -> None:
    """
    Handle audit-related errors and raise appropriate HTTP exceptions.

    Args:
        error: The exception that occurred

    Raises:
        HTTPException: With appropriate status code and message
    """
    error_msg = str(error)

    # Configuration/Environment errors (400 Bad Request)
    if any(keyword in error_msg.lower() for keyword in [
        "missing required environment variable",
        "environment validation failed",
        "not_configured",
        "invalid configuration"
    ]):
        raise HTTPException(
            status_code=400,
            detail=f"Configuration error: {error_msg}"
        )

    # Authentication/Authorization errors (401/403)
    if any(keyword in error_msg.lower() for keyword in [
        "api key",
        "authentication",
        "authorization",
        "unauthorized",
        "forbidden"
    ]):
        raise HTTPException(
            status_code=401,
            detail="Authentication error: Please check API keys and permissions"
        )

    # Validation errors (422 Unprocessable Entity)
    if isinstance(error, ValidationError):
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {error_msg}"
        )

    # Not found errors (404)
    if any(keyword in error_msg.lower() for keyword in [
        "not found",
        "does not exist",
        "no such file"
    ]):
        raise HTTPException(
            status_code=404,
            detail=f"Resource not found: {error_msg}"
        )

    # Rate limiting or service unavailable (429/503)
    if any(keyword in error_msg.lower() for keyword in [
        "rate limit",
        "quota exceeded",
        "service unavailable",
        "timeout",
        "connection failed"
    ]):
        raise HTTPException(
            status_code=503,
            detail=f"Service temporarily unavailable: {error_msg}"
        )

    # Default to 500 for unexpected errors
    logger.error(f"Unexpected audit error: {error}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="Internal server error occurred during audit"
    )


@router.post("/run", response_model=AuditResponse)
async def trigger_audit(request: AuditRequest, background_tasks: BackgroundTasks):
    """
    Trigger an AI audit of the codebase and data

    Args:
        request: Audit configuration
        background_tasks: FastAPI background tasks

    Returns:
        Audit status and job information
    """
    try:
        if request.async_mode:
            # Run in background
            job_id = f"audit_{int(__import__('time').time())}"
            background_tasks.add_task(_run_audit_task, request.audit_type, job_id)

            return AuditResponse(
                status="started",
                message=f"Audit {job_id} started in background",
                job_id=job_id,
            )
        else:
            # Run synchronously (may take time)
            result = await run_audit(request.audit_type)

            if result.get("status") == "completed":
                return AuditResponse(
                    status="completed",
                    message="Audit completed successfully",
                    report_path=result.get("report_path"),
                    trace_id=result.get("trace_id"),
                )
            else:
                # Handle specific audit failure reasons
                error_msg = result.get("error", "Unknown audit error")
                if "provider" in error_msg.lower() or "api" in error_msg.lower():
                    raise HTTPException(
                        status_code=503,
                        detail=f"Audit service unavailable: {error_msg}"
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Audit failed: {error_msg}"
                    )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle other exceptions with our error handler
        handle_audit_error(e)


async def _run_audit_task(audit_type: str, job_id: str):
    """Background task to run audit"""
    logger.info(f"Running audit {job_id} (type: {audit_type})")
    try:
        result = await run_audit(audit_type)
        status = result.get("status", "unknown")
        logger.info(f"Audit {job_id} completed with status: {status}")

        if status != "completed":
            logger.error(f"Audit {job_id} failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Audit {job_id} failed with exception: {e}", exc_info=True)


@router.get("/status")
async def get_audit_status():
    """
    Get status of the AI audit system

    Returns:
        System status and configuration
    """
    from api.audit.config import audit_config

    return {
        "enabled": audit_config.enabled,
        "primary_provider": audit_config.primary_provider.value,
        "fallback_provider": (
            audit_config.fallback_provider.value
            if audit_config.fallback_provider
            else None
        ),
        "realtime_logs": audit_config.realtime_logs,
        "schedule": audit_config.schedule,
    }


@router.get("/health")
async def check_audit_health():
    """
    Check health of AI audit system (verify API keys, etc.)

    Returns:
        Health check results
    """
    from api.audit.config import audit_config

    health = {
        "overall": "healthy",
        "providers": {},
    }

    # Check OpenAI (Primary)
    if audit_config.openai_api_key:
        health["providers"]["openai"] = "configured (primary - GPT-5 extended context)"
    else:
        health["providers"]["openai"] = "not_configured"

    # Check Perplexity (Fallback with online RAG)
    if audit_config.perplexity_api_key:
        health["providers"]["perplexity"] = "configured (fallback - online RAG)"
    else:
        health["providers"]["perplexity"] = "not_configured"

    # Overall health
    if not any(
        "configured" in status for status in health["providers"].values()
    ):
        health["overall"] = "unhealthy - no providers configured"
    
    health["note"] = "Anthropic removed - using OpenAI (GPT-5) + Perplexity for optimal reasoning"

    return health
