from nodes.nodes import (
    Identifier,
    IntLiteral,
    PrintStatement,
    Program,
    StringLiteral,
    VarDecl,
)
from lexer.token import Token, TokenType
from utils.errors import ParseError

VALID_TYPES = {"int", "str"}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> Program:
        statements = []
        while self._peek().type != TokenType.EOF:
            statements.append(self._parse_statement())
        return Program(statements)

    def _parse_statement(self):
        token = self._peek()
        if token.type == TokenType.IDENTIFIER and token.value == "print":
            return self._parse_print_statement()
        if token.type == TokenType.IDENTIFIER and token.value == "var":
            return self._parse_var_decl()
        raise ParseError(
            f"Unexpected token {token.value!r}", token.line, token.column
        )

    def _parse_print_statement(self) -> PrintStatement:
        self._expect(TokenType.IDENTIFIER, "print")
        self._expect(TokenType.LPAREN)
        argument = self._parse_expression()
        self._expect(TokenType.RPAREN)
        self._expect(TokenType.SEMICOLON)
        return PrintStatement(argument)

    def _parse_var_decl(self) -> VarDecl:
        self._expect(TokenType.IDENTIFIER, "var")
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        type_token = self._expect(TokenType.IDENTIFIER)
        if type_token.value not in VALID_TYPES:
            raise ParseError(
                f"Unknown type {type_token.value!r}",
                type_token.line,
                type_token.column,
            )
        self._expect(TokenType.EQUALS)
        value = self._parse_expression()
        self._expect(TokenType.SEMICOLON)

        if type_token.value == "str" and not isinstance(value, StringLiteral):
            raise ParseError(
                f"Cannot assign non-string value to 'str' variable {name_token.value!r}",
                type_token.line,
                type_token.column,
            )
        if type_token.value == "int" and not isinstance(value, IntLiteral):
            raise ParseError(
                f"Cannot assign non-int value to 'int' variable {name_token.value!r}",
                type_token.line,
                type_token.column,
            )

        return VarDecl(name_token.value, type_token.value, value)

    def _parse_expression(self):
        token = self._peek()
        if token.type == TokenType.STRING:
            self._advance()
            return StringLiteral(token.value)
        if token.type == TokenType.INT:
            self._advance()
            return IntLiteral(int(token.value))
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            return Identifier(token.value)
        raise ParseError(
            f"Expected an expression but got {token.value!r}",
            token.line,
            token.column,
        )

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def _expect(self, type: TokenType, value: str | None = None) -> Token:
        token = self._peek()
        if token.type != type or (value is not None and token.value != value):
            expected = value if value is not None else type.name
            raise ParseError(
                f"Expected {expected!r} but got {token.value!r}",
                token.line,
                token.column,
            )
        return self._advance()
