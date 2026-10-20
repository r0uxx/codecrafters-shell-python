import sys
import os
from pathlib import Path

def exit_builtin(*args, **kwargs) -> None:
    """Terminates the shell process."""
    sys.exit()

def echo_builtin(cmd: str, arguments: list[str], **kwargs) -> None:
    """Prints the passed CLI arguments."""
    print(" ".join(arguments))

def type_builtin(cmd: str, arguments: list[str], **kwargs) -> None:
    """Prints the type of a command."""
    if len(arguments) != 1:
        return print(f"Error in length of arguments passed: {len(arguments)}, expected: 1")

    command = arguments[0]
    cb = __BUILTINS.get(command)
    if cb:
        return print(f"{command} is a shell builtin")

    print(_find_executable(command))


def _find_executable(cmd: str) -> str:
    """Checks if a command is an Executable by searching the OS PATH env directories."""
    path_env = os.getenv("PATH", "")
    path_dirs = path_env.split(os.pathsep)
    for dir in path_dirs:
        full_path = os.path.join(dir, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return f"{cmd} is {full_path}"
    
    return f"{cmd}: not found"


# Dictionairy of supported commands and their corresponding callbacks
__BUILTINS = {
    "exit": exit_builtin,
    "echo": echo_builtin,
    "type": type_builtin,
}

def main():
    """Main function."""
    while True:
        sys.stdout.write("$ ")
        command = input()
        command = command.strip()
        if not command:
            continue

        args = command.split(" ")
        command = args[0]
        if not (cb := __BUILTINS.get(command)):
            print(f"{command}: command not found")
            continue

        cb(args[0], args[1:])


if __name__ == "__main__":
    """Main entrypoint."""
    main()
