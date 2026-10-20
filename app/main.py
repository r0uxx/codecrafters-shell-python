import sys
import os

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

    builtin_or_executable = arguments[0]
    cb = __BUILTINS.get(builtin_or_executable)
    if cb:
        return print(f"{builtin_or_executable} is a shell builtin")

    exec_path = _find_executable_path(builtin_or_executable)
    if exec_path:
        return print(f"{builtin_or_executable} is {exec_path}")
    return print(f"{builtin_or_executable}: not found")


def _find_executable_path(cmd: str) -> str:
    """Checks if a command is an Executable by searching the OS PATH env directories."""
    path_env = os.getenv("PATH", "")
    path_dirs = path_env.split(os.pathsep)
    for dir in path_dirs:
        full_path = os.path.join(dir, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    
    return ""

def pwd_builtin(*args, **kwargs):
    """Prints the abolute full working directory."""
    print(os.getcwd())

def cd_builtin(cmd: str, arguments:list[str], *args, **kwargs):
    """Changes current working directory."""
    if len(arguments) != 1:
        return print(f"Error: unexpected arguments: {arguments}, only pass the directory you want to change to.")

    path = arguments[0]
    if path and path.startswith("~") and len(path) == 1:
        path = os.getenv("HOME", "")

    if os.path.isdir(path):
        return os.chdir(path)

    return print(f"{cmd}: {path}: No such file or directory")

def _execute_subprocess(cmd: str, args: list[str]):
    """Executes command in a subshell."""
    os.system(f"{cmd} {" ".join(args)}")


# Dictionairy of supported commands and their corresponding callbacks
__BUILTINS = {
    "exit": exit_builtin,
    "echo": echo_builtin,
    "type": type_builtin,
    "pwd": pwd_builtin,
    "cd": cd_builtin,
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
        if cb := __BUILTINS.get(command):
            cb(command, args[1:])
            continue

        elif path := _find_executable_path(command):
            _execute_subprocess(command, args[1:])
            continue

        print(f"{command}: command not found")


if __name__ == "__main__":
    """Main entrypoint."""
    main()
