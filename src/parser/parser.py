from nodes.nodes import (
    AddressOf,
    AppendCall,
    AsciiStatement,
    Assignment,
    BinaryOp,
    BoolLiteral,
    CallStatement,
    ClassDecl,
    Dereference,
    DerefAssignment,
    ExpressionStatement,
    FloatLiteral,
    ForStatement,
    Identifier,
    IfStatement,
    IndexAssignment,
    IndexExpr,
    InputCall,
    IntLiteral,
    LengthCall,
    ListDecl,
    ListLiteral,
    Mention,
    ParseCall,
    PrintStatement,
    Program,
    StringLiteral,
    ThrowStatement,
    TryStatement,
    UnaryOp,
    VarDecl,
    WhileStatement,
)
from lexer.token import Token, TokenType
from utils.errors import ParseError

VALID_TYPES = {"int", "str", "float", "bool"}
POINTABLE_TYPES = {"int", "str", "float", "bool"}
LIST_ELEMENT_TYPES = {"int", "str", "float", "bool"}
RESERVED_CLASS_NAMES = {"main", "init"}
LITERAL_TYPES_BY_NAME = {
    "int": IntLiteral,
    "str": StringLiteral,
    "float": FloatLiteral,
    "bool": BoolLiteral,
}

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
        # Separate from declared_types (which stores "list"/"list<int>" as
        # a single string like every other type) because .append(...)/
        # list[i] = ...; need just the element type name on its own to
        # look up LITERAL_TYPES_BY_NAME - None here means an untyped list.
        self.list_element_types: dict[str, str | None] = {}
        self.class_names: set[str] = set()
        self.mention_aliases: set[str] = set()

    def parse(self) -> Program:
        self._prescan_names()

        mentions: list[Mention] = []
        while self._peek().type == TokenType.AT:
            mentions.append(self._parse_mention())

        classes: dict[str, ClassDecl] = {}
        while self._peek().type != TokenType.EOF:
            class_decl = self._parse_class()
            if class_decl.name in classes:
                raise ParseError(
                    f"Class {class_decl.name!r} is already defined",
                    self._peek().line,
                    self._peek().column,
                )
            classes[class_decl.name] = class_decl

        if not classes and not mentions:
            raise ParseError(
                "Empty file: expected at least one 'class' declaration",
                self._peek().line,
                self._peek().column,
            )

        return Program(classes, mentions)

    def _prescan_names(self) -> None:
        # Walk the top-level tokens once to collect every class name and
        # mention alias before real parsing begins, so a class body can
        # call another class declared later in the file (or an @mentions
        # alias declared anywhere) without a "forward reference" error.
        i = 0
        depth = 0
        while i < len(self.tokens):
            token = self.tokens[i]
            if token.type == TokenType.EOF:
                break
            if token.type == TokenType.LBRACE:
                depth += 1
            elif token.type == TokenType.RBRACE:
                depth -= 1
            elif depth == 0 and token.type == TokenType.AT:
                # @ mentions FILE(.FILE)* -> ALIAS ;
                j = i + 1
                if j < len(self.tokens) and self.tokens[j].value == "mentions":
                    j += 1
                    while (
                        j < len(self.tokens)
                        and self.tokens[j].type != TokenType.ARROW
                        and self.tokens[j].type != TokenType.EOF
                    ):
                        j += 1
                    if j < len(self.tokens) and self.tokens[j].type == TokenType.ARROW:
                        j += 1
                        if j < len(self.tokens) and self.tokens[j].type == TokenType.IDENTIFIER:
                            self.mention_aliases.add(self.tokens[j].value)
            elif (
                depth == 0
                and token.type == TokenType.IDENTIFIER
                and token.value == "class"
            ):
                if i + 1 < len(self.tokens) and self.tokens[i + 1].type == TokenType.IDENTIFIER:
                    self.class_names.add(self.tokens[i + 1].value)
            i += 1

    def _parse_mention(self) -> Mention:
        self._expect(TokenType.AT)
        self._expect(TokenType.IDENTIFIER, "mentions")
        filename = self._parse_filename()
        self._expect(TokenType.ARROW)
        alias_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.SEMICOLON)
        self.mention_aliases.add(alias_token.value)
        return Mention(filename, alias_token.value)

    def _parse_filename(self) -> str:
        parts = [self._expect(TokenType.IDENTIFIER).value]
        while self._peek().type == TokenType.DOT:
            self._advance()
            parts.append(self._expect(TokenType.IDENTIFIER).value)
        return ".".join(parts)

    def _parse_class(self) -> ClassDecl:
        self._expect(TokenType.IDENTIFIER, "class")
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.LPAREN)

        is_ment = False
        if self._peek().type == TokenType.IDENTIFIER:
            self._expect(TokenType.IDENTIFIER, "ment")
            is_ment = True

        self._expect(TokenType.RPAREN)
        body = self._parse_block()
        self._skip_optional_semicolon()

        self.class_names.add(name_token.value)
        return ClassDecl(name_token.value, is_ment, body)

    def _parse_statement(self):
        token = self._peek()
        if token.type == TokenType.IDENTIFIER and token.value == "print":
            return self._parse_print_statement()
        if token.type == TokenType.IDENTIFIER and token.value == "var":
            return self._parse_var_decl()
        if token.type == TokenType.IDENTIFIER and token.value == "list":
            return self._parse_list_decl()
        if token.type == TokenType.IDENTIFIER and token.value == "if":
            return self._parse_if_statement()
        if token.type == TokenType.IDENTIFIER and token.value == "while":
            return self._parse_while_statement()
        if token.type == TokenType.IDENTIFIER and token.value == "for":
            return self._parse_for_statement()
        if token.type == TokenType.IDENTIFIER and token.value == "try":
            return self._parse_try_statement()
        if token.type == TokenType.IDENTIFIER and token.value == "throw":
            return self._parse_throw_statement()
        if token.type == TokenType.IDENTIFIER and token.value == "ascii":
            return self._parse_ascii_statement()
        if token.type == TokenType.STAR:
            return self._parse_deref_assignment()
        if token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.EQUALS:
            return self._parse_assignment()
        if token.type == TokenType.IDENTIFIER and self._peek(1).type in COMPOUND_OPERATORS:
            return self._parse_compound_assignment()
        if token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.LBRACKET:
            return self._parse_index_assignment()
        if (
            token.type == TokenType.IDENTIFIER
            and self._peek(1).type == TokenType.DOT
            and token.value in self.mention_aliases
        ):
            return self._parse_call_statement()
        if token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.DOT:
            return self._parse_expression_statement()
        if (
            token.type == TokenType.IDENTIFIER
            and self._peek(1).type == TokenType.SEMICOLON
            and token.value in self.class_names
        ):
            return self._parse_call_statement()
        raise ParseError(
            f"Unexpected token {token.value!r}", token.line, token.column
        )

    def _parse_call_statement(self) -> CallStatement:
        first_token = self._expect(TokenType.IDENTIFIER)
        if self._peek().type == TokenType.DOT:
            self._advance()
            name_token = self._expect(TokenType.IDENTIFIER)
            self._expect(TokenType.SEMICOLON)
            return CallStatement(first_token.value, name_token.value)
        self._expect(TokenType.SEMICOLON)
        if first_token.value in RESERVED_CLASS_NAMES:
            raise ParseError(
                f"Cannot call {first_token.value!r} explicitly - it already "
                "runs automatically"
                + (" as the entry point" if first_token.value == "main" else " before main"),
                first_token.line,
                first_token.column,
            )
        return CallStatement(None, first_token.value)

    def _parse_expression_statement(self) -> ExpressionStatement:
        expression = self._parse_expression()
        self._expect(TokenType.SEMICOLON)
        return ExpressionStatement(expression)

    def _parse_print_statement(self) -> PrintStatement:
        self._expect(TokenType.IDENTIFIER, "print")
        self._expect(TokenType.LPAREN)
        argument = self._parse_expression()
        self._expect(TokenType.RPAREN)
        self._expect(TokenType.SEMICOLON)
        return PrintStatement(argument)

    def _parse_type_name(self) -> str:
        # Either a plain type (int/str/float/bool) or a pointer type
        # ptr<type>, where <type> must itself be one of POINTABLE_TYPES
        # (no pointer-to-pointer yet). Returned as a single string
        # ("int" or "ptr<int>") so it threads through declared_types the
        # same way plain types already do, without restructuring that
        # dict's value type.
        type_token = self._expect(TokenType.IDENTIFIER)
        if type_token.value == "ptr":
            self._expect(TokenType.LESS)
            inner_token = self._expect(TokenType.IDENTIFIER)
            if inner_token.value not in POINTABLE_TYPES:
                raise ParseError(
                    f"Unknown type {inner_token.value!r} in ptr<...>",
                    inner_token.line,
                    inner_token.column,
                )
            self._expect(TokenType.GREATER)
            return f"ptr<{inner_token.value}>"
        if type_token.value not in VALID_TYPES:
            raise ParseError(
                f"Unknown type {type_token.value!r}",
                type_token.line,
                type_token.column,
            )
        return type_token.value

    def _parse_var_decl(self, consume_semicolon: bool = True) -> VarDecl:
        self._expect(TokenType.IDENTIFIER, "var")
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        type_name = self._parse_type_name()

        self.declared_types[name_token.value] = type_name

        if self._peek().type == TokenType.SEMICOLON:
            if consume_semicolon:
                self._advance()
            return VarDecl(name_token.value, type_name, None)
        if not consume_semicolon and self._peek().type == TokenType.RPAREN:
            return VarDecl(name_token.value, type_name, None)

        self._expect(TokenType.EQUALS)
        value = self._parse_expression()
        if consume_semicolon:
            self._expect(TokenType.SEMICOLON)
        self._check_type(name_token, type_name, value)

        return VarDecl(name_token.value, type_name, value)

    def _parse_list_decl(self, consume_semicolon: bool = True) -> ListDecl:
        self._expect(TokenType.IDENTIFIER, "list")
        element_type: str | None = None
        if self._peek().type == TokenType.LESS:
            self._advance()
            type_token = self._expect(TokenType.IDENTIFIER)
            if type_token.value not in LIST_ELEMENT_TYPES:
                raise ParseError(
                    f"Unknown type {type_token.value!r} in list<...>",
                    type_token.line,
                    type_token.column,
                )
            self._expect(TokenType.GREATER)
            element_type = type_token.value

        name_token = self._expect(TokenType.IDENTIFIER)
        self.declared_types[name_token.value] = (
            f"list<{element_type}>" if element_type else "list"
        )
        self.list_element_types[name_token.value] = element_type

        if self._peek().type == TokenType.SEMICOLON:
            # list NAME; with no initializer - sugar for an empty list,
            # immediately usable with .append(...)/indexing, unlike a bare
            # `var NAME: type;` which has no storage until first assigned.
            if consume_semicolon:
                self._advance()
            return ListDecl(name_token.value, element_type, [])

        self._expect(TokenType.COLON)
        elements = self._parse_list_literal_elements()
        if consume_semicolon:
            self._expect(TokenType.SEMICOLON)

        if element_type is not None:
            expected_literal = LITERAL_TYPES_BY_NAME[element_type]
            for element in elements:
                if not isinstance(element, expected_literal):
                    raise ParseError(
                        f"Cannot include a non-{element_type} literal in "
                        f"list<{element_type}> {name_token.value!r}",
                        name_token.line,
                        name_token.column,
                    )

        return ListDecl(name_token.value, element_type, elements)

    def _parse_list_literal_elements(self) -> list:
        self._expect(TokenType.LBRACKET)
        elements = []
        if self._peek().type != TokenType.RBRACKET:
            elements.append(self._parse_expression())
            while self._peek().type == TokenType.COMMA:
                self._advance()
                elements.append(self._parse_expression())
        self._expect(TokenType.RBRACKET)
        return elements

    def _parse_index_assignment(self, consume_semicolon: bool = True) -> IndexAssignment:
        name_token = self._expect(TokenType.IDENTIFIER)
        self._require_list(name_token)
        self._expect(TokenType.LBRACKET)
        index = self._parse_expression()
        self._expect(TokenType.RBRACKET)
        self._expect(TokenType.EQUALS)
        value = self._parse_expression()
        if consume_semicolon:
            self._expect(TokenType.SEMICOLON)

        element_type = self.list_element_types.get(name_token.value)
        if element_type is not None:
            expected_literal = LITERAL_TYPES_BY_NAME[element_type]
            if isinstance(value, tuple(LITERAL_TYPES_BY_NAME.values())) and not isinstance(
                value, expected_literal
            ):
                raise ParseError(
                    f"Cannot assign a non-{element_type} value into "
                    f"list<{element_type}> {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )

        return IndexAssignment(Identifier(name_token.value), index, value)

    def _require_list(self, name_token: Token) -> None:
        declared = self.declared_types.get(name_token.value)
        if declared is None or not (declared == "list" or declared.startswith("list<")):
            raise ParseError(
                f"{name_token.value!r} is not a declared list "
                f"(declared {declared or 'nothing'!r})",
                name_token.line,
                name_token.column,
            )

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

    def _parse_while_statement(self) -> WhileStatement:
        self._expect(TokenType.IDENTIFIER, "while")
        self._expect(TokenType.LPAREN)
        condition = self._parse_expression()
        self._expect(TokenType.RPAREN)
        body = self._parse_block()
        self._skip_optional_semicolon()
        return WhileStatement(condition, body)

    def _parse_for_statement(self) -> ForStatement:
        self._expect(TokenType.IDENTIFIER, "for")
        self._expect(TokenType.LPAREN)

        init = None
        if self._peek().type != TokenType.SEMICOLON:
            init = self._parse_for_clause_statement()
        self._expect(TokenType.SEMICOLON)

        condition = None
        if self._peek().type != TokenType.SEMICOLON:
            condition = self._parse_expression()
        self._expect(TokenType.SEMICOLON)

        update = None
        if self._peek().type != TokenType.RPAREN:
            update = self._parse_for_clause_statement()
        self._expect(TokenType.RPAREN)

        body = self._parse_block()
        self._skip_optional_semicolon()
        return ForStatement(init, condition, update, body)

    def _parse_try_statement(self) -> TryStatement:
        self._expect(TokenType.IDENTIFIER, "try")
        try_body = self._parse_block()

        self._expect(TokenType.IDENTIFIER, "catch")
        self._expect(TokenType.LPAREN)
        catch_var_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        type_token = self._expect(TokenType.IDENTIFIER, "str")
        self._expect(TokenType.RPAREN)

        # catch (e: str) implicitly declares `e` as a str variable, visible
        # for the rest of the catch block - the same as any other `var`.
        self.declared_types[catch_var_token.value] = type_token.value
        catch_body = self._parse_block()
        self._skip_optional_semicolon()

        return TryStatement(try_body, catch_var_token.value, catch_body)

    def _parse_throw_statement(self) -> ThrowStatement:
        self._expect(TokenType.IDENTIFIER, "throw")
        expression = self._parse_expression()
        self._expect(TokenType.SEMICOLON)
        return ThrowStatement(expression)

    def _parse_ascii_statement(self) -> AsciiStatement:
        self._expect(TokenType.IDENTIFIER, "ascii")
        path = self._parse_expression()
        self._expect(TokenType.SEMICOLON)
        return AsciiStatement(path)

    def _parse_for_clause_statement(self):
        # The init/update clauses of a for-header are statements without
        # their own trailing ';' (the header's own ';'/')' delimits them
        # instead), so these reuse the normal statement parsers with
        # consume_semicolon=False.
        token = self._peek()
        if token.type == TokenType.IDENTIFIER and token.value == "var":
            return self._parse_var_decl(consume_semicolon=False)
        if token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.EQUALS:
            return self._parse_assignment(consume_semicolon=False)
        if token.type == TokenType.IDENTIFIER and self._peek(1).type in COMPOUND_OPERATORS:
            return self._parse_compound_assignment(consume_semicolon=False)
        raise ParseError(
            f"Expected a variable declaration or assignment in for(...) but got {token.value!r}",
            token.line,
            token.column,
        )

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

    def _parse_assignment(self, consume_semicolon: bool = True) -> Assignment:
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.EQUALS)
        value = self._parse_expression()
        if consume_semicolon:
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

    def _parse_deref_assignment(self, consume_semicolon: bool = True) -> DerefAssignment:
        self._expect(TokenType.STAR)
        pointer_token = self._expect(TokenType.IDENTIFIER)
        pointer = Identifier(pointer_token.value)
        self._expect(TokenType.EQUALS)
        value = self._parse_expression()
        if consume_semicolon:
            self._expect(TokenType.SEMICOLON)

        pointer_type = self.declared_types.get(pointer_token.value)
        if pointer_type is None:
            raise ParseError(
                f"Assignment through undeclared variable {pointer_token.value!r}",
                pointer_token.line,
                pointer_token.column,
            )
        if not pointer_type.startswith("ptr<"):
            raise ParseError(
                f"Cannot dereference non-pointer variable {pointer_token.value!r} "
                f"(declared {pointer_type!r})",
                pointer_token.line,
                pointer_token.column,
            )
        pointee_type = pointer_type[len("ptr<") : -1]
        # Reuse a synthetic Token so _check_type's error messages read
        # naturally ("variable 'p'" -> what's actually being written
        # through is p's pointee, so name the pointer for context).
        self._check_type(pointer_token, pointee_type, value)

        return DerefAssignment(pointer, value)

    def _parse_compound_assignment(self, consume_semicolon: bool = True) -> Assignment:
        name_token = self._expect(TokenType.IDENTIFIER)
        op_token = self._advance()
        operator = COMPOUND_OPERATORS[op_token.type]
        rhs = self._parse_expression()
        if consume_semicolon:
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
        arithmetic_ops = ("+", "-", "*", "/")
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
        elif isinstance(rhs, BinaryOp) and rhs.operator in arithmetic_ops:
            pass  # runtime-checked, same as general arithmetic elsewhere
        elif isinstance(rhs, UnaryOp) and rhs.operator == "-":
            pass  # runtime-checked
        else:
            raise ParseError(
                f"Cannot use {op_token.value!r} with a non-{declared_type} value",
                name_token.line,
                name_token.column,
            )

        value = BinaryOp(operator, Identifier(name_token.value), rhs)
        return Assignment(name_token.value, value)

    def _check_type(self, name_token: Token, type_name: str, value) -> None:
        if isinstance(value, AddressOf):
            if not type_name.startswith("ptr<"):
                raise ParseError(
                    f"Cannot assign a pointer to {type_name!r} variable "
                    f"{name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
            pointee_type = type_name[len("ptr<") : -1]
            target_type = self.declared_types.get(value.name)
            if target_type != pointee_type:
                raise ParseError(
                    f"Cannot assign &{value.name} ({target_type or 'undeclared'}) "
                    f"to {type_name!r} variable {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
            return
        if isinstance(value, ParseCall):
            if value.target_type != type_name:
                raise ParseError(
                    f"Cannot assign .parse({value.target_type}) to "
                    f"{type_name!r} variable {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
            return
        # Arithmetic expressions (+, -, *, /) and unary minus aren't
        # statically type-checked - the parser doesn't trace through
        # arbitrary expression trees to infer a type, since evanslang
        # variables can hold either int or float and both support every
        # arithmetic operator. Assigning the result of arithmetic to a
        # non-numeric ('str'/'bool') variable is still rejected here;
        # whether the actual runtime values behave (e.g. int vs float
        # mismatches) is checked when the expression actually runs,
        # matching how comparisons (==, <, etc) are already runtime-only.
        if isinstance(value, BinaryOp) and value.operator in ("+", "-", "*", "/"):
            if type_name not in ("int", "float"):
                raise ParseError(
                    f"Cannot assign an arithmetic expression to "
                    f"{type_name!r} variable {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
            return
        if isinstance(value, UnaryOp) and value.operator == "-":
            if type_name not in ("int", "float"):
                raise ParseError(
                    f"Cannot assign an arithmetic expression to "
                    f"{type_name!r} variable {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
            return
        # Comparisons and boolean combinators always produce a bool at
        # runtime regardless of their operands' types, so (like arithmetic
        # above) these are only checked for the *target* being 'bool' -
        # operand compatibility is a runtime concern (matches how bare
        # comparisons outside of var decls have always behaved).
        boolean_ops = ("==", "!=", "<", "<=", ">", ">=", "&&", "||")
        if isinstance(value, BinaryOp) and value.operator in boolean_ops:
            if type_name != "bool":
                raise ParseError(
                    f"Cannot assign a boolean expression to "
                    f"{type_name!r} variable {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
            return
        if isinstance(value, UnaryOp) and value.operator == "!":
            if type_name != "bool":
                raise ParseError(
                    f"Cannot assign a boolean expression to "
                    f"{type_name!r} variable {name_token.value!r}",
                    name_token.line,
                    name_token.column,
                )
            return
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
        if type_name.startswith("ptr<"):
            # Reachable only when value wasn't an AddressOf (handled, with
            # its own return, above) - so anything getting here is not a
            # pointer expression at all.
            raise ParseError(
                f"Cannot assign a non-pointer value to {type_name!r} "
                f"variable {name_token.value!r}",
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
        left = self._parse_additive()
        if self._peek().type in COMPARISON_OPERATORS:
            operator = COMPARISON_OPERATORS[self._peek().type]
            self._advance()
            right = self._parse_additive()
            return BinaryOp(operator, left, right)
        return left

    def _parse_additive(self):
        left = self._parse_multiplicative()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            operator = "+" if self._peek().type == TokenType.PLUS else "-"
            self._advance()
            right = self._parse_multiplicative()
            left = BinaryOp(operator, left, right)
        return left

    def _parse_multiplicative(self):
        left = self._parse_unary_minus()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH):
            operator = "*" if self._peek().type == TokenType.STAR else "/"
            self._advance()
            right = self._parse_unary_minus()
            left = BinaryOp(operator, left, right)
        return left

    def _parse_unary_minus(self):
        if self._peek().type == TokenType.MINUS:
            self._advance()
            operand = self._parse_unary_minus()
            return UnaryOp("-", operand)
        if self._peek().type == TokenType.STAR:
            # Unambiguous with multiplication: '*' as multiplication is
            # only ever consumed one level up, in _parse_multiplicative's
            # infix loop, so a STAR reaching here is always a prefix
            # dereference (e.g. "*p" or "*p + 1").
            self._advance()
            operand = self._parse_unary_minus()
            return Dereference(operand)
        if self._peek().type == TokenType.AMPERSAND:
            self._advance()
            name_token = self._expect(TokenType.IDENTIFIER)
            return AddressOf(name_token.value)
        return self._parse_primary()

    def _parse_primary(self):
        token = self._peek()
        if token.type == TokenType.LPAREN:
            self._advance()
            expression = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expression
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
            target = Identifier(token.value)
            if self._peek().type == TokenType.LBRACKET:
                self._require_list(token)
                self._advance()
                index = self._parse_expression()
                self._expect(TokenType.RBRACKET)
                return IndexExpr(target, index)
            if self._peek().type == TokenType.DOT:
                self._advance()
                method_token = self._expect(TokenType.IDENTIFIER)
                if method_token.value == "parse":
                    source_type = self.declared_types.get(target.name)
                    if source_type != "str":
                        raise ParseError(
                            f"Cannot call .parse on {source_type or 'undeclared'} variable {target.name!r} (expected 'str')",
                            token.line,
                            token.column,
                        )
                    self._expect(TokenType.LPAREN)
                    type_token = self._expect(TokenType.IDENTIFIER)
                    if type_token.value not in VALID_TYPES:
                        raise ParseError(
                            f"Unknown type {type_token.value!r} in .parse(...)",
                            type_token.line,
                            type_token.column,
                        )
                    self._expect(TokenType.RPAREN)
                    return ParseCall(target, type_token.value)
                if method_token.value == "append":
                    self._require_list(token)
                    self._expect(TokenType.LPAREN)
                    value = self._parse_expression()
                    self._expect(TokenType.RPAREN)
                    element_type = self.list_element_types.get(target.name)
                    if element_type is not None:
                        expected_literal = LITERAL_TYPES_BY_NAME[element_type]
                        if isinstance(
                            value, tuple(LITERAL_TYPES_BY_NAME.values())
                        ) and not isinstance(value, expected_literal):
                            raise ParseError(
                                f"Cannot append a non-{element_type} value to "
                                f"list<{element_type}> {target.name!r}",
                                token.line,
                                token.column,
                            )
                    return AppendCall(target, value)
                if method_token.value == "length":
                    self._require_list(token)
                    self._expect(TokenType.LPAREN)
                    self._expect(TokenType.RPAREN)
                    return LengthCall(target)
                raise ParseError(
                    f"Unknown method {method_token.value!r}",
                    method_token.line,
                    method_token.column,
                )
            return target
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
