"""
SecurityExtractor module.

This module provides an extractor for security-related data from events,
which extracts security alerts and warning information.
"""

from typing import Dict, Any, Optional, List
import logging
import json

from app.business_logic.extractors.base import BaseExtractor, extractor_registry
from app.models.security_alert import SecurityAlert

# Set up logging
logger = logging.getLogger(__name__)


class SecurityExtractor(BaseExtractor):
    """Extractor for security-related data from events.
    
    Extracts security alerts and warning information from events
    that contain security data.
    """
    
    def can_process(self, event) -> bool:
        """Determine if this extractor can process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if the event contains security data, False otherwise
        """
        if not event.data:
            return False
        
        # Check if the event has security data
        return "security" in event.data
    
    async def process(self, event, db_session) -> None:
        """Process the event and extract security data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        if not event.data:
            logger.warning(f"No data in event {event.id}")
            return
        
        # Extract security alerts
        await self._extract_security_alerts(event, db_session)
    
    async def _extract_security_alerts(self, event, db_session) -> List[SecurityAlert]:
        """Extract security alerts from the event.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            List of created SecurityAlert objects
        """
        try:
            data = event.data
            
            # Get security data
            security = data.get("security", {})
            if not security:
                return []
            
            alerts = []
            
            # Process top-level alert
            alert_level = security.get("alert_level")
            if alert_level and alert_level != "none":
                alert = SecurityAlert(
                    event_id=event.id,
                    alert_level=alert_level,
                    field_path="",
                    description=f"Security alert detected in {event.event_type} event"
                )
                await db_session.add(alert)
                alerts.append(alert)
            
            # Process field-specific alerts
            field_checks = security.get("field_checks", {})
            if field_checks:
                for field_path, field_data in self._flatten_security_checks(field_checks):
                    alert_level = field_data.get("alert_level")
                    if alert_level and alert_level != "none":
                        alert = SecurityAlert(
                            event_id=event.id,
                            alert_level=alert_level,
                            field_path=field_path,
                            description=f"Security alert detected in field '{field_path}'"
                        )
                        await db_session.add(alert)
                        alerts.append(alert)
            
            # Check for direct security notifications in the data
            if "security_alerts" in data:
                sec_alerts = data.get("security_alerts", [])
                if isinstance(sec_alerts, list):
                    for i, sec_alert in enumerate(sec_alerts):
                        if isinstance(sec_alert, dict):
                            level = sec_alert.get("level", "warning")
                            description = sec_alert.get("description", f"Security issue #{i+1}")
                            field = sec_alert.get("field", "")
                            
                            alert = SecurityAlert(
                                event_id=event.id,
                                alert_level=level,
                                field_path=field,
                                description=description
                            )
                            await db_session.add(alert)
                            alerts.append(alert)
                elif isinstance(sec_alerts, dict):
                    # Handle dictionary format
                    for field, alert_info in sec_alerts.items():
                        level = "warning"
                        description = f"Security issue in {field}"
                        
                        if isinstance(alert_info, dict):
                            level = alert_info.get("level", "warning")
                            description = alert_info.get("description", description)
                        
                        alert = SecurityAlert(
                            event_id=event.id,
                            alert_level=level,
                            field_path=field,
                            description=description
                        )
                        await db_session.add(alert)
                        alerts.append(alert)
            
            # Check for potential security issues in prompt content
            if event.event_type == "model_request" and "prompts" in data:
                prompts = data.get("prompts", [])
                if prompts and isinstance(prompts, list):
                    # Basic security checks for concerning content
                    security_keywords = [
                        "password", "secret", "token", "api key", "credential", 
                        "exploit", "hack", "bypass", "vulnerability"
                    ]
                    
                    for i, prompt in enumerate(prompts):
                        if not isinstance(prompt, str):
                            continue
                            
                        prompt_lower = prompt.lower()
                        for keyword in security_keywords:
                            if keyword in prompt_lower:
                                alert = SecurityAlert(
                                    event_id=event.id,
                                    alert_level="warning",
                                    field_path=f"prompts[{i}]",
                                    description=f"Potential security concern: prompt contains '{keyword}'"
                                )
                                await db_session.add(alert)
                                alerts.append(alert)
                                break  # Only one alert per prompt
            
            if alerts:
                logger.info(f"Extracted {len(alerts)} security alerts for event {event.id}")
            
            return alerts
        except Exception as e:
            logger.error(f"Error extracting security alerts for event {event.id}: {str(e)}")
            return []
    
    def _flatten_security_checks(self, field_checks, prefix=""):
        """Flatten nested security checks into (path, data) pairs.
        
        Args:
            field_checks: Nested field checks dictionary
            prefix: Path prefix for nested fields
            
        Yields:
            Tuples of (field_path, field_data)
        """
        for key, value in field_checks.items():
            path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict) and "alert_level" in value:
                # This is a leaf node
                yield (path, value)
            elif isinstance(value, dict):
                # This is a nested dictionary
                yield from self._flatten_security_checks(value, path)


# Register the extractor
extractor_registry.register(SecurityExtractor()) 