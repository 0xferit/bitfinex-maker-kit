"""
Base command classes for the command pattern implementation.

Provides abstract interfaces for all trading commands with validation,
execution, and undo capabilities.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ...services.trading_service import TradingService
from .command_result import CommandResult, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Context information for command execution."""

    trading_service: TradingService
    dry_run: bool = False
    user_confirmation_required: bool = True
    timeout_seconds: float | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize context."""
        if self.metadata is None:
            self.metadata = {}


class Command(ABC):
    """
    Abstract base class for all trading commands.

    Implements the command pattern to separate business logic from
    CLI presentation, enabling validation, execution, and undo operations.
    """

    def __init__(self, name: str, description: str = "") -> None:
        """
        Initialize command.

        Args:
            name: Command name for identification
            description: Human-readable command description
        """
        self.name = name
        self.description = description
        self.execution_id: str | None = None
        self.execution_time: float | None = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def validate(self, context: CommandContext) -> ValidationResult:
        """
        Validate command parameters and preconditions.

        Args:
            context: Command execution context

        Returns:
            ValidationResult indicating if command is valid
        """
        pass

    @abstractmethod
    def execute(self, context: CommandContext) -> CommandResult:
        """
        Execute the command.

        Args:
            context: Command execution context

        Returns:
            CommandResult with execution outcome
        """
        pass

    def can_undo(self) -> bool:
        """
        Check if command supports undo operation.

        Returns:
            True if command can be undone
        """
        return False

    def undo(self, context: CommandContext) -> CommandResult:
        """
        Undo the command execution.

        Args:
            context: Command execution context

        Returns:
            CommandResult with undo outcome
        """
        return CommandResult.failure("Undo operation not supported for this command")

    def get_preview(self, context: CommandContext) -> str:
        """
        Get a preview of what the command will do.

        Args:
            context: Command execution context

        Returns:
            Human-readable preview string
        """
        return f"Execute command: {self.name}"

    def get_confirmation_message(self, context: CommandContext) -> str:
        """
        Get confirmation message for user prompt.

        Args:
            context: Command execution context

        Returns:
            Confirmation message string
        """
        return f"Do you want to execute: {self.get_preview(context)}?"

    def requires_confirmation(self, context: CommandContext) -> bool:
        """
        Check if command requires user confirmation.

        Args:
            context: Command execution context

        Returns:
            True if confirmation is required
        """
        return context.user_confirmation_required and not context.dry_run

    def execute_with_validation(self, context: CommandContext) -> CommandResult:
        """
        Execute command with full validation and error handling.

        Args:
            context: Command execution context

        Returns:
            CommandResult with complete execution outcome
        """
        start_time = time.time()

        try:
            # Generate execution ID
            import uuid

            self.execution_id = str(uuid.uuid4())

            self.logger.info(f"Starting command execution: {self.name} ({self.execution_id})")

            # Validate command
            validation_result = self.validate(context)
            if not validation_result.is_valid:
                self.logger.warning(
                    f"Command validation failed: {validation_result.get_error_summary()}"
                )
                return CommandResult.validation_error(validation_result)

            # Log warnings if any
            if validation_result.has_warnings():
                self.logger.warning(f"Command warnings: {validation_result.get_warning_summary()}")

            # Handle dry run mode
            if context.dry_run:
                self.logger.info(f"Dry run mode: {self.get_preview(context)}")
                result = CommandResult.success(
                    data={"dry_run": True, "preview": self.get_preview(context)}
                )
            else:
                # Execute command
                result = self.execute(context)

            # Record execution time
            self.execution_time = time.time() - start_time
            result.execution_time = self.execution_time
            result.add_metadata("execution_id", self.execution_id)
            result.add_metadata("command_name", self.name)

            if result.is_success():
                self.logger.info(
                    f"Command executed successfully: {self.name} ({self.execution_time:.3f}s)"
                )
            else:
                self.logger.error(f"Command failed: {self.name} - {result.error_message}")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Unexpected error in command {self.name}: {e}", exc_info=True)
            result = CommandResult.failure(f"Unexpected error: {e!s}")
            result.execution_time = execution_time
            return result

    def __str__(self) -> str:
        """String representation of the command."""
        return f"Command({self.name})"

    def __repr__(self) -> str:
        """Developer representation of the command."""
        return f"Command(name='{self.name}', description='{self.description}')"


class ReadOnlyCommand(Command):
    """
    Base class for read-only commands that don't modify state.

    These commands typically don't require confirmation and can't be undone.
    """

    def requires_confirmation(self, context: CommandContext) -> bool:
        """Read-only commands don't require confirmation."""
        return False


class TransactionalCommand(Command):
    """
    Base class for commands that modify state and may be undoable.

    These commands typically require confirmation and may support undo.
    """

    def __init__(self, name: str, description: str = "", supports_undo: bool = False) -> None:
        """
        Initialize transactional command.

        Args:
            name: Command name
            description: Command description
            supports_undo: Whether this command supports undo
        """
        super().__init__(name, description)
        self._supports_undo = supports_undo

    def can_undo(self) -> bool:
        """Transactional commands may support undo."""
        return self._supports_undo

    def requires_confirmation(self, context: CommandContext) -> bool:
        """Transactional commands require confirmation unless disabled."""
        return context.user_confirmation_required and not context.dry_run


class BatchCommand(Command):
    """
    Base class for commands that execute multiple operations.

    Provides support for batch execution with partial failure handling.
    """

    def __init__(self, name: str, description: str = "", fail_fast: bool = True) -> None:
        """
        Initialize batch command.

        Args:
            name: Command name
            description: Command description
            fail_fast: Whether to stop on first failure
        """
        super().__init__(name, description)
        self.fail_fast = fail_fast
        self.partial_results: list = []

    def execute_batch_operation(self, operations: list, context: CommandContext) -> CommandResult:
        """
        Execute a batch of operations with error handling.

        Args:
            operations: List of operations to execute
            context: Command execution context

        Returns:
            CommandResult with batch execution outcome
        """
        self.partial_results = []
        successful_operations = 0
        failed_operations = 0

        for i, operation in enumerate(operations):
            try:
                result = self._execute_single_operation(operation, context)
                self.partial_results.append(result)

                if result.is_success():
                    successful_operations += 1
                else:
                    failed_operations += 1
                    if self.fail_fast:
                        break

            except Exception as e:
                error_result = CommandResult.failure(f"Operation {i + 1} failed: {e!s}")
                self.partial_results.append(error_result)
                failed_operations += 1

                if self.fail_fast:
                    break

        # Create summary result
        total_operations = len(operations)
        summary = {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "partial_results": self.partial_results,
        }

        if failed_operations == 0:
            return CommandResult.success(data=summary)
        elif successful_operations == 0:
            return CommandResult.failure(f"All {total_operations} operations failed")
        else:
            return CommandResult.failure(
                f"{failed_operations} of {total_operations} operations failed", data=summary
            )

    @abstractmethod
    def _execute_single_operation(self, operation: Any, context: CommandContext) -> CommandResult:
        """
        Execute a single operation within the batch.

        Args:
            operation: Single operation to execute
            context: Command execution context

        Returns:
            CommandResult for the single operation
        """
        pass
