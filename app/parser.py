import shlex

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