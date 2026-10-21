import os
import readline

from app.utils import BUILTINS, get_path_dirs


def get_executable_names() -> set[str]:
    """Find executable names in PATH directories."""
    executables = set()

    for directory in get_path_dirs():
        try:
            with os.scandir(directory or ".") as entries:
                for entry in entries:
                    if entry.is_file() and os.access(entry.path, os.X_OK):
                        executables.add(entry.name)
        except OSError:
            continue

    return executables


class CommandCompleter:
    def __init__(self):
        self.matches: list[str] = []

    def __call__(self, text: str, state: int) -> str | None:
        if state == 0:
            if readline.get_begidx() != 0:
                self.matches = []
            else:
                commands = set(BUILTINS) | get_executable_names()
                self.matches = sorted(
                    cmd for cmd in commands if cmd.startswith(text)
                )

        return f"{self.matches[state]} " if state < len(self.matches) else None