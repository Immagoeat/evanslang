from enum import Enum, auto


class OpCode(Enum):
    PUSH_CONST = auto()
    LOAD = auto()
    STORE = auto()
    PRINT = auto()
    HALT = auto()


class Instruction:
    def __init__(self, opcode: OpCode, operand=None):
        self.opcode = opcode
        self.operand = operand

    def __repr__(self):
        if self.operand is None:
            return f"{self.opcode.name}"
        return f"{self.opcode.name} {self.operand!r}"


class Program:
    def __init__(self, instructions: list[Instruction]):
        self.instructions = instructions
