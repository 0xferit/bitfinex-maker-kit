"""
Command executor infrastructure for the command pattern.

Provides centralized command execution with logging, validation,
confirmation prompts, and error handling.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ...config.trading_config import TradingConfig
from ...services.container import ServiceContainer
from .base_command import Command, CommandContext
from .command_result import CommandResult, CommandStatus

logger = logging.getLogger(__name__)


@dataclass
class ExecutionOptions:
    """Options for command execution."""

    dry_run: bool = False
    skip_confirmation: bool = False
    timeout_seconds: float | None = None
    fail_fast: bool = True
    log_execution: bool = True

    @classmethod
    def for_cli(cls, dry_run: bool = False, yes: bool = False) -> "ExecutionOptions":
        """Create execution options suitable for CLI usage."""
        return cls(
            dry_run=dry_run,
            skip_confirmation=yes,
            timeout_seconds=300.0,  # 5 minutes default timeout
            fail_fast=True,
            log_execution=True,
        )

    @classmethod
    def for_batch(cls, dry_run: bool = False) -> "ExecutionOptions":
        """Create execution options suitable for batch operations."""
        return cls(
            dry_run=dry_run,
            skip_confirmation=True,
            timeout_seconds=600.0,  # 10 minutes for batch
            fail_fast=False,
            log_execution=True,
        )


class ConfirmationHandler:
    """Handles user confirmation prompts."""

    def __init__(self, prompt_function: Callable[[str], bool] | None = None) -> None:
        """
        Initialize confirmation handler.

        Args:
            prompt_function: Function to prompt user for confirmation
        """
        self.prompt_function = prompt_function or self._default_prompt

    def _default_prompt(self, message: str) -> bool:
        """Default confirmation prompt using console input."""
        try:
            response = input(f"\n{message} (y/N): ").strip().lower()
            return response in ["y", "yes"]
        except (EOFError, KeyboardInterrupt):
            return False

    def confirm(self, command: Command, context: CommandContext) -> bool:
        """
        Request confirmation for command execution.

        Args:
            command: Command to confirm
            context: Command execution context

        Returns:
            True if user confirms, False otherwise
        """
        if not command.requires_confirmation(context):
            return True

        try:
            message = command.get_confirmation_message(context)
            return self.prompt_function(message)
        except Exception as e:
            logger.error(f"Error in confirmation prompt: {e}")
            return False


class CommandExecutor:
    """
    Centralized command executor with full command pattern support.

    Provides command execution with validation, confirmation,
    logging, timeout handling, and error recovery.
    """

    def __init__(self, container: ServiceContainer, config: TradingConfig) -> None:
        """
        Initialize command executor.

        Args:
            container: Service container for dependency injection
            config: Trading configuration
        """
        self.container = container
        self.config = config
        self.confirmation_handler = ConfirmationHandler()
        self.execution_history: list[dict[str, Any]] = []

        # Statistics
        self.total_commands_executed = 0
        self.successful_commands = 0
        self.failed_commands = 0

    def execute_command(self, command: Command, options: ExecutionOptions) -> CommandResult:
        """
        Execute a single command with full error handling.

        Args:
            command: Command to execute
            options: Execution options

        Returns:
            CommandResult with execution outcome
        """
        start_time = time.time()

        try:
            # Create command context
            context = self._create_command_context(options)

            # Log command start
            if options.log_execution:
                logger.info(f"Executing command: {command.name}")
                if options.dry_run:
                    logger.info("DRY RUN MODE - No actual changes will be made")

            # Show preview if not dry run
            if not options.dry_run and options.log_execution:
                preview = command.get_preview(context)
                print(f"\n📋 {preview}")

            # Request confirmation if needed
            if not options.skip_confirmation and not self.confirmation_handler.confirm(
                command, context
            ):
                result = CommandResult.cancelled("User cancelled operation")
                self._record_execution(command, result, options)
                return result

            # Execute command with timeout
            if options.timeout_seconds:
                result = self._execute_with_timeout(command, context, options.timeout_seconds)
            else:
                result = command.execute_with_validation(context)

            # Update statistics
            self.total_commands_executed += 1
            if result.is_success():
                self.successful_commands += 1
            else:
                self.failed_commands += 1

            # Log result
            if options.log_execution:
                self._log_command_result(command, result)

            # Record execution
            self._record_execution(command, result, options)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error executing command {command.name}: {e}", exc_info=True)

            result = CommandResult.failure(f"Executor error: {e!s}")
            result.execution_time = execution_time

            self.failed_commands += 1
            self._record_execution(command, result, options)

            return result

    def execute_batch(
        self, commands: list[Command], options: ExecutionOptions
    ) -> list[CommandResult]:
        """
        Execute multiple commands in batch.

        Args:
            commands: List of commands to execute
            options: Execution options

        Returns:
            List of CommandResults for each command
        """
        if not commands:
            return []

        logger.info(f"Executing batch of {len(commands)} commands")

        results = []
        successful_count = 0
        failed_count = 0

        for i, command in enumerate(commands):
            try:
                logger.info(f"Batch progress: {i + 1}/{len(commands)} - {command.name}")

                result = self.execute_command(command, options)
                results.append(result)

                if result.is_success():
                    successful_count += 1
                else:
                    failed_count += 1

                    # Handle fail-fast behavior
                    if options.fail_fast and result.status == CommandStatus.FAILED:
                        logger.warning(
                            f"Stopping batch execution due to failure: {result.error_message}"
                        )
                        break

            except Exception as e:
                logger.error(f"Error executing command {i + 1} in batch: {e}")
                error_result = CommandResult.failure(f"Batch execution error: {e!s}")
                results.append(error_result)
                failed_count += 1

                if options.fail_fast:
                    break

        # Log batch summary
        logger.info(
            f"Batch execution complete: {successful_count} successful, {failed_count} failed"
        )

        return results

    def undo_command(self, command: Command, options: ExecutionOptions) -> CommandResult:
        """
        Undo a previously executed command.

        Args:
            command: Command to undo
            options: Execution options

        Returns:
            CommandResult with undo outcome
        """
        if not command.can_undo():
            return CommandResult.failure(f"Command {command.name} does not support undo")

        try:
            context = self._create_command_context(options)

            logger.info(f"Undoing command: {command.name}")

            # Request confirmation for undo
            if not options.skip_confirmation:
                undo_message = f"Do you want to undo: {command.name}?"
                if not self.confirmation_handler.prompt_function(undo_message):
                    return CommandResult.cancelled("Undo cancelled by user")

            result = command.undo(context)

            if options.log_execution:
                self._log_command_result(command, result, is_undo=True)

            return result

        except Exception as e:
            logger.error(f"Error undoing command {command.name}: {e}")
            return CommandResult.failure(f"Undo error: {e!s}")

    def _create_command_context(self, options: ExecutionOptions) -> CommandContext:
        """Create command context from execution options."""
        trading_service = self.container.create_trading_service()

        return CommandContext(
            trading_service=trading_service,
            dry_run=options.dry_run,
            user_confirmation_required=not options.skip_confirmation,
            timeout_seconds=options.timeout_seconds,
        )

    def _execute_with_timeout(
        self, command: Command, context: CommandContext, timeout_seconds: float
    ) -> CommandResult:
        """Execute command with timeout handling."""
        import signal

        class TimeoutError(Exception):
            pass

        def timeout_handler(signum: int, frame: Any) -> None:
            raise TimeoutError(f"Command timed out after {timeout_seconds} seconds")

        # Set up timeout signal (Unix only)
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout_seconds))

        try:
            result = command.execute_with_validation(context)
            signal.alarm(0)  # Cancel alarm
            return result
        except TimeoutError:
            return CommandResult.timeout(timeout_seconds)
        finally:
            signal.signal(signal.SIGALRM, old_handler)

    def _log_command_result(
        self, command: Command, result: CommandResult, is_undo: bool = False
    ) -> None:
        """Log command execution result."""
        operation = "undo" if is_undo else "execution"

        if result.is_success():
            message = f"✅ Command {operation} successful: {command.name}"
            if result.execution_time:
                message += f" ({result.execution_time:.3f}s)"
            logger.info(message)
            print(message)
        else:
            message = f"❌ Command {operation} failed: {command.name} - {result.error_message}"
            logger.error(message)
            print(message)

    def _record_execution(
        self, command: Command, result: CommandResult, options: ExecutionOptions
    ) -> None:
        """Record command execution in history."""
        execution_record = {
            "command_name": command.name,
            "command_description": command.description,
            "execution_id": command.execution_id,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
            "status": result.status.value,
            "execution_time": result.execution_time,
            "dry_run": options.dry_run,
            "error_message": result.error_message,
            "has_data": result.data is not None,
        }

        self.execution_history.append(execution_record)

        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_execution_statistics(self) -> dict[str, Any]:
        """Get command execution statistics."""
        return {
            "total_commands": self.total_commands_executed,
            "successful_commands": self.successful_commands,
            "failed_commands": self.failed_commands,
            "success_rate": (self.successful_commands / max(1, self.total_commands_executed)) * 100,
            "recent_executions": len(self.execution_history),
        }

    def get_recent_executions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent command executions."""
        return self.execution_history[-limit:] if self.execution_history else []

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()
        logger.info("Command execution history cleared")


# Global executor instance
_global_executor: CommandExecutor | None = None


def get_executor() -> CommandExecutor:
    """
    Get the global command executor instance.

    Returns:
        Global CommandExecutor instance
    """
    global _global_executor
    if _global_executor is None:
        from ...config.environment import create_trading_config_for_environment
        from ...services.container import get_container

        container = get_container()
        config = create_trading_config_for_environment()
        _global_executor = CommandExecutor(container, config)

    return _global_executor


def configure_executor(container: ServiceContainer, config: TradingConfig) -> CommandExecutor:
    """
    Configure the global command executor.

    Args:
        container: Service container
        config: Trading configuration

    Returns:
        Configured CommandExecutor instance
    """
    global _global_executor
    _global_executor = CommandExecutor(container, config)
    return _global_executor


def reset_executor() -> None:
    """Reset the global executor (mainly for testing)."""
    global _global_executor
    _global_executor = None
