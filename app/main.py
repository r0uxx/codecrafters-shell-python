import sys
import readline
import functools

from typing import Callable
from app.completion import CommandCompleter
from app.job_manager import JobManager
from contextlib import ExitStack, redirect_stdout
from app.parser import parse_line
from app.utils import (
    HISTORY,
    SHELL_VARIABLES,
    get_builtin_cb,
    is_executable,
    run_executable,
    run_job,
    run_pipeline,
    load_history
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

def execute_command(cmd: str, args: list[str], stdout=None, stderr=None) -> None:
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

def main():
    """Main shell loop."""
    setup_readline()
    job_manager = JobManager()
    load_history()

    while True:
        shell_input = input("$ ").strip()
        if not shell_input:
            continue

        HISTORY.append(shell_input)
        try:
            commands = parse_line(shell_input, SHELL_VARIABLES)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            continue

        if len(commands) > 1:
            run_pipeline([command.argv for command in commands])
            job_manager.reap()
            continue

        if not commands or not commands[0].argv:
            continue

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

        job_manager.reap()


if __name__ == "__main__":
    """Main entrypoint."""
    main()
