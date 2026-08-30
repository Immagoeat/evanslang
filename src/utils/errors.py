class EvansLangError(Exception):
    pass


class LexError(EvansLangError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Lex error at line {line}, column {column}: {message}")


class ParseError(EvansLangError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Parse error at line {line}, column {column}: {message}")
