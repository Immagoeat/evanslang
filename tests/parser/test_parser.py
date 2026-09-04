import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from nodes.nodes import (
    AddressOf,
    AppendCall,
    AsciiStatement,
    Assignment,
    BinaryOp,
    BoolLiteral,
    CallStatement,
    Dereference,
    DerefAssignment,
    ExpressionStatement,
    FloatLiteral,
    ForStatement,
    GotoStatement,
    Identifier,
    IfStatement,
    IndexAssignment,
    IndexExpr,
    InputCall,
    IntLiteral,
    LengthCall,
    ListDecl,
    ParseCall,
    PrintStatement,
    StringLiteral,
    ThrowStatement,
    TryStatement,
    UnaryOp,
    VarDecl,
    VideoStatement,
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


def test_parses_dot_parse_int_in_var_decl():
    statements = parse_program('var bob: str = "42";\nvar n: int = bob.parse(int);')

    decl = statements[1]
    assert isinstance(decl, VarDecl)
    assert decl.type_name == "int"
    assert isinstance(decl.value, ParseCall)
    assert decl.value.target_type == "int"
    assert isinstance(decl.value.target, Identifier)
    assert decl.value.target.name == "bob"


def test_parses_dot_parse_float_target():
    statements = parse_program('var bob: str = "3.14";\nvar f: float = bob.parse(float);')

    decl = statements[1]
    assert isinstance(decl.value, ParseCall)
    assert decl.value.target_type == "float"


def test_parses_dot_parse_bool_target():
    statements = parse_program('var bob: str = "true";\nvar b: bool = bob.parse(bool);')

    decl = statements[1]
    assert isinstance(decl.value, ParseCall)
    assert decl.value.target_type == "bool"


def test_parses_dot_parse_str_target():
    statements = parse_program('var bob: str = "hi";\nvar copy: str = bob.parse(str);')

    decl = statements[1]
    assert isinstance(decl.value, ParseCall)
    assert decl.value.target_type == "str"


def test_parses_bare_dot_parse_as_expression_statement():
    statements = parse_program('var bob: str = "42";\nbob.parse(int);')

    stmt = statements[1]
    assert isinstance(stmt, ExpressionStatement)
    assert isinstance(stmt.expression, ParseCall)
    assert stmt.expression.target.name == "bob"
    assert stmt.expression.target_type == "int"


def test_rejects_dot_parse_on_non_str_variable():
    with pytest.raises(ParseError):
        parse_program("var n: int = 5;\nvar m: int = n.parse(int);")


def test_rejects_dot_parse_on_undeclared_variable():
    with pytest.raises(ParseError):
        parse_program("var n: int = x.parse(int);")


def test_rejects_dot_parse_with_unknown_type():
    with pytest.raises(ParseError):
        parse_program('var s: str = "42";\nvar n: int = s.parse(banana);')


def test_rejects_dot_parse_target_type_mismatch_with_declared_type():
    with pytest.raises(ParseError):
        parse_program('var s: str = "42";\nvar f: float = s.parse(int);')


def test_rejects_bare_dot_parse_without_parens():
    with pytest.raises(ParseError):
        parse_program('var s: str = "42";\nvar n: int = s.parse;')


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


def test_rejects_explicit_local_call_to_init():
    # init already runs automatically before main; calling it explicitly
    # would run its body twice.
    source = 'class init() {\nprint("setup");\n}\nclass main() {\ninit;\n}'
    tokens = Lexer(source).tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_rejects_explicit_local_call_to_main():
    source = 'class main() {\nprint("hi");\nmain;\n}'
    tokens = Lexer(source).tokenize()
    with pytest.raises(ParseError):
        Parser(tokens).parse()


def test_allows_calling_a_mentioned_files_main_via_alias():
    # A mentioned file's own class main() never auto-runs, so calling it
    # explicitly via alias.main is fine - the double-run risk only exists
    # for LOCAL, unaliased calls to the file's own main/init.
    source = "@mentions lib.el -> lib;\nclass main() {\nlib.main;\n}"
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    call = program.classes["main"].body[0]
    assert isinstance(call, CallStatement)
    assert call.alias == "lib"
    assert call.name == "main"


def test_parses_additive_and_multiplicative_precedence():
    statements = parse_program("var a: int = 2 + 3 * 4;")
    value = statements[0].value

    assert isinstance(value, BinaryOp)
    assert value.operator == "+"
    assert isinstance(value.left, IntLiteral)
    assert value.left.value == 2
    assert isinstance(value.right, BinaryOp)
    assert value.right.operator == "*"


def test_parses_parenthesized_expression_overriding_precedence():
    statements = parse_program("var a: int = (2 + 3) * 4;")
    value = statements[0].value

    assert isinstance(value, BinaryOp)
    assert value.operator == "*"
    assert isinstance(value.left, BinaryOp)
    assert value.left.operator == "+"
    assert isinstance(value.right, IntLiteral)
    assert value.right.value == 4


def test_parses_unary_minus():
    statements = parse_program("var a: int = -5;")
    value = statements[0].value

    assert isinstance(value, UnaryOp)
    assert value.operator == "-"
    assert isinstance(value.operand, IntLiteral)
    assert value.operand.value == 5


def test_rejects_arithmetic_assigned_to_str_variable():
    with pytest.raises(ParseError):
        parse_program("var a: str = 2 + 3;")


def test_parses_try_catch():
    statements = parse_program(
        'try {\nprint("a");\n}\ncatch (e: str) {\nprint(e);\n}'
    )

    statement = statements[0]
    assert isinstance(statement, TryStatement)
    assert len(statement.try_body) == 1
    assert statement.catch_var_name == "e"
    assert len(statement.catch_body) == 1


def test_parses_throw():
    statements = parse_program('throw "oops";')

    statement = statements[0]
    assert isinstance(statement, ThrowStatement)
    assert isinstance(statement.expression, StringLiteral)
    assert statement.expression.value == "oops"


def test_catch_variable_is_declared_as_str():
    # catch (e: str) implicitly declares `e` as a str variable, so a later
    # .parse(...) call on it (which requires a declared str) must parse.
    statements = parse_program(
        'try {\nthrow "x";\n}\ncatch (e: str) {\nvar n: int = e.parse(int);\n}'
    )
    catch_body = statements[0].catch_body
    assert isinstance(catch_body[0], VarDecl)
    assert isinstance(catch_body[0].value, ParseCall)
    assert catch_body[0].value.target.name == "e"


def test_rejects_try_without_catch():
    with pytest.raises(ParseError):
        parse_program('try {\nprint("a");\n}')


def test_parses_pointer_var_decl():
    statements = parse_program("var x: int = 5;\nvar p: ptr<int> = &x;")

    decl = statements[1]
    assert isinstance(decl, VarDecl)
    assert decl.type_name == "ptr<int>"
    assert isinstance(decl.value, AddressOf)
    assert decl.value.name == "x"


def test_parses_dereference_in_expression():
    statements = parse_program(
        "var x: int = 5;\nvar p: ptr<int> = &x;\nprint(*p);"
    )
    print_stmt = statements[2]
    assert isinstance(print_stmt.argument, Dereference)
    assert isinstance(print_stmt.argument.operand, Identifier)
    assert print_stmt.argument.operand.name == "p"


def test_parses_deref_assignment():
    statements = parse_program(
        "var x: int = 5;\nvar p: ptr<int> = &x;\n*p = 10;"
    )
    assign = statements[2]
    assert isinstance(assign, DerefAssignment)
    assert isinstance(assign.pointer, Identifier)
    assert assign.pointer.name == "p"
    assert isinstance(assign.value, IntLiteral)
    assert assign.value.value == 10


def test_pointer_reassignment_to_another_variable():
    statements = parse_program(
        "var x: int = 1;\nvar y: int = 2;\n"
        "var p: ptr<int> = &x;\np = &y;"
    )
    reassign = statements[3]
    assert isinstance(reassign, Assignment)
    assert isinstance(reassign.value, AddressOf)
    assert reassign.value.name == "y"


def test_rejects_pointer_to_mismatched_type():
    with pytest.raises(ParseError):
        parse_program("var x: int = 5;\nvar p: ptr<str> = &x;")


def test_rejects_dereferencing_a_non_pointer():
    with pytest.raises(ParseError):
        parse_program("var x: int = 5;\n*x = 10;")


def test_rejects_unknown_pointee_type():
    with pytest.raises(ParseError):
        parse_program("var p: ptr<nonsense> = &x;")


def test_rejects_non_pointer_value_assigned_to_ptr_variable():
    with pytest.raises(ParseError):
        parse_program("var x: int = 5;\nvar p: ptr<int> = 5;")


def test_parses_empty_list_decl():
    statements = parse_program("list nums;")

    decl = statements[0]
    assert isinstance(decl, ListDecl)
    assert decl.element_type is None
    assert decl.elements == []


def test_parses_untyped_list_with_mixed_elements():
    statements = parse_program('list mixed: [1, "two", true];')

    decl = statements[0]
    assert isinstance(decl, ListDecl)
    assert decl.element_type is None
    assert len(decl.elements) == 3
    assert isinstance(decl.elements[0], IntLiteral)
    assert isinstance(decl.elements[1], StringLiteral)
    assert isinstance(decl.elements[2], BoolLiteral)


def test_parses_typed_list_decl():
    statements = parse_program("list<int> nums: [1, 2, 3];")

    decl = statements[0]
    assert isinstance(decl, ListDecl)
    assert decl.element_type == "int"
    assert len(decl.elements) == 3


def test_rejects_typed_list_with_mismatched_literal():
    with pytest.raises(ParseError):
        parse_program('list<int> nums: [1, "two"];')


def test_parses_list_index_expression():
    statements = parse_program("list nums: [1, 2, 3];\nprint(nums[0]);")

    print_stmt = statements[1]
    assert isinstance(print_stmt.argument, IndexExpr)
    assert isinstance(print_stmt.argument.target, Identifier)
    assert print_stmt.argument.target.name == "nums"
    assert isinstance(print_stmt.argument.index, IntLiteral)


def test_parses_list_index_assignment():
    statements = parse_program("list nums: [1, 2, 3];\nnums[0] = 5;")

    assign = statements[1]
    assert isinstance(assign, IndexAssignment)
    assert isinstance(assign.target, Identifier)
    assert assign.target.name == "nums"
    assert isinstance(assign.value, IntLiteral)
    assert assign.value.value == 5


def test_rejects_typed_list_index_assignment_with_mismatched_literal():
    with pytest.raises(ParseError):
        parse_program('list<int> nums: [1, 2, 3];\nnums[0] = "bad";')


def test_parses_append_call():
    statements = parse_program("list nums: [1, 2];\nnums.append(3);")

    append_stmt = statements[1]
    assert isinstance(append_stmt, ExpressionStatement)
    assert isinstance(append_stmt.expression, AppendCall)
    assert isinstance(append_stmt.expression.value, IntLiteral)
    assert append_stmt.expression.value.value == 3


def test_rejects_typed_list_append_with_mismatched_literal():
    with pytest.raises(ParseError):
        parse_program('list<int> nums: [1, 2];\nnums.append("bad");')


def test_parses_length_call():
    statements = parse_program("list nums: [1, 2];\nprint(nums.length());")

    print_stmt = statements[1]
    assert isinstance(print_stmt.argument, LengthCall)
    assert isinstance(print_stmt.argument.target, Identifier)
    assert print_stmt.argument.target.name == "nums"


def test_rejects_indexing_a_non_list_variable():
    with pytest.raises(ParseError):
        parse_program("var x: int = 5;\nprint(x[0]);")


def test_rejects_append_on_a_non_list_variable():
    with pytest.raises(ParseError):
        parse_program("var x: int = 5;\nx.append(1);")


def test_rejects_length_on_a_non_list_variable():
    with pytest.raises(ParseError):
        parse_program("var x: int = 5;\nprint(x.length());")


def test_parses_ascii_statement_with_string_literal():
    statements = parse_program('ascii "image.png";')

    statement = statements[0]
    assert isinstance(statement, AsciiStatement)
    assert isinstance(statement.path, StringLiteral)
    assert statement.path.value == "image.png"


def test_parses_ascii_statement_with_identifier():
    statements = parse_program('var path: str = "image.png";\nascii path;')

    statement = statements[1]
    assert isinstance(statement, AsciiStatement)
    assert isinstance(statement.path, Identifier)
    assert statement.path.name == "path"


def test_parses_video_statement_with_string_literal():
    statements = parse_program('video "clip.mp4";')

    statement = statements[0]
    assert isinstance(statement, VideoStatement)
    assert isinstance(statement.path, StringLiteral)
    assert statement.path.value == "clip.mp4"


def test_parses_video_statement_with_identifier():
    statements = parse_program('var path: str = "clip.mp4";\nvideo path;')

    statement = statements[1]
    assert isinstance(statement, VideoStatement)
    assert isinstance(statement.path, Identifier)
    assert statement.path.name == "path"


def test_parses_goto_statement():
    statements = parse_program("goto ln: 5;")

    statement = statements[0]
    assert isinstance(statement, GotoStatement)
    assert statement.target_line == 5


def test_statements_are_tagged_with_their_source_line():
    # parse_program wraps `source` as `class main() {\n<source>\n}`, so
    # `source`'s own first line is line 2.
    statements = parse_program('print("a");\nprint("b");')

    assert statements[0].line == 2
    assert statements[1].line == 3


def test_parses_goto_inside_if_body():
    statements = parse_program(
        'if (true) {\ngoto ln: 5;\n}'
    )
    if_stmt = statements[0]
    goto_stmt = if_stmt.body[0]
    assert isinstance(goto_stmt, GotoStatement)
    assert goto_stmt.target_line == 5


def test_parses_goto_inside_nested_if_body():
    statements = parse_program(
        'if (true) {\nif (true) {\ngoto ln: 5;\n}\n}'
    )
    goto_stmt = statements[0].body[0].body[0]
    assert isinstance(goto_stmt, GotoStatement)


def test_parses_goto_inside_elseif_and_else_bodies():
    statements = parse_program(
        'if (false) {\nprint("a");\n}\n'
        'elseif (false) {\ngoto ln: 1;\n}\n'
        'else {\ngoto ln: 1;\n}'
    )
    if_stmt = statements[0]
    assert isinstance(if_stmt.elif_branches[0][1][0], GotoStatement)
    assert isinstance(if_stmt.else_body[0], GotoStatement)


def test_rejects_goto_inside_while_body():
    with pytest.raises(ParseError):
        parse_program("while (true) {\ngoto ln: 1;\n}")


def test_rejects_goto_inside_for_body():
    with pytest.raises(ParseError):
        parse_program("for (;;) {\ngoto ln: 1;\n}")


def test_rejects_goto_inside_try_body():
    with pytest.raises(ParseError):
        parse_program('try {\ngoto ln: 1;\n}\ncatch (e: str) {\nprint(e);\n}')


def test_rejects_goto_inside_catch_body():
    with pytest.raises(ParseError):
        parse_program('try {\nprint("a");\n}\ncatch (e: str) {\ngoto ln: 1;\n}')


def test_rejects_goto_inside_while_nested_in_if():
    # goto is allowed directly inside if/elseif/else, but a while inside
    # an if must still reject it - the permission doesn't leak through
    # while/for/try regardless of what encloses them.
    with pytest.raises(ParseError):
        parse_program(
            'if (true) {\nwhile (true) {\ngoto ln: 1;\n}\n}'
        )
