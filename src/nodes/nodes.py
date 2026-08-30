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


class PrintStatement(Node):
    def __init__(self, argument: Node):
        self.argument = argument

    def __repr__(self):
        return f"PrintStatement({self.argument!r})"


class BinaryOp(Node):
    def __init__(self, operator: str, left: Node, right: Node):
        self.operator = operator
        self.left = left
        self.right = right

    def __repr__(self):
        return f"BinaryOp({self.operator!r}, {self.left!r}, {self.right!r})"


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


class Program(Node):
    def __init__(self, statements: list[Node]):
        self.statements = statements

    def __repr__(self):
        return f"Program({self.statements!r})"
