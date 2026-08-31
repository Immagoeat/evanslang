class Node:
    pass


class StringLiteral(Node):
    def __init__(self, value: str):
        self.value = value

    def __repr__(self):
        return f"StringLiteral({self.value!r})"


class IntLiteral(Node):
    def __init__(self, value: int):
        self.value = value

    def __repr__(self):
        return f"IntLiteral({self.value!r})"


class FloatLiteral(Node):
    def __init__(self, value: float):
        self.value = value

    def __repr__(self):
        return f"FloatLiteral({self.value!r})"


class BoolLiteral(Node):
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"BoolLiteral({self.value!r})"


class Identifier(Node):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name!r})"


class VarDecl(Node):
    def __init__(self, name: str, type_name: str, value: Node | None):
        self.name = name
        self.type_name = type_name
        self.value = value

    def __repr__(self):
        return f"VarDecl({self.name!r}, {self.type_name!r}, {self.value!r})"


class Assignment(Node):
    def __init__(self, name: str, value: Node):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"Assignment({self.name!r}, {self.value!r})"


class InputCall(Node):
    def __init__(self, prompt: Node):
        self.prompt = prompt

    def __repr__(self):
        return f"InputCall({self.prompt!r})"


class ParseCall(Node):
    def __init__(self, target: Node, target_type: str):
        self.target = target
        self.target_type = target_type

    def __repr__(self):
        return f"ParseCall({self.target!r}, {self.target_type!r})"


class PrintStatement(Node):
    def __init__(self, argument: Node):
        self.argument = argument

    def __repr__(self):
        return f"PrintStatement({self.argument!r})"


class ExpressionStatement(Node):
    def __init__(self, expression: Node):
        self.expression = expression

    def __repr__(self):
        return f"ExpressionStatement({self.expression!r})"


class BinaryOp(Node):
    def __init__(self, operator: str, left: Node, right: Node):
        self.operator = operator
        self.left = left
        self.right = right

    def __repr__(self):
        return f"BinaryOp({self.operator!r}, {self.left!r}, {self.right!r})"


class UnaryOp(Node):
    def __init__(self, operator: str, operand: Node):
        self.operator = operator
        self.operand = operand

    def __repr__(self):
        return f"UnaryOp({self.operator!r}, {self.operand!r})"


class WhileStatement(Node):
    def __init__(self, condition: Node, body: list[Node]):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"WhileStatement({self.condition!r}, {self.body!r})"


class ForStatement(Node):
    def __init__(
        self,
        init: Node | None,
        condition: Node | None,
        update: Node | None,
        body: list[Node],
    ):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

    def __repr__(self):
        return (
            f"ForStatement(init={self.init!r}, condition={self.condition!r}, "
            f"update={self.update!r}, body={self.body!r})"
        )


class IfStatement(Node):
    def __init__(
        self,
        condition: Node,
        body: list[Node],
        elif_branches: list[tuple[Node, list[Node]]] | None = None,
        else_body: list[Node] | None = None,
    ):
        self.condition = condition
        self.body = body
        self.elif_branches = elif_branches or []
        self.else_body = else_body

    def __repr__(self):
        return (
            f"IfStatement({self.condition!r}, {self.body!r}, "
            f"elif_branches={self.elif_branches!r}, else_body={self.else_body!r})"
        )


class TryStatement(Node):
    def __init__(
        self,
        try_body: list[Node],
        catch_var_name: str,
        catch_body: list[Node],
    ):
        self.try_body = try_body
        self.catch_var_name = catch_var_name
        self.catch_body = catch_body

    def __repr__(self):
        return (
            f"TryStatement({self.try_body!r}, catch_var_name={self.catch_var_name!r}, "
            f"catch_body={self.catch_body!r})"
        )


class ThrowStatement(Node):
    def __init__(self, expression: Node):
        self.expression = expression

    def __repr__(self):
        return f"ThrowStatement({self.expression!r})"


class ClassDecl(Node):
    def __init__(self, name: str, is_ment: bool, body: list[Node]):
        self.name = name
        self.is_ment = is_ment
        self.body = body

    def __repr__(self):
        return f"ClassDecl({self.name!r}, is_ment={self.is_ment!r}, {self.body!r})"


class Mention(Node):
    def __init__(self, filename: str, alias: str):
        self.filename = filename
        self.alias = alias

    def __repr__(self):
        return f"Mention({self.filename!r}, {self.alias!r})"


class CallStatement(Node):
    def __init__(self, alias: str | None, name: str):
        self.alias = alias
        self.name = name
        # Filled in by the linker: the fully-qualified key into
        # ResolvedProgram.classes that this call actually resolves to,
        # computed using the ALIAS TABLE OF THE FILE THIS CALL WAS PARSED
        # IN (not the root file's), so a mentioned file's own @mentions
        # still work correctly when that file is itself linked in.
        self.resolved_target: str | None = None

    def __repr__(self):
        return (
            f"CallStatement(alias={self.alias!r}, name={self.name!r}, "
            f"resolved_target={self.resolved_target!r})"
        )


class Program(Node):
    def __init__(
        self,
        classes: dict[str, ClassDecl],
        mentions: list[Mention] | None = None,
    ):
        self.classes = classes
        self.mentions = mentions or []

    def __repr__(self):
        return f"Program(classes={self.classes!r}, mentions={self.mentions!r})"
