from fastapi import HTTPException


class SnowflakeConnectionError(Exception):
    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class ConfigurationError(Exception):
    def __init__(self, message: str, config_field: str | None = None):
        self.message = message
        self.config_field = config_field
        super().__init__(self.message)


class DataProcessingError(Exception):
    def __init__(self, message: str, operation: str | None = None):
        self.message = message
        self.operation = operation
        super().__init__(self.message)


class ResourceNotFoundError(HTTPException):
    def __init__(self, resource_type: str, resource_id: str):
        detail = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(status_code=404, detail=detail)


class ValidationError(HTTPException):
    def __init__(self, message: str, field: str | None = None):
        detail = f"Validation error: {message}"
        if field:
            detail += f" (field: {field})"
        super().__init__(status_code=400, detail=detail)
