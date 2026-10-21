import sys
import readline
import os

from contextlib import redirect_stdout
from app.parser import parse_command
from app.utils import (
    get_builtin_cb,
    is_executable,
    run_executable,
    get_path_dirs,
    BUILTINS,
)

PATH = get_path_dirs()

def complete_command(text: str, state: int) -> str | None:
    """Autocomplete supported shell commands."""
    if readline.get_begidx() != 0:
        return None

    completions = {builtin for builtin in BUILTINS}
    
    executables = set()
    for dir in PATH:
        res = list(os.walk(dir))
        if res:
            executables = executables.union(set(res[0][-1]))

    completions = completions.union(executables)
    matches = [cmd for cmd in completions if cmd.startswith(text)]
    if matches:
        return f"{matches[state]} " if state < len(matches) else print("\x07", end="", flush=True)

    return print("\x07", end="", flush=True)


def setup_readline() -> None:
    """Configure shell command autocompletion (my mac uses ^I rl_complete)."""
    readline.set_completer(complete_command)

    backend = getattr(readline, "backend", None)
    is_libedit = backend == "editline" or (
        backend is None
        and "libedit" in (readline.__doc__ or "").lower()
    )

    if is_libedit:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

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
        sys.stdout.write("$ ")
        shell_input = input()
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
