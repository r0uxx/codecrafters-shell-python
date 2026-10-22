import sys
import readline
import os

from app.completion import CommandCompleter
from contextlib import redirect_stdout
from app.parser import parse_command
from app.utils import (
    get_builtin_cb,
    is_executable,
    run_executable,
)

def setup_readline() -> None:
    """Configure shell command autocompletion (my mac uses ^I rl_complete)."""
    readline.set_completer(CommandCompleter())
    readline.set_completer_delims(" \t\n")

    is_libedit = (
        getattr(readline, "backend", None) == "editline"
        or "libedit" in (readline.__doc__ or "").lower()
    )

    if is_libedit:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set bell-style audible")
        readline.parse_and_bind("set show-all-if-ambiguous off")
        readline.parse_and_bind("set show-all-if-unmodified off")
        readline.parse_and_bind("set print-completions-horizontally on")

def execute_command(cmd, args, stdout=None, stderr=None):
    """Executes a builtin or external command."""

    if cb := get_builtin_cb(cmd):
        if stdout is None:
            cb(cmd, args)
        else:
            with redirect_stdout(stdout):
                cb(cmd, args)

    elif is_executable(cmd):
        run_executable(cmd, args, stdout=stdout, stderr=stderr)
    else:
        print(f"{cmd}: command not found", file=sys.stderr)

def main():
    """Main shell loop."""
    setup_readline()
    while True:
        shell_input = input("$ ").strip()
        if not shell_input:
            continue

        try:
            tokens, output_path, std_kwarg, file_mode = parse_command(shell_input)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            continue

        if not tokens:
            continue

        keyword, *args = tokens
        try:
            if output_path is not None:
                with open(output_path, file_mode, encoding="utf-8") as file:
                    kwargs = {}
                    if std_kwarg:
                        kwargs[std_kwarg] = file

                    execute_command(keyword, args, **kwargs)
            else:
                execute_command(keyword, args)

        except OSError as e:
            print(f"shell: {e}", file=sys.stderr)


if __name__ == "__main__":
    """Main entrypoint."""
    main()
