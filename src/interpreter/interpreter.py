from nodes.nodes import (
    Assignment,
    BinaryOp,
    Identifier,
    IfStatement,
    InputCall,
    IntLiteral,
    PrintStatement,
    Program,
    StringLiteral,
    VarDecl,
)
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
            if node.value is not None:
                self.variables[node.name] = self._evaluate(node.value)
            return
        if isinstance(node, Assignment):
            self.variables[node.name] = self._evaluate(node.value)
            return
        if isinstance(node, IfStatement):
            if self._evaluate(node.condition):
                for statement in node.body:
                    self._execute(statement)
                return
            for elif_condition, elif_body in node.elif_branches:
                if self._evaluate(elif_condition):
                    for statement in elif_body:
                        self._execute(statement)
                    return
            if node.else_body is not None:
                for statement in node.else_body:
                    self._execute(statement)
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
        if isinstance(node, InputCall):
            return input(self._evaluate(node.prompt))
        if isinstance(node, BinaryOp):
            if node.operator != "==":
                raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
            return self._evaluate(node.left) == self._evaluate(node.right)
        raise NotImplementedError(f"Cannot evaluate node: {node!r}")
