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
    def __init__(self, name: str, type_name: str, value: Node):
        self.name = name
        self.type_name = type_name
        self.value = value

    def __repr__(self):
        return f"VarDecl({self.name!r}, {self.type_name!r}, {self.value!r})"


class PrintStatement(Node):
    def __init__(self, argument: Node):
        self.argument = argument

    def __repr__(self):
        return f"PrintStatement({self.argument!r})"


class Program(Node):
    def __init__(self, statements: list[Node]):
        self.statements = statements

    def __repr__(self):
        return f"Program({self.statements!r})"
