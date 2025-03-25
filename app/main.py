from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
import uvicorn
from typing import List, Dict, Any, Union
import json
import argparse
import os

from app.database.init_db import init_db
from app.api import api_router
from app.schemas import ValidationErrorItem, ErrorResponse, ErrorDetail

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Startup
    await init_db()
    yield
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(
    title="Cylestio Mini-Local Server",
    description="A lightweight server for collecting and querying Cylestio monitoring data",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - in production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint at the root level with its own tag
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "cylestio-mini-local-server"}

# Include the API router which will include all endpoints organized by their type
app.include_router(api_router, prefix="/api")

# Override the default validation error handler to provide better error responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with a cleaner format.
    This improves the API documentation and provides better error responses.
    """
    error_items = []
    for error in exc.errors():
        # Create a better formatted error item
        error_items.append(ValidationErrorItem(
            field=".".join(str(loc) for loc in error.get("loc", [])) if "loc" in error else None,
            message=error.get("msg", "Validation error"),
            type=error.get("type", "unknown_error")
        ))
    
    error_response = ErrorResponse(
        status="error",
        message="Validation error",
        detail=ErrorDetail(errors=error_items)
    )
    
    return JSONResponse(
        status_code=400,
        content=json.loads(error_response.model_dump_json())
    )

# Custom OpenAPI schema generation to properly include our error schemas
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Directly define our error schemas in OpenAPI format to avoid Pydantic V2 schema issues
    error_schemas = {
        "ValidationErrorItem": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string", 
                    "description": "The field path that caused the error",
                    "example": "body.name"
                },
                "message": {
                    "type": "string",
                    "description": "Human-readable error message",
                    "example": "Field required"
                },
                "type": {
                    "type": "string",
                    "description": "The error type identifier",
                    "example": "missing"
                }
            },
            "required": ["message", "type"]
        },
        "ErrorDetail": {
            "type": "object",
            "properties": {
                "errors": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/ValidationErrorItem"},
                    "description": "List of validation errors"
                }
            },
            "required": ["errors"]
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Error status",
                    "example": "error"
                },
                "message": {
                    "type": "string",
                    "description": "General error message",
                    "example": "Validation error"
                },
                "detail": {
                    "$ref": "#/components/schemas/ErrorDetail",
                    "description": "Detailed error information if available"
                }
            },
            "required": ["status", "message"]
        }
    }
    
    # Add schemas to the components section
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
        
    # Add our manually defined schemas
    for schema_name, schema in error_schemas.items():
        openapi_schema["components"]["schemas"][schema_name] = schema
    
    # Remove the default ValidationError and HTTPValidationError schemas
    if "ValidationError" in openapi_schema["components"]["schemas"]:
        del openapi_schema["components"]["schemas"]["ValidationError"]
    
    if "HTTPValidationError" in openapi_schema["components"]["schemas"]:
        del openapi_schema["components"]["schemas"]["HTTPValidationError"]
    
    # Replace validation error references in endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue
                
            response_section = openapi_schema["paths"][path][method].get("responses", {})
            
            # Replace 422 responses with 400 using our error format
            if "422" in response_section:
                del response_section["422"]
            
            # Add our error response to all endpoints for 400 errors
            response_section["400"] = {
                "description": "Validation Error", 
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Replace the default OpenAPI schema with our custom one
app.openapi = custom_openapi

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Cylestio Mini-Local Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CYLESTIO_PORT", 8000)), 
                        help="Port to bind the server to (default: 8000)")
    args = parser.parse_args()
    
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=True) 