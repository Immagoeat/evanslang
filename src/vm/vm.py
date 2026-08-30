from ir.ir import OpCode
from ir.ir import Program as IrProgram
from utils.errors import EvansLangError


class VM:
    def __init__(self):
        self.stack = []
        self.variables = {}

    def run(self, program: IrProgram):
        for instruction in program.instructions:
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
            elif instruction.opcode == OpCode.HALT:
                return
            else:
                raise NotImplementedError(f"Unknown opcode: {instruction.opcode}")
