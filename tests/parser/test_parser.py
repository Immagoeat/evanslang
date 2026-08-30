import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from nodes.nodes import (
    Assignment,
    BinaryOp,
    BoolLiteral,
    ExpressionStatement,
    FloatLiteral,
    Identifier,
    IfStatement,
    InputCall,
    IntLiteral,
    ParseCall,
    PrintStatement,
    StringLiteral,
    UnaryOp,
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


def test_parses_all_comparison_operators():
    tokens = Lexer("a != b").tokenize()
    expr = Parser(tokens)._parse_expression()
    assert isinstance(expr, BinaryOp) and expr.operator == "!="

    for source, op in [("a < b", "<"), ("a <= b", "<="), ("a > b", ">"), ("a >= b", ">=")]:
        tokens = Lexer(source).tokenize()
        expr = Parser(tokens)._parse_expression()
        assert isinstance(expr, BinaryOp) and expr.operator == op


def test_parses_and_or_with_correct_precedence():
    tokens = Lexer("a == b && c == d || e == f").tokenize()
    expr = Parser(tokens)._parse_expression()

    # || is lowest precedence, so the top node is the ||
    assert isinstance(expr, BinaryOp) and expr.operator == "||"
    assert isinstance(expr.left, BinaryOp) and expr.left.operator == "&&"
    assert isinstance(expr.right, BinaryOp) and expr.right.operator == "=="


def test_parses_not_operator():
    tokens = Lexer("!a == b").tokenize()
    expr = Parser(tokens)._parse_expression()

    assert isinstance(expr, UnaryOp) and expr.operator == "!"
    assert isinstance(expr.operand, BinaryOp) and expr.operand.operator == "=="


def test_parses_not_on_identifier():
    tokens = Lexer("!flag").tokenize()
    expr = Parser(tokens)._parse_expression()

    assert isinstance(expr, UnaryOp)
    assert isinstance(expr.operand, Identifier)
    assert expr.operand.name == "flag"


def test_parses_float_var_decl():
    tokens = Lexer("var pi: float = 3.14;").tokenize()
    program = Parser(tokens).parse()

    statement = program.statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.type_name == "float"
    assert isinstance(statement.value, FloatLiteral)
    assert statement.value.value == 3.14


def test_parses_bool_var_decl_true_and_false():
    tokens = Lexer("var flag: bool = true;\nvar other: bool = false;").tokenize()
    program = Parser(tokens).parse()

    flag_decl, other_decl = program.statements
    assert isinstance(flag_decl.value, BoolLiteral) and flag_decl.value.value is True
    assert isinstance(other_decl.value, BoolLiteral) and other_decl.value.value is False


def test_rejects_int_literal_for_float_variable():
    tokens = Lexer("var f: float = 5;").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_float_literal_for_int_variable():
    tokens = Lexer("var n: int = 5.0;").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_non_bool_for_bool_variable():
    tokens = Lexer('var b: bool = "x";').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_parses_compound_assignment_on_float_variable():
    tokens = Lexer("var f: float = 1.0;\nf += 2.5;").tokenize()
    program = Parser(tokens).parse()

    assign = program.statements[1]
    assert isinstance(assign, Assignment)
    assert isinstance(assign.value, BinaryOp) and assign.value.operator == "+"
    assert isinstance(assign.value.right, FloatLiteral)
    assert assign.value.right.value == 2.5


def test_rejects_int_literal_in_float_compound_assignment():
    tokens = Lexer("var f: float = 1.0;\nf += 2;").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_mixing_int_and_float_variables_in_compound_assignment():
    tokens = Lexer("var f: float = 1.0;\nvar n: int = 2;\nf += n;").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_parses_dot_parse_in_var_decl():
    tokens = Lexer('var bob: str = "42";\nvar n: int = bob.parse;').tokenize()
    program = Parser(tokens).parse()

    decl = program.statements[1]
    assert isinstance(decl, VarDecl)
    assert decl.type_name == "int"
    assert isinstance(decl.value, ParseCall)
    assert isinstance(decl.value.target, Identifier)
    assert decl.value.target.name == "bob"


def test_parses_dot_parse_for_float_target():
    tokens = Lexer('var bob: str = "3.14";\nvar f: float = bob.parse;').tokenize()
    program = Parser(tokens).parse()

    decl = program.statements[1]
    assert isinstance(decl.value, ParseCall)


def test_parses_bare_dot_parse_as_expression_statement():
    tokens = Lexer('var bob: str = "42";\nbob.parse;').tokenize()
    program = Parser(tokens).parse()

    stmt = program.statements[1]
    assert isinstance(stmt, ExpressionStatement)
    assert isinstance(stmt.expression, ParseCall)
    assert stmt.expression.target.name == "bob"


def test_rejects_dot_parse_on_non_str_variable():
    tokens = Lexer("var n: int = 5;\nvar m: int = n.parse;").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_dot_parse_on_undeclared_variable():
    tokens = Lexer("var n: int = x.parse;").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_dot_parse_assigned_to_bool():
    tokens = Lexer('var s: str = "true";\nvar b: bool = s.parse;').tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()
