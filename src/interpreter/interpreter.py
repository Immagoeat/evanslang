from nodes.nodes import Identifier, IntLiteral, PrintStatement, Program, StringLiteral, VarDecl
from utils.errors import EvansLangError


class Interpreter:
    def __init__(self):
        self.variables = {}

    def run(self, program: Program):
        for statement in program.statements:
            self._execute(statement)

    def _execute(self, node):
        if isinstance(node, PrintStatement):
            print(self._evaluate(node.argument))
            return
        if isinstance(node, VarDecl):
            self.variables[node.name] = self._evaluate(node.value)
            return
        raise NotImplementedError(f"Cannot execute node: {node!r}")

    def _evaluate(self, node):
        if isinstance(node, StringLiteral):
            return node.value
        if isinstance(node, IntLiteral):
            return node.value
        if isinstance(node, Identifier):
            if node.name not in self.variables:
                raise EvansLangError(f"Undefined variable {node.name!r}")
            return self.variables[node.name]
        raise NotImplementedError(f"Cannot evaluate node: {node!r}")
