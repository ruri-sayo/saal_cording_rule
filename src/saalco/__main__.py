"""Entry point for saalco when run as `python -m saalco`.

Responsibilities:
    - Delegate to the CLI module to execute the main command dispatcher.

Non-responsibilities:
    - Command implementation details.
    - Environment or argument parsing (delegated to `cli.main()`).
"""

from .cli import main

raise SystemExit(main())
