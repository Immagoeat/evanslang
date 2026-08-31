import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from nodes.nodes import (
    Assignment,
    BinaryOp,
    BoolLiteral,
    CallStatement,
    ExpressionStatement,
    FloatLiteral,
    ForStatement,
    Identifier,
    IfStatement,
    InputCall,
    IntLiteral,
    ParseCall,
    PrintStatement,
    StringLiteral,
    UnaryOp,
    VarDecl,
    WhileStatement,
)
from lexer.lexer import Lexer
from parser.parser import Parser
from utils.errors import ParseError


def parse_program(source: str) -> list:
    """Parse `source` as the body of class main() and return its statement list."""
    wrapped = f"class main() {{\n{source}\n}}"
    tokens = Lexer(wrapped).tokenize()
    program = Parser(tokens).parse()
    return program.classes["main"].body


def test_parses_print_statement():
    statements = parse_program('print("Hello, World!");')

    assert len(statements) == 1
    statement = statements[0]
    assert isinstance(statement, PrintStatement)
    assert isinstance(statement.argument, StringLiteral)
    assert statement.argument.value == "Hello, World!"


def test_parses_str_var_decl():
    statements = parse_program('var EXAMPLE: str = "Hello";')

    statement = statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.name == "EXAMPLE"
    assert statement.type_name == "str"
    assert isinstance(statement.value, StringLiteral)
    assert statement.value.value == "Hello"


def test_parses_int_var_decl():
    statements = parse_program("var COUNT: int = 9;")

    statement = statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.name == "COUNT"
    assert statement.type_name == "int"
    assert isinstance(statement.value, IntLiteral)
    assert statement.value.value == 9


def test_rejects_mismatched_var_type():
    with pytest.raises(ParseError):
        parse_program('var COUNT: int = "nope";')


def test_parses_var_decl_without_value():
    statements = parse_program("var bob: str;")

    statement = statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.name == "bob"
    assert statement.type_name == "str"
    assert statement.value is None


def test_parses_assignment_with_input_call():
    statements = parse_program('var bob: str;\nbob = input("MESSAGE");')

    assign = statements[1]
    assert isinstance(assign, Assignment)
    assert assign.name == "bob"
    assert isinstance(assign.value, InputCall)
    assert assign.value.prompt.value == "MESSAGE"


def test_rejects_assignment_to_undeclared_variable():
    with pytest.raises(ParseError):
        parse_program('undeclared = "x";')


def test_rejects_input_assigned_to_int_variable():
    with pytest.raises(ParseError):
        parse_program('var n: int;\nn = input("x");')


def test_parses_if_statement():
    statements = parse_program('var bob: str = "Hi";\nif (bob == "Hi") {\nprint(bob);\n}')

    if_stmt = statements[1]
    assert isinstance(if_stmt, IfStatement)
    assert isinstance(if_stmt.condition, BinaryOp)
    assert if_stmt.condition.operator == "=="
    assert len(if_stmt.body) == 1
    assert isinstance(if_stmt.body[0], PrintStatement)


def test_rejects_unterminated_if_block():
    with pytest.raises(ParseError):
        parse_program('var x: int = 1;\nif (x == 1) {\nprint(x);\n')


def test_parses_if_elseif_else_chain():
    source = (
        'var bob: str = "Hello";\n'
        'if (bob == "Hi") {}\n'
        'elseif (bob == "Hello") {\n'
        "print(bob);\n"
        "}\n"
        "else {}\n"
    )
    statements = parse_program(source)

    if_stmt = statements[1]
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
    statements = parse_program(source)

    if_stmt = statements[1]
    assert isinstance(if_stmt, IfStatement)
    assert len(if_stmt.elif_branches) == 1
    assert if_stmt.else_body == []


def test_parses_if_without_elseif_or_else():
    statements = parse_program('var bob: str = "Hi";\nif (bob == "Hi") {}\n')

    if_stmt = statements[1]
    assert if_stmt.elif_branches == []
    assert if_stmt.else_body is None


def test_parses_compound_assignment():
    statements = parse_program("var bob: int = 10;\nbob += 3;")

    assign = statements[1]
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
    statements = parse_program(source)

    operators = [stmt.value.operator for stmt in statements[1:]]
    assert operators == ["+", "-", "*", "/"]


def test_parses_compound_assignment_with_identifier_rhs():
    statements = parse_program("var a: int = 5;\nvar b: int = 3;\na += b;")

    assign = statements[2]
    assert isinstance(assign.value, BinaryOp)
    assert isinstance(assign.value.right, Identifier)
    assert assign.value.right.name == "b"


def test_rejects_compound_assignment_to_undeclared_variable():
    with pytest.raises(ParseError):
        parse_program("x += 1;")


def test_rejects_compound_assignment_on_str_variable():
    with pytest.raises(ParseError):
        parse_program('var s: str = "hi";\ns += 1;')


def test_rejects_compound_assignment_with_str_rhs():
    with pytest.raises(ParseError):
        parse_program('var n: int = 1;\nn += "x";')


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
    statements = parse_program("var pi: float = 3.14;")

    statement = statements[0]
    assert isinstance(statement, VarDecl)
    assert statement.type_name == "float"
    assert isinstance(statement.value, FloatLiteral)
    assert statement.value.value == 3.14


def test_parses_bool_var_decl_true_and_false():
    statements = parse_program("var flag: bool = true;\nvar other: bool = false;")

    flag_decl, other_decl = statements
    assert isinstance(flag_decl.value, BoolLiteral) and flag_decl.value.value is True
    assert isinstance(other_decl.value, BoolLiteral) and other_decl.value.value is False


def test_rejects_int_literal_for_float_variable():
    with pytest.raises(ParseError):
        parse_program("var f: float = 5;")


def test_rejects_float_literal_for_int_variable():
    with pytest.raises(ParseError):
        parse_program("var n: int = 5.0;")


def test_rejects_non_bool_for_bool_variable():
    with pytest.raises(ParseError):
        parse_program('var b: bool = "x";')


def test_parses_compound_assignment_on_float_variable():
    statements = parse_program("var f: float = 1.0;\nf += 2.5;")

    assign = statements[1]
    assert isinstance(assign, Assignment)
    assert isinstance(assign.value, BinaryOp) and assign.value.operator == "+"
    assert isinstance(assign.value.right, FloatLiteral)
    assert assign.value.right.value == 2.5


def test_rejects_int_literal_in_float_compound_assignment():
    with pytest.raises(ParseError):
        parse_program("var f: float = 1.0;\nf += 2;")


def test_rejects_mixing_int_and_float_variables_in_compound_assignment():
    with pytest.raises(ParseError):
        parse_program("var f: float = 1.0;\nvar n: int = 2;\nf += n;")


def test_parses_dot_parse_in_var_decl():
    statements = parse_program('var bob: str = "42";\nvar n: int = bob.parse;')

    decl = statements[1]
    assert isinstance(decl, VarDecl)
    assert decl.type_name == "int"
    assert isinstance(decl.value, ParseCall)
    assert isinstance(decl.value.target, Identifier)
    assert decl.value.target.name == "bob"


def test_parses_dot_parse_for_float_target():
    statements = parse_program('var bob: str = "3.14";\nvar f: float = bob.parse;')

    decl = statements[1]
    assert isinstance(decl.value, ParseCall)


def test_parses_bare_dot_parse_as_expression_statement():
    statements = parse_program('var bob: str = "42";\nbob.parse;')

    stmt = statements[1]
    assert isinstance(stmt, ExpressionStatement)
    assert isinstance(stmt.expression, ParseCall)
    assert stmt.expression.target.name == "bob"


def test_rejects_dot_parse_on_non_str_variable():
    with pytest.raises(ParseError):
        parse_program("var n: int = 5;\nvar m: int = n.parse;")


def test_rejects_dot_parse_on_undeclared_variable():
    with pytest.raises(ParseError):
        parse_program("var n: int = x.parse;")


def test_rejects_dot_parse_assigned_to_bool():
    with pytest.raises(ParseError):
        parse_program('var s: str = "true";\nvar b: bool = s.parse;')


def test_parses_class_main_wrapper():
    tokens = Lexer('class main() {\nprint("hi");\n}').tokenize()
    program = Parser(tokens).parse()

    assert len(program.classes["main"].body) == 1
    assert isinstance(program.classes["main"].body[0], PrintStatement)


def test_parses_class_main_with_trailing_semicolon():
    tokens = Lexer('class main() {\nprint("hi");\n};').tokenize()
    program = Parser(tokens).parse()

    assert len(program.classes["main"].body) == 1


def test_rejects_empty_file():
    tokens = Lexer("").tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_parses_empty_class_main():
    tokens = Lexer("class main() {}").tokenize()
    program = Parser(tokens).parse()

    assert program.classes["main"].body == []
    assert program.classes["main"].is_ment is False


def test_parses_ment_class():
    tokens = Lexer('class bob(ment) {\nprint("bob running");\n}\nclass main() {}').tokenize()
    program = Parser(tokens).parse()

    assert program.classes["bob"].is_ment is True
    assert program.classes["main"].is_ment is False


def test_parses_init_class():
    tokens = Lexer('class init() {\nprint("init");\n}\nclass main() {}').tokenize()
    program = Parser(tokens).parse()

    assert "init" in program.classes


def test_parses_local_class_call():
    source = 'class helper() {\nprint("hi");\n}\nclass main() {\nhelper;\n}'
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    call = program.classes["main"].body[0]
    assert isinstance(call, CallStatement)
    assert call.alias is None
    assert call.name == "helper"


def test_parses_forward_referenced_local_class_call():
    # main calls helper, but helper is declared *after* main in the file.
    source = 'class main() {\nhelper;\n}\nclass helper() {\nprint(\"hi\");\n}'
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    call = program.classes["main"].body[0]
    assert isinstance(call, CallStatement)
    assert call.name == "helper"


def test_parses_mention_directive():
    source = "@mentions test.el -> test;\nclass main() {}"
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    assert len(program.mentions) == 1
    assert program.mentions[0].filename == "test.el"
    assert program.mentions[0].alias == "test"


def test_parses_aliased_class_call():
    source = "@mentions test.el -> test;\nclass main() {\ntest.sdgdsg;\n}"
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    call = program.classes["main"].body[0]
    assert isinstance(call, CallStatement)
    assert call.alias == "test"
    assert call.name == "sdgdsg"


def test_rejects_duplicate_class_name():
    source = "class main() {}\nclass main() {}"
    tokens = Lexer(source).tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_file_with_no_main_parses_when_it_has_other_classes():
    # A library-only file (no class main) is valid syntax on its own -
    # the "needs an entry point" rule is enforced by the linker, not the
    # parser, since a file might only ever be @mentions-ed, never run.
    tokens = Lexer('class util(ment) {\nprint("hi");\n}').tokenize()
    program = Parser(tokens).parse()

    assert "main" not in program.classes
    assert "util" in program.classes


def test_parses_while_statement():
    statements = parse_program("var i: int = 0;\nwhile (i < 3) {\ni += 1;\n}")

    while_stmt = statements[1]
    assert isinstance(while_stmt, WhileStatement)
    assert isinstance(while_stmt.condition, BinaryOp)
    assert while_stmt.condition.operator == "<"
    assert len(while_stmt.body) == 1


def test_parses_while_with_trailing_semicolon():
    statements = parse_program("while (true) {};")
    assert isinstance(statements[0], WhileStatement)


def test_parses_empty_while_body():
    statements = parse_program("while (false) {}")
    while_stmt = statements[0]
    assert while_stmt.body == []


def test_parses_for_statement_with_all_clauses():
    statements = parse_program("for (var j: int = 0; j < 3; j += 1) {\nprint(j);\n}")

    for_stmt = statements[0]
    assert isinstance(for_stmt, ForStatement)
    assert isinstance(for_stmt.init, VarDecl)
    assert for_stmt.init.name == "j"
    assert isinstance(for_stmt.condition, BinaryOp)
    assert for_stmt.condition.operator == "<"
    assert isinstance(for_stmt.update, Assignment)
    assert for_stmt.update.name == "j"
    assert len(for_stmt.body) == 1


def test_parses_for_with_assignment_init_and_update():
    statements = parse_program(
        "var j: int = 0;\nfor (j = 0; j < 3; j += 1) {\nprint(j);\n}"
    )
    for_stmt = statements[1]
    assert isinstance(for_stmt.init, Assignment)
    assert isinstance(for_stmt.update, Assignment)


def test_parses_for_with_omitted_clauses():
    statements = parse_program("var i: int = 0;\nfor (; i < 3;) {\ni += 1;\n}")

    for_stmt = statements[1]
    assert for_stmt.init is None
    assert for_stmt.condition is not None
    assert for_stmt.update is None


def test_parses_for_with_all_clauses_omitted():
    statements = parse_program("for (;;) {}")

    for_stmt = statements[0]
    assert for_stmt.init is None
    assert for_stmt.condition is None
    assert for_stmt.update is None


def test_parses_for_with_trailing_semicolon():
    statements = parse_program("for (;;) {};")
    assert isinstance(statements[0], ForStatement)


def test_rejects_for_with_invalid_init_clause():
    with pytest.raises(ParseError):
        parse_program('for (print("x"); true;) {}')
