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
            if readline.get_begidx() == 0:
                commands = set(BUILTINS) | get_executable_names()
                self.matches = sorted(
                    cmd for cmd in commands if cmd.startswith(text)
                )
                if len(self.matches) == 1:
                    self.matches[0] += " "
            else:
                try:
                    constructed_dir = "."
                    prefix = text
                    if "/" in text:
                        path = text.split("/")
                        prefix = path[-1]
                        constructed_dir = "/".join(path[:-1]) + "/"
                    with os.scandir(constructed_dir) as entries:
                        self.matches = sorted(
                            constructed_dir + entry.name if constructed_dir != "." else entry.name
                            for entry in entries
                            if (entry.is_file() or entry.is_dir) and entry.name.startswith(prefix)
                        )
                        if len(self.matches) == 1:
                            self.matches[0] += "/" if "." not in self.matches[0] else " "
                except OSError:
                    self.matches = []

        return self.matches[state] if state < len(self.matches) else None