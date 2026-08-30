import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from nodes.nodes import (
    Assignment,
    BinaryOp,
    IfStatement,
    InputCall,
    IntLiteral,
    PrintStatement,
    StringLiteral,
    VarDecl,
)
from lexer.lexer import Lexer
from parser.parser import Parser
from utils.errors import ParseError


def test_parses_print_statement():
    tokens = Lexer('print("Hello, World!");').tokenize()
    program = Parser(tokens).parse()

    assert len(program.statements) == 1
    statement = program.statements[0]
    assert isinstance(statement, PrintStatement)
    assert isinstance(statement.argument, StringLiteral)
    assert statement.argument.value == "Hello, World!"


def test_parses_str_var_decl():
    tokens = Lexer('var EXAMPLE: str = "Hello";').tokenize()
    program = Parser(tokens).parse()

    statement = program.statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.name == "EXAMPLE"
    assert statement.type_name == "str"
    assert isinstance(statement.value, StringLiteral)
    assert statement.value.value == "Hello"


def test_parses_int_var_decl():
    tokens = Lexer("var COUNT: int = 9;").tokenize()
    program = Parser(tokens).parse()

    statement = program.statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.name == "COUNT"
    assert statement.type_name == "int"
    assert isinstance(statement.value, IntLiteral)
    assert statement.value.value == 9


def test_rejects_mismatched_var_type():
    tokens = Lexer('var COUNT: int = "nope";').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_parses_var_decl_without_value():
    tokens = Lexer("var bob: str;").tokenize()
    program = Parser(tokens).parse()

    statement = program.statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.name == "bob"
    assert statement.type_name == "str"
    assert statement.value is None


def test_parses_assignment_with_input_call():
    tokens = Lexer('var bob: str;\nbob = input("MESSAGE");').tokenize()
    program = Parser(tokens).parse()

    assign = program.statements[1]
    assert isinstance(assign, Assignment)
    assert assign.name == "bob"
    assert isinstance(assign.value, InputCall)
    assert assign.value.prompt.value == "MESSAGE"


def test_rejects_assignment_to_undeclared_variable():
    tokens = Lexer('undeclared = "x";').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_input_assigned_to_int_variable():
    tokens = Lexer('var n: int;\nn = input("x");').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_parses_if_statement():
    tokens = Lexer('var bob: str = "Hi";\nif (bob == "Hi") {\nprint(bob);\n}').tokenize()
    program = Parser(tokens).parse()

    if_stmt = program.statements[1]
    assert isinstance(if_stmt, IfStatement)
    assert isinstance(if_stmt.condition, BinaryOp)
    assert if_stmt.condition.operator == "=="
    assert len(if_stmt.body) == 1
    assert isinstance(if_stmt.body[0], PrintStatement)


def test_rejects_unterminated_if_block():
    tokens = Lexer('var x: int = 1;\nif (x == 1) {\nprint(x);\n').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_parses_if_elseif_else_chain():
    source = (
        'var bob: str = "Hello";\n'
        'if (bob == "Hi") {}\n'
        'elseif (bob == "Hello") {\n'
        "print(bob);\n"
        "}\n"
        "else {}\n"
    )
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    if_stmt = program.statements[1]
    assert isinstance(if_stmt, IfStatement)
    assert len(if_stmt.elif_branches) == 1
    elif_condition, elif_body = if_stmt.elif_branches[0]
    assert isinstance(elif_condition, BinaryOp)
    assert len(elif_body) == 1
    assert if_stmt.else_body == []


def test_parses_if_with_trailing_semicolons():
    source = (
        'var bob: str = "Hi";\n'
        'if (bob == "Hi") {};\n'
        'elseif (bob == "Hello") {};\n'
        "else {};\n"
    )
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    if_stmt = program.statements[1]
    assert isinstance(if_stmt, IfStatement)
    assert len(if_stmt.elif_branches) == 1
    assert if_stmt.else_body == []


def test_parses_if_without_elseif_or_else():
    tokens = Lexer('var bob: str = "Hi";\nif (bob == "Hi") {}\n').tokenize()
    program = Parser(tokens).parse()

    if_stmt = program.statements[1]
    assert if_stmt.elif_branches == []
    assert if_stmt.else_body is None


def test_parses_compound_assignment():
    tokens = Lexer("var bob: int = 10;\nbob += 3;").tokenize()
    program = Parser(tokens).parse()

    assign = program.statements[1]
    assert isinstance(assign, Assignment)
    assert assign.name == "bob"
    assert isinstance(assign.value, BinaryOp)
    assert assign.value.operator == "+"
    assert isinstance(assign.value.left, Identifier)
    assert assign.value.left.name == "bob"
    assert isinstance(assign.value.right, IntLiteral)
    assert assign.value.right.value == 3


def test_parses_all_compound_operators():
    source = "var bob: int = 10;\nbob += 3;\nbob -= 3;\nbob *= 3;\nbob /= 3;\n"
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    operators = [stmt.value.operator for stmt in program.statements[1:]]
    assert operators == ["+", "-", "*", "/"]


def test_parses_compound_assignment_with_identifier_rhs():
    tokens = Lexer("var a: int = 5;\nvar b: int = 3;\na += b;").tokenize()
    program = Parser(tokens).parse()

    assign = program.statements[2]
    assert isinstance(assign.value, BinaryOp)
    assert isinstance(assign.value.right, Identifier)
    assert assign.value.right.name == "b"


def test_rejects_compound_assignment_to_undeclared_variable():
    tokens = Lexer("x += 1;").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_compound_assignment_on_str_variable():
    tokens = Lexer('var s: str = "hi";\ns += 1;').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_compound_assignment_with_str_rhs():
    tokens = Lexer('var n: int = 1;\nn += "x";').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()
