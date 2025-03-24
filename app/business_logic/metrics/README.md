# Metrics Calculators

This directory contains the implementation of metric calculators for the Cylestio Monitor. These calculators process normalized data from the database to produce metrics and insights for the dashboard.

## Overview

The metrics system is designed to be:

- **Modular**: Each calculator focuses on a specific metric for better maintainability
- **Extensible**: New calculators can be easily added by inheriting from the base class
- **Configurable**: Metrics can be filtered by time range, agent ID, session, etc.
- **Efficient**: Utilizes database queries for optimized performance

## Metric Categories

### Performance Metrics

Performance metrics measure how efficiently AI agents are operating:

- **Response Time**: Average, min, max, and percentile response times
- **Request Rate**: Frequency of requests over time
- **Model Performance**: Performance comparisons across different models

### Token Usage Metrics

Token usage metrics track the consumption of tokens:

- **Total Token Usage**: Input, output, and total token usage
- **Average Token Usage**: Average tokens per request/response
- **Token Rate**: Tokens used per minute/hour
- **Model Token Usage**: Token usage by model

### Quality Metrics

Quality metrics measure the quality of AI agent responses:

- **Response Complexity**: Word count, sentence count, words per sentence
- **Response Appropriateness**: Error rates, refusal rates, hallucination rates
- **Content Type Distribution**: Distribution of code, URLs, lists, JSON in responses

### Security Metrics

Security metrics monitor potential security issues:

- **Security Alert Frequency**: Rate of security alerts
- **Risk Level Distribution**: Distribution of risk levels
- **Security Event Types**: Types of security events detected

### Usage Metrics

Usage metrics analyze patterns of agent usage:

- **Framework Usage**: Distribution of frameworks being used
- **Model Usage**: Distribution of models being used
- **Agent Usage**: Distribution of agent activity
- **Session Counts**: Session metrics and activity
- **Event Type Distribution**: Distribution of event types
- **Channel Distribution**: Distribution of channels

## Usage

### Basic Usage

```python
from app.business_logic.metrics import metric_registry

# Get a specific calculator
response_time_calculator = metric_registry.calculators.get("ResponseTimeCalculator")

# Run a calculation with filters
metrics = response_time_calculator.calculate(
    db=db_session,
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2023, 1, 31),
    agent_id="agent-123"
)

# Run all metrics
all_metrics = metric_registry.run_all(
    db=db_session,
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2023, 1, 31)
)

# Run selected metrics
selected_metrics = metric_registry.run_selected(
    calculator_names=["ResponseTimeCalculator", "TotalTokenUsageCalculator"],
    db=db_session,
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2023, 1, 31)
)
```

### Creating a New Calculator

To create a new calculator:

1. Inherit from `BaseMetricCalculator`
2. Implement the `calculate` method
3. Register the calculator with `metric_registry`

Example:

```python
from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry

class MyNewMetricCalculator(BaseMetricCalculator):
    def calculate(self, db, start_time=None, end_time=None, agent_id=None, session_id=None, **kwargs):
        # Query data and calculate metrics
        # ...
        return {"metric_name": metric_value}

# Register the calculator
metric_registry.register(MyNewMetricCalculator())
```

## Implementation Notes

- Calculators should handle missing or incomplete data gracefully
- Consider caching results when appropriate for performance
- Metrics can be stored in the database or calculated on-demand
- Filter parameters should be passed to database queries for optimized performance

## Testing

Each calculator has corresponding unit tests in `tests/unit/metrics/` that validate its functionality with mock data.

Run tests with:

```
pytest tests/unit/metrics/
``` 