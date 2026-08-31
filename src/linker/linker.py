from pathlib import Path

from lexer.lexer import Lexer
from nodes.nodes import (
    CallStatement,
    ClassDecl,
    ForStatement,
    IfStatement,
    Program,
    WhileStatement,
)
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


def _qualify(scope: Path, root_scope: Path, name: str) -> str:
    # The root file's own classes keep their bare names (no prefix), so
    # `class main() {}` stays reachable as "main" rather than a
    # path-prefixed key. Every other file's classes are namespaced by
    # their own resolved path, which is unique and stable regardless of
    # how many different aliases different files use to reach them.
    if scope == root_scope:
        return name
    return f"{scope}{SEPARATOR}{name}"


def _statements_in(node) -> list:
    # Statements can nest inside if/elseif/else/while/for bodies; walk
    # those to find every CallStatement so its resolved_target can be set,
    # no matter how deeply it's nested inside a class body.
    if isinstance(node, IfStatement):
        nested = list(node.body)
        for _, body in node.elif_branches:
            nested.extend(body)
        if node.else_body is not None:
            nested.extend(node.else_body)
        return nested
    if isinstance(node, WhileStatement):
        return list(node.body)
    if isinstance(node, ForStatement):
        nested = list(node.body)
        if node.init is not None:
            nested.append(node.init)
        if node.update is not None:
            nested.append(node.update)
        return nested
    return []


def _resolve_calls_in_body(
    body: list,
    scope: Path,
    root_scope: Path,
    alias_scopes: dict[str, Path],
    ment_by_scope: dict[Path, dict[str, bool]],
) -> None:
    stack = list(body)
    while stack:
        node = stack.pop()
        if isinstance(node, CallStatement):
            if node.alias is None:
                node.resolved_target = _qualify(scope, root_scope, node.name)
            else:
                target_scope = alias_scopes.get(node.alias)
                if target_scope is None:
                    # Genuinely unreachable given the parser only accepts
                    # aliases it saw declared in this same file, but fail
                    # loudly rather than silently mis-resolving a call.
                    raise EvansLangError(
                        f"Call to {node.alias}.{node.name} uses an alias "
                        f"that was never declared with @mentions"
                    )
                is_ment = ment_by_scope.get(target_scope, {}).get(node.name)
                if not is_ment:
                    raise EvansLangError(
                        f"{node.name!r} is not a mentionable class in the "
                        f"file mentioned as {node.alias!r} (mark it "
                        f"'class {node.name}(ment) {{}}' to make it "
                        f"reachable, or check the class exists)"
                    )
                node.resolved_target = _qualify(target_scope, root_scope, node.name)
        stack.extend(_statements_in(node))


def link(root_path: Path) -> ResolvedProgram:
    resolved_root = root_path.resolve()
    classes: dict[str, ClassDecl] = {}
    ment_by_scope: dict[Path, dict[str, bool]] = {}
    _link_file(
        resolved_root,
        root_scope=resolved_root,
        classes=classes,
        ment_by_scope=ment_by_scope,
    )

    if "main" not in classes:
        raise EvansLangError(
            f"{root_path} has no entry point: missing 'class main() {{...}}'"
        )

    return ResolvedProgram(classes, entry="main")


def _link_file(
    path: Path,
    root_scope: Path,
    classes: dict[str, ClassDecl],
    ment_by_scope: dict[Path, dict[str, bool]],
) -> None:
    # `path` (resolved, absolute) is this file's scope - stable and unique
    # no matter how many different aliases, in how many different files,
    # end up pointing at it. Every class in a linked file is kept (not
    # just (ment) ones), so the file's own internal calls keep working;
    # (ment)-ness is enforced separately, only when ANOTHER file's call
    # reaches in via an alias (see _resolve_calls_in_body).
    if path in ment_by_scope:
        return  # already linked (reached via more than one alias/path)

    if not path.exists():
        raise EvansLangError(f"Mentioned file not found: {path}")

    program = _parse_file(path)

    # Record this file's own classes' (ment) status before recursing, so
    # the recursion guard above (and any call resolution into this file)
    # sees it as already-linked from this point on, which also makes a
    # direct self-mention (or a longer @mentions cycle) a no-op re-entry
    # rather than infinite recursion.
    ment_by_scope[path] = {name: cls.is_ment for name, cls in program.classes.items()}

    # This file's own aliases resolve relative to ITS OWN mentions, always
    # - regardless of how this file itself was reached.
    alias_scopes: dict[str, Path] = {}
    for mention in program.mentions:
        mentioned_path = (path.parent / mention.filename).resolve()
        if mention.alias in alias_scopes:
            raise EvansLangError(
                f"@mentions alias {mention.alias!r} is used more than once in {path}"
            )
        alias_scopes[mention.alias] = mentioned_path

        _link_file(
            mentioned_path,
            root_scope=root_scope,
            classes=classes,
            ment_by_scope=ment_by_scope,
        )

    for cls_name, cls in program.classes.items():
        _resolve_calls_in_body(cls.body, path, root_scope, alias_scopes, ment_by_scope)
        classes[_qualify(path, root_scope, cls_name)] = cls
