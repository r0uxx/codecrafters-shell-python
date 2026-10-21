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

def get_completion_kind(text: str) -> str:
    """Determine what kind of completion is needed."""
    line_before_word = readline.get_line_buffer()[:readline.get_begidx()]
    previous_words = line_before_word.split()

    if not previous_words:
        return "path" if "/" in text else "command"

    if len(previous_words) == 1 and previous_words[0] == "type":
        return "command"

    if previous_words[0] == "cd":
        return "directory"

    return "path"


def complete_commands(prefix: str) -> list[str]:
    """Find matching builtins and executables."""
    commands = set(BUILTINS) | get_executable_names()

    return sorted(
        cmd for cmd in commands if cmd.startswith(prefix)
    )

def complete_paths(
    prefix: str,
    directories_only: bool = False,
) -> list[str]:
    """Find matching filesystem paths."""
    directory, name_prefix = os.path.split(prefix)
    search_dir = os.path.expanduser(directory or ".")

    matches = []

    try:
        with os.scandir(search_dir) as entries:
            for entry in entries:
                if not entry.name.startswith(name_prefix):
                    continue

                is_directory = entry.is_dir()

                if directories_only and not is_directory:
                    continue

                path = os.path.join(directory, entry.name)
                matches.append(path + ("/" if is_directory else ""))

    except OSError:
        return []

    return sorted(matches)


class CommandCompleter:
    def __init__(self) -> None:
        self.matches: list[str] = []

    def __call__(self, text: str, state: int) -> str | None:
        if state == 0:
            kind = get_completion_kind(text)

            if kind == "command":
                self.matches = complete_commands(text)
            else:
                self.matches = complete_paths(
                    text,
                    directories_only=(kind == "directory"),
                )

            if len(self.matches) == 1:
                if not self.matches[0].endswith("/"):
                    self.matches[0] += " "

        return self.matches[state] if state < len(self.matches) else None