import sys
import shlex
from app.utils import get_builtin_cb, is_executable, run_executable

def main():
    """Main function."""
    while True:
        sys.stdout.write("$ ")
        shell_input = input().strip()
        if not shell_input:
            continue

        try:
            keyword, *args = shlex.split(shell_input)
        except ValueError as e:
            print(f"Error: {e}")
            continue

        if cb := get_builtin_cb(keyword):
            cb(keyword, args)
            continue

        elif is_executable(keyword):
            run_executable(keyword, args)
            continue

        print(f"{keyword}: command not found")


if __name__ == "__main__":
    """Main entrypoint."""
    main()
