"""
Error schema models for the API.

This module contains Pydantic models for error responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class ValidationErrorItem(BaseModel):
    """A single validation error details."""
    field: Optional[str] = Field(
        None, 
        description="The field path that caused the error",
        examples=["body.name"]
    )
    message: str = Field(
        ..., 
        description="Human-readable error message",
        examples=["Field required"]
    )
    type: str = Field(
        ..., 
        description="The error type identifier",
        examples=["missing"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "field": "body.name",
                    "message": "Field required",
                    "type": "missing"
                }
            ]
        }
    }

class ErrorDetail(BaseModel):
    """Details of an API error."""
    errors: List[ValidationErrorItem] = Field(
        ..., 
        description="List of validation errors"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "errors": [
                        {
                            "field": "body.name",
                            "message": "Field required",
                            "type": "missing"
                        },
                        {
                            "field": "body.age",
                            "message": "Value must be greater than 0",
                            "type": "value_error"
                        }
                    ]
                }
            ]
        }
    }

class ErrorResponse(BaseModel):
    """Standard error response format."""
    status: str = Field(
        "error", 
        description="Error status",
        examples=["error"]
    )
    message: str = Field(
        ..., 
        description="General error message",
        examples=["Validation error"]
    )
    detail: Optional[ErrorDetail] = Field(
        None, 
        description="Detailed error information if available"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "error",
                    "message": "Validation error",
                    "detail": {
                        "errors": [
                            {
                                "field": "body.name",
                                "message": "Field required",
                                "type": "missing"
                            },
                            {
                                "field": "body.age",
                                "message": "Value must be greater than 0",
                                "type": "value_error"
                            }
                        ]
                    }
                }
            ]
        }
    } 