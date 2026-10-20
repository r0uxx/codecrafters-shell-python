import sys

def exit_builtin(*args, **kwargs) -> None:
    """Terminates the shell process."""
    sys.exit()

def echo_builtin(arguments: list[str], *args, **kwargs) -> None:
    """Prints the passed CLI arguments."""
    print(" ".join(arguments[1:]))

def type_builtin(arguments: list[str], *args, **kwargs) -> None:
    """Prints the type of a command."""
    if len(arguments) > 2 or len(arguments) == 1 or not arguments:
        print(f"Error in length of arguments passed: {len(arguments)}, expected: 2")

    type_to_search = "".join(arguments[1:])
    cb = __BUILTINS.get(type_to_search)
    if cb:
        return print(f"{type_to_search} is a shell builtin")

    print(f"{type_to_search}: not found")

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

        cb(args)


if __name__ == "__main__":
    """Main entrypoint."""
    main()
