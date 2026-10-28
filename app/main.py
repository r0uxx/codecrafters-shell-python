import os
import sys
import functools

try:
    import readline
except Exception:
    readline = None

from typing import Callable
from app.completion import CommandCompleter
from app.job_manager import JobManager
from contextlib import ExitStack, redirect_stdout
from app.parser import parse_line
from app.utils import (
    HISTORY,
    SHELL_VARIABLES,
    exit_builtin,
    get_builtin_cb,
    is_executable,
    run_executable,
    run_job,
    run_pipeline,
    load_history,
)

def setup_readline() -> None:
    """Configure shell command autocompletion (my mac uses ^I rl_complete)."""
    if readline is None:
        return

    readline.set_completer(CommandCompleter())
    readline.set_completer_delims(" \t\n")

    is_libedit = (
        getattr(readline, "backend", None) == "editline"
        or "libedit" in (readline.__doc__ or "").lower()
    )

    if is_libedit:
        readline.parse_and_bind("bind ^I rl_complete")
        return

    bindings = [
        "tab: complete",
        "set bell-style audible",
        "set show-all-if-ambiguous off",
        "set show-all-if-unmodified off",
        "set print-completions-horizontally on",
    ]
    for binding in bindings:
        # pyreadline3 (Windows) doesn't support every GNU readline setting, skip the ones it rejects
        try:
            readline.parse_and_bind(binding)
        except Exception:
            continue

def execute_command(cmd: str, args: list[str], stdout=None, stderr=None):
    """Executes a builtin, external or job."""
    job = bool(args and args[-1] == "&")
    if job:
        args.pop(-1)

    cb = construct_callback(cmd, args, job, stdout, stderr)
    if stdout:
        with redirect_stdout(stdout):
            return cb()

    return cb()

def construct_callback(cmd: str, args: list[str], job: bool = False, stdout=None, stderr=None) -> Callable:
    """Constructs the callback and passes its args, returns the callable to the caller."""
    if job:
        return functools.partial(run_job, cmd, args)

    if cb := get_builtin_cb(cmd):
        return functools.partial(cb, cmd=cmd, arguments=args)

    elif is_executable(cmd):
        kwargs = {"stdout": stdout, "stderr": stderr}
        return functools.partial(run_executable, cmd=cmd, args=args, **kwargs)

    return functools.partial(lambda cmd: print(f"{cmd}: command not found", file=sys.stderr), cmd)

def run_line(shell_input: str) -> None:
    """Parses and runs one line of input: a single command or a pipeline."""
    try:
        commands = parse_line(shell_input, SHELL_VARIABLES)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    if len(commands) > 1:
        run_pipeline([command.argv for command in commands])
        return

    if not commands or not commands[0].argv:
        return

    command = commands[0]
    keyword, *args = command.argv
    try:
        with ExitStack() as stack:
            streams = {
                redirect.stream: stack.enter_context(open(redirect.path, redirect.mode, encoding="utf-8"))
                for redirect in command.redirects
            }
            execute_command(keyword, args, **streams)

    except OSError as e:
        print(f"shell: {e}", file=sys.stderr)

def get_prompt() -> str:
    """Shows the current directory (home as ~) before the $, only in the built executable so the tests still see "$ "."""
    if not getattr(sys, "frozen", False):
        return "$ "

    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd == home or cwd.startswith(home + os.sep):
        cwd = "~" + cwd[len(home):]
    return f"{cwd} $ "

def main():
    """Main shell loop."""
    setup_readline()
    job_manager = JobManager()
    load_history()

    while True:
        try:
            shell_input = input(get_prompt()).strip()
        except EOFError:
            print()
            exit_builtin()
        except KeyboardInterrupt:
            print()
            continue

        if not shell_input:
            continue

        HISTORY.append(shell_input)
        try:
            run_line(shell_input)
        except KeyboardInterrupt:
            print()

        job_manager.reap()


if __name__ == "__main__":
    """Main entrypoint."""
    main()
