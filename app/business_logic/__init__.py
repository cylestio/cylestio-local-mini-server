"""
Business Logic package for the Cylestio Mini-Local Server.

This package provides the business logic layer for the Cylestio Mini-Local Server, 
including metrics calculation, insights extraction, and analytics capabilities.
"""

from app.business_logic.metrics import BaseMetricCalculator, metric_registry
from app.business_logic.insights import BaseInsightExtractor, insight_registry

# Define the BusinessLogicLayer class for integrating all components
class BusinessLogicLayer:
    """The main business logic layer that integrates all components.
    
    This class provides a unified interface for accessing metrics and insights
    from the business logic layer.
    """
    
    def __init__(self):
        self.metric_registry = metric_registry
        self.insight_registry = insight_registry
    
    def calculate_metric(self, metric_name, db, **kwargs):
        """Calculate a specific metric.
        
        Args:
            metric_name: Name of the metric to calculate
            db: Database session
            **kwargs: Additional arguments to pass to the metric calculator
            
        Returns:
            The calculated metric result, or None if the metric doesn't exist
            
        Raises:
            ValueError: If the specified metric doesn't exist
        """
        calculator = self.metric_registry.get_calculator(metric_name)
        if calculator:
            return calculator.calculate(db=db, **kwargs)
        raise ValueError(f"Metric '{metric_name}' not found")
    
    def calculate_all_metrics(self, db, **kwargs):
        """Calculate all registered metrics.
        
        Args:
            db: Database session
            **kwargs: Additional arguments to pass to the metric calculators
            
        Returns:
            Dict mapping metric names to their calculated results
        """
        results = {}
        for name, calculator in self.metric_registry.get_all_calculators().items():
            results[name] = calculator.calculate(db=db, **kwargs)
        return results
    
    def extract_insight(self, insight_name, db, **kwargs):
        """Extract a specific insight.
        
        Args:
            insight_name: Name of the insight to extract
            db: Database session
            **kwargs: Additional arguments to pass to the insight extractor
            
        Returns:
            The extracted insight, or None if the insight doesn't exist
            
        Raises:
            ValueError: If the specified insight doesn't exist
        """
        extractor = self.insight_registry.get_extractor(insight_name)
        if extractor:
            return extractor.extract(db=db, **kwargs)
        raise ValueError(f"Insight '{insight_name}' not found")
    
    def extract_all_insights(self, db, **kwargs):
        """Extract all registered insights.
        
        Args:
            db: Database session
            **kwargs: Additional arguments to pass to the insight extractors
            
        Returns:
            Dict mapping insight names to their extracted results
        """
        results = {}
        for name, extractor in self.insight_registry.get_all_extractors().items():
            results[name] = extractor.extract(db=db, **kwargs)
        return results
    
    def get_available_metrics(self):
        """Get a list of all available metrics.
        
        Returns:
            List of metric names that can be calculated
        """
        return self.metric_registry.get_available_metrics()
    
    def get_available_insights(self):
        """Get a list of all available insights.
        
        Returns:
            List of insight names that can be extracted
        """
        return self.insight_registry.get_available_insights()


# Create a default instance of the business logic layer
business_logic = BusinessLogicLayer()

# Export key components
__all__ = [
    "business_logic",
    "BusinessLogicLayer",
    "BaseMetricCalculator",
    "metric_registry",
    "BaseInsightExtractor", 
    "insight_registry"
]
