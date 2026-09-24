"""Error classes for SAALCO.

Responsibilities:
- Define exception hierarchy with appropriate exit codes for different error conditions.

Non-responsibilities:
- Error message formatting (done by CLI layer).
"""


class SaalcoError(Exception):
    """Base exception for SAALCO errors.

    Attributes:
        exit_code: CLI exit code (2 for usage/configuration errors).
    """

    exit_code = 2


class CheckFailed(SaalcoError):
    """Raised when verification checks fail.

    Exit code is 1 (reserved for check failures per spec §5).
    """

    exit_code = 1


class ToolError(SaalcoError):
    """Raised when external tool (git, subprocess) execution fails.

    Exit code is 3 (environment/external tool error per spec §5).
    """

    exit_code = 3


# Alias for backward compatibility (evidence.py imports EnvironmentError)
EnvironmentError = ToolError
