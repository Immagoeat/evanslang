import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from lexer.lexer import Lexer
from lexer.token import TokenType


def test_tokenizes_print_statement():
    tokens = Lexer('print("Hello, World!");').tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,
        TokenType.LPAREN,
        TokenType.STRING,
        TokenType.RPAREN,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]
    assert tokens[2].value == "Hello, World!"


def test_tokenizes_var_decl():
    tokens = Lexer('var COUNT: int = 9;').tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,  # var
        TokenType.IDENTIFIER,  # COUNT
        TokenType.COLON,
        TokenType.IDENTIFIER,  # int
        TokenType.EQUALS,
        TokenType.INT,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]
    assert tokens[5].value == "9"


def test_tokenizes_if_statement():
    tokens = Lexer('if (bob == "Hi") {}').tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,  # if
        TokenType.LPAREN,
        TokenType.IDENTIFIER,  # bob
        TokenType.EQUALS_EQUALS,
        TokenType.STRING,
        TokenType.RPAREN,
        TokenType.LBRACE,
        TokenType.RBRACE,
        TokenType.EOF,
    ]


def test_tokenizes_compound_assignment_operators():
    tokens = Lexer("bob += 3; bob -= 3; bob *= 3; bob /= 3;").tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,
        TokenType.PLUS_EQUALS,
        TokenType.INT,
        TokenType.SEMICOLON,
        TokenType.IDENTIFIER,
        TokenType.MINUS_EQUALS,
        TokenType.INT,
        TokenType.SEMICOLON,
        TokenType.IDENTIFIER,
        TokenType.STAR_EQUALS,
        TokenType.INT,
        TokenType.SEMICOLON,
        TokenType.IDENTIFIER,
        TokenType.SLASH_EQUALS,
        TokenType.INT,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_skips_full_line_comment():
    tokens = Lexer('# a comment\nprint("hi");').tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,
        TokenType.LPAREN,
        TokenType.STRING,
        TokenType.RPAREN,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_skips_trailing_comment():
    tokens = Lexer('print("hi"); # trailing comment').tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,
        TokenType.LPAREN,
        TokenType.STRING,
        TokenType.RPAREN,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_comment_only_source_tokenizes_to_eof():
    tokens = Lexer("# nothing but a comment").tokenize()
    assert [t.type for t in tokens] == [TokenType.EOF]


def test_line_number_correct_after_comment():
    tokens = Lexer('# comment\nprint("x");').tokenize()
    assert tokens[0].line == 2


def test_tokenizes_comparison_operators():
    tokens = Lexer("a != b; a < b; a <= b; a > b; a >= b;").tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER, TokenType.NOT_EQUALS, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.IDENTIFIER, TokenType.LESS, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.IDENTIFIER, TokenType.LESS_EQUALS, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.IDENTIFIER, TokenType.GREATER, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.IDENTIFIER, TokenType.GREATER_EQUALS, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_tokenizes_boolean_operators():
    tokens = Lexer("a && b; a || b; !a;").tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER, TokenType.AND_AND, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.IDENTIFIER, TokenType.OR_OR, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.BANG, TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_tokenizes_float_literal():
    tokens = Lexer("var pi: float = 3.14;").tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,  # var
        TokenType.IDENTIFIER,  # pi
        TokenType.COLON,
        TokenType.IDENTIFIER,  # float
        TokenType.EQUALS,
        TokenType.FLOAT,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]
    assert tokens[5].value == "3.14"


def test_tokenizes_int_then_dot_as_separate_when_no_trailing_digit():
    # "9." with nothing after the dot isn't a float; the '.' isn't valid
    # syntax anywhere else, so it should raise rather than silently merge.
    tokens = Lexer("9").tokenize()
    assert tokens[0].type == TokenType.INT
    assert tokens[0].value == "9"


def test_tokenizes_true_false_as_identifiers():
    tokens = Lexer("true false").tokenize()
    types = [t.type for t in tokens]
    assert types == [TokenType.IDENTIFIER, TokenType.IDENTIFIER, TokenType.EOF]
    assert tokens[0].value == "true"
    assert tokens[1].value == "false"
