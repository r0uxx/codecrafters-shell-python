import sys
import os

from typing import Callable

PATH = os.getenv("PATH", "")

def exit_builtin(*args, **kwargs) -> None:
    """Terminates the shell process."""
    sys.exit()

def echo_builtin(cmd: str, arguments: list[str], **kwargs) -> None:
    """Prints the passed CLI arguments."""
    print(" ".join(arguments))

def type_builtin(cmd: str = "type", arguments: list[str] | None = None, to_print: bool = True, **kwargs) -> str:
    """Prints the type of a command."""
    if not arguments or len(arguments) != 1:
        if to_print:
            print(f"Error in arguments passed: {arguments}")
        return "unkown"

    builtin_or_executable = arguments[0]
    cb = __BUILTINS.get(builtin_or_executable)
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

def _find_executable_path(cmd: str) -> str:
    """Checks if a command is an Executable by searching the OS PATH env directories."""
    path_dirs = PATH.split(os.pathsep)
    for dir in path_dirs:
        full_path = os.path.join(dir, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    
    return ""

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


# Dictionairy of supported commands and their corresponding callbacks
__BUILTINS = {
    "exit": exit_builtin,
    "echo": echo_builtin,
    "type": type_builtin,
    "pwd": pwd_builtin,
    "cd": cd_builtin,
}

def get_builtin_cb(cmd: str) -> Callable | None:
    """Returns a builtin if found else None."""
    return __BUILTINS.get(cmd)

def is_executable(cmd: str) -> bool:
    """Checks if the given command is an executable found in PATH."""
    res = type_builtin(arguments=[cmd], to_print=False)
    return not ("builtin" in res or "unknown" in res)

def run_executable(cmd: str, args: list[str]) -> None:
    """Executes command in a subshell."""
    parsed = ""
    for arg in args:
        parsed += f"'{arg}' "

    parsed.strip()
    os.system(f"{cmd} {parsed}")
