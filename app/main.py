import sys
from app.utils import get_builtin_cb, is_executable, run_executable

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
        if cb := get_builtin_cb(command):
            cb(command, args[1:])
            continue

        elif is_executable(command):
            run_executable(command, args[1:])
            continue

        print(f"{command}: command not found")


if __name__ == "__main__":
    """Main entrypoint."""
    main()
