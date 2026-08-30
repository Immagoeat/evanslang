from ir.ir import OpCode
from ir.ir import Program as IrProgram
from utils.errors import EvansLangError


class VM:
    def __init__(self):
        self.stack = []
        self.variables = {}

    def run(self, program: IrProgram):
        pc = 0
        instructions = program.instructions
        while pc < len(instructions):
            instruction = instructions[pc]
            if instruction.opcode == OpCode.PUSH_CONST:
                self.stack.append(instruction.operand)
            elif instruction.opcode == OpCode.STORE:
                self.variables[instruction.operand] = self.stack.pop()
            elif instruction.opcode == OpCode.LOAD:
                if instruction.operand not in self.variables:
                    raise EvansLangError(
                        f"Undefined variable {instruction.operand!r}"
                    )
                self.stack.append(self.variables[instruction.operand])
            elif instruction.opcode == OpCode.INPUT:
                prompt = self.stack.pop()
                self.stack.append(input(prompt))
            elif instruction.opcode == OpCode.PRINT:
                print(self.stack.pop())
            elif instruction.opcode == OpCode.EQ:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left == right)
            elif instruction.opcode == OpCode.NEQ:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left != right)
            elif instruction.opcode == OpCode.LT:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(self._compare(left, right, "<"))
            elif instruction.opcode == OpCode.LTE:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(self._compare(left, right, "<="))
            elif instruction.opcode == OpCode.GT:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(self._compare(left, right, ">"))
            elif instruction.opcode == OpCode.GTE:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(self._compare(left, right, ">="))
            elif instruction.opcode == OpCode.AND:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(bool(left) and bool(right))
            elif instruction.opcode == OpCode.OR:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(bool(left) or bool(right))
            elif instruction.opcode == OpCode.NOT:
                value = self.stack.pop()
                self.stack.append(not value)
            elif instruction.opcode == OpCode.ADD:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left + right)
            elif instruction.opcode == OpCode.SUB:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left - right)
            elif instruction.opcode == OpCode.MUL:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left * right)
            elif instruction.opcode == OpCode.DIV:
                right = self.stack.pop()
                left = self.stack.pop()
                if right == 0:
                    raise EvansLangError("Division by zero")
                self.stack.append(left // right)
            elif instruction.opcode == OpCode.JUMP_IF_FALSE:
                condition = self.stack.pop()
                if not condition:
                    pc += instruction.operand
                    continue
            elif instruction.opcode == OpCode.JUMP:
                pc += instruction.operand
                continue
            elif instruction.opcode == OpCode.HALT:
                return
            else:
                raise NotImplementedError(f"Unknown opcode: {instruction.opcode}")
            pc += 1

    def _compare(self, left, right, operator: str) -> bool:
        try:
            if operator == "<":
                return left < right
            if operator == "<=":
                return left <= right
            if operator == ">":
                return left > right
            return left >= right
        except TypeError:
            raise EvansLangError(
                f"Cannot compare {type(left).__name__} with {type(right).__name__} using {operator!r}"
            )
