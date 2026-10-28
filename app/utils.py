import io
import sys
import os
import shutil
import subprocess
import threading
import webbrowser
from contextlib import redirect_stdout
from typing import IO, Callable, TextIO

from app.job_manager import JobManager


PATH = os.getenv("PATH", "")
COMPLETION_REGISTRY = {}
HISTORY: list[str] = []
SHELL_VARIABLES = {}
RICKROLL_URL = "https://www.youtube.com/watch?v=Aq5WXmQQooo"

def exit_builtin(*args, **kwargs) -> None:
    """Terminates the shell process."""
    save_history()
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
    """
    Checks if a command is an Executable by searching the OS PATH env directories.
    shutil.which knows each OS's rules (the execute bit on POSIX, PATHEXT like `.exe` on Windows).
    """
    return shutil.which(cmd, path=PATH) or ""

def is_executable_file(path: str) -> bool:
    """Checks if a file can be run as a program on this OS."""
    if not os.path.isfile(path):
        return False

    if sys.platform == "win32":
        extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").upper().split(os.pathsep)
        return os.path.splitext(path)[1].upper() in extensions

    return os.access(path, os.X_OK)

def popen(argv: list[str], **kwargs) -> subprocess.Popen:
    """Starts a program, resolving it through PATH first."""
    path = _find_executable_path(argv[0]) or None
    if sys.platform != "win32":
        # argv[0] stays what the user typed, so the program still sees its own name
        return subprocess.Popen(argv, executable=path, **kwargs)

    # Windows only finds `.exe` files on PATH by itself, so pass the full path (needed for `.cmd`/`.bat`).
    # `.py` scripts can't be run directly there, they're handed to the Python launcher instead.
    program = path or argv[0]
    interpreter = []
    if program.lower().endswith(".py"):
        interpreter = [shutil.which("py") or shutil.which("python") or "python"]

    return subprocess.Popen([*interpreter, program, *argv[1:]], **kwargs)

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

    path = os.path.expanduser(arguments[0])

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
    if arguments:
        if (flag := arguments[0]).isdigit():
            start = max(len(HISTORY) - int(arguments[0]), 0)

        elif flag == "-r":
            file_path = arguments[-1]
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if line != "\n":
                        HISTORY.append(line.strip())
                return

        elif flag == "-w":
            file_path = arguments[-1]
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(f"\n".join(HISTORY) + "\n")
                return

        elif flag == "-a":
            file_path = arguments[-1]
            current, *older = HISTORY[::-1]
            commands_to_write = [current]
            for command in older:
                if command.startswith("history -a"):
                    break
                commands_to_write.append(command)

            with open(file_path, "a", encoding="utf-8") as file:
                file.write(f"\n".join(commands_to_write[::-1]) + "\n")
            return

    for number, line in enumerate(HISTORY[start:], start=start + 1):
        print(f"{number:>5}  {line}")

def declare_builtin(cmd: str, arguments: list[str], *args, **kwargs) -> None:
    """Declare a variable which can be expanded and passed to commands."""
    if arguments:
        if (flag := arguments[0]) not in {"-p"}:
            name, _, value = flag.partition("=")
            if not (name.isascii() and name.isidentifier()):
                return print(f"{cmd}: `{flag}': not a valid identifier", file=sys.stderr)

            SHELL_VARIABLES[name] = value

        if flag == "-p":
            if (var_name := arguments[-1]) in SHELL_VARIABLES:
                print(f'declare -- {var_name}="{SHELL_VARIABLES[var_name]}"')
                return

            print(f"{cmd}: {arguments[-1]}: not found")

def tac_builtin(cmd: str, arguments: list[str], *args, stdin: IO | None = None, **kwargs) -> None:
    """Just 'cat', but prints each file's lines in reverse. Reads stdin when given no files or `-`."""
    for source in arguments or ["-"]:
        try:
            if source == "-":
                text = (stdin or sys.stdin).read()
            else:
                with open(source, encoding="utf-8", errors="replace") as file:
                    text = file.read()
        except OSError as e:
            print(f"{cmd}: {source}: {e.strerror}", file=sys.stderr)
            continue

        for line in reversed(text.splitlines()):
            print(line)

def rickroll_builtin(*args, **kwargs) -> None:
    """Never gonna give you up."""
    if not webbrowser.open(RICKROLL_URL):
        print(f"No browser found, you'll have to rickroll yourself: {RICKROLL_URL}")

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
    "declare": declare_builtin,
    "tac": tac_builtin,
    "rickroll": rickroll_builtin,
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
):
    """Executes a command with optional stdout redirection, returning its exit code."""
    with popen([cmd, *args], stdout=stdout, stderr=stderr) as process:
        return process.wait()

def _write_and_close(fd: int, data: str) -> None:
    """Writes data into a pipe's write end, then closes it so the reader sees EOF."""
    try:
        with os.fdopen(fd, "w") as pipe:
            pipe.write(data)
    except BrokenPipeError:
        pass  # The reader exited early (e.g. `head`), nothing left to do

def _run_piped_builtin(builtin: Callable, cmd: str, args: list[str], is_last: bool, stdin: IO | None) -> IO | None:
    """
    Runs a builtin inside the shell process, handing it the previous command's output as `stdin`.
    Returns a readable pipe holding its output, or None if it's last and printed to the terminal.
    """
    if stdin is not None and not isinstance(stdin, io.TextIOBase):
        stdin = io.TextIOWrapper(stdin, encoding="utf-8", errors="replace")

    try:
        if is_last:
            builtin(cmd=cmd, arguments=args, stdin=stdin)
            sys.stdout.flush()
            return None

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            builtin(cmd=cmd, arguments=args, stdin=stdin)
    finally:
        if stdin is not None:
            stdin.close()

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
            prev_stdout = _run_piped_builtin(builtin, cmd, args, is_last, stdin=prev_stdout)
            continue

        # If the previous command failed to start, give this one an empty stdin
        stdin = prev_stdout if prev_stdout or is_first else subprocess.DEVNULL
        try:
            process = popen(
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
        sub_p = popen([cmd, *arguments])
        if sub_p:
            command = f"{cmd} " + " ".join(arguments)
            job_num = job_manager.register_job(sub_p, command)
            print(f"[{job_num}] {sub_p.pid}")

def load_history() -> None:
    """Loads history from HISTFILE in memory."""
    histfile_path = os.getenv("HISTFILE")
    if histfile_path:
        history_builtin("history", ["-r", histfile_path])

def save_history() -> None:
    """Loads history from HISTFILE in memory."""
    histfile_path = os.getenv("HISTFILE")
    if histfile_path:
        history_builtin("history", ["-w", histfile_path])
