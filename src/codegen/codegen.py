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

BINARY_OPCODES = {
    "==": OpCode.EQ,
    "+": OpCode.ADD,
    "-": OpCode.SUB,
    "*": OpCode.MUL,
    "/": OpCode.DIV,
}


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
        branches = [(node.condition, node.body), *node.elif_branches]

        # Build each conditional branch as [condition..., JUMP_IF_FALSE, body...,
        # JUMP] where JUMP skips to the very end (past all other branches and
        # the else body). The trailing JUMP is only needed when there's more
        # after this branch (another branch or an else); otherwise it's
        # omitted since falling through already reaches the end.
        branch_blocks: list[tuple[list[Instruction], list[Instruction]]] = []
        for condition, body in branches:
            cond_instrs = self._generate_expression(condition)
            body_instrs: list[Instruction] = []
            for statement in body:
                body_instrs.extend(self._generate_statement(statement))
            branch_blocks.append((cond_instrs, body_instrs))

        else_instrs: list[Instruction] = []
        if node.else_body is not None:
            for statement in node.else_body:
                else_instrs.extend(self._generate_statement(statement))

        has_trailer = len(branch_blocks) > 1 or node.else_body is not None

        result: list[Instruction] = []
        for i, (cond_instrs, body_instrs) in enumerate(branch_blocks):
            is_last_branch = i == len(branch_blocks) - 1
            needs_jump = has_trailer and not (is_last_branch and node.else_body is None)

            # JUMP_IF_FALSE skips the body (and the trailing JUMP if present).
            skip = len(body_instrs) + (1 if needs_jump else 0) + 1
            block = [*cond_instrs, Instruction(OpCode.JUMP_IF_FALSE, skip), *body_instrs]
            if needs_jump:
                block.append(Instruction(OpCode.JUMP, None))  # patched below
            result.append(block)

        # Patch each branch's trailing JUMP to skip past every remaining
        # branch/else block to the very end of the whole if/elseif/else chain.
        flat_lengths = [len(block) for block in result]
        for i, block in enumerate(result):
            if block and block[-1].opcode == OpCode.JUMP and block[-1].operand is None:
                remaining = sum(flat_lengths[i + 1 :]) + len(else_instrs)
                block[-1].operand = remaining + 1

        instructions: list[Instruction] = []
        for block in result:
            instructions.extend(block)
        instructions.extend(else_instrs)
        return instructions

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
            opcode = BINARY_OPCODES.get(node.operator)
            if opcode is None:
                raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
            return [
                *self._generate_expression(node.left),
                *self._generate_expression(node.right),
                Instruction(opcode),
            ]
        raise NotImplementedError(f"Cannot generate code for node: {node!r}")
