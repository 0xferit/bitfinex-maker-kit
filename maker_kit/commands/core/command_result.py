"""
Command result types for standardized command execution results.

Provides consistent result handling across all command implementations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
from datetime import datetime


class CommandStatus(Enum):
    """Command execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"
    
    def is_success(self) -> bool:
        """Check if status indicates success."""
        return self == CommandStatus.SUCCESS
    
    def is_error(self) -> bool:
        """Check if status indicates an error."""
        return self in [CommandStatus.FAILED, CommandStatus.VALIDATION_ERROR, CommandStatus.TIMEOUT]


@dataclass
class ValidationResult:
    """Result of command validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if there are validation errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are validation warnings."""
        return len(self.warnings) > 0
    
    def get_error_summary(self) -> str:
        """Get a summary of all errors."""
        return "; ".join(self.errors)
    
    def get_warning_summary(self) -> str:
        """Get a summary of all warnings."""
        return "; ".join(self.warnings)
    
    @classmethod
    def success(cls) -> 'ValidationResult':
        """Create a successful validation result."""
        return cls(is_valid=True, errors=[], warnings=[])
    
    @classmethod
    def failure(cls, errors: List[str]) -> 'ValidationResult':
        """Create a failed validation result."""
        return cls(is_valid=False, errors=errors, warnings=[])


@dataclass
class CommandResult:
    """Result of command execution."""
    status: CommandStatus
    data: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize result with timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
    
    def is_success(self) -> bool:
        """Check if command execution was successful."""
        return self.status.is_success()
    
    def is_error(self) -> bool:
        """Check if command execution failed."""
        return self.status.is_error()
    
    def get_error(self) -> Optional[str]:
        """Get error message if command failed."""
        return self.error_message if self.is_error() else None
    
    def get_data(self) -> Optional[Any]:
        """Get command result data if successful."""
        return self.data if self.is_success() else None
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the result."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key."""
        return self.metadata.get(key, default)
    
    @classmethod
    def success(cls, data: Any = None, execution_time: float = None) -> 'CommandResult':
        """Create a successful command result."""
        return cls(
            status=CommandStatus.SUCCESS,
            data=data,
            execution_time=execution_time
        )
    
    @classmethod
    def failure(cls, error_message: str, execution_time: float = None) -> 'CommandResult':
        """Create a failed command result."""
        return cls(
            status=CommandStatus.FAILED,
            error_message=error_message,
            execution_time=execution_time
        )
    
    @classmethod
    def validation_error(cls, validation_result: ValidationResult) -> 'CommandResult':
        """Create a validation error command result."""
        return cls(
            status=CommandStatus.VALIDATION_ERROR,
            error_message=validation_result.get_error_summary(),
            data=validation_result
        )
    
    @classmethod
    def cancelled(cls, reason: str = None) -> 'CommandResult':
        """Create a cancelled command result."""
        return cls(
            status=CommandStatus.CANCELLED,
            error_message=reason or "Command was cancelled"
        )
    
    @classmethod
    def timeout(cls, timeout_seconds: float) -> 'CommandResult':
        """Create a timeout command result."""
        return cls(
            status=CommandStatus.TIMEOUT,
            error_message=f"Command timed out after {timeout_seconds} seconds"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            'status': self.status.value,
            'data': self.data,
            'error_message': self.error_message,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata
        }
    
    def __str__(self) -> str:
        """String representation of the command result."""
        if self.is_success():
            return f"SUCCESS: {self.data}"
        else:
            return f"{self.status.value.upper()}: {self.error_message}"