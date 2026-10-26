import io
import sys
import os
import subprocess
import threading
from contextlib import redirect_stdout
from typing import IO, Callable, TextIO

from app.job_manager import JobManager


PATH = os.getenv("PATH", "")
COMPLETION_REGISTRY = {}
HISTORY: list[str] = []

def exit_builtin(*args, **kwargs) -> None:
    """Terminates the shell process."""
    sys.exit()

def echo_builtin(arguments: list[str], *args, **kwargs) -> None:
    """Prints the passed CLI arguments."""
    print(" ".join(arguments))

def type_builtin(arguments: list[str] | None = None, to_print: bool = True, *args, **kwargs) -> str:
    """Prints the type of a command."""
    if not arguments or len(arguments) != 1:
        if to_print:
            print(f"Error in arguments passed: {arguments}")
        return "unkown"

    builtin_or_executable = arguments[0]
    cb = BUILTINS.get(builtin_or_executable)
    if cb:
        if to_print:
            print(f"{builtin_or_executable} is a shell builtin")
        return "builtin"

    exec_path = _find_executable_path(builtin_or_executable)
    if exec_path:
        if to_print:
            print(f"{builtin_or_executable} is {exec_path}")
        return "executable"

    if to_print:
        print(f"{builtin_or_executable}: not found")
    return "unknown"

def _find_executable_path(cmd: str, *args, **kwargs) -> str:
    """Checks if a command is an Executable by searching the OS PATH env directories."""
    path_dirs = get_path_dirs()
    for dir in path_dirs:
        full_path = os.path.join(dir, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    
    return ""

def get_path_dirs() -> list[str]:
    """Returns the path directories."""
    return PATH.split(os.pathsep)

def pwd_builtin(*args, **kwargs) -> None:
    """Prints the abolute full working directory."""
    print(os.getcwd())

def cd_builtin(cmd: str, arguments:list[str], *args, **kwargs) -> None:
    """Changes current working directory."""
    if len(arguments) != 1:
        return print(f"Error: unexpected arguments: {arguments}, only pass the directory you want to change to.")

    path = arguments[0]
    if path and path.startswith("~") and len(path) == 1:
        path = os.getenv("HOME", "")

    if os.path.isdir(path):
        return os.chdir(path)

    return print(f"{cmd}: {path}: No such file or directory")

def complete_builtin(cmd: str, arguments: list[str],*args, **kwargs) -> None:
    """Allow programmable completion."""
    if not arguments:
        return print(f"Error")

    if arguments[0].startswith("-p") and len(arguments) > 1:
        if completion_path := COMPLETION_REGISTRY.get(arguments[1]):
            return print(f"{cmd} -C '{completion_path}' {arguments[1]}")

        return print(f"{cmd}: {arguments[1]}: no completion specification")

    if arguments[0].startswith("-C") and len(arguments) > 2:
        COMPLETION_REGISTRY[arguments[2]] = arguments[1]
        return

    if arguments[0].startswith("-r") and len(arguments) > 1:
        COMPLETION_REGISTRY.pop(arguments[1])
        return

def jobs_builtin(cmd: str, arguments: list[str], *args, **kwargs) -> None:
    """Implement later."""
    manager = JobManager()
    for job in manager.get_jobs():
        print(job)
    manager.reap(to_print=False)

def history_builtin(cmd: str, arguments: list[str], *args, **kwargs) -> None:
    """Lists previously executed commands, optionally only the last n (`history n`)."""
    start = 0
    if arguments and arguments[0].isdigit():
        start = max(len(HISTORY) - int(arguments[0]), 0)

    for number, line in enumerate(HISTORY[start:], start=start + 1):
        print(f"{number:>5}  {line}")

# Dictionairy of supported commands and their corresponding callbacks
BUILTINS = {
    "exit": exit_builtin,
    "echo": echo_builtin,
    "type": type_builtin,
    "pwd": pwd_builtin,
    "cd": cd_builtin,
    "complete": complete_builtin,
    "jobs": jobs_builtin,
    "history": history_builtin,
}

def get_builtin_cb(cmd: str) -> Callable | None:
    """Returns a builtin if found else None."""
    return BUILTINS.get(cmd)

def is_executable(cmd: str) -> bool:
    """Checks if the given command is an executable found in PATH."""
    res = type_builtin(arguments=[cmd], to_print=False)
    return not ("builtin" in res or "unknown" in res)

def run_executable(
    cmd: str,
    args: list[str],
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> None:
    """Executes a command with optional stdout redirection."""
    subprocess.run([cmd, *args], stdout=stdout, stderr=stderr)

def _write_and_close(fd: int, data: str) -> None:
    """Writes data into a pipe's write end, then closes it so the reader sees EOF."""
    try:
        with os.fdopen(fd, "w") as pipe:
            pipe.write(data)
    except BrokenPipeError:
        pass  # The reader exited early (e.g. `head`), nothing left to do

def _run_piped_builtin(builtin: Callable, cmd: str, args: list[str], is_last: bool) -> IO | None:
    """
    Runs a builtin inside the shell process.
    Returns a readable pipe holding its output, or None if it's last and printed to the terminal.
    """
    if is_last:
        builtin(cmd=cmd, arguments=args)
        sys.stdout.flush()
        return None

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        builtin(cmd=cmd, arguments=args)

    # Write from a thread, so output larger than the pipe buffer can't block the shell
    read_fd, write_fd = os.pipe()
    threading.Thread(target=_write_and_close, args=(write_fd, buffer.getvalue()), daemon=True).start()
    return os.fdopen(read_fd)

def run_pipeline(commands: list[list[str]]) -> None:
    """Runs commands with each one's stdout piped into the next one's stdin."""
    processes = []
    prev_stdout = None

    for i, (cmd, *args) in enumerate(commands):
        is_first = i == 0
        is_last = i == len(commands) - 1

        if builtin := get_builtin_cb(cmd):
            # Builtins don't read stdin, so the incoming pipe is just closed
            if prev_stdout:
                prev_stdout.close()

            prev_stdout = _run_piped_builtin(builtin, cmd, args, is_last)
            continue

        # If the previous command failed to start, give this one an empty stdin
        stdin = prev_stdout if prev_stdout or is_first else subprocess.DEVNULL
        try:
            process = subprocess.Popen(
                [cmd, *args],
                stdin=stdin,
                stdout=None if is_last else subprocess.PIPE,
            )
        except FileNotFoundError:
            print(f"{cmd}: command not found", file=sys.stderr)
            process = None

        # Drop our copy of the read end, so only the next command holds it.
        # Without this, the writer never gets SIGPIPE when the reader exits (e.g. `tail -f | head`).
        if prev_stdout:
            prev_stdout.close()

        prev_stdout = process.stdout if process else None
        if process:
            processes.append(process)

    for process in processes:
        process.wait()

def run_job(cmd: str, arguments: list[str], *args, **kwargs) -> None:
    """Runs a task in a non blocking subprocess."""
    job_manager = JobManager()
    if cmd and arguments:
        sub_p = subprocess.Popen([cmd] + arguments, *args)
        if sub_p:
            command = f"{cmd} " + " ".join(arguments)
            job_num = job_manager.register_job(sub_p, command)
            print(f"[{job_num}] {sub_p.pid}")