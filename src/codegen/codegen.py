from nodes.nodes import (
    Assignment,
    Identifier,
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
        raise NotImplementedError(f"Cannot generate code for node: {node!r}")

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
        raise NotImplementedError(f"Cannot generate code for node: {node!r}")
