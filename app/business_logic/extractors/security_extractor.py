"""
SecurityExtractor module.

This module extracts security-related information from events.
"""

import logging
from typing import Optional

from app.models.security_alert import SecurityAlert
from app.business_logic.extractors.base import BaseExtractor
from sqlalchemy import select

# Set up logging
logger = logging.getLogger(__name__)


class SecurityExtractor(BaseExtractor):
    """Extractor for security alert data.
    
    Extracts security alerts, warnings, and suspicious activity markers
    from events that contain security-related information.
    """
    
    def can_process(self, event) -> bool:
        """Check if this event contains security data.
        
        Args:
            event: The event to check
            
        Returns:
            True if this event might contain security data
        """
        # Skip events with explicit "none" alert
        if hasattr(event, 'alert') and event.alert and event.alert.lower() == "none":
            return False
            
        # Skip events with "none" alert in data
        if event.data and 'alert' in event.data and event.data['alert'].lower() == "none":
            return False
            
        # Check for alert field at top level
        if hasattr(event, 'alert') and event.alert:
            return True
            
        # Check for alert in data
        if event.data and 'alert' in event.data:
            return True
            
        # Check for security-oriented event types
        security_event_types = {
            "LLM_call_start",
            "LLM_call_finish",
            "LLM_call_blocked"
        }
        
        return event.event_type in security_event_types
    
    async def process(self, event, db_session) -> None:
        """Extract security information from the event.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        # Check if security alert already exists for this event
        result = await db_session.execute(
            select(SecurityAlert).where(SecurityAlert.event_id == event.id)
        )
        existing_security_alert = result.scalars().first()
        
        if existing_security_alert:
            logger.info(f"Security alert already exists for event {event.id}, skipping extraction")
            return
            
        security_alert = await self._extract_security_alert(event)
        
        if security_alert:
            db_session.add(security_alert)
    
    async def _extract_security_alert(self, event) -> Optional[SecurityAlert]:
        """Extract security alert data from the event.
        
        Args:
            event: The event to extract from
            
        Returns:
            SecurityAlert object or None if no security data found
        """
        try:
            # Base security fields
            alert_type = None
            severity = None
            description = None
            
            # Check direct event attribute
            if hasattr(event, 'alert') and event.alert:
                alert_type = event.alert
            
            # Check in data field
            if not alert_type and event.data and 'alert' in event.data:
                alert_type = event.data['alert']
            
            # Skip if alert type is explicitly "none"
            if alert_type and alert_type.lower() == "none":
                return None
                
            # Special handling for LLM_call_blocked events
            if event.event_type == "LLM_call_blocked":
                if 'reason' in event.data:
                    reason = event.data['reason']
                    alert_type = 'blocked'
                    severity = 'high'
                    description = f"LLM call blocked: {reason}"
            
            # Set severity based on alert type
            if alert_type and not severity:
                if alert_type.lower() == 'dangerous':
                    severity = 'high'
                    description = 'Potentially harmful content detected'
                elif alert_type.lower() == 'suspicious':
                    severity = 'medium'
                    description = 'Suspicious pattern detected'
                else:
                    severity = 'low'
                    description = 'Informational security notice'
            
            # Handle specific event types
            if event.event_type == "LLM_call_start" and event.data:
                # Check prompt content for suspicious patterns
                if 'prompt' in event.data:
                    prompt = event.data['prompt']
                    # Simple check for potentially problematic content
                    dangerous_keywords = {'hack', 'exploit', 'bomb', 'attack', 'bypass'}
                    
                    if isinstance(prompt, list) and len(prompt) > 0:
                        # For list-type prompts, check the last item (most recent user message)
                        last_prompt = prompt[-1]
                        content = last_prompt.get('content', '') if isinstance(last_prompt, dict) else str(last_prompt)
                        
                        # Check for dangerous keywords
                        if any(keyword in content.lower() for keyword in dangerous_keywords):
                            alert_type = 'suspicious'
                            severity = 'medium'
                            description = 'Potentially problematic content in prompt'
            
            # If we found security data, create the object
            if alert_type:
                return SecurityAlert(
                    event_id=event.id,
                    alert_type=alert_type,
                    severity=severity or 'low',
                    description=description or 'Security alert detected',
                    timestamp=event.timestamp
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting security alert from event {event.id}: {str(e)}")
            return None 