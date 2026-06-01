class FHIRSQLError(Exception):
    """Base exception."""
    pass

class AuthenticationError(FHIRSQLError):
    pass

class ResourceNotFoundError(FHIRSQLError):
    def __init__(self, resource_type, resource_id):
        super().__init__(f"{resource_type} {resource_id} not found")

class ValidationError(FHIRSQLError):
    pass

class APIError(FHIRSQLError):
    def __init__(self, message, status_code=None):
        self.status_code = status_code
        super().__init__(f"API Error ({status_code}): {message}" if status_code else message)
