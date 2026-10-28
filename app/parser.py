import os
from dataclasses import dataclass, field


REDIRECT_STREAMS = {"1": "stdout", "2": "stderr"}
DOUBLE_QUOTE_ESCAPABLE = {"$", '"', "\\", "`", "\n"}


class Operator(str):
    """An unquoted operator token (`|`, `>`, `2>>`, ...), as opposed to a word that just looks like one."""


@dataclass
class Redirect:
    """An output redirection such as `2>> errors.log`."""
    stream: str
    path: str
    mode: str


@dataclass
class Command:
    """A single command of a pipeline: its arguments and redirections."""
    argv: list[str] = field(default_factory=list)
    redirects: list[Redirect] = field(default_factory=list)


def _is_name_char(char: str) -> bool:
    """Checks if a character can be part of a variable name (ASCII letter, digit or underscore)."""
    return char == "_" or (char.isascii() and char.isalnum())

def _read_variable_name(line: str, start: int) -> str:
    """Reads a variable name starting at `start`, or returns "" if there isn't a valid one."""
    end = start
    while end < len(line) and _is_name_char(line[end]):
        end += 1

    name = line[start:end]
    return "" if not name or name[0].isdigit() else name

def _read_variable_reference(line: str, start: int) -> tuple[str, int]:
    """
    Reads the `NAME` or `{NAME}` right after a `$`.
    Returns the name and how many characters it took up, or ("", 0) if there's no variable here.
    """
    if line[start:start + 1] != "{":
        name = _read_variable_name(line, start)
        return name, len(name)

    end = line.find("}", start)
    if end == -1:
        raise ValueError("unexpected EOF while looking for matching `}'")

    name = line[start + 1:end]
    if not name or _read_variable_name(name, 0) != name:
        raise ValueError(f"${line[start:end + 1]}: bad substitution")

    return name, len(name) + 2

def _read_redirect_operator(line: str, start: int, at_word_start: bool) -> str:
    """Reads a redirection operator (`>`, `>>`, `1>`, `2>>`, ...) at `start`, or returns ""."""
    end = start
    if at_word_start and line[end] in REDIRECT_STREAMS and line[end + 1:end + 2] == ">":
        end += 1

    if line[end:end + 1] != ">":
        return ""

    end += 2 if line[end + 1:end + 2] == ">" else 1
    return line[start:end]

def tokenize(line: str, variables: dict[str, str]) -> list[str]:
    """
    Splits a line into words and Operators in a single pass, like bash:
    handles quotes and backslashes, and expands `$NAME`/`${NAME}` (except inside single quotes).
    """
    tokens: list[str] = []
    word: str | None = None
    quote: str | None = None
    i = 0

    def add(text: str) -> None:
        nonlocal word
        word = (word or "") + text

    def end_word() -> None:
        nonlocal word
        if word is not None:
            tokens.append(word)
            word = None

    def add_unquoted_expansion(value: str) -> None:
        """Unquoted values are split on whitespace into separate words, like bash."""
        parts = value.split()
        if not parts:
            if value:
                end_word()
            return

        if value[0].isspace():
            end_word()

        for n, part in enumerate(parts):
            if n:
                end_word()
            add(part)

        if value[-1].isspace():
            end_word()

    while i < len(line):
        char = line[i]
        next_char = line[i + 1:i + 2]

        if quote == "'":
            if char == "'":
                quote = None
            else:
                add(char)
            i += 1
            continue

        if char == "\\":
            if quote == '"' and next_char not in DOUBLE_QUOTE_ESCAPABLE:
                add(char)
                i += 1
            else:
                add(next_char)
                i += 2
            continue

        if char == "$":
            name, length = _read_variable_reference(line, i + 1)
            if name:
                value = variables.get(name, os.environ.get(name, ""))
                if quote:
                    add(value)
                else:
                    add_unquoted_expansion(value)
                i += 1 + length
                continue

        if quote == '"':
            if char == '"':
                quote = None
            else:
                add(char)
            i += 1
            continue

        # Unquoted from here on
        if char in ("'", '"'):
            quote = char
            add("")
            i += 1
            continue

        if char.isspace():
            end_word()
            i += 1
            continue

        operator = "|" if char == "|" else _read_redirect_operator(line, i, word is None)
        if operator:
            end_word()
            tokens.append(Operator(operator))
            i += len(operator)
            continue

        add(char)
        i += 1

    if quote:
        raise ValueError(f"unexpected EOF while looking for matching `{quote}'")

    end_word()
    return tokens

def parse_line(line: str, variables: dict[str, str]) -> list[Command]:
    """Parses a line into its pipeline of Commands (a single command is a pipeline of one)."""
    tokens = tokenize(line, variables)
    if not tokens:
        return []

    commands = [Command()]
    remaining = iter(tokens)

    for token in remaining:
        if not isinstance(token, Operator):
            commands[-1].argv.append(token)

        elif token == "|":
            commands.append(Command())

        else:
            path = next(remaining, None)
            if path is None or isinstance(path, Operator):
                raise ValueError(f"syntax error near unexpected token `{path or 'newline'}'")

            fd = token[0] if token[0] in REDIRECT_STREAMS else "1"
            mode = "a" if token.endswith(">>") else "w"
            commands[-1].redirects.append(Redirect(REDIRECT_STREAMS[fd], path, mode))

    if len(commands) > 1 and not all(command.argv for command in commands):
        raise ValueError("syntax error near unexpected token `|'")

    return commands
