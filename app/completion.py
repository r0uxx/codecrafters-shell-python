import os
import readline
import subprocess

from app.utils import BUILTINS, COMPLETION_REGISTRY, get_path_dirs


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

def get_completion_kind(text: str) -> tuple[str, str]:
    """Determine what kind of completion is needed."""
    line_before_word = readline.get_line_buffer()[:readline.get_begidx()]
    previous_words = line_before_word.split()

    if not previous_words:
        res = "path" if "/" in text else "command"
        return res, ""

    if len(previous_words) == 1 and previous_words[0] == "type":
        return "command", ""

    if previous_words[0] == "cd":
        return "directory", ""

    if previous_words[0] in COMPLETION_REGISTRY:
        return "completion", previous_words[0]

    return "path", ""


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


def execute_completion(cmd: str) -> list[str]:
    """Run the completer script registered for cmd and return its output lines."""
    script_path = COMPLETION_REGISTRY.get(cmd)
    if not script_path:
        return []

    line = readline.get_line_buffer().split()
    w_at_cursor = line[-1]
    w_before_cursos = "" if len(line) <= 2 else line[-2]
    try:
        result = subprocess.run([script_path, cmd, w_at_cursor, w_before_cursos], capture_output=True, text=True)
    except OSError:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


class CommandCompleter:
    def __init__(self) -> None:
        self.matches: list[str] = []

    def __call__(self, text: str, state: int) -> str | None:
        if state == 0:
            kind, cmd = get_completion_kind(text)

            if kind == "completion":
                self.matches = execute_completion(cmd)
            elif kind == "command":
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