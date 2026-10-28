import os
import shlex

def _is_name_char(char: str) -> bool:
    """Checks if a character can be part of a variable name (ASCII letter, digit or underscore)."""
    return char == "_" or (char.isascii() and char.isalnum())

def expand_variables(line: str, variables: dict[str, str]) -> str:
    """
    Replaces `$NAME` with the variable's value (falling back to the environment, else empty).
    Not expanded inside single quotes or when the `$` is escaped, like bash.
    """
    result = []
    quote = None
    escaped = False
    i = 0

    while i < len(line):
        char = line[i]

        if escaped:
            escaped = False

        elif char == "\\" and quote != "'":
            escaped = True

        elif char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None

        elif char == "$" and quote != "'":
            end = i + 1
            while end < len(line) and _is_name_char(line[end]):
                end += 1

            name = line[i + 1:end]
            if name and not name[0].isdigit():
                result.append(variables.get(name, os.environ.get(name, "")))
                i = end
                continue

        result.append(char)
        i += 1

    return "".join(result)

def split_pipeline(line: str) -> list[str]:
    """Splits a line on unquoted, unescaped `|` into pipeline segments."""
    segments = []
    quote = None
    escaped = False
    start = 0

    for i, char in enumerate(line):
        if escaped:
            escaped = False
            continue

        if char == "\\" and quote != "'":
            escaped = True
            continue

        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue

        if char == "|" and quote is None:
            segments.append(line[start:i].strip())
            start = i + 1

    segments.append(line[start:].strip())

    if len(segments) > 1 and not all(segments):
        raise ValueError("syntax error near unexpected token `|'")

    return segments

def parse_command(line: str) -> tuple[list[str], str | None, str, str]:
    """Parses a command and optional stdout redirection."""
    quote = None
    escaped = False
    std_kwarg = ""
    file_mode = "w"
    filename = None

    for i, char in enumerate(line):
        if escaped:
            escaped = False
            continue

        if char == "\\" and quote != "'":
            escaped = True
            continue

        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue

        if char == ">" and quote is None:
            start = i
            if line[i:i + 2] == ">>":
                file_mode = "a"
                start = i - 1
                std_kwarg = "stderr" if line[i - 1] == "2" else "stdout"
                i += 1

            elif (i > 0 and line[i - 1] == "1"and (i == 1 or line[i - 2].isspace())):
                std_kwarg = "stdout"
                start = i - 1
                
            elif (i > 0 and line[i - 1] != "1"):
                if line[i - 1].isspace():
                    std_kwarg = "stdout"

                elif line[i - 1] == "2" and (i == 1 or line[i - 2].isspace()):
                    std_kwarg = "stderr"

                start = i - 1

            before = shlex.split(line[:start])
            after = shlex.split(line[i + 1:])

            if not after:
                raise ValueError("Missing redirection filename")

            filename, *remaining_args = after
            return before + remaining_args, filename, std_kwarg, file_mode

    return shlex.split(line), filename, std_kwarg, file_mode