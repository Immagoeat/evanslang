from pathlib import Path

from lexer.lexer import Lexer
from nodes.nodes import ClassDecl, Program
from parser.parser import Parser
from utils.errors import EvansLangError

SEPARATOR = "::"


class ResolvedProgram:
    def __init__(self, classes: dict[str, ClassDecl], entry: str):
        self.classes = classes
        self.entry = entry


def _parse_file(path: Path) -> Program:
    source = path.read_text()
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def link(root_path: Path) -> ResolvedProgram:
    classes: dict[str, ClassDecl] = {}
    _link_file(root_path.resolve(), alias=None, visiting=[], classes=classes)

    if "main" not in classes:
        raise EvansLangError(
            f"{root_path} has no entry point: missing 'class main() {{...}}'"
        )

    return ResolvedProgram(classes, entry="main")


def _link_file(
    path: Path,
    alias: str | None,
    visiting: list[Path],
    classes: dict[str, ClassDecl],
) -> None:
    if path in visiting:
        cycle = " -> ".join(p.name for p in [*visiting, path])
        raise EvansLangError(f"Circular @mentions import: {cycle}")

    if not path.exists():
        raise EvansLangError(f"Mentioned file not found: {path}")

    program = _parse_file(path)

    for cls_name, cls in program.classes.items():
        if alias is None:
            qualified = cls_name
        else:
            if not cls.is_ment:
                continue
            qualified = f"{alias}{SEPARATOR}{cls_name}"
        classes[qualified] = cls

    for mention in program.mentions:
        mention_path = (path.parent / mention.filename).resolve()
        _link_file(mention_path, mention.alias, [*visiting, path], classes)
