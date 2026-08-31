from nodes.nodes import (
    Assignment,
    BinaryOp,
    BoolLiteral,
    CallStatement,
    ExpressionStatement,
    FloatLiteral,
    ForStatement,
    Identifier,
    IfStatement,
    InputCall,
    IntLiteral,
    ParseCall,
    PrintStatement,
    StringLiteral,
    UnaryOp,
    VarDecl,
    WhileStatement,
)
from linker.linker import ResolvedProgram
from utils.errors import EvansLangError
from utils.runtime import display, parse_as


# Lower than the VM's limit: the interpreter uses native Python recursion
# (_run_class -> _execute -> _run_class -> ...), costing several Python
# stack frames per evanslang-level call, so this must stay well under
# Python's own default recursion limit (sys.getrecursionlimit(), 1000) to
# ensure this raises a clean EvansLangError before Python raises its own
# uncatchable-by-our-error-handling RecursionError.
MAX_CALL_DEPTH = 200


class Interpreter:
    def __init__(self):
        self.variables = {}
        self.call_depth = 0

    def run(self, resolved: ResolvedProgram):
        self.classes = resolved.classes
        if "init" in self.classes:
            self._run_class("init")
        self._run_class(resolved.entry)

    def _run_class(self, name: str) -> None:
        if self.call_depth >= MAX_CALL_DEPTH:
            raise EvansLangError(
                f"Call stack exceeded {MAX_CALL_DEPTH} deep "
                "(likely unbounded recursion)"
            )
        self.call_depth += 1
        try:
            for statement in self.classes[name].body:
                self._execute(statement)
        finally:
            self.call_depth -= 1

    def _execute(self, node):
        if isinstance(node, CallStatement):
            # resolved_target is computed by the linker, using the alias
            # table of whichever file this call was parsed in.
            if node.resolved_target is None or node.resolved_target not in self.classes:
                raise EvansLangError(
                    f"Internal error: call to {node.name!r} was never resolved"
                )
            self._run_class(node.resolved_target)
            return
        if isinstance(node, PrintStatement):
            print(display(self._evaluate(node.argument)))
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
        if isinstance(node, ExpressionStatement):
            self._evaluate(node.expression)
            return
        if isinstance(node, WhileStatement):
            while self._evaluate(node.condition):
                for statement in node.body:
                    self._execute(statement)
            return
        if isinstance(node, ForStatement):
            if node.init is not None:
                self._execute(node.init)
            while node.condition is None or self._evaluate(node.condition):
                for statement in node.body:
                    self._execute(statement)
                if node.update is not None:
                    self._execute(node.update)
            return
        raise NotImplementedError(f"Cannot execute node: {node!r}")

    def _evaluate(self, node):
        if isinstance(node, StringLiteral):
            return node.value
        if isinstance(node, IntLiteral):
            return node.value
        if isinstance(node, FloatLiteral):
            return node.value
        if isinstance(node, BoolLiteral):
            return node.value
        if isinstance(node, Identifier):
            if node.name not in self.variables:
                raise EvansLangError(f"Undefined variable {node.name!r}")
            return self.variables[node.name]
        if isinstance(node, InputCall):
            return input(self._evaluate(node.prompt))
        if isinstance(node, ParseCall):
            return parse_as(self._evaluate(node.target), node.target_type)
        if isinstance(node, BinaryOp):
            left = self._evaluate(node.left)
            right = self._evaluate(node.right)
            if node.operator == "==":
                return left == right
            if node.operator == "!=":
                return left != right
            if node.operator == "&&":
                return bool(left) and bool(right)
            if node.operator == "||":
                return bool(left) or bool(right)
            if node.operator in ("<", "<=", ">", ">="):
                try:
                    if node.operator == "<":
                        return left < right
                    if node.operator == "<=":
                        return left <= right
                    if node.operator == ">":
                        return left > right
                    return left >= right
                except TypeError:
                    raise EvansLangError(
                        f"Cannot compare {type(left).__name__} with {type(right).__name__} using {node.operator!r}"
                    )
            if node.operator == "+":
                return left + right
            if node.operator == "-":
                return left - right
            if node.operator == "*":
                return left * right
            if node.operator == "/":
                if right == 0:
                    raise EvansLangError("Division by zero")
                if isinstance(left, int) and isinstance(right, int):
                    return left // right
                return left / right
            raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
        if isinstance(node, UnaryOp):
            if node.operator == "!":
                return not self._evaluate(node.operand)
            raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
        raise NotImplementedError(f"Cannot evaluate node: {node!r}")
