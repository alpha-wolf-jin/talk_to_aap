"""
Custom exceptions for AAP AI Assistant.
Provides better error handling and more informative error messages.
"""


class AAPAssistantError(Exception):
    """Base exception for AAP AI Assistant."""
    pass


class ConfigurationError(AAPAssistantError):
    """Raised when configuration is invalid or missing."""
    pass


class AuthenticationError(AAPAssistantError):
    """Raised when AAP authentication fails."""
    pass


class MCPConnectionError(AAPAssistantError):
    """Raised when MCP server connection fails."""
    pass


class ToolExecutionError(AAPAssistantError):
    """Raised when tool execution fails."""
    
    def __init__(self, tool_name: str, message: str, details: str = None):
        self.tool_name = tool_name
        self.details = details
        super().__init__(f"Tool '{tool_name}' execution failed: {message}")


class JobTimeoutError(AAPAssistantError):
    """Raised when AAP job times out."""
    
    def __init__(self, job_id: int, timeout_seconds: int):
        self.job_id = job_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Job {job_id} timed out after {timeout_seconds} seconds"
        )


class JobFailedError(AAPAssistantError):
    """Raised when AAP job fails."""
    
    def __init__(self, job_id: int, status: str, details: str = None):
        self.job_id = job_id
        self.status = status
        self.details = details
        message = f"Job {job_id} failed with status: {status}"
        if details:
            message += f"\nDetails: {details}"
        super().__init__(message)


class SessionExpiredError(AAPAssistantError):
    """Raised when user session has expired."""
    pass


class InvalidToolCallError(AAPAssistantError):
    """Raised when tool call format is invalid."""
    pass

