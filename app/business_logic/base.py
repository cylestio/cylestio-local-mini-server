"""
Base module for business logic layer.

This module provides base classes and registries for the business logic layer.
"""

from typing import Dict, Any, List, Type, Set, Optional
from sqlalchemy.orm import Session
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)


class BaseMetricCalculator:
    """Base class for metric calculators.
    
    All metric calculators should inherit from this class and implement
    the calculate method.
    """
    
    def get_name(self) -> str:
        """Get the name of the calculator.
        
        Returns the class name by default, can be overridden for custom names.
        """
        return self.__class__.__name__
    
    def calculate(self, db: Session, **kwargs) -> Dict[str, Any]:
        """Calculate metrics.
        
        Args:
            db: Database session
            **kwargs: Additional parameters for calculation
            
        Returns:
            Dict containing calculated metrics
        """
        raise NotImplementedError("Subclasses must implement calculate()")


class MetricRegistry:
    """Registry for metric calculators.
    
    Keeps track of all available metric calculators and provides
    methods to access them.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._calculators = {}
    
    def register(self, calculator: BaseMetricCalculator) -> None:
        """Register a metric calculator.
        
        Args:
            calculator: The calculator to register
        """
        name = calculator.get_name()
        self._calculators[name] = calculator
        logger.info(f"Registered metric calculator: {name}")
    
    def get_calculator(self, name: str) -> Optional[BaseMetricCalculator]:
        """Get a calculator by name.
        
        Args:
            name: Name of the calculator to get
            
        Returns:
            The calculator if found, None otherwise
        """
        return self._calculators.get(name)
    
    def get_all_calculators(self) -> Dict[str, BaseMetricCalculator]:
        """Get all registered calculators.
        
        Returns:
            Dict mapping calculator names to calculators
        """
        return self._calculators.copy()
    
    def get_available_metrics(self) -> List[str]:
        """Get names of all available metrics.
        
        Returns:
            List of metric names
        """
        return list(self._calculators.keys())


class BaseInsightExtractor:
    """Base class for insight extractors.
    
    All insight extractors should inherit from this class and implement
    the extract method.
    """
    
    def get_name(self) -> str:
        """Get the name of the extractor.
        
        Returns the class name by default, can be overridden for custom names.
        """
        return self.__class__.__name__
    
    def extract(self, db: Session, **kwargs) -> Dict[str, Any]:
        """Extract insights.
        
        Args:
            db: Database session
            **kwargs: Additional parameters for extraction
            
        Returns:
            Dict containing extracted insights
        """
        raise NotImplementedError("Subclasses must implement extract()")


class InsightRegistry:
    """Registry for insight extractors.
    
    Keeps track of all available insight extractors and provides
    methods to access them.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._extractors = {}
    
    def register(self, extractor: BaseInsightExtractor) -> None:
        """Register an insight extractor.
        
        Args:
            extractor: The extractor to register
        """
        name = extractor.get_name()
        self._extractors[name] = extractor
        logger.info(f"Registered insight extractor: {name}")
    
    def get_extractor(self, name: str) -> Optional[BaseInsightExtractor]:
        """Get an extractor by name.
        
        Args:
            name: Name of the extractor to get
            
        Returns:
            The extractor if found, None otherwise
        """
        return self._extractors.get(name)
    
    def get_all_extractors(self) -> Dict[str, BaseInsightExtractor]:
        """Get all registered extractors.
        
        Returns:
            Dict mapping extractor names to extractors
        """
        return self._extractors.copy()
    
    def get_available_insights(self) -> List[str]:
        """Get names of all available insights.
        
        Returns:
            List of insight names
        """
        return list(self._extractors.keys())


# Create global registry instances
metric_registry = MetricRegistry()
insight_registry = InsightRegistry()


class BusinessLogicLayer:
    """Business logic layer for calculating metrics and extracting insights.
    
    Provides a unified interface to access all metrics and insights.
    """
    
    def __init__(self):
        """Initialize the business logic layer."""
        self.metric_registry = metric_registry
        self.insight_registry = insight_registry
    
    @staticmethod
    def get_available_metrics() -> List[str]:
        """Get names of all available metrics.
        
        Returns:
            List of metric names
        """
        return metric_registry.get_available_metrics()
    
    @staticmethod
    def get_available_insights() -> List[str]:
        """Get names of all available insights.
        
        Returns:
            List of insight names
        """
        return insight_registry.get_available_insights()
    
    def calculate_metric(self, metric_name: str, **kwargs) -> Dict[str, Any]:
        """Calculate a specific metric.
        
        Args:
            metric_name: Name of the metric to calculate
            **kwargs: Additional parameters for calculation
            
        Returns:
            Dict containing calculated metrics
            
        Raises:
            ValueError: If the metric is not found
        """
        calculator = self.metric_registry.get_calculator(metric_name)
        if calculator is None:
            raise ValueError(f"Metric calculator not found: {metric_name}")
        
        try:
            logger.info(f"Calculating metric: {metric_name}")
            result = calculator.calculate(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error calculating metric {metric_name}: {str(e)}")
            raise
    
    def calculate_all_metrics(self, **kwargs) -> Dict[str, Dict[str, Any]]:
        """Calculate all available metrics.
        
        Args:
            **kwargs: Additional parameters for calculation
            
        Returns:
            Dict mapping metric names to calculation results
        """
        results = {}
        for name, calculator in self.metric_registry.get_all_calculators().items():
            try:
                logger.info(f"Calculating metric: {name}")
                results[name] = calculator.calculate(**kwargs)
            except Exception as e:
                logger.error(f"Error calculating metric {name}: {str(e)}")
                results[name] = {"error": str(e)}
        
        return results
    
    def extract_insight(self, insight_name: str, **kwargs) -> Dict[str, Any]:
        """Extract a specific insight.
        
        Args:
            insight_name: Name of the insight to extract
            **kwargs: Additional parameters for extraction
            
        Returns:
            Dict containing extracted insights
            
        Raises:
            ValueError: If the insight is not found
        """
        extractor = self.insight_registry.get_extractor(insight_name)
        if extractor is None:
            raise ValueError(f"Insight extractor not found: {insight_name}")
        
        try:
            logger.info(f"Extracting insight: {insight_name}")
            result = extractor.extract(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error extracting insight {insight_name}: {str(e)}")
            raise
    
    def extract_all_insights(self, **kwargs) -> Dict[str, Dict[str, Any]]:
        """Extract all available insights.
        
        Args:
            **kwargs: Additional parameters for extraction
            
        Returns:
            Dict mapping insight names to extraction results
        """
        results = {}
        for name, extractor in self.insight_registry.get_all_extractors().items():
            try:
                logger.info(f"Extracting insight: {name}")
                results[name] = extractor.extract(**kwargs)
            except Exception as e:
                logger.error(f"Error extracting insight {name}: {str(e)}")
                results[name] = {"error": str(e)}
        
        return results 