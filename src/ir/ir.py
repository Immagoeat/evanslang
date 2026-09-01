from enum import Enum, auto


class OpCode(Enum):
    PUSH_CONST = auto()
    LOAD = auto()
    STORE = auto()
    INPUT = auto()
    PARSE = auto()
    PRINT = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    NEG = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    JUMP_IF_FALSE = auto()
    JUMP = auto()
    CALL = auto()
    RETURN = auto()
    POP = auto()
    TRY_BEGIN = auto()
    TRY_END = auto()
    THROW = auto()
    ADDR_OF = auto()
    DEREF = auto()
    DEREF_STORE = auto()
    LIST_NEW = auto()
    INDEX_GET = auto()
    INDEX_SET = auto()
    LIST_APPEND = auto()
    LIST_LEN = auto()
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
