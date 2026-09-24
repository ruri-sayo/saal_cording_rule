"""Command-line interface for SAALCO.

Responsibilities:
- Parse command-line arguments.
- Dispatch commands to appropriate handlers.
- Format and print command output.
- Handle errors and convert exceptions to exit codes per spec §5.

Non-responsibilities:
- Command logic (delegated to commands.* modules).

External dependencies:
- argparse: argument parsing.
- subprocess: may be invoked by dispatched commands (errors caught here).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from .checks import run as run_check
from .commands import approve, init_project, new_feature, new_item
from .errors import SaalcoError
from .evidence import create as create_evidence
from .evidence import package as package_evidence
from .project import discover
from .trace import generate


def parser() -> argparse.ArgumentParser:
    """Create argument parser for all saalco commands.

    Returns:
        Configured ArgumentParser.
    """
    main = argparse.ArgumentParser(prog="saalco", description="Operate SAAL development rules")
    main.add_argument("--version", action="version", version="saalco 1.0.0")
    subs = main.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init", help="initialize a project")
    init.add_argument("--name")
    init.add_argument("--type", choices=["research", "system"])
    init.add_argument("--language", choices=["python", "other"])
    init.add_argument("--spec", action="append", default=[])
    init.add_argument("--non-interactive", action="store_true")
    new = subs.add_parser("new", help="create a feature or document item")
    new.add_argument("kind", choices=["feature", "req", "ad", "dd", "md", "ut", "it", "st", "dev"])
    new.add_argument("title")
    new.add_argument("--feature")
    new.add_argument("--tier", choices=["S", "M", "L"])
    new.add_argument("--slug")
    app = subs.add_parser("approve", help="record human approval")
    app.add_argument("paths", nargs="+")
    check = subs.add_parser("check", help="check project conformance")
    check.add_argument("--verification", action="store_true")
    check.add_argument("--json", action="store_true")
    trace = subs.add_parser("trace", help="generate the RTM")
    trace.add_argument("--json", action="store_true")
    evidence = subs.add_parser("evidence", help="run gates and record Evidence")
    evidence.add_argument("--package", metavar="FEATURE")
    return main


def _required(value: str | None, prompt: str, non_interactive: bool) -> str:
    """Prompt for a required value in interactive mode.

    Args:
        value: User-provided value; if truthy, returned unchanged.
        prompt: Prompt text (should include the option name, e.g., '--name').
        non_interactive: If True, raise error instead of prompting.

    Returns:
        value if truthy; otherwise prompt for input.

    Raises:
        SaalcoError: If non_interactive and value is falsy, or if not a TTY and value is falsy.
    """
    if value:
        return value
    if non_interactive:
        raise SaalcoError(f"ERROR {prompt} is required in non-interactive mode.")
    if not sys.stdin.isatty():
        raise SaalcoError(f"ERROR {prompt} is required; pass it as an option.")
    return input(f"{prompt}: ").strip()


def dispatch(args: argparse.Namespace) -> int:
    """Dispatch parsed arguments to command handlers.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for check failure, 2 for usage error, 3 for environment error).

    Raises:
        SaalcoError: Caught and converted to exit code.

    Side Effects:
        Executes commands, writes files, runs external tools, prints to stdout/stderr.
    """
    if args.command == "init":
        root = Path.cwd()
        name = _required(args.name, "project name (--name)", args.non_interactive)
        kind = _required(args.type, "project type (--type)", args.non_interactive)
        language = _required(args.language, "language (--language)", args.non_interactive)
        conflicts = init_project(root, name, kind, language, args.spec)
        print("Initialized SAALCO project.")
        for item in conflicts:
            print(f"WARNING not overwritten: {item}", file=sys.stderr)
        return 0
    root = discover()
    if args.command == "new":
        if args.kind == "feature":
            if not args.tier:
                raise SaalcoError("ERROR new feature requires --tier S|M|L.")
            slug = args.slug
            if slug is None and args.title:
                # Try to auto-generate slug; if it fails, prompt in interactive mode
                auto_slug = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")
                if not auto_slug:
                    # Non-ASCII title; need explicit slug
                    if args.non_interactive:
                        raise SaalcoError("ERROR title produces no ASCII slug; pass --slug SLUG.")
                    if not sys.stdin.isatty():
                        raise SaalcoError("ERROR title produces no ASCII slug; pass --slug SLUG.")
                    slug = input("slug (--slug): ").strip()
                    if not slug:
                        raise SaalcoError("ERROR slug is required.")
                else:
                    slug = auto_slug
            print(new_feature(root, args.title, args.tier, slug))
        else:
            if not args.feature:
                raise SaalcoError("ERROR new item requires --feature F-nnn.")
            ident, warning = new_item(root, args.kind, args.feature, args.title)
            print(ident)
            if warning:
                print(f"WARNING {warning}", file=sys.stderr)
        return 0
    if args.command == "approve":
        approve(root, args.paths)
        return 0
    if args.command == "check":
        report = run_check(root, args.verification)
        print(report.output(args.json))
        return 0 if report.ok else 1
    if args.command == "trace":
        rows = generate(root)
        print(
            json.dumps(rows, ensure_ascii=False, indent=2)
            if args.json
            else f"Generated RTM with {len(rows)} requirement rows."
        )
        return 0
    if args.command == "evidence":
        if args.package:
            print(package_evidence(root, args.package))
            return 0
        path, overall = create_evidence(root)
        print(f"Created {path.relative_to(root)}")
        print(f"Overall: {overall}")
        print("Commit evidence/ and docs/trace/.")
        return 0 if overall == "PASS" else 1
    return 2


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments; defaults to sys.argv[1:] if None.

    Returns:
        Exit code per spec §5: 0=success, 1=check failure, 2=usage error, 3=environment error.

    Side Effects:
        Prints output to stdout/stderr, may write files and execute external processes.
    """
    try:
        return dispatch(parser().parse_args(argv))
    except SaalcoError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code
    except subprocess.CalledProcessError as exc:
        print(f"ERROR subprocess failed: {exc.cmd}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("ERROR interrupted", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
