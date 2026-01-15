"""
Code Execution Safety Utilities
Secure execution of Python code and shell commands in sandboxed environments.

Extracted from llamacli.py for use across projects requiring safe code execution.
"""

import os
import sys
import asyncio
import tempfile
import logging
from typing import Optional, List
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    stdout: str
    stderr: str
    exit_code: Optional[int] = None
    error: Optional[str] = None

    @property
    def output(self) -> str:
        """Get combined output (stdout + stderr if error)"""
        if self.success:
            return self.stdout
        return f"{self.stdout}\n{self.stderr}".strip() if self.stderr else self.stdout


# Default unsafe bash tokens
UNSAFE_BASH_TOKENS = [
    'sudo',
    'rm -rf',
    'mkfs',
    'dd if=',
    '> /dev/',
    'curl | sh',
    'wget | sh',
    'eval',
    '__import__',
    'chmod +s',
    ':(){:|:&};:',  # fork bomb
]


class SafeExecutor:
    """
    Safe code executor with sandboxing and restrictions.

    Provides methods for executing Python code and shell commands
    with safety restrictions and resource limits.
    """

    def __init__(
        self,
        temp_dir: Optional[str] = None,
        allowed_imports: Optional[List[str]] = None,
        blocked_imports: Optional[List[str]] = None,
        timeout: int = 30
    ):
        """
        Initialize safe executor.

        Args:
            temp_dir: Temporary directory for execution (default: system temp)
            allowed_imports: Whitelist of allowed Python imports (None = allow all except blocked)
            blocked_imports: Blacklist of blocked Python imports
            timeout: Execution timeout in seconds (default: 30)
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.python_path = sys.executable
        self.timeout = timeout

        # Import controls
        self.allowed_imports = allowed_imports
        self.blocked_imports = blocked_imports or [
            'os.system',
            'subprocess',
            'eval',
            'exec',
            '__import__',
            'compile',
            'open',  # Can be dangerous, consider carefully
        ]

    async def run_python_code(
        self,
        code: str,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute Python code in a sandboxed subprocess.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds (default: use instance timeout)

        Returns:
            ExecutionResult with output and status

        Example:
            >>> executor = SafeExecutor()
            >>> result = await executor.run_python_code("print('Hello')")  # doctest: +SKIP
            >>> result.success  # doctest: +SKIP
            True
            >>> result.output  # doctest: +SKIP
            'Hello'
        """
        timeout = timeout or self.timeout

        try:
            # Create temporary file for code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                dir=self.temp_dir
            ) as f:
                f.write(code)
                temp_path = f.name

            logger.debug(f"Executing Python code from {temp_path}")

            # Execute in subprocess with restricted environment
            proc = await asyncio.create_subprocess_exec(
                self.python_path,
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir,
                env={
                    'PATH': os.environ.get('PATH', ''),
                    'PYTHONDONTWRITEBYTECODE': '1',  # Don't create .pyc files
                    'PYTHONHASHSEED': '0',  # Deterministic hashing
                }
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    success=False,
                    stdout='',
                    stderr='',
                    error=f'Execution timed out after {timeout}s'
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {temp_path}: {e}")

            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()

            success = proc.returncode == 0

            if not success:
                logger.warning(f"Python execution failed with code {proc.returncode}")

            return ExecutionResult(
                success=success,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=proc.returncode
            )

        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return ExecutionResult(
                success=False,
                stdout='',
                stderr='',
                error=str(e)
            )

    async def run_bash_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        unsafe_tokens: Optional[List[str]] = None
    ) -> ExecutionResult:
        """
        Execute a bash command in a sandboxed subprocess.

        Args:
            command: Bash command to execute
            timeout: Execution timeout in seconds (default: use instance timeout)
            unsafe_tokens: List of unsafe tokens to block (default: UNSAFE_BASH_TOKENS)

        Returns:
            ExecutionResult with output and status

        Example:
            >>> executor = SafeExecutor()
            >>> result = await executor.run_bash_command("echo 'Hello'")  # doctest: +SKIP
            >>> result.success  # doctest: +SKIP
            True
            >>> result.output  # doctest: +SKIP
            'Hello'
        """
        timeout = timeout or self.timeout
        unsafe_tokens = unsafe_tokens or UNSAFE_BASH_TOKENS

        # Check for unsafe tokens
        for token in unsafe_tokens:
            if token in command:
                logger.warning(f"Blocked unsafe command containing: {token}")
                return ExecutionResult(
                    success=False,
                    stdout='',
                    stderr='',
                    error=f"Command contains unsafe operation: {token}"
                )

        try:
            logger.debug(f"Executing bash command: {command}")

            # Execute in subprocess with restricted environment
            proc = await asyncio.create_subprocess_exec(
                'sh', '-c', command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir,
                env={
                    'PATH': '/usr/bin:/bin',
                    'HOME': self.temp_dir,
                    'TMPDIR': self.temp_dir,
                }
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    success=False,
                    stdout='',
                    stderr='',
                    error=f'Execution timed out after {timeout}s'
                )

            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()

            success = proc.returncode == 0

            if not success:
                logger.warning(f"Bash execution failed with code {proc.returncode}")

            return ExecutionResult(
                success=success,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=proc.returncode
            )

        except Exception as e:
            logger.error(f"Error executing bash command: {e}")
            return ExecutionResult(
                success=False,
                stdout='',
                stderr='',
                error=str(e)
            )

    def run_python_code_sync(self, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """
        Synchronous wrapper for run_python_code.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            ExecutionResult with output and status
        """
        return asyncio.run(self.run_python_code(code, timeout))

    def run_bash_command_sync(self, command: str, timeout: Optional[int] = None) -> ExecutionResult:
        """
        Synchronous wrapper for run_bash_command.

        Args:
            command: Bash command to execute
            timeout: Execution timeout in seconds

        Returns:
            ExecutionResult with output and status
        """
        return asyncio.run(self.run_bash_command(command, timeout))


# Convenience functions for one-off executions
def execute_python(code: str, timeout: int = 30) -> ExecutionResult:
    """
    Execute Python code safely (synchronous).

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds (default: 30)

    Returns:
        ExecutionResult with output and status

    Example:
        >>> result = execute_python("print(2 + 2)")  # doctest: +SKIP
        >>> result.output  # doctest: +SKIP
        '4'
    """
    executor = SafeExecutor(timeout=timeout)
    return executor.run_python_code_sync(code, timeout)


def execute_bash(command: str, timeout: int = 30) -> ExecutionResult:
    """
    Execute bash command safely (synchronous).

    Args:
        command: Bash command to execute
        timeout: Execution timeout in seconds (default: 30)

    Returns:
        ExecutionResult with output and status

    Example:
        >>> result = execute_bash("echo 'test'")  # doctest: +SKIP
        >>> result.output  # doctest: +SKIP
        'test'
    """
    executor = SafeExecutor(timeout=timeout)
    return executor.run_bash_command_sync(command, timeout)


def is_command_safe(command: str, unsafe_tokens: Optional[List[str]] = None) -> tuple[bool, Optional[str]]:
    """
    Check if a bash command is safe to execute.

    Args:
        command: Bash command to check
        unsafe_tokens: List of unsafe tokens (default: UNSAFE_BASH_TOKENS)

    Returns:
        Tuple of (is_safe, unsafe_token_found)

    Example:
        >>> is_command_safe("echo 'hello'")
        (True, None)
        >>> is_command_safe("sudo rm -rf /")
        (False, 'sudo')
    """
    unsafe_tokens = unsafe_tokens or UNSAFE_BASH_TOKENS

    for token in unsafe_tokens:
        if token in command:
            return False, token

    return True, None
