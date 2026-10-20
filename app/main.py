import sys

TERMINATE_SHELL = "exit"

def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        if command == TERMINATE_SHELL:
            break

        print(f"{command}: command not found")


if __name__ == "__main__":
    main()
