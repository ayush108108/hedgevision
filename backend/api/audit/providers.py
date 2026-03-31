"""
LLM Provider interface for AI audit framework
Enhanced reasoning capabilities for comprehensive judgment
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from api.audit.config import AuditConfig, LLMProvider

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: AuditConfig):
        self.config = config

    @abstractmethod
    async def analyze(
        self, context: Dict[str, Any], analysis_type: str
    ) -> Dict[str, Any]:
        """
        Analyze the given context and return insights

        Args:
            context: Dictionary containing all relevant data (code, logs, data)
            analysis_type: Type of analysis (codebase, data, logs, calculations)

        Returns:
            Dictionary with analysis results and recommendations
        """
        pass

    def _build_system_prompt(self, analysis_type: str) -> str:
        """Build system prompt based on analysis type with enhanced reasoning"""
        base_prompt = """You are an EXPERT AI AUDITOR AND JUDGE for HedgeVision, a quantitative trading platform.

**YOUR ROLE AS JUDGE:**
You are not just identifying issues - you are JUDGING the quality, correctness, and reliability of:
- Code architecture and implementation
- Data integrity and consistency
- Calculation accuracy and mathematical correctness
- System design and performance
- Security and best practices

**CRITICAL THINKING REQUIREMENTS:**
1. **Deep Analysis**: Don't just surface-level scan. Understand the business logic, mathematical foundations, and data flow.
2. **Cross-Reference**: Verify calculations against formulas, check data consistency across tables, validate logic across files.
3. **Root Cause**: Don't just report symptoms - identify root causes and trace issues to their source.
4. **Impact Assessment**: Rate each issue by its ACTUAL business impact, not just technical severity.
5. **Evidence-Based**: Provide specific file paths, line numbers, data examples, and code snippets as evidence.
6. **Reasoning Chain**: Show your reasoning process - explain WHY something is wrong and HOW you determined it.

**JUDGMENT CRITERIA:**
- **CRITICAL**: Data corruption, incorrect calculations affecting money, security vulnerabilities, data loss risks
- **HIGH**: Logic errors, performance issues affecting users, data quality problems, missing error handling
- **MEDIUM**: Code quality issues, minor inconsistencies, optimization opportunities, documentation gaps
- **LOW**: Style issues, minor improvements, best practice suggestions

**OUTPUT FORMAT:**
For each issue found:
1. **Issue**: Clear description of what's wrong
2. **Evidence**: Specific code/data/log excerpts proving the issue
3. **Reasoning**: Your analytical process - how you identified this
4. **Root Cause**: Why this happened (design flaw, oversight, edge case, etc.)
5. **Impact**: Business/technical consequences
6. **Severity**: CRITICAL/HIGH/MEDIUM/LOW with justification
7. **Recommendation**: Specific, actionable fix with code examples if applicable

**IMPORTANT:**
- Be thorough but efficient - focus on real issues, not nitpicks
- Understand the FINANCIAL domain - this is trading/quant code
- Verify calculations: cointegration tests, spreads, z-scores, correlations
- Check data integrity: referential integrity, schema consistency, outliers
- Think like a senior engineer reviewing a critical production system
"""

        type_specific = {
            "codebase": """
**CODEBASE ANALYSIS - JUDGE THE CODE ARCHITECTURE:**

Evaluate:
1. **Correctness**: Does the code do what it claims? Are algorithms implemented correctly?
2. **Data Flow**: Trace data from ingestion → processing → storage → retrieval. Any breaks?
3. **Error Handling**: Are edge cases handled? What happens on failure?
4. **Performance**: Any O(n²) when O(n) is possible? Database N+1 queries? Memory leaks?
5. **Security**: SQL injection risks? API key exposure? Input validation?
6. **Type Safety**: Are types used correctly? Any type mismatches?
7. **API Design**: RESTful? Consistent? Well-documented?
8. **Database Queries**: Efficient? Using indexes? Avoiding full scans?

Cross-check:
- Service layer logic vs. database schema
- API contracts vs. actual implementations
- Error handling across the call stack
- Data validation at all entry points
""",
            "data": """
**DATABASE ANALYSIS - JUDGE THE DATA INTEGRITY:**

Evaluate:
1. **Schema Consistency**: Do table relationships make sense? Foreign keys valid?
2. **Data Quality**: Any NULL where shouldn't be? Outliers? Invalid ranges?
3. **Referential Integrity**: Orphaned records? Broken relationships?
4. **Calculation Accuracy**: Do stored calculations match expected formulas?
   - Spreads = asset1 - (beta * asset2 + alpha)
   - Z-scores = (spread - mean) / std
   - Correlations in [-1, 1] range
5. **Temporal Consistency**: Timestamps logical? No future dates? Correct timezones?
6. **Index Usage**: Are queries using indexes? Missing indexes causing slowdowns?
7. **Data Completeness**: Expected records present? Gaps in time series?

Cross-check:
- Price data vs. calculated metrics (verify formulas)
- Asset table vs. price_history (all assets have data?)
- Cointegration scores vs. pair_trades (consistency?)
- Spread history vs. real-time calculations (matching?)
""",
            "logs": """
**LOG ANALYSIS - JUDGE THE OPERATIONAL HEALTH:**

Evaluate:
1. **Error Patterns**: Recurring errors? Escalating frequency? Correlated failures?
2. **Performance Trends**: Response times increasing? Timeouts? Memory issues?
3. **Data Pipeline**: Any failed ingestions? Missing data? Incomplete updates?
4. **Anomalies**: Unusual behavior? Unexpected spikes? Security concerns?
5. **Failed Operations**: What's failing? Why? How often? Impact?

Look for:
- Error bursts (indicating systemic issues)
- Silent failures (logged but not alerting)
- Performance degradation trends
- Security events (failed auth, suspicious queries)
- Data quality warnings

Trace:
- Follow error chains to root cause
- Correlate errors across services
- Identify patterns over time
""",
            "calculations": """
**CALCULATION VERIFICATION - JUDGE THE MATHEMATICAL ACCURACY:**

This is CRITICAL - incorrect calculations mean wrong trades and lost money.

Verify:
1. **Cointegration Tests**:
   - Engle-Granger: residuals = Y - (beta*X + alpha), ADF test on residuals
   - Johansen: correct trace statistic calculation
   - P-values in [0,1], test statistics match critical values
   
2. **Spread Calculation**:
   - Formula: spread = asset1_price - (hedge_ratio * asset2_price + intercept)
   - Verify hedge_ratio from regression
   - Check intercept (alpha) is included
   
3. **Z-Score Calculation**:
   - Formula: z = (spread - mean(spread)) / std(spread)
   - Verify using correct mean/std (rolling window vs. full series)
   - Check for division by zero
   
4. **Correlation Calculations**:
   - Pearson: linear correlation in [-1, 1]
   - Spearman: rank correlation, handles non-linear
   - Verify using correct data (close prices, not OHLC)
   
5. **Numerical Stability**:
   - Check for NaN, Inf, division by zero
   - Verify precision (float64 vs float32)
   - Handle edge cases (zero variance, perfect correlation)

Cross-verify:
- Recalculate sample spreads from raw data
- Check calculations against statsmodels/scipy
- Verify database-stored values vs. real-time calculations
- Test edge cases (zero prices, missing data, single data point)
""",
        }

        return base_prompt + type_specific.get(analysis_type, "")


    def _format_response(self, raw_response: str) -> Dict[str, Any]:
        """Format LLM response into structured output"""
        try:
            # Try to parse as JSON first
            import json

            return json.loads(raw_response)
        except Exception:
            # If not JSON, create structured response
            return {
                "analysis": raw_response,
                "issues": self._extract_issues(raw_response),
                "recommendations": self._extract_recommendations(raw_response),
            }

    def _extract_issues(self, text: str) -> List[Dict[str, str]]:
        """Extract issues from text response"""
        issues = []
        lines = text.split("\n")
        current_issue = None

        for line in lines:
            line_lower = line.lower()
            if any(
                keyword in line_lower
                for keyword in ["error", "bug", "issue", "problem", "critical", "high"]
            ):
                if current_issue:
                    issues.append(current_issue)
                current_issue = {"description": line, "severity": "MEDIUM"}
            elif current_issue and line.strip():
                current_issue["description"] += " " + line

        if current_issue:
            issues.append(current_issue)

        return issues

    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract recommendations from text response"""
        recommendations = []
        lines = text.split("\n")

        for line in lines:
            line_lower = line.lower()
            if any(
                keyword in line_lower
                for keyword in ["recommend", "suggest", "should", "consider", "fix"]
            ):
                if line.strip():
                    recommendations.append(line.strip())

        return recommendations


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider"""

    def __init__(self, config: AuditConfig):
        super().__init__(config)
        
        # GPT-5 specific parameter handling
        model_kwargs = {
            "model": config.openai_model,
            "api_key": config.openai_api_key,
        }
        
        # GPT-5 models use different parameters
        if "gpt-5" in config.openai_model.lower():
            # GPT-5 uses max_completion_tokens and only supports temperature=1
            model_kwargs["max_completion_tokens"] = config.openai_max_tokens
            # Don't set temperature for GPT-5 (defaults to 1)
        else:
            # GPT-4 and earlier use max_tokens and support custom temperature
            model_kwargs["max_tokens"] = config.openai_max_tokens
            model_kwargs["temperature"] = config.openai_temperature
        
        self.client = ChatOpenAI(**model_kwargs)

    async def analyze(
        self, context: Dict[str, Any], analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze using OpenAI GPT"""
        try:
            system_prompt = self._build_system_prompt(analysis_type)
            user_message = self._build_context_message(context, analysis_type)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]

            response = await self.client.ainvoke(messages)
            return self._format_response(response.content)

        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            return {"error": str(e), "provider": "openai"}

    def _build_context_message(
        self, context: Dict[str, Any], analysis_type: str
    ) -> str:
        """Build context message for analysis"""
        message_parts = [f"Performing {analysis_type} analysis.\n"]

        if "files" in context:
            message_parts.append(
                f"\n## Code Files ({len(context['files'])} files)\n"
            )
            for file_path, content in context["files"].items():
                message_parts.append(f"\n### {file_path}\n```python\n{content}\n```\n")

        if "data" in context:
            message_parts.append(f"\n## Database Data\n```json\n{context['data']}\n```\n")

        if "logs" in context:
            message_parts.append(f"\n## Logs\n```\n{context['logs']}\n```\n")

        if "schema" in context:
            message_parts.append(f"\n## Database Schema\n```sql\n{context['schema']}\n```\n")

        if "metrics" in context:
            message_parts.append(f"\n## Metrics\n{context['metrics']}\n")

        return "\n".join(message_parts)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider - DEPRECATED, removed from configuration"""

    def __init__(self, config: AuditConfig):
        super().__init__(config)
        # Anthropic support removed - using GPT-5 + Perplexity instead
        raise NotImplementedError(
            "Anthropic provider has been removed. Use OpenAI (GPT-5) or Perplexity instead."
        )

    async def analyze(
        self, context: Dict[str, Any], analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze using Anthropic Claude - DEPRECATED"""
        raise NotImplementedError(
            "Anthropic provider has been removed. Use OpenAI (GPT-5) or Perplexity instead."
        )


class PerplexityProvider(BaseLLMProvider):
    """Perplexity AI provider (via OpenAI-compatible API)"""

    def __init__(self, config: AuditConfig):
        super().__init__(config)
        # Perplexity uses OpenAI-compatible API
        self.client = ChatOpenAI(
            model=config.perplexity_model,
            api_key=config.perplexity_api_key,
            base_url="https://api.perplexity.ai",
            max_tokens=config.perplexity_max_tokens,
            temperature=config.perplexity_temperature,
        )

    async def analyze(
        self, context: Dict[str, Any], analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze using Perplexity AI"""
        try:
            system_prompt = self._build_system_prompt(analysis_type)
            user_message = self._build_context_message(context, analysis_type)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]

            response = await self.client.ainvoke(messages)
            return self._format_response(response.content)

        except Exception as e:
            logger.error(f"Perplexity analysis failed: {e}")
            return {"error": str(e), "provider": "perplexity"}

    def _build_context_message(
        self, context: Dict[str, Any], analysis_type: str
    ) -> str:
        """Build context message for analysis"""
        # Same implementation as OpenAI
        message_parts = [f"Performing {analysis_type} analysis.\n"]

        if "files" in context:
            message_parts.append(
                f"\n## Code Files ({len(context['files'])} files)\n"
            )
            for file_path, content in context["files"].items():
                message_parts.append(f"\n### {file_path}\n```python\n{content}\n```\n")

        if "data" in context:
            message_parts.append(f"\n## Database Data\n```json\n{context['data']}\n```\n")

        if "logs" in context:
            message_parts.append(f"\n## Logs\n```\n{context['logs']}\n```\n")

        if "schema" in context:
            message_parts.append(f"\n## Database Schema\n```sql\n{context['schema']}\n```\n")

        if "metrics" in context:
            message_parts.append(f"\n## Metrics\n{context['metrics']}\n")

        return "\n".join(message_parts)


def get_llm_provider(
    provider: LLMProvider, config: AuditConfig
) -> BaseLLMProvider:
    """Factory function to get LLM provider (OpenAI or Perplexity only)"""
    providers = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.PERPLEXITY: PerplexityProvider,
        # Anthropic removed - using GPT-5 + Perplexity for better reasoning
    }

    provider_class = providers.get(provider)
    if not provider_class:
        raise ValueError(
            f"Unsupported provider: {provider}. Use 'openai' or 'perplexity' only."
        )

    return provider_class(config)
