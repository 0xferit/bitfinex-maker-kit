"""
Batch executor for handling multiple command operations.

Provides advanced batch execution capabilities including
parallel execution, dependency management, and rollback.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .base_command import Command
from .command_executor import CommandExecutor, ExecutionOptions
from .command_result import CommandResult

logger = logging.getLogger(__name__)


class BatchStrategy(Enum):
    """Strategy for batch execution."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEPENDENCY_AWARE = "dependency_aware"


@dataclass
class CommandDependency:
    """Represents a dependency between commands."""

    command_id: str
    depends_on: str
    dependency_type: str = "completion"  # completion, success, data


@dataclass
class BatchExecutionPlan:
    """Execution plan for batch operations."""

    commands: list[Command]
    dependencies: list[CommandDependency]
    strategy: BatchStrategy
    max_parallel: int = 5
    rollback_on_failure: bool = False
    continue_on_failure: bool = True


class BatchExecutor:
    """
    Advanced batch executor with dependency management and rollback.

    Supports sequential, parallel, and dependency-aware execution
    with automatic rollback capabilities for failed operations.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize batch executor.

        Args:
            executor: Command executor for individual commands
        """
        self.executor = executor
        self.execution_graph: dict[str, set[str]] = {}
        self.completed_commands: set[str] = set()
        self.failed_commands: set[str] = set()
        self.command_results: dict[str, CommandResult] = {}

    def execute_batch_plan(
        self, plan: BatchExecutionPlan, options: ExecutionOptions
    ) -> dict[str, CommandResult]:
        """
        Execute a batch execution plan.

        Args:
            plan: Batch execution plan
            options: Execution options

        Returns:
            Dictionary mapping command IDs to results
        """
        logger.info(
            f"Executing batch plan with {len(plan.commands)} commands using {plan.strategy.value} strategy"
        )

        # Reset state
        self.completed_commands.clear()
        self.failed_commands.clear()
        self.command_results.clear()

        # Build execution graph
        if plan.strategy == BatchStrategy.DEPENDENCY_AWARE:
            self._build_execution_graph(plan.commands, plan.dependencies)

        # Execute based on strategy
        if plan.strategy == BatchStrategy.SEQUENTIAL:
            return self._execute_sequential(plan, options)
        elif plan.strategy == BatchStrategy.PARALLEL:
            return self._execute_parallel(plan, options)
        elif plan.strategy == BatchStrategy.DEPENDENCY_AWARE:
            return self._execute_dependency_aware(plan, options)
        else:
            raise ValueError(f"Unknown batch strategy: {plan.strategy}")

    def _execute_sequential(
        self, plan: BatchExecutionPlan, options: ExecutionOptions
    ) -> dict[str, CommandResult]:
        """Execute commands sequentially."""
        results = {}

        for i, command in enumerate(plan.commands):
            command_id = f"cmd_{i}"
            logger.info(f"Executing command {i + 1}/{len(plan.commands)}: {command.name}")

            try:
                result = self.executor.execute_command(command, options)
                results[command_id] = result

                if result.is_success():
                    self.completed_commands.add(command_id)
                else:
                    self.failed_commands.add(command_id)

                    if not plan.continue_on_failure:
                        logger.warning(
                            f"Stopping batch execution due to failure in command {command.name}"
                        )
                        break

            except Exception as e:
                logger.error(f"Error executing command {command.name}: {e}")
                result = CommandResult.failure(f"Execution error: {e!s}")
                results[command_id] = result
                self.failed_commands.add(command_id)

                if not plan.continue_on_failure:
                    break

        # Handle rollback if needed
        if plan.rollback_on_failure and self.failed_commands:
            logger.info("Performing rollback due to failures")
            self._perform_rollback(plan, options, results)

        return results

    def _execute_parallel(
        self, plan: BatchExecutionPlan, options: ExecutionOptions
    ) -> dict[str, CommandResult]:
        """Execute commands in parallel (limited concurrency)."""
        import concurrent.futures

        results = {}

        # Create thread pool for parallel execution
        max_workers = min(plan.max_parallel, len(plan.commands))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all commands
            future_to_command = {}
            for i, command in enumerate(plan.commands):
                command_id = f"cmd_{i}"
                future = executor.submit(self.executor.execute_command, command, options)
                future_to_command[future] = (command_id, command)

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_command):
                command_id, command = future_to_command[future]

                try:
                    result = future.result()
                    results[command_id] = result

                    if result.is_success():
                        self.completed_commands.add(command_id)
                        logger.info(f"Command completed successfully: {command.name}")
                    else:
                        self.failed_commands.add(command_id)
                        logger.error(f"Command failed: {command.name} - {result.error_message}")

                except Exception as e:
                    logger.error(f"Error in parallel execution of {command.name}: {e}")
                    result = CommandResult.failure(f"Parallel execution error: {e!s}")
                    results[command_id] = result
                    self.failed_commands.add(command_id)

        # Handle rollback if needed
        if plan.rollback_on_failure and self.failed_commands:
            logger.info("Performing rollback due to failures")
            self._perform_rollback(plan, options, results)

        return results

    def _execute_dependency_aware(
        self, plan: BatchExecutionPlan, options: ExecutionOptions
    ) -> dict[str, CommandResult]:
        """Execute commands respecting dependencies."""
        results: dict[str, CommandResult] = {}
        ready_commands = self._get_ready_commands(plan.commands)

        while ready_commands or (
            len(results) < len(plan.commands) and not self._all_blocked(plan.commands, results)
        ):
            if not ready_commands:
                logger.warning("No ready commands found - possible circular dependency")
                break

            # Execute ready commands (potentially in parallel)
            if len(ready_commands) == 1 or plan.max_parallel == 1:
                # Sequential execution
                command_idx = ready_commands.pop(0)
                command = plan.commands[command_idx]
                command_id = f"cmd_{command_idx}"

                result = self.executor.execute_command(command, options)
                results[command_id] = result

                if result.is_success():
                    self.completed_commands.add(command_id)
                else:
                    self.failed_commands.add(command_id)
                    if not plan.continue_on_failure:
                        break
            else:
                # Parallel execution of ready commands
                batch_results = self._execute_ready_commands_parallel(
                    ready_commands, plan.commands, options, plan.max_parallel
                )
                results.update(batch_results)

            # Update ready commands
            ready_commands = self._get_ready_commands(
                plan.commands, completed=self.completed_commands
            )

        # Handle rollback if needed
        if plan.rollback_on_failure and self.failed_commands:
            logger.info("Performing rollback due to failures")
            self._perform_rollback(plan, options, results)

        return results

    def _build_execution_graph(
        self, commands: list[Command], dependencies: list[CommandDependency]
    ) -> None:
        """Build execution dependency graph."""
        self.execution_graph.clear()

        # Initialize graph
        for i, _ in enumerate(commands):
            command_id = f"cmd_{i}"
            self.execution_graph[command_id] = set()

        # Add dependencies
        for dep in dependencies:
            if dep.command_id in self.execution_graph:
                self.execution_graph[dep.command_id].add(dep.depends_on)

    def _get_ready_commands(
        self, commands: list[Command], completed: set[str] | None = None
    ) -> list[int]:
        """Get list of command indices that are ready to execute."""
        if completed is None:
            completed = self.completed_commands

        ready = []

        for i, _ in enumerate(commands):
            command_id = f"cmd_{i}"

            # Skip if already completed or failed
            if command_id in completed or command_id in self.failed_commands:
                continue

            # Check dependencies
            dependencies = self.execution_graph.get(command_id, set())
            if all(dep in completed for dep in dependencies):
                ready.append(i)

        return ready

    def _all_blocked(self, commands: list[Command], results: dict[str, CommandResult]) -> bool:
        """Check if all remaining commands are blocked by dependencies."""
        remaining_commands = len(commands) - len(results)
        if remaining_commands == 0:
            return False

        ready_commands = self._get_ready_commands(commands)
        return len(ready_commands) == 0

    def _execute_ready_commands_parallel(
        self,
        ready_indices: list[int],
        commands: list[Command],
        options: ExecutionOptions,
        max_parallel: int,
    ) -> dict[str, CommandResult]:
        """Execute ready commands in parallel."""
        import concurrent.futures

        results = {}
        batch_size = min(max_parallel, len(ready_indices))

        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            future_to_command = {}

            # Submit batch of ready commands
            for idx in ready_indices[:batch_size]:
                command = commands[idx]
                command_id = f"cmd_{idx}"
                future = executor.submit(self.executor.execute_command, command, options)
                future_to_command[future] = (command_id, command, idx)

            # Collect results
            for future in concurrent.futures.as_completed(future_to_command):
                command_id, command, idx = future_to_command[future]

                try:
                    result = future.result()
                    results[command_id] = result

                    if result.is_success():
                        self.completed_commands.add(command_id)
                    else:
                        self.failed_commands.add(command_id)

                except Exception as e:
                    logger.error(f"Error in parallel dependency-aware execution: {e}")
                    result = CommandResult.failure(f"Parallel execution error: {e!s}")
                    results[command_id] = result
                    self.failed_commands.add(command_id)

        return results

    def _perform_rollback(
        self, plan: BatchExecutionPlan, options: ExecutionOptions, results: dict[str, CommandResult]
    ) -> None:
        """Perform rollback of successfully executed commands."""
        logger.info(f"Starting rollback of {len(self.completed_commands)} completed commands")

        rollback_options = ExecutionOptions(
            dry_run=options.dry_run,
            skip_confirmation=True,  # Don't prompt for rollback confirmations
            timeout_seconds=options.timeout_seconds,
            fail_fast=False,  # Continue rolling back even if some fail
            log_execution=options.log_execution,
        )

        # Rollback in reverse order
        rollback_count = 0
        rollback_failures = 0

        for i in reversed(range(len(plan.commands))):
            command_id = f"cmd_{i}"

            if command_id in self.completed_commands:
                command = plan.commands[i]

                if command.can_undo():
                    try:
                        logger.info(f"Rolling back command: {command.name}")
                        undo_result = self.executor.undo_command(command, rollback_options)

                        if undo_result.is_success():
                            rollback_count += 1
                        else:
                            rollback_failures += 1
                            logger.error(
                                f"Failed to rollback {command.name}: {undo_result.error_message}"
                            )

                    except Exception as e:
                        rollback_failures += 1
                        logger.error(f"Error during rollback of {command.name}: {e}")
                else:
                    logger.warning(
                        f"Command {command.name} does not support undo - skipping rollback"
                    )

        logger.info(f"Rollback complete: {rollback_count} successful, {rollback_failures} failed")

    def create_simple_batch_plan(
        self,
        commands: list[Command],
        strategy: BatchStrategy = BatchStrategy.SEQUENTIAL,
        rollback_on_failure: bool = False,
    ) -> BatchExecutionPlan:
        """
        Create a simple batch execution plan.

        Args:
            commands: List of commands to execute
            strategy: Execution strategy
            rollback_on_failure: Whether to rollback on failure

        Returns:
            BatchExecutionPlan
        """
        return BatchExecutionPlan(
            commands=commands,
            dependencies=[],
            strategy=strategy,
            rollback_on_failure=rollback_on_failure,
        )

    def get_execution_summary(self) -> dict[str, Any]:
        """Get summary of batch execution."""
        total_commands = len(self.completed_commands) + len(self.failed_commands)

        return {
            "total_commands": total_commands,
            "completed_commands": len(self.completed_commands),
            "failed_commands": len(self.failed_commands),
            "success_rate": (len(self.completed_commands) / max(1, total_commands)) * 100,
            "completed_command_ids": list(self.completed_commands),
            "failed_command_ids": list(self.failed_commands),
        }
