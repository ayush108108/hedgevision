"""
Configuration for AI Audit Framework
"""
import os
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def require_env(name: str, description: str = "") -> str:
    """
    Get required environment variable with validation.

    Args:
        name: Environment variable name
        description: Human-readable description for error messages

    Returns:
        The environment variable value

    Raises:
        RuntimeError: If the environment variable is missing or empty
    """
    value = os.getenv(name)
    if not value or value.strip() == "":
        desc = f" ({description})" if description else ""
        raise RuntimeError(
            f"Missing required environment variable: {name}{desc}. "
            "Please set this variable in your environment or .env file."
        )
    return value.strip()


def validate_env_vars() -> None:
    """
    Validate all required environment variables at startup.

    Raises:
        RuntimeError: If any required environment variables are missing
    """
    errors = []

    # Required Supabase variables
    try:
        require_env("SUPABASE_URL", "Supabase project URL")
        require_env("SUPABASE_ANON_KEY", "Supabase anonymous key")
    except RuntimeError as e:
        errors.append(str(e))

    # Required audit provider variables
    try:
        require_env("OPENAI_API_KEY", "OpenAI API key for primary audit provider")
    except RuntimeError as e:
        errors.append(str(e))

    # Optional but recommended variables
    if not os.getenv("PERPLEXITY_API_KEY"):
        errors.append(
            "Warning: PERPLEXITY_API_KEY not set. "
            "Dual provider audit will not be available as fallback."
        )

    if errors:
        error_msg = "Environment validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(error_msg)


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"


class AlertLevel(str, Enum):
    """Alert severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditConfig(BaseModel):
    """Configuration for AI audit system"""

    # Enable/disable audit system
    enabled: bool = Field(default=True, description="Enable AI audit system")

    # LLM Provider configuration
    primary_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI, description="Primary LLM provider"
    )
    fallback_provider: Optional[LLMProvider] = Field(
        default=LLMProvider.ANTHROPIC, description="Fallback LLM provider"
    )

    # OpenAI configuration (GPT-5 with extended context)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-4-turbo-preview", description="OpenAI model (use gpt-4-turbo or gpt-5 when available)"
    )
    openai_max_tokens: int = Field(default=128000, description="Max input tokens for OpenAI (128K context)")
    openai_temperature: float = Field(default=0.1, description="Temperature for OpenAI")

    # Perplexity configuration (Online RAG capabilities)
    perplexity_api_key: Optional[str] = Field(
        default=None, description="Perplexity API key"
    )
    perplexity_model: str = Field(
        default="llama-3.1-sonar-huge-128k-online", description="Perplexity model with online search"
    )
    perplexity_max_tokens: int = Field(
        default=127000, description="Max input tokens for Perplexity (127K context)"
    )
    perplexity_temperature: float = Field(
        default=0.1, description="Temperature for Perplexity"
    )

    # Audit behavior
    schedule: str = Field(default="0 */6 * * *", description="Cron schedule")
    realtime_logs: bool = Field(
        default=True, description="Monitor logs in real-time"
    )
    data_sampling_rate: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Data sampling rate (0-1), default 15%"
    )
    max_context_size: int = Field(
        default=250000, description="Maximum context tokens (250K for extended analysis)"
    )
    report_formats: List[str] = Field(
        default=["json", "markdown"], description="Report output formats"
    )
    alert_threshold: AlertLevel = Field(
        default=AlertLevel.HIGH, description="Minimum alert level"
    )

    # Notification settings
    slack_webhook: Optional[str] = Field(
        default=None, description="Slack webhook for alerts"
    )
    email_alerts: Optional[List[str]] = Field(
        default=None, description="Email addresses for alerts"
    )

    # Paths
    codebase_root: str = Field(
        default=".", description="Root directory of codebase"
    )
    audit_reports_dir: str = Field(
        default="./audit_reports", description="Directory for audit reports"
    )
    log_files: List[str] = Field(
        default=["./logs/*.log"], description="Log files to monitor"
    )

    @classmethod
    def from_env(cls) -> "AuditConfig":
        """Load configuration from environment variables"""
        # Validate required environment variables first
        validate_env_vars()

        return cls(
            enabled=os.getenv("AI_AUDIT_ENABLED", "true").lower() == "true",
            primary_provider=LLMProvider(
                os.getenv("AI_AUDIT_PRIMARY_PROVIDER", "openai")
            ),
            fallback_provider=(
                LLMProvider(os.getenv("AI_AUDIT_FALLBACK_PROVIDER"))
                if os.getenv("AI_AUDIT_FALLBACK_PROVIDER")
                else None
            ),
            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "128000")),
            openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            # Perplexity
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
            perplexity_model=os.getenv(
                "PERPLEXITY_MODEL", "llama-3.1-sonar-huge-128k-online"
            ),
            perplexity_max_tokens=int(os.getenv("PERPLEXITY_MAX_TOKENS", "127000")),
            perplexity_temperature=float(os.getenv("PERPLEXITY_TEMPERATURE", "0.1")),
            # Audit settings
            schedule=os.getenv("AI_AUDIT_SCHEDULE", "0 */6 * * *"),
            realtime_logs=os.getenv("AI_AUDIT_REALTIME_LOGS", "true").lower()
            == "true",
            data_sampling_rate=float(os.getenv("AI_AUDIT_DATA_SAMPLING_RATE", "0.15")),
            max_context_size=int(os.getenv("AI_AUDIT_MAX_CONTEXT_SIZE", "250000")),
            report_formats=os.getenv("AI_AUDIT_REPORT_FORMAT", "json,markdown").split(
                ","
            ),
            alert_threshold=AlertLevel(
                os.getenv("AI_AUDIT_ALERT_THRESHOLD", "high")
            ),
            slack_webhook=os.getenv("AI_AUDIT_SLACK_WEBHOOK"),
            email_alerts=(
                os.getenv("AI_AUDIT_EMAIL_ALERTS", "").split(",")
                if os.getenv("AI_AUDIT_EMAIL_ALERTS")
                else None
            ),
        )


# Global configuration instance
audit_config = AuditConfig.from_env()
