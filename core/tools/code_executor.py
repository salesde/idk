"""Sandboxed Python code executor for generated scripts."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30


async def execute_python(code: str, timeout: int = TIMEOUT_SECONDS) -> tuple[str, str, int]:
    """
    Execute a Python code snippet in a subprocess.
    Returns (stdout, stderr, returncode).
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return "", "Execution timed out", 1

        return stdout.decode(), stderr.decode(), proc.returncode
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def validate_python_syntax(code: str) -> tuple[bool, str]:
    """Check if Python code is syntactically valid."""
    stdout, stderr, code_rc = await execute_python(
        f"import ast\nast.parse({repr(code)})\nprint('OK')"
    )
    if code_rc == 0 and "OK" in stdout:
        return True, ""
    return False, stderr
