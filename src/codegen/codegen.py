from nodes.nodes import (
    Assignment,
    BinaryOp,
    Identifier,
    IfStatement,
    InputCall,
    IntLiteral,
    PrintStatement,
    StringLiteral,
    VarDecl,
)
from nodes.nodes import Program as AstProgram
from ir.ir import Instruction, OpCode
from ir.ir import Program as IrProgram


class CodeGenerator:
    def generate(self, program: AstProgram) -> IrProgram:
        instructions = []
        for statement in program.statements:
            instructions.extend(self._generate_statement(statement))
        instructions.append(Instruction(OpCode.HALT))
        return IrProgram(instructions)

    def _generate_statement(self, node) -> list[Instruction]:
        if isinstance(node, PrintStatement):
            return [
                *self._generate_expression(node.argument),
                Instruction(OpCode.PRINT),
            ]
        if isinstance(node, VarDecl):
            if node.value is None:
                return []
            return [
                *self._generate_expression(node.value),
                Instruction(OpCode.STORE, node.name),
            ]
        if isinstance(node, Assignment):
            return [
                *self._generate_expression(node.value),
                Instruction(OpCode.STORE, node.name),
            ]
        if isinstance(node, IfStatement):
            return self._generate_if(node)
        raise NotImplementedError(f"Cannot generate code for node: {node!r}")

    def _generate_if(self, node: IfStatement) -> list[Instruction]:
        condition = self._generate_expression(node.condition)
        body: list[Instruction] = []
        for statement in node.body:
            body.extend(self._generate_statement(statement))

        # Offset is relative to the JUMP_IF_FALSE instruction itself: skip
        # over the body (len(body)) plus the jump instruction (+1) to land
        # on whatever comes right after the if-block.
        jump_if_false = Instruction(OpCode.JUMP_IF_FALSE, len(body) + 1)
        return [*condition, jump_if_false, *body]

    def _generate_expression(self, node) -> list[Instruction]:
        if isinstance(node, StringLiteral):
            return [Instruction(OpCode.PUSH_CONST, node.value)]
        if isinstance(node, IntLiteral):
            return [Instruction(OpCode.PUSH_CONST, node.value)]
        if isinstance(node, Identifier):
            return [Instruction(OpCode.LOAD, node.name)]
        if isinstance(node, InputCall):
            return [
                *self._generate_expression(node.prompt),
                Instruction(OpCode.INPUT),
            ]
        if isinstance(node, BinaryOp):
            if node.operator != "==":
                raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
            return [
                *self._generate_expression(node.left),
                *self._generate_expression(node.right),
                Instruction(OpCode.EQ),
            ]
        raise NotImplementedError(f"Cannot generate code for node: {node!r}")
