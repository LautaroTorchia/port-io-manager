"""Custom exceptions for the Port.io Manager."""

class PortManagerError(Exception):
    """Base exception for Port.io Manager errors."""
    pass

class BlueprintNotFoundError(PortManagerError):
    """Raised when a blueprint is not found."""
    pass

class BlueprintValidationError(PortManagerError):
    """Raised when a blueprint fails validation."""
    pass

class BlueprintSyncError(PortManagerError):
    """Raised when synchronization fails."""
    pass

class BlueprintFileError(PortManagerError):
    """Raised when there are issues with blueprint files."""
    pass 