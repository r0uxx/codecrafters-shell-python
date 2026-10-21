import sys

from contextlib import redirect_stdout

from app.parser import parse_command
from app.utils import (
    get_builtin_cb,
    is_executable,
    run_executable,
)


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
    while True:
        sys.stdout.write("$ ")
        shell_input = input().strip()
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
