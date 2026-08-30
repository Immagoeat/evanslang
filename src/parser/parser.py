from nodes.nodes import (
    Assignment,
    BinaryOp,
    BoolLiteral,
    FloatLiteral,
    Identifier,
    IfStatement,
    InputCall,
    IntLiteral,
    PrintStatement,
    Program,
    StringLiteral,
    UnaryOp,
    VarDecl,
)
from lexer.token import Token, TokenType
from utils.errors import ParseError

VALID_TYPES = {"int", "str", "float", "bool"}

COMPOUND_OPERATORS = {
    TokenType.PLUS_EQUALS: "+",
    TokenType.MINUS_EQUALS: "-",
    TokenType.STAR_EQUALS: "*",
    TokenType.SLASH_EQUALS: "/",
}

COMPARISON_OPERATORS = {
    TokenType.EQUALS_EQUALS: "==",
    TokenType.NOT_EQUALS: "!=",
    TokenType.LESS: "<",
    TokenType.LESS_EQUALS: "<=",
    TokenType.GREATER: ">",
    TokenType.GREATER_EQUALS: ">=",
}


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
        if token.type == TokenType.IDENTIFIER and token.value == "if":
            return self._parse_if_statement()
        if token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.EQUALS:
            return self._parse_assignment()
        if token.type == TokenType.IDENTIFIER and self._peek(1).type in COMPOUND_OPERATORS:
            return self._parse_compound_assignment()
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

    def _parse_if_statement(self) -> IfStatement:
        self._expect(TokenType.IDENTIFIER, "if")
        self._expect(TokenType.LPAREN)
        condition = self._parse_expression()
        self._expect(TokenType.RPAREN)
        body = self._parse_block()
        self._skip_optional_semicolon()

        elif_branches: list[tuple] = []
        while (
            self._peek().type == TokenType.IDENTIFIER
            and self._peek().value == "elseif"
        ):
            self._advance()
            self._expect(TokenType.LPAREN)
            elif_condition = self._parse_expression()
            self._expect(TokenType.RPAREN)
            elif_body = self._parse_block()
            self._skip_optional_semicolon()
            elif_branches.append((elif_condition, elif_body))

        else_body = None
        if self._peek().type == TokenType.IDENTIFIER and self._peek().value == "else":
            self._advance()
            else_body = self._parse_block()
            self._skip_optional_semicolon()

        return IfStatement(condition, body, elif_branches, else_body)

    def _parse_block(self) -> list:
        self._expect(TokenType.LBRACE)
        statements = []
        while self._peek().type != TokenType.RBRACE:
            if self._peek().type == TokenType.EOF:
                raise ParseError(
                    "Unterminated block, expected '}'",
                    self._peek().line,
                    self._peek().column,
                )
            statements.append(self._parse_statement())
        self._expect(TokenType.RBRACE)
        return statements

    def _skip_optional_semicolon(self) -> None:
        if self._peek().type == TokenType.SEMICOLON:
            self._advance()

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

    def _parse_compound_assignment(self) -> Assignment:
        name_token = self._expect(TokenType.IDENTIFIER)
        op_token = self._advance()
        operator = COMPOUND_OPERATORS[op_token.type]
        rhs = self._parse_expression()
        self._expect(TokenType.SEMICOLON)

        declared_type = self.declared_types.get(name_token.value)
        if declared_type is None:
            raise ParseError(
                f"Assignment to undeclared variable {name_token.value!r}",
                name_token.line,
                name_token.column,
            )
        if declared_type not in ("int", "float"):
            raise ParseError(
                f"Cannot use {op_token.value!r} on non-numeric variable {name_token.value!r}",
                name_token.line,
                name_token.column,
            )

        literal_types = {"int": IntLiteral, "float": FloatLiteral}
        if isinstance(rhs, literal_types[declared_type]):
            pass
        elif isinstance(rhs, Identifier):
            rhs_type = self.declared_types.get(rhs.name)
            if rhs_type != declared_type:
                raise ParseError(
                    f"Cannot use {op_token.value!r} with {rhs_type or 'undeclared'} variable {rhs.name!r} on {declared_type!r} variable {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
        else:
            raise ParseError(
                f"Cannot use {op_token.value!r} with a non-{declared_type} value",
                name_token.line,
                name_token.column,
            )

        value = BinaryOp(operator, Identifier(name_token.value), rhs)
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
        if type_name == "float" and not isinstance(value, FloatLiteral):
            raise ParseError(
                f"Cannot assign non-float value to 'float' variable {name_token.value!r}",
                name_token.line,
                name_token.column,
            )
        if type_name == "bool" and not isinstance(value, BoolLiteral):
            raise ParseError(
                f"Cannot assign non-bool value to 'bool' variable {name_token.value!r}",
                name_token.line,
                name_token.column,
            )

    def _parse_expression(self):
        return self._parse_or()

    def _parse_or(self):
        left = self._parse_and()
        while self._peek().type == TokenType.OR_OR:
            self._advance()
            right = self._parse_and()
            left = BinaryOp("||", left, right)
        return left

    def _parse_and(self):
        left = self._parse_unary_not()
        while self._peek().type == TokenType.AND_AND:
            self._advance()
            right = self._parse_unary_not()
            left = BinaryOp("&&", left, right)
        return left

    def _parse_unary_not(self):
        if self._peek().type == TokenType.BANG:
            self._advance()
            operand = self._parse_unary_not()
            return UnaryOp("!", operand)
        return self._parse_comparison()

    def _parse_comparison(self):
        left = self._parse_primary()
        if self._peek().type in COMPARISON_OPERATORS:
            operator = COMPARISON_OPERATORS[self._peek().type]
            self._advance()
            right = self._parse_primary()
            return BinaryOp(operator, left, right)
        return left

    def _parse_primary(self):
        token = self._peek()
        if token.type == TokenType.STRING:
            self._advance()
            return StringLiteral(token.value)
        if token.type == TokenType.INT:
            self._advance()
            return IntLiteral(int(token.value))
        if token.type == TokenType.FLOAT:
            self._advance()
            return FloatLiteral(float(token.value))
        if token.type == TokenType.IDENTIFIER and token.value == "input":
            return self._parse_input_call()
        if token.type == TokenType.IDENTIFIER and token.value == "true":
            self._advance()
            return BoolLiteral(True)
        if token.type == TokenType.IDENTIFIER and token.value == "false":
            self._advance()
            return BoolLiteral(False)
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
