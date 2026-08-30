from lexer.token import Token, TokenType
from utils.errors import LexError


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        tokens = []
        while True:
            token = self._next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens

    def _next_token(self) -> Token:
        self._skip_whitespace()

        if self.pos >= len(self.source):
            return Token(TokenType.EOF, "", self.line, self.column)

        char = self.source[self.pos]
        line, column = self.line, self.column

        if char == "(":
            self._advance()
            return Token(TokenType.LPAREN, "(", line, column)

        if char == ")":
            self._advance()
            return Token(TokenType.RPAREN, ")", line, column)

        if char == ";":
            self._advance()
            return Token(TokenType.SEMICOLON, ";", line, column)

        if char == ":":
            self._advance()
            return Token(TokenType.COLON, ":", line, column)

        if char == "=":
            self._advance()
            return Token(TokenType.EQUALS, "=", line, column)

        if char == '"':
            return self._read_string()

        if char.isalpha() or char == "_":
            return self._read_identifier()

        if char.isdigit():
            return self._read_int()

        raise LexError(f"Unexpected character {char!r}", line, column)

    def _read_string(self) -> Token:
        line, column = self.line, self.column
        self._advance()  # opening quote
        value = []
        while True:
            if self.pos >= len(self.source):
                raise LexError("Unterminated string literal", line, column)
            char = self.source[self.pos]
            if char == '"':
                self._advance()
                break
            if char == "\n":
                raise LexError("Unterminated string literal", line, column)
            value.append(char)
            self._advance()
        return Token(TokenType.STRING, "".join(value), line, column)

    def _read_identifier(self) -> Token:
        line, column = self.line, self.column
        value = []
        while self.pos < len(self.source) and (
            self.source[self.pos].isalnum() or self.source[self.pos] == "_"
        ):
            value.append(self.source[self.pos])
            self._advance()
        return Token(TokenType.IDENTIFIER, "".join(value), line, column)

    def _read_int(self) -> Token:
        line, column = self.line, self.column
        value = []
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            value.append(self.source[self.pos])
            self._advance()
        return Token(TokenType.INT, "".join(value), line, column)

    def _skip_whitespace(self):
        while self.pos < len(self.source) and self.source[self.pos].isspace():
            self._advance()

    def _advance(self):
        if self.source[self.pos] == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1
