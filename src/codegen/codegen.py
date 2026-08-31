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
from ir.ir import Instruction, OpCode
from ir.ir import Program as IrProgram
from linker.linker import SEPARATOR, ResolvedProgram
from utils.errors import EvansLangError

BINARY_OPCODES = {
    "==": OpCode.EQ,
    "!=": OpCode.NEQ,
    "<": OpCode.LT,
    "<=": OpCode.LTE,
    ">": OpCode.GT,
    ">=": OpCode.GTE,
    "&&": OpCode.AND,
    "||": OpCode.OR,
    "+": OpCode.ADD,
    "-": OpCode.SUB,
    "*": OpCode.MUL,
    "/": OpCode.DIV,
}

UNARY_OPCODES = {
    "!": OpCode.NOT,
}


class CodeGenerator:
    def generate(self, resolved: ResolvedProgram) -> IrProgram:
        # Compile every class body independently first (each ending in a
        # RETURN), then lay them out one after another and patch every CALL
        # to the absolute start index of its target class's block. The
        # program starts with a small prologue that calls "init" (if
        # present) then the entry class, and HALTs when that returns.
        class_blocks: dict[str, list[Instruction]] = {}
        for name, class_decl in resolved.classes.items():
            body_instrs: list[Instruction] = []
            for statement in class_decl.body:
                body_instrs.extend(self._generate_statement(statement))
            body_instrs.append(Instruction(OpCode.RETURN))
            class_blocks[name] = body_instrs

        prologue: list[Instruction] = []
        if "init" in class_blocks:
            prologue.append(Instruction(OpCode.CALL, "init"))
        prologue.append(Instruction(OpCode.CALL, resolved.entry))
        prologue.append(Instruction(OpCode.HALT))

        instructions: list[Instruction] = list(prologue)
        block_starts: dict[str, int] = {}
        for name, block in class_blocks.items():
            block_starts[name] = len(instructions)
            instructions.extend(block)

        for instruction in instructions:
            if instruction.opcode == OpCode.CALL:
                target = instruction.operand
                if target not in block_starts:
                    if SEPARATOR in target:
                        alias, name = target.split(SEPARATOR, 1)
                        raise EvansLangError(
                            f"{name!r} is not a mentionable class in the file "
                            f"mentioned as {alias!r} (mark it 'class {name}(ment) {{}}' "
                            f"to make it reachable, or check the class exists)"
                        )
                    raise EvansLangError(f"Call to undefined class {target!r}")
                instruction.operand = block_starts[target]

        return IrProgram(instructions)

    def _generate_statement(self, node) -> list[Instruction]:
        if isinstance(node, CallStatement):
            target = node.name if node.alias is None else f"{node.alias}{SEPARATOR}{node.name}"
            return [Instruction(OpCode.CALL, target)]
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
        if isinstance(node, WhileStatement):
            return self._generate_while(node)
        if isinstance(node, ForStatement):
            return self._generate_for(node)
        if isinstance(node, ExpressionStatement):
            return [
                *self._generate_expression(node.expression),
                Instruction(OpCode.POP),
            ]
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

    def _generate_while(self, node: WhileStatement) -> list[Instruction]:
        cond_instrs = self._generate_expression(node.condition)
        body_instrs: list[Instruction] = []
        for statement in node.body:
            body_instrs.extend(self._generate_statement(statement))

        # Layout: [condition..., JUMP_IF_FALSE <past body+JUMP>, body..., JUMP <back to condition>]
        jump_if_false = Instruction(OpCode.JUMP_IF_FALSE, len(body_instrs) + 2)
        jump_back = Instruction(
            OpCode.JUMP, -(len(cond_instrs) + 1 + len(body_instrs))
        )
        return [*cond_instrs, jump_if_false, *body_instrs, jump_back]

    def _generate_for(self, node: ForStatement) -> list[Instruction]:
        init_instrs = (
            self._generate_statement(node.init) if node.init is not None else []
        )
        cond_instrs = (
            self._generate_expression(node.condition)
            if node.condition is not None
            else [Instruction(OpCode.PUSH_CONST, True)]
        )
        update_instrs = (
            self._generate_statement(node.update) if node.update is not None else []
        )
        body_instrs: list[Instruction] = []
        for statement in node.body:
            body_instrs.extend(self._generate_statement(statement))

        # Layout: [init..., condition..., JUMP_IF_FALSE <past body+update+JUMP>,
        #          body..., update..., JUMP <back to condition>]
        jump_if_false = Instruction(
            OpCode.JUMP_IF_FALSE, len(body_instrs) + len(update_instrs) + 2
        )
        jump_back = Instruction(
            OpCode.JUMP,
            -(len(cond_instrs) + 1 + len(body_instrs) + len(update_instrs)),
        )
        return [
            *init_instrs,
            *cond_instrs,
            jump_if_false,
            *body_instrs,
            *update_instrs,
            jump_back,
        ]

    def _generate_expression(self, node) -> list[Instruction]:
        if isinstance(node, StringLiteral):
            return [Instruction(OpCode.PUSH_CONST, node.value)]
        if isinstance(node, IntLiteral):
            return [Instruction(OpCode.PUSH_CONST, node.value)]
        if isinstance(node, FloatLiteral):
            return [Instruction(OpCode.PUSH_CONST, node.value)]
        if isinstance(node, BoolLiteral):
            return [Instruction(OpCode.PUSH_CONST, node.value)]
        if isinstance(node, Identifier):
            return [Instruction(OpCode.LOAD, node.name)]
        if isinstance(node, InputCall):
            return [
                *self._generate_expression(node.prompt),
                Instruction(OpCode.INPUT),
            ]
        if isinstance(node, ParseCall):
            return [
                *self._generate_expression(node.target),
                Instruction(OpCode.PARSE),
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
        if isinstance(node, UnaryOp):
            opcode = UNARY_OPCODES.get(node.operator)
            if opcode is None:
                raise NotImplementedError(f"Unsupported operator: {node.operator!r}")
            return [
                *self._generate_expression(node.operand),
                Instruction(opcode),
            ]
        raise NotImplementedError(f"Cannot generate code for node: {node!r}")
