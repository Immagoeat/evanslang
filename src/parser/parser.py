from nodes.nodes import (
    Assignment,
    Identifier,
    InputCall,
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
        self.declared_types: dict[str, str] = {}

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
        if token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.EQUALS:
            return self._parse_assignment()
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

        self.declared_types[name_token.value] = type_token.value

        if self._peek().type == TokenType.SEMICOLON:
            self._advance()
            return VarDecl(name_token.value, type_token.value, None)

        self._expect(TokenType.EQUALS)
        value = self._parse_expression()
        self._expect(TokenType.SEMICOLON)
        self._check_type(name_token, type_token.value, value)

        return VarDecl(name_token.value, type_token.value, value)

    def _parse_assignment(self) -> Assignment:
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.EQUALS)
        value = self._parse_expression()
        self._expect(TokenType.SEMICOLON)

        declared_type = self.declared_types.get(name_token.value)
        if declared_type is None:
            raise ParseError(
                f"Assignment to undeclared variable {name_token.value!r}",
                name_token.line,
                name_token.column,
            )
        self._check_type(name_token, declared_type, value)

        return Assignment(name_token.value, value)

    def _check_type(self, name_token: Token, type_name: str, value) -> None:
        if type_name == "str" and not isinstance(value, (StringLiteral, InputCall)):
            raise ParseError(
                f"Cannot assign non-string value to 'str' variable {name_token.value!r}",
                name_token.line,
                name_token.column,
            )
        if type_name == "int" and not isinstance(value, IntLiteral):
            raise ParseError(
                f"Cannot assign non-int value to 'int' variable {name_token.value!r}",
                name_token.line,
                name_token.column,
            )

    def _parse_expression(self):
        token = self._peek()
        if token.type == TokenType.STRING:
            self._advance()
            return StringLiteral(token.value)
        if token.type == TokenType.INT:
            self._advance()
            return IntLiteral(int(token.value))
        if token.type == TokenType.IDENTIFIER and token.value == "input":
            return self._parse_input_call()
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            return Identifier(token.value)
        raise ParseError(
            f"Expected an expression but got {token.value!r}",
            token.line,
            token.column,
        )

    def _parse_input_call(self) -> InputCall:
        self._expect(TokenType.IDENTIFIER, "input")
        self._expect(TokenType.LPAREN)
        prompt_token = self._expect(TokenType.STRING)
        self._expect(TokenType.RPAREN)
        return InputCall(StringLiteral(prompt_token.value))

    def _peek(self, offset: int = 0) -> Token:
        index = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[index]

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
