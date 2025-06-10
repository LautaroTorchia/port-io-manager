"""Exceptions for the Port.io API client."""

from typing import Optional, Dict
from pprint import pformat

class PortAPIError(Exception):
    """Base exception for Port.io API errors."""
    def __init__(self, status_code: int, message: str, response_data: Optional[Dict] = None, request_data: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        self.request_data = request_data
        super().__init__(self.message)

    def get_detailed_message(self) -> str:
        """Get a detailed error message with request/response context."""
        if self.response_data and isinstance(self.response_data, dict):
            error_msg = self.response_data.get('message', '')
            error_code = self.response_data.get('code', '')
            validation_errors = self.response_data.get('validationErrors', [])
            
            details = []
            if error_msg:
                details.append(error_msg)
            if error_code:
                details.append(f"Code: {error_code}")
            if validation_errors:
                details.extend(validation_errors)
            
            if details:
                return f"{self.status_code} Error: {' | '.join(details)}"
        
        return f"{self.status_code} Error: {self.message}"

    def get_full_details(self) -> str:
        """Get complete error details including request/response data for debugging."""
        details = [f"{self.status_code} Error: {self.message}"]
        
        if self.request_data:
            details.append("\nRequest Data:")
            details.append(pformat(self.request_data))
        
        if self.response_data:
            details.append("\nResponse Data:")
            details.append(pformat(self.response_data))
        
        return "\n".join(details)

class PortAPIConflictError(PortAPIError):
    """Exception for 409 Conflict errors."""
    pass 