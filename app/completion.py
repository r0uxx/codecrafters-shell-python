import os
import subprocess

try:
    import readline
except Exception:
    readline = None

from app.utils import BUILTINS, COMPLETION_REGISTRY, get_path_dirs, is_executable_file, popen


def get_executable_names() -> set[str]:
    """Find executable names in PATH directories."""
    executables = set()

    for directory in get_path_dirs():
        try:
            with os.scandir(directory or ".") as entries:
                for entry in entries:
                    if is_executable_file(entry.path):
                        executables.add(entry.name)
        except OSError:
            continue

    return executables

def get_completion_kind(text: str) -> tuple[str, str]:
    """Determine what kind of completion is needed."""
    line_before_word = readline.get_line_buffer()[:readline.get_begidx()]
    previous_words = line_before_word.split()

    if not previous_words:
        res = "path" if os.path.dirname(text) else "command"
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
                matches.append(path + (os.sep if is_directory else ""))

    except OSError:
        return []

    return sorted(matches)


def execute_completion(cmd: str, text: str) -> list[str]:
    """Run the completer script registered for cmd and return its output lines."""
    script_path = COMPLETION_REGISTRY.get(cmd)
    if not script_path:
        return []

    line = readline.get_line_buffer()
    w_before_cursor = line[:readline.get_begidx()].split()[-1]
    env = {
        **os.environ,
        "COMP_LINE": line,
        "COMP_POINT": str(readline.get_endidx()),
    }
    try:
        # popen also makes `.py`/`.cmd` completer scripts work on Windows
        with popen(
            [script_path, cmd, text, w_before_cursor],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
        ) as process:
            output, _ = process.communicate()
    except OSError:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]


class CommandCompleter:
    def __init__(self) -> None:
        self.matches: list[str] = []

    def __call__(self, text: str, state: int) -> str | None:
        if state == 0:
            kind, cmd = get_completion_kind(text)

            if kind == "completion":
                self.matches = execute_completion(cmd, text)
            elif kind == "command":
                self.matches = complete_commands(text)
            else:
                self.matches = complete_paths(
                    text,
                    directories_only=(kind == "directory"),
                )

            if len(self.matches) == 1:
                if not self.matches[0].endswith(os.sep):
                    self.matches[0] += " "

        return self.matches[state] if state < len(self.matches) else None