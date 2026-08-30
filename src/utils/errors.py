class EvansLangError(Exception):
    kind = "error"

    def __init__(self, message: str, line: int | None = None, column: int | None = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(message)


class LexError(EvansLangError):
    kind = "lex error"

    def __init__(self, message: str, line: int, column: int):
        super().__init__(message, line, column)


class ParseError(EvansLangError):
    kind = "parse error"

    def __init__(self, message: str, line: int, column: int):
        super().__init__(message, line, column)
