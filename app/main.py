import sys

def terminate_shell(*args, **kwargs) -> None:
    """Terminates the shell process."""
    sys.exit()

def echo_builtin(arguments: list[str], *args, **kwargs) -> None:
    """Prints the passed CLI arguments."""
    print(" ".join(arguments))

# Dictionairy of supported commands and their corresponding callbacks
KEYWORDS = {
    "exit": terminate_shell,
    "echo": echo_builtin,
}

def main():
    """Main function."""
    while True:
        sys.stdout.write("$ ")
        command = input()
        if not command:
            continue

        args = command.split(" ")
        command = args[0]
        if not (cb := KEYWORDS.get(command)):
            print(f"{command}: command not found")
            continue

        cb(args[1:])


if __name__ == "__main__":
    """Main entrypoint."""
    main()
