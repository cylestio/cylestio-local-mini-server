"""
Insights package for the Cylestio Mini-Local Server.

This package contains modules for extracting business insights from AI agent telemetry data.
"""

# Import base classes and registry
from app.business_logic.insights.base import BaseInsightExtractor, insight_registry

# Import insight modules
from app.business_logic.insights import agent_health_insights
from app.business_logic.insights import conversation_quality_insights
from app.business_logic.insights import session_analytics_insights
from app.business_logic.insights import content_insights

# Export key components
__all__ = [
    "BaseInsightExtractor",
    "insight_registry",
    "agent_health_insights",
    "conversation_quality_insights",
    "session_analytics_insights",
    "content_insights"
]
