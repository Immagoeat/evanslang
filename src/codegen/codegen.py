from nodes.nodes import Identifier, IntLiteral, PrintStatement, StringLiteral, VarDecl
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
        raise NotImplementedError(f"Cannot generate code for node: {node!r}")
