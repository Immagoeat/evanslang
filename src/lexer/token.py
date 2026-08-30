from enum import Enum, auto


class TokenType(Enum):
    IDENTIFIER = auto()
    STRING = auto()
    INT = auto()
    LPAREN = auto()
    RPAREN = auto()
    SEMICOLON = auto()
    COLON = auto()
    EQUALS = auto()
    EOF = auto()


class Token:
    def __init__(self, type: TokenType, value: str, line: int, column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.column})"
