from nodes.nodes import (
    AddressOf,
    AppendCall,
    AsciiStatement,
    Assignment,
    BinaryOp,
    BoolLiteral,
    CallStatement,
    Dereference,
    DerefAssignment,
    ExpressionStatement,
    FloatLiteral,
    ForStatement,
    Identifier,
    IfStatement,
    IndexAssignment,
    IndexExpr,
    InputCall,
    IntLiteral,
    LengthCall,
    ListDecl,
    ListLiteral,
    ParseCall,
    PrintStatement,
    StringLiteral,
    ThrowStatement,
    TryStatement,
    UnaryOp,
    VarDecl,
    WhileStatement,
)
from linker.linker import ResolvedProgram
from utils.errors import EvansLangError
from utils.runtime import (
    Cell,
    EvList,
    check_element_type,
    display,
    parse_as,
    render_ascii_art,
)


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

    def _store(self, name: str, value) -> None:
        cell = self.variables.get(name)
        if cell is None:
            self.variables[name] = Cell(value)
        else:
            # Reuse the existing Cell so a pointer taken via &x before this
            # assignment still observes the new value afterward.
            cell.value = value

    def _index(self, target, index):
        if not isinstance(target, list):
            raise EvansLangError("Cannot index a non-list value")
        if not isinstance(index, int) or isinstance(index, bool):
            raise EvansLangError(f"List index must be an int, got {type(index).__name__}")
        if index < 0 or index >= len(target):
            raise EvansLangError(f"List index {index} out of range (length {len(target)})")
        return target[index]

    def _index_set(self, target, index, value) -> None:
        if not isinstance(target, list):
            raise EvansLangError("Cannot index a non-list value")
        if not isinstance(index, int) or isinstance(index, bool):
            raise EvansLangError(f"List index must be an int, got {type(index).__name__}")
        if index < 0 or index >= len(target):
            raise EvansLangError(f"List index {index} out of range (length {len(target)})")
        target[index] = value

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
                self._store(node.name, self._evaluate(node.value))
            return
        if isinstance(node, Assignment):
            self._store(node.name, self._evaluate(node.value))
            return
        if isinstance(node, DerefAssignment):
            cell = self._evaluate(node.pointer)
            if not isinstance(cell, Cell):
                raise EvansLangError("Cannot dereference a non-pointer value")
            cell.value = self._evaluate(node.value)
            return
        if isinstance(node, ListDecl):
            self._store(
                node.name,
                self._evaluate(ListLiteral(node.elements, node.element_type)),
            )
            return
        if isinstance(node, IndexAssignment):
            target = self._evaluate(node.target)
            index = self._evaluate(node.index)
            value = self._evaluate(node.value)
            check_element_type(target, value, "assign")
            self._index_set(target, index, value)
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
        if isinstance(node, TryStatement):
            try:
                for statement in node.try_body:
                    self._execute(statement)
            except EvansLangError as error:
                self._store(node.catch_var_name, error.message)
                for statement in node.catch_body:
                    self._execute(statement)
            return
        if isinstance(node, ThrowStatement):
            value = self._evaluate(node.expression)
            if not isinstance(value, str):
                raise EvansLangError(
                    f"Cannot throw a {type(value).__name__} (expected str)"
                )
            raise EvansLangError(value)
        if isinstance(node, AsciiStatement):
            path = self._evaluate(node.path)
            if not isinstance(path, str):
                raise EvansLangError(
                    f"Cannot use a {type(path).__name__} as an ascii image path (expected str)"
                )
            print(render_ascii_art(path))
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
            return self.variables[node.name].value
        if isinstance(node, AddressOf):
            if node.name not in self.variables:
                raise EvansLangError(f"Undefined variable {node.name!r}")
            return self.variables[node.name]
        if isinstance(node, Dereference):
            cell = self._evaluate(node.operand)
            if not isinstance(cell, Cell):
                raise EvansLangError("Cannot dereference a non-pointer value")
            return cell.value
        if isinstance(node, ListLiteral):
            return EvList(
                (self._evaluate(element) for element in node.elements),
                node.element_type,
            )
        if isinstance(node, IndexExpr):
            target = self._evaluate(node.target)
            index = self._evaluate(node.index)
            return self._index(target, index)
        if isinstance(node, AppendCall):
            target = self._evaluate(node.target)
            if not isinstance(target, list):
                raise EvansLangError("Cannot call .append on a non-list value")
            value = self._evaluate(node.value)
            check_element_type(target, value, "append")
            target.append(value)
            return value
        if isinstance(node, LengthCall):
            target = self._evaluate(node.target)
            if not isinstance(target, list):
                raise EvansLangError("Cannot call .length on a non-list value")
            return len(target)
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
            if node.operator in ("+", "-", "*", "/"):
                if node.operator == "/" and right == 0:
                    raise EvansLangError("Division by zero")
                try:
                    if node.operator == "+":
                        return left + right
                    if node.operator == "-":
                        return left - right
                    if node.operator == "*":
                        return left * right
                    if isinstance(left, int) and isinstance(right, int):
                        return left // right
                    return left / right
                except TypeError:
                    raise EvansLangError(
                        f"Cannot apply {node.operator!r} to {type(left).__name__} and {type(right).__name__}"
                    )
            raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
        if isinstance(node, UnaryOp):
            if node.operator == "!":
                return not self._evaluate(node.operand)
            if node.operator == "-":
                value = self._evaluate(node.operand)
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise EvansLangError(f"Cannot negate a {type(value).__name__}")
                return -value
            raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
        raise NotImplementedError(f"Cannot evaluate node: {node!r}")
