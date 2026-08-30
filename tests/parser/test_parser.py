import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from nodes.nodes import (
    Assignment,
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
