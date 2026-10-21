import shlex

def parse_command(line: str) -> tuple[list[str], str | None]:
    """Parses a command and optional stdout redirection."""
    quote = None
    escaped = False

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
            if line[i:i + 2] == ">>":
                raise ValueError("Append redirection is not supported yet")

            start = i
            if (
                i > 0
                and line[i - 1] == "1"
                and (i == 1 or line[i - 2].isspace())
            ):
                start = i - 1

            before = shlex.split(line[:start])
            after = shlex.split(line[i + 1:])

            if not after:
                raise ValueError("Missing redirection filename")

            filename, *remaining_args = after
            return before + remaining_args, filename

    return shlex.split(line), None