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

        if char == "{":
            self._advance()
            return Token(TokenType.LBRACE, "{", line, column)

        if char == "}":
            self._advance()
            return Token(TokenType.RBRACE, "}", line, column)

        if char == ";":
            self._advance()
            return Token(TokenType.SEMICOLON, ";", line, column)

        if char == ":":
            self._advance()
            return Token(TokenType.COLON, ":", line, column)

        if char == ".":
            self._advance()
            return Token(TokenType.DOT, ".", line, column)

        if char == "@":
            self._advance()
            return Token(TokenType.AT, "@", line, column)

        if char == "=":
            self._advance()
            if self.pos < len(self.source) and self.source[self.pos] == "=":
                self._advance()
                return Token(TokenType.EQUALS_EQUALS, "==", line, column)
            return Token(TokenType.EQUALS, "=", line, column)

        if char == "!":
            self._advance()
            if self.pos < len(self.source) and self.source[self.pos] == "=":
                self._advance()
                return Token(TokenType.NOT_EQUALS, "!=", line, column)
            return Token(TokenType.BANG, "!", line, column)

        if char == "<":
            self._advance()
            if self.pos < len(self.source) and self.source[self.pos] == "=":
                self._advance()
                return Token(TokenType.LESS_EQUALS, "<=", line, column)
            return Token(TokenType.LESS, "<", line, column)

        if char == ">":
            self._advance()
            if self.pos < len(self.source) and self.source[self.pos] == "=":
                self._advance()
                return Token(TokenType.GREATER_EQUALS, ">=", line, column)
            return Token(TokenType.GREATER, ">", line, column)

        if char == "&" and self._peek_char(1) == "&":
            self._advance()
            self._advance()
            return Token(TokenType.AND_AND, "&&", line, column)

        if char == "|" and self._peek_char(1) == "|":
            self._advance()
            self._advance()
            return Token(TokenType.OR_OR, "||", line, column)

        if char == "+" and self._peek_char(1) == "=":
            self._advance()
            self._advance()
            return Token(TokenType.PLUS_EQUALS, "+=", line, column)

        if char == "-" and self._peek_char(1) == "=":
            self._advance()
            self._advance()
            return Token(TokenType.MINUS_EQUALS, "-=", line, column)

        if char == "-" and self._peek_char(1) == ">":
            self._advance()
            self._advance()
            return Token(TokenType.ARROW, "->", line, column)

        if char == "*" and self._peek_char(1) == "=":
            self._advance()
            self._advance()
            return Token(TokenType.STAR_EQUALS, "*=", line, column)

        if char == "/" and self._peek_char(1) == "=":
            self._advance()
            self._advance()
            return Token(TokenType.SLASH_EQUALS, "/=", line, column)

        if char == "+":
            self._advance()
            return Token(TokenType.PLUS, "+", line, column)

        if char == "-":
            self._advance()
            return Token(TokenType.MINUS, "-", line, column)

        if char == "*":
            self._advance()
            return Token(TokenType.STAR, "*", line, column)

        if char == "/":
            self._advance()
            return Token(TokenType.SLASH, "/", line, column)

        if char == '"':
            return self._read_string()

        if char.isalpha() or char == "_":
            return self._read_identifier()

        if char.isdigit():
            return self._read_number()

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

    def _read_number(self) -> Token:
        line, column = self.line, self.column
        value = []
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            value.append(self.source[self.pos])
            self._advance()

        if self.source[self.pos : self.pos + 1] == "." and (
            self._peek_char(1) is not None and self._peek_char(1).isdigit()
        ):
            value.append(self.source[self.pos])
            self._advance()
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                value.append(self.source[self.pos])
                self._advance()
            return Token(TokenType.FLOAT, "".join(value), line, column)

        return Token(TokenType.INT, "".join(value), line, column)

    def _peek_char(self, offset: int) -> str | None:
        index = self.pos + offset
        if index < len(self.source):
            return self.source[index]
        return None

    def _skip_whitespace(self):
        while self.pos < len(self.source):
            if self.source[self.pos].isspace():
                self._advance()
            elif self.source[self.pos] == "#":
                self._skip_comment()
            else:
                break

    def _skip_comment(self):
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            self._advance()

    def _advance(self):
        if self.source[self.pos] == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1
