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
